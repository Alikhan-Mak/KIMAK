"""
test_bot.py — Quick smoke-test for both Telegram bots.
Run:  python test_bot.py

Requires .env with:
  TELEGRAM_NOTIFY_TOKEN  (dispatcher bot)
  TELEGRAM_BOT_TOKEN     (citizen bot)
  DISPATCHER_CHAT_ID     (channel/group id, e.g. -1001234567890)
"""
import os, asyncio
from dotenv import load_dotenv

load_dotenv()

NOTIFY_TOKEN    = os.getenv("TELEGRAM_NOTIFY_TOKEN", "")
CITIZEN_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
DISPATCHER_ID   = os.getenv("DISPATCHER_CHAT_ID", "")

try:
    from telegram import Bot
except ImportError:
    print("❌  python-telegram-bot not installed.\n"
          "    Run: pip install python-telegram-bot")
    raise SystemExit(1)


async def test_dispatcher():
    """Send a mock P1 alert to the dispatcher channel."""
    if not NOTIFY_TOKEN:
        print("⚠️  TELEGRAM_NOTIFY_TOKEN not set — skipping dispatcher test")
        return
    if not DISPATCHER_ID:
        print("⚠️  DISPATCHER_CHAT_ID not set — skipping dispatcher test")
        return

    bot = Bot(token=NOTIFY_TOKEN)
    me = await bot.get_me()
    print(f"✅  Dispatcher bot connected: @{me.username}")

    msg = (
        "🔴 <b>[P1] SMART CITY ALMATY — TEST ALERT</b>\n"
        "📍 <b>Location:</b> Ауэзовский\n"
        "🕐 <b>Time:</b> TEST RUN\n"
        "📋 <b>Details:</b> Transformer T-07 thermal overload — 94% load. "
        "Cascade failure risk for 48,000 residents.\n\n"
        "<i>This is a test message from test_bot.py</i>"
    )
    await bot.send_message(chat_id=DISPATCHER_ID, text=msg, parse_mode="HTML")
    print(f"✅  Test P1 alert sent to chat {DISPATCHER_ID}")


async def test_citizen_bot_token():
    """Just verify the citizen bot token is valid (no message sent)."""
    if not CITIZEN_TOKEN:
        print("⚠️  TELEGRAM_BOT_TOKEN not set — skipping citizen bot test")
        return
    bot = Bot(token=CITIZEN_TOKEN)
    me = await bot.get_me()
    print(f"✅  Citizen bot connected: @{me.username}")
    print("    To test it: open Telegram, find the bot, send /start")


async def main():
    print("=" * 50)
    print("  Smart City Almaty — Bot Test")
    print("=" * 50)
    await test_dispatcher()
    await test_citizen_bot_token()
    print("=" * 50)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
