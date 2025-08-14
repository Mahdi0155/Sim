import os
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
                      Message, ChatMember)
from telegram.constants import ParseMode
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          MessageHandler, CallbackQueryHandler, filters, ContextTypes)

from config import (
    BOT_TOKEN, WEBHOOK_SECRET, WEBHOOK_BASE, ADMIN_IDS, OWNER_ID,
    CHANNEL_UPLOAD_ID, DELETE_AFTER_SECONDS_DEFAULT, SELF_PING_INTERVAL_SECONDS,
    TZ_NAME
)
from db import (
    init_db, DBSession, User, FileBatch, FileItem, ForcedChannel, AdminUser,
    LinkHit, Setting, now_utc
)

import pytz
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

app = FastAPI()

# Telegram Application
telegram_app: Application | None = None

# Reply Keyboard (Admin Panel)
ADMIN_PANEL_KB = ReplyKeyboardMarkup(
    [["آپلود📂"], ["ارسال همگانی📩"], ["تنظیم کانال🔒"], ["آمار📊"], ["تنظیمات بیشتر"]],
    resize_keyboard=True
)

BACK_TO_PANEL_KB = ReplyKeyboardMarkup([["↩️ بازگشت به پنل"]], resize_keyboard=True)

# Upload state per admin
UPLOAD_STATE: Dict[int, Dict[str, Any]] = {}
MAX_UPLOAD = 20

# Helpers
TEHRAN_TZ = pytz.timezone(TZ_NAME)

def fmt_now_tz():
    dt = datetime.now(TEHRAN_TZ)
    return dt.strftime("%H:%M:%S"), dt.strftime("%Y/%m/%d")

async def is_admin(user_id: int) -> bool:
    async with DBSession() as s:
        au = await s.get(AdminUser, user_id)
        return (user_id in ADMIN_IDS) or (au is not None)

async def ensure_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# Forced membership check
async def user_in_channel(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> Optional[bool]:
    try:
        member: ChatMember = await ctx.bot.get_chat_member(chat_id, user_id)
        status = member.status
        return status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"get_chat_member failed for {chat_id}: {e}")
        return None  # unknown

async def check_forced_membership(ctx: ContextTypes.DEFAULT_TYPE, user_id: int) -> List[ForcedChannel]:
    """Return list of channels the user is NOT in yet (only those we can verify)."""
    async with DBSession() as s:
        chans = (await s.execute(ForcedChannel.select_all())).scalars().all()
    not_joined: List[ForcedChannel] = []
    for ch in chans:
        if ch.chat_id is None:
            # can't verify membership; still require by presenting it
            not_joined.append(ch)
            continue
        ok = await user_in_channel(ctx, ch.chat_id, user_id)
        if ok is False:
            not_joined.append(ch)
        elif ok is None:
            # verification failed; be safe and request join
            not_joined.append(ch)
    return not_joined

# Deep link helpers
DL_PREFIX = "dl_"

def make_deeplink(code: str, bot_username: str) -> str:
    return f"https://t.me/{bot_username}?start={DL_PREFIX}{code}"

# FastAPI models
class WebhookBody(BaseModel):
    update_id: Optional[int]

# Webhook endpoint
@app.post(f"/webhook/{{secret}}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)  # type: ignore
    await telegram_app.process_update(update)  # type: ignore
    return JSONResponse({"ok": True})

@app.get("/ping")
async def ping():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}

# Startup: DB + Telegram + Webhook + Self-ping
@app.on_event("startup")
async def on_startup():
    global telegram_app
    await init_db()
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    telegram_app.add_handler(CommandHandler("start", on_start))
    telegram_app.add_handler(CommandHandler("panel", on_panel))
    telegram_app.add_handler(CallbackQueryHandler(on_callback))
    telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_text))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.Audio.ALL | filters.Photo.ALL, on_media))

    await telegram_app.initialize()

    # Set webhook
    me = await telegram_app.bot.get_me()
    secret = WEBHOOK_SECRET
    url = f"{WEBHOOK_BASE}/webhook/{secret}"
    await telegram_app.bot.set_webhook(url, allowed_updates=["message", "callback_query"])
    logger.info("Webhook set to %s for @%s", url, me.username)

    # Start background self-ping
    asyncio.create_task(self_ping_loop())

async def self_ping_loop():
    base = WEBHOOK_BASE.rstrip('/')
    interval = max(60, SELF_PING_INTERVAL_SECONDS)
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                await client.get(f"{base}/ping")
                logger.info("self ping ok")
            except Exception as e:
                logger.warning(f"self ping failed: {e}")
            await asyncio.sleep(interval)
