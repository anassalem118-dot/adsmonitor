"""
core/telegram_service.py
------------------------
ربط بوت تيليجرام من داخل المنصة:
  1) بتلصق توكن البوت  -> verify_bot() بيتأكد منه وبيرجع اسم البوت
  2) بتبعت /start للبوت -> detect_chat() بيلقط الـ chat id اوتوماتيك
  3) send_message()     -> بيبعت التنبيهات
"""
import asyncio
import html
from telegram import Bot
from .database import get_secret, get_setting


def _run(coro):
    return asyncio.run(coro)


async def _verify(token: str):
    async with Bot(token) as bot:
        return await bot.get_me()


def verify_bot(token: str) -> str:
    """بيرجع @username للبوت او بيرمي استثناء لو التوكن غلط."""
    me = _run(_verify(token))
    return f"@{me.username}"


async def _detect(token: str):
    async with Bot(token) as bot:
        updates = await bot.get_updates(timeout=0, limit=100)
    for u in reversed(updates):
        msg = u.effective_message
        if msg and u.effective_chat:
            chat = u.effective_chat
            title = chat.title or chat.full_name or chat.username or str(chat.id)
            return str(chat.id), title
    return None


def detect_chat(token: str):
    """بيرجع (chat_id, اسم) لاخر محادثة بعتت رسالة للبوت، او None."""
    return _run(_detect(token))


async def _send(token: str, chat_id: str, text: str):
    async with Bot(token) as bot:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",
                               disable_web_page_preview=True)


def send_message(text: str, token: str | None = None, chat_id: str | None = None) -> bool:
    token = token or get_secret("tg_token")
    chat_id = chat_id or get_setting("tg_chat_id")
    if not token or not chat_id:
        return False
    try:
        _run(_send(token, chat_id, text))
        return True
    except Exception:
        return False


def notify_alerts(alerts: list[dict], target) -> bool:
    if not alerts:
        return False
    icon = {"critical": "🔴", "warning": "🟠"}
    lines = [f"<b>تنبيهات اعلانات ميتا — {target}</b>"]
    for a in alerts:
        lines.append(f"{icon.get(a['severity'], '⚪')} <b>{html.escape(a['campaign_name'])}</b>\n"
                     f"   {html.escape(a['message'])}")
    ok, chunk = True, ""
    for line in lines:
        if len(chunk) + len(line) + 1 > 3800:
            ok &= send_message(chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk:
        ok &= send_message(chunk)
    return ok
