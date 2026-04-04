"""
Smart City Almaty — AI Backend
Flask + Claude API + Telegram Citizen Complaint Bot
"""
import os, json, logging, asyncio
from threading import Thread
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TG_OK = True
except ImportError:
    TG_OK = False

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MODEL = "claude-opus-4-6"

app    = Flask(__name__, static_folder=".")
CORS(app)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM = """You are an AI assistant for the Smart City Almaty Management Dashboard.
Analyze infrastructure data and give specific, actionable recommendations.
Always name responsible parties, locations, and response times. Never vague advice.
Almaty districts: Алатауский, Турксибский, Жетысуский, Алмалинский,
Бостандыкский, Медеуский, Ауэзовский, Наурызбайский.
Incident priority: P1=casualties risk, P2=financial loss, P3=services disruption,
P4=environmental, P5=transport, P6=discomfort. Respond in Russian."""

# File-backed incident store
INCIDENTS_FILE = os.path.join(os.path.dirname(__file__), "incidents.json")

def _load_incidents() -> list[dict]:
    try:
        with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def _save_incidents():
    with open(INCIDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(incidents, f, ensure_ascii=False, indent=2)

incidents: list[dict] = _load_incidents()


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def call_claude(prompt: str, max_tokens: int = 1024, history: list = None):
    if not claude:
        return None, "ANTHROPIC_API_KEY not configured"
    msgs = list(history or [])
    msgs.append({"role": "user", "content": prompt})
    try:
        r = claude.messages.create(model=MODEL, max_tokens=max_tokens, system=SYSTEM, messages=msgs)
        return r.content[0].text.strip(), None
    except Exception as e:
        return None, str(e)


def parse_json(text: str) -> dict | list | None:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        return None


# ════════════════════════════════════════════════════════════
# AI ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data     = request.json or {}
    district = data.get("district", "Unknown")
    domain   = data.get("domain", "energy")
    metrics  = data.get("metrics", {})
    alerts   = data.get("alerts", [])

    prompt = (
        f"Analyze {district} district in Almaty. Domain: {domain.upper()}.\n"
        f"Metrics: {json.dumps(metrics)}\n"
        f"Alerts:  {json.dumps(alerts)}\n\n"
        "Respond as JSON with keys \"situation\", \"criticality\", \"actions\":\n"
        "- situation: factual summary\n"
        "- criticality: P1–P6 level + justification\n"
        "- actions: numbered steps with names, locations, ETAs"
    )
    text, err = call_claude(prompt)
    if err:
        return jsonify({"success": False, "error": err}), 500
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
    prompt = (
        "Generate a Daily Digest for Almaty Smart City.\n"
        "Current situation: Ауэзовский grid 94% (CRITICAL), Алмалинский water 2.1bar (CRITICAL),\n"
        "Турксибский AQI 178 (WARNING), Медеуский tourism 95% (HIGH).\n\n"
        'Return a JSON array of top 3 issues. Each: {"priority":"P1","title":"...","summary":"1-2 sentences with numbers"}'
    )
    text, err = call_claude(prompt, 512)
    if err:
        return jsonify({"success": False, "error": err}), 500
    issues = parse_json(text) or [{"priority": "P1", "title": "AI unavailable", "summary": text[:120]}]
    return jsonify({"success": True, "issues": issues})


@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    return jsonify({"success": True, "incidents": incidents[-50:]})


@app.route("/api/incidents/<int:incident_id>", methods=["DELETE"])
def delete_incident(incident_id):
    for i, inc in enumerate(incidents):
        if inc.get("id") == incident_id:
            incidents.pop(i)
            _save_incidents()
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404


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
# TELEGRAM — CITIZEN COMPLAINT BOT
# ════════════════════════════════════════════════════════════

_MSG_WELCOME = (
    "Smart City Алматы — Бот жалоб\n\n"
    "Отправьте вашу жалобу, и городские операторы будут уведомлены."
)


async def bot_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_MSG_WELCOME)


async def bot_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    text     = (update.message.text or "").strip()
    username = update.effective_user.username or f"id{update.effective_user.id}"

    incident = {
        "id":        len(incidents) + 1,
        "source":    "telegram",
        "username":  username,
        "text":      text,
        "timestamp": datetime.now().isoformat(),
    }
    incidents.append(incident)
    _save_incidents()
    log.info("Incident #%d from %s: %s", incident["id"], username, text[:80])

    await update.message.reply_text(
        f"Жалоба принята.\nНомер обращения: #INC-{incident['id']:04d}"
    )


def run_citizen_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", bot_start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_message))
    log.info("Citizen complaint bot started (polling)")
    bot_app.run_polling(allowed_updates=Update.ALL_TYPES)


# ════════════════════════════════════════════════════════════
# STARTUP
# ════════════════════════════════════════════════════════════

def start_telegram():
    if not TG_OK:
        log.info("Telegram not installed. Run: pip install python-telegram-bot")
        return
    if not TELEGRAM_BOT_TOKEN:
        log.info("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return
    Thread(target=run_citizen_bot, daemon=True).start()


if __name__ == "__main__":
    start_telegram()
    print("=" * 55)
    print("  Smart City Almaty — Backend")
    print(f"  Claude API   : {'OK' if ANTHROPIC_API_KEY else 'MISSING — set ANTHROPIC_API_KEY'}")
    print(f"  Citizen Bot  : {'OK' if TELEGRAM_BOT_TOKEN else 'MISSING — set TELEGRAM_BOT_TOKEN'}")
    print(f"  Dashboard    : http://localhost:5000")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
