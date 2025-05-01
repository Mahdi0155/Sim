# File: sender_bot.py

import os
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN_SENDER")
CHANNELS = []
ADMINS = [6387942633]
TEMP_FILES = {}

application = Application.builder().token(TOKEN).build()

async def check_membership(user_id):
    for channel in CHANNELS:
        try:
            member = await application.bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            continue
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("درخواست نامعتبر")
        return
    file_key = args[0]
    if not await check_membership(user_id):
        await update.message.reply_text("برای دریافت فایل، ابتدا در کانال‌ها عضو شوید")
        return
    file = TEMP_FILES.get(file_key)
    if not file:
        await update.message.reply_text("این فایل منقضی شده یا وجود ندارد")
        return
    if file['type'] == 'video':
        await update.message.reply_video(file['id'], caption=file['caption'])
    elif file['type'] == 'photo':
        await update.message.reply_photo(file['id'], caption=file['caption'])
    del TEMP_FILES[file_key]

async def temp_share(file_type, file_id, caption):
    key = str(int(time.time()))
    TEMP_FILES[key] = {
        'type': file_type,
        'id': file_id,
        'caption': caption,
        'expires': time.time() + 30
    }
    return key

def clear_expired():
    now = time.time()
    expired = [k for k, v in TEMP_FILES.items() if v['expires'] < now]
    for k in expired:
        del TEMP_FILES[k]

application.add_handler(CommandHandler("start", start))

application.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    webhook_url='https://your-app-name.onrender.com/sender'
)
