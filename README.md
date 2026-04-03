# Smart City Almaty — Setup Guide

## File Structure
```
index.html   ← main dashboard (open this in browser)
style.css    ← light theme styles
script.js    ← map, charts, AI logic
app.py       ← Python backend (Claude API)
.env         ← your secrets (create this)
```

---

## Quick Start (no backend)
Just open `index.html` in your browser. Everything works with mock data.

---

## Step 1 — Install Python dependencies

```bash
pip install flask flask-cors anthropic python-dotenv
```

Or create `requirements.txt`:
```
flask
flask-cors
anthropic
python-dotenv
```
Then `pip install -r requirements.txt`

---

## Step 2 — Get Claude API Key

1. Go to **https://console.anthropic.com**
2. Sign up / log in
3. Click **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)

---

## Step 3 — Create `.env` file

In the project folder, create a file named `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> ⚠️ Never commit `.env` to git. Add it to `.gitignore`.

---

## Step 4 — Run the backend

```bash
python app.py
```

Output:
```
==================================================
  Smart City Almaty — Backend
  Claude API : ✅ Ready
  Dashboard  : http://localhost:5000
==================================================
```

Open **http://localhost:5000** in your browser.

---

## Step 5 — Connect Claude to the frontend

When `app.py` is running, the dashboard automatically calls:
- `POST /api/analyze` — district AI analysis
- `POST /api/chat` — follow-up chat
- `GET /api/digest` — daily digest

If the backend is **not** running, the dashboard falls back to built-in mock responses automatically.

---

## Step 6 — Telegram Bots (optional, add later)

### Create bots via BotFather

1. Open Telegram, search **@BotFather**
2. Send `/newbot`
3. Follow prompts, get a token like `7123456789:AAF...`

Create **two bots**:
- **Dispatcher Bot** — sends P1/P2 alerts to your team channel
- **Citizen Bot** — receives citizen complaints

Add to `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
TELEGRAM_NOTIFY_TOKEN=7123456789:AAF_dispatcher_token
TELEGRAM_BOT_TOKEN=7987654321:AAF_citizen_token
DISPATCHER_CHAT_ID=-1001234567890
```

Install Telegram library:
```bash
pip install python-telegram-bot apscheduler
```

To get `DISPATCHER_CHAT_ID`: add your dispatcher bot to a channel/group, send a message, then visit:
```
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```
Look for `"chat":{"id": ...}` in the response.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Map doesn't load | Check internet connection (needs CartoDB tiles) |
| Charts spin forever | Click a different tab then back — or refresh |
| `ANTHROPIC_API_KEY not set` | Check your `.env` file and restart `python app.py` |
| Port 5000 in use | `python app.py` — change `port=5000` to `port=5001` in app.py |
| CORS error in browser | Make sure `flask-cors` is installed |
