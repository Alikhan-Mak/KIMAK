"""
Smart City Almaty — AI Backend
Flask + Claude API + Telegram Bots
"""
import os, json, logging, asyncio, functools, re
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv

# ── Telegram (optional) ──────────────────────────────────────────────────────
try:
    from telegram import Bot, Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    from apscheduler.schedulers.background import BackgroundScheduler
    TG_OK = True
except ImportError:
    TG_OK = False

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_NOTIFY_TOKEN = os.getenv("TELEGRAM_NOTIFY_TOKEN", "")   # dispatcher bot token
TELEGRAM_BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")      # citizen complaint bot token
DISPATCHER_CHAT_ID    = os.getenv("DISPATCHER_CHAT_ID", "")      # channel/group id (e.g. -1001234567890)
MODEL = "claude-opus-4-6"

app   = Flask(__name__, static_folder=".")
CORS(app)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM = """You are an AI assistant for the Smart City Almaty Management Dashboard.
Analyze infrastructure data and give specific, actionable recommendations.
Always name responsible parties, locations, and response times. Never vague advice.
Almaty districts: Алатауский, Турксибский, Жетысуский, Алмалинский,
Бостандыкский, Медеуский, Ауэзовский, Наурызбайский.
Incident priority: P1=casualties risk, P2=financial loss, P3=services disruption,
P4=environmental, P5=transport, P6=discomfort. Respond in English."""

# in-memory incident store (from citizen bot)
incidents: list[dict] = []


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def call_claude(prompt, max_tokens=1024, history=None):
    if not claude:
        return None, "ANTHROPIC_API_KEY not configured"
    msgs = list(history or [])
    msgs.append({"role": "user", "content": prompt})
    try:
        r = claude.messages.create(model=MODEL, max_tokens=max_tokens, system=SYSTEM, messages=msgs)
        return r.content[0].text.strip(), None
    except Exception as e:
        return None, str(e)

def parse_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"): t = t[4:]
    try:    return json.loads(t)
    except: return None


# ════════════════════════════════════════════════════════════
# AI ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    district = data.get("district", "Unknown")
    domain   = data.get("domain", "energy")
    metrics  = data.get("metrics", {})
    alerts   = data.get("alerts", [])

    prompt = f"""Analyze {district} district in Almaty. Domain: {domain.upper()}.
Metrics: {json.dumps(metrics)}
Alerts:  {json.dumps(alerts)}

Respond as JSON with keys "situation", "criticality", "actions":
- situation: factual summary
- criticality: P1–P6 level + justification
- actions: numbered steps with names, locations, ETAs"""

    text, err = call_claude(prompt)
    if err: return jsonify({"success": False, "error": err}), 500
    result = parse_json(text) or {"situation": text, "criticality": "See above", "actions": "See above"}
    return jsonify({"success": True, "analysis": result})


