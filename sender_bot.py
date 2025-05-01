# File: sender_bot.py

import os
import time
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN_SENDER")
CHANNELS = []
ADMINS = [6387942633]

# اتصال به دیتابیس
conn = sqlite3.connect('videos.db')
cursor = conn.cursor()

# ایجاد جدول در دیتابیس
cursor.execute('''CREATE TABLE IF NOT EXISTS videos
                  (file_name TEXT PRIMARY KEY, file_id TEXT, caption TEXT, cover_id TEXT, created DATETIME)''')
conn.commit()

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

    # بررسی ویدیو یا فایل از دیتابیس
    cursor.execute('SELECT * FROM videos WHERE file_name = ?', (file_key,))
    result = cursor.fetchone()
    if not result:
        await update.message.reply_text("این فایل منقضی شده یا وجود ندارد")
        return

    file_id, caption, cover_id, created = result[1], result[2], result[3], result[4]
    if time.time() - time.mktime(time.strptime(created, "%Y-%m-%d %H:%M:%S")) > 30:
        await update.message.reply_text("این لینک منقضی شده است")
        return

    # ارسال فایل ویدیو یا عکس
    if cover_id:
        await update.message.reply_photo(cover_id, caption=caption)
    else:
        await update.message.reply_video(file_id, caption=caption)

async def temp_share(file_type, file_id, caption):
    # ذخیره فایل در دیتابیس
    file_name = str(int(time.time()))  # استفاده از timestamp به عنوان نام فایل
    cover_id = None  # در صورت نیاز می‌توانید کاور را اضافه کنید.

    cursor.execute('''
    INSERT OR REPLACE INTO videos (file_name, file_id, caption, cover_id, created)
    VALUES (?, ?, ?, ?, ?)
    ''', (file_name, file_id, caption, cover_id, datetime.utcnow()))
    conn.commit()

    return file_name

def clear_expired():
    now = time.time()
    cursor.execute('SELECT file_name, created FROM videos')
    files = cursor.fetchall()
    for file in files:
        file_name, created = file
        if now - time.mktime(time.strptime(created, "%Y-%m-%d %H:%M:%S")) > 30:
            cursor.execute('DELETE FROM videos WHERE file_name = ?', (file_name,))
            conn.commit()

application.add_handler(CommandHandler("start", start))

application.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    webhook_url='https://your-app-name.onrender.com/sender'
)