@app.route("/api/chat", methods=["POST"])
def chat():
    data     = request.json or {}
    district = data.get("district", "Unknown")
    history  = [{"role": h["role"], "content": h["content"]} for h in data.get("history", [])[-10:]]
    message  = data.get("message", "")

    if not claude:
        return jsonify({"success": False, "error": "ANTHROPIC_API_KEY not set"}), 503
    try:
        r = claude.messages.create(
            model=MODEL, max_tokens=512,
            system=f"{SYSTEM}\n\nContext: Analyzing {district} district.",
            messages=history + [{"role": "user", "content": message}]
        )
        return jsonify({"success": True, "response": r.content[0].text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/digest", methods=["GET"])
def digest():
    prompt = """Generate a Daily Digest for Almaty Smart City.
Current situation: Ауэзовский grid 94% (CRITICAL), Алмалинский water 2.1bar (CRITICAL),
Турксибский AQI 178 (WARNING), Медеуский tourism 95% (HIGH).

Return a JSON array of top 3 issues. Each: {"priority":"P1","title":"...","summary":"1-2 sentences with numbers"}"""
    text, err = call_claude(prompt, 512)
    if err: return jsonify({"success": False, "error": err}), 500
    issues = parse_json(text) or [{"priority": "P1", "title": "AI unavailable", "summary": text[:120]}]
    return jsonify({"success": True, "issues": issues})


@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    return jsonify({"success": True, "incidents": incidents[-50:]})


# ════════════════════════════════════════════════════════════
# STATIC FILES
# ════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# ════════════════════════════════════════════════════════════
# TELEGRAM — DISPATCHER NOTIFICATION BOT
# Sends P1/P2 alerts and weekly reports to dispatcher channel
# ════════════════════════════════════════════════════════════

def _build_alert_text(priority: str, location: str, description: str) -> str:
    emoji = {"P1": "🔴", "P2": "🟠", "P3": "🟡"}.get(priority, "⚪")
    return (
        f"{emoji} <b>[{priority}] SMART CITY ALMATY — ALERT</b>\n"
        f"📍 <b>Location:</b> {location}\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M, %d %b %Y')}\n"
        f"📋 <b>Details:</b> {description}\n\n"
        f"<i>Open dashboard for full AI analysis.</i>"
    )

def send_dispatcher_alert(priority: str, location: str, description: str):
    """Sync version — safe to call from non-async context (Flask routes, scheduler)."""
    if not (TG_OK and TELEGRAM_NOTIFY_TOKEN and DISPATCHER_CHAT_ID):
        log.info("[MOCK ALERT] %s @ %s: %s", priority, location, description)
        return
    text = _build_alert_text(priority, location, description)
    asyncio.run(Bot(token=TELEGRAM_NOTIFY_TOKEN).send_message(
        chat_id=DISPATCHER_CHAT_ID, text=text, parse_mode="HTML"
    ))

async def send_dispatcher_alert_async(priority: str, location: str, description: str):
    """Async version — safe to await from inside the bot event loop."""
    if not (TG_OK and TELEGRAM_NOTIFY_TOKEN and DISPATCHER_CHAT_ID):
        log.info("[MOCK ALERT] %s @ %s: %s", priority, location, description)
        return
    text = _build_alert_text(priority, location, description)
    await Bot(token=TELEGRAM_NOTIFY_TOKEN).send_message(
        chat_id=DISPATCHER_CHAT_ID, text=text, parse_mode="HTML"
    )


def send_weekly_report():
    """Scheduled every Monday 08:00 — structured district summary."""
    if not (TG_OK and TELEGRAM_NOTIFY_TOKEN and DISPATCHER_CHAT_ID):
        return
    report = (
        f"📊 <b>Weekly District Report — Smart City Almaty</b>\n"
        f"📅 {datetime.now().strftime('Week of %d %b %Y')}\n\n"
        "🔴 <b>Critical:</b> Ауэзовский — 3 P1 incidents this week\n"
        "🟡 <b>Watch:</b> Турксибский (AQI avg 142), Алмалинский (pipe repairs ongoing)\n"
        "🟢 <b>Stable:</b> Алатауский, Наурызбайский, Бостандыкский\n\n"
        "📈 City energy avg: 71% (+4% vs last week)\n"
        "💧 Water incidents: 7 (resolved: 6)\n"
        "🚗 Traffic peak: 8.4 — Алмалинский, Thu 08:15\n\n"
        "<i>Full report: http://your-dashboard-url/</i>"
    )
    async def _send():
        await Bot(token=TELEGRAM_NOTIFY_TOKEN).send_message(
            chat_id=DISPATCHER_CHAT_ID, text=report, parse_mode="HTML"
        )
    asyncio.run(_send())


# ════════════════════════════════════════════════════════════
# TELEGRAM — CITIZEN COMPLAINT BOT
# Receives free-text complaints, classifies with Claude,
# stores P1–P6 incidents, forwards P1–P2 to dispatcher
# ════════════════════════════════════════════════════════════

# Patterns for pre-flight checks (no AI needed)
_OBVIOUS_NON_COMPLAINT = re.compile(
    r'^\s*(hi+|hello+|hey+|привет|салем|сәлем|test|тест|check|проверка'
    r'|ok+|ок|start|старт|stop|стоп|help|помощь|thanks|спасибо'
    r'|good\s*(morning|day|evening)|доброе?\s*(утро|день|вечер)'
    r'|\?+|\.+|!+)\s*$',
    re.IGNORECASE
)

_LOCATION_PATTERN = re.compile(
    r'(ул\.|улица|avenue|ave\.?|проспект|пр\.|мкр\.?|микрорайон|район|district'
    r'|квартал|street|str\.|köшесі|даңғылы'
    r'|алатауск|турксибск|жетысуск|алмалинск|ауэзовск|бостандыкск|медеуск|наурызбайск'
    r'|абай|достык|фурманов|сейфуллин|аль.?фараби|момышулы|рыскулов|байзаков'
    r'|саяхат|сайран|самал|орбита|тастак|калкаман|шанырак|акбулак|алгабас'
    r'|\d+\s*(дом|д\.|үй|building|bld))',
    re.IGNORECASE
)

_RESPONSE_A = (
    "Complaint not accepted.\n\n"
    "Please include:\n"
    "- What the problem is\n"
    "- Where it is (street, district, or neighborhood)\n\n"
    "Example: No water on Abay Ave, Almaly district\n\n"
    "Try again with more details."
)

_RESPONSE_A_UNAVAILABLE = (
    "Service temporarily unavailable, please try again."
)

_CLASSIFY_TIMEOUT = 5.0  # seconds


def _looks_like_non_complaint(text: str) -> bool:
    """True for obvious greetings/spam that don't need AI."""
    return bool(_OBVIOUS_NON_COMPLAINT.match(text))


def _has_location(text: str) -> bool:
    """True if the text contains any location hint."""
    return bool(_LOCATION_PATTERN.search(text))


def _find_duplicate(district: str, summary: str) -> dict | None:
    """Return an existing incident if same district+summary submitted within 10 min."""
    cutoff = datetime.now() - timedelta(minutes=10)
    for inc in reversed(incidents):
        try:
            ts = datetime.fromisoformat(inc["timestamp"])
        except (ValueError, KeyError):
            continue
        if ts < cutoff:
            break  # list is append-only, older entries won't match either
        if (inc.get("district") == district
                and inc.get("summary", "")[:50].lower() == summary[:50].lower()):
            return inc
    return None


async def bot_start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Smart City Almaty — Complaint Bot\n\n"
        "Send me your complaint and I will classify it and forward it to city operators.\n\n"
        "Examples:\n"
        "  No water on Abay Ave, Almaly district\n"
        "  Gas smell near Seifullin Ave 42\n"
        "  Traffic light broken at Furmanov/Abai crossing\n\n"
        "Always include WHAT the problem is and WHERE it is."
    )


_executor = ThreadPoolExecutor(max_workers=4)


async def bot_complaint(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    user_text = (update.message.text or "").strip()
    username  = update.effective_user.username or f"user_{update.effective_user.id}"

    # ── Fast-path reject: obvious non-complaint ───────────────────────────
    if _looks_like_non_complaint(user_text) or len(user_text) < 8:
        await update.message.reply_text(_RESPONSE_A)
        return

    # ── Fast-path reject: no location hint ───────────────────────────────
    if not _has_location(user_text):
        await update.message.reply_text(_RESPONSE_A)
        return

    # ── AI unavailable ────────────────────────────────────────────────────
    if not claude:
        await update.message.reply_text(_RESPONSE_A_UNAVAILABLE)
        return

    await update.message.reply_text("Classifying your complaint...")

    prompt = (
        f'Classify this citizen complaint from Almaty, Kazakhstan.\n\n'
        f'Complaint: "{user_text}"\n\n'
        'Respond ONLY with valid JSON, no extra text:\n'
        '{\n'
        '  "priority": "P3",\n'
        '  "district": "Алмалинский",\n'
        '  "category": "utilities",\n'
        '  "summary": "one-sentence summary",\n'
        '  "is_actionable": true\n'
        '}\n\n'
        'Priority: P1=human safety risk, P2=financial loss, P3=service disruption, '
        'P4=environmental, P5=transport, P6=minor discomfort.\n'
        'Districts: Алатауский, Турксибский, Жетысуский, Алмалинский, '
        'Бостандыкский, Медеуский, Ауэзовский, Наурызбайский.\n'
        'Set is_actionable=false ONLY for spam or messages with no discernible issue.'
    )

    # ── Classify with hard 5-second timeout ──────────────────────────────
    loop = asyncio.get_event_loop()
    try:
        classify_task = loop.run_in_executor(
            _executor, functools.partial(call_claude, prompt, 250)
        )
        text, err = await asyncio.wait_for(classify_task, timeout=_CLASSIFY_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("bot_complaint: AI classification timed out for user %s", username)
        await update.message.reply_text(_RESPONSE_A_UNAVAILABLE)
        return
    except Exception as e:
        log.error("bot_complaint executor error: %s", e)
        await update.message.reply_text(_RESPONSE_A_UNAVAILABLE)
        return

    if err or not text:
        log.error("bot_complaint Claude error: %s", err)
        await update.message.reply_text(_RESPONSE_A_UNAVAILABLE)
        return

    cl = parse_json(text)
    if not cl or not cl.get("is_actionable", True):
        await update.message.reply_text(_RESPONSE_A)
        return

    priority = cl.get("priority", "P6")
    district = cl.get("district", "Unknown")
    summary  = cl.get("summary", user_text[:100])
    p_num    = int(priority[1]) if len(priority) == 2 and priority[1].isdigit() else 6

    # ── Duplicate check ───────────────────────────────────────────────────
    dup = _find_duplicate(district, summary)
    if dup:
        await update.message.reply_text(
            f"This complaint is already registered as #INC-{dup['id']:04d}. "
            "No duplicate created."
        )
        return

    # ── Save incident (P1–P6 all accepted) ───────────────────────────────
    incident = {
        "id":        len(incidents) + 1,
        "source":    "telegram_citizen",
        "username":  username,
        "text":      user_text,
        "priority":  priority,
        "district":  district,
        "category":  cl.get("category", "other"),
        "summary":   summary,
        "timestamp": datetime.now().isoformat(),
    }
    incidents.append(incident)
    log.info("Citizen incident [%s] %s: %s", priority, district, summary)

    # ── Forward P1–P2 to dispatcher ───────────────────────────────────────
    if p_num <= 2:
        await send_dispatcher_alert_async(priority, district, f"[CITIZEN REPORT] {summary}")

    # ── Response B ────────────────────────────────────────────────────────
    await update.message.reply_text(
        f"Complaint received\n\n"
        f"Priority: {priority}\n"
        f"District: {district}\n"
        f"Issue: {summary}\n\n"
        f"Forwarded to city operators. Reference #INC-{incident['id']:04d}"
    )


def run_citizen_bot():
    """Citizen complaint bot — runs in background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", bot_start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_complaint))
    log.info("🤖 Citizen complaint bot started (polling)")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)


# ════════════════════════════════════════════════════════════
# STARTUP
# ════════════════════════════════════════════════════════════

def start_telegram():
    if not TG_OK:
        log.info("Telegram not installed. Run: pip install python-telegram-bot apscheduler")
        return
    if not TELEGRAM_NOTIFY_TOKEN or not TELEGRAM_BOT_TOKEN:
        log.info("Telegram tokens not set in .env — bots disabled")
        return

    # Weekly report scheduler (Monday 08:00)
    sched = BackgroundScheduler()
    sched.add_job(send_weekly_report, "cron", day_of_week="mon", hour=8, minute=0)
    sched.start()
    log.info("📅 Weekly report scheduled every Monday 08:00")

    # Citizen bot in background thread
    Thread(target=run_citizen_bot, daemon=True).start()


if __name__ == "__main__":
    start_telegram()
    print("=" * 55)
    print("  🏙️  Smart City Almaty — Backend")
    print(f"  Claude API     : {'✅' if ANTHROPIC_API_KEY else '❌ set ANTHROPIC_API_KEY'}")
    print(f"  Dispatcher Bot : {'✅' if TELEGRAM_NOTIFY_TOKEN else '❌ set TELEGRAM_NOTIFY_TOKEN'}")
    print(f"  Citizen Bot    : {'✅' if TELEGRAM_BOT_TOKEN else '❌ set TELEGRAM_BOT_TOKEN'}")
    print(f"  Dashboard      : http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
