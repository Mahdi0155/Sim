# File: uploader_bot.py

import os
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN_UPLOADER")
CHANNELS = []
ADMINS = [6387942633]
VIDEOS = {}
USER_STATS = {}

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
    if not await check_membership(user_id):
        await update.message.reply_text("برای استفاده ابتدا عضو کانال‌ها شوید")
        return
    await update.message.reply_text("خوش آمدید، فایل مورد نظر را از طریق پنل آپلود دریافت کنید")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return
    keyboard = [
        [InlineKeyboardButton("آپلود", callback_data="upload")],
        [InlineKeyboardButton("آمار", callback_data="stats")],
        [InlineKeyboardButton("عضویت اجباری", callback_data="forcejoin")]
    ]
    await update.message.reply_text("پنل مدیریت", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()
    if data == "upload":
        context.user_data.clear()
        await query.message.reply_text("ویدیو را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
        context.user_data['uploading'] = True
    elif data == "stats":
        stats = USER_STATS.get(user_id, {"joined": 0, "today": 0, "week": 0, "month": 0})
        text = f"تعداد عضویت موفق: {stats['joined']}\nامروز: {stats['today']}\nهفته: {stats['week']}\nماه: {stats['month']}"
        await query.message.reply_text(text)
    elif data == "forcejoin":
        context.user_data['set_force'] = True
        await query.message.reply_text("آیدی کانال را بفرستید:")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('uploading'):
        file_id = update.message.video.file_id
        context.user_data['file_id'] = file_id
        context.user_data['file_name'] = str(int(time.time()))
        await update.message.reply_text("کپشن را ارسال کنید:")
        context.user_data['step'] = 'caption'
    elif context.user_data.get('step') == 'cover':
        cover_id = update.message.photo[-1].file_id if update.message.photo else None
        file_name = context.user_data['file_name']
        VIDEOS[file_name] = {
            'video': context.user_data['file_id'],
            'caption': context.user_data['caption'],
            'cover': cover_id,
            'created': datetime.utcnow()
        }
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("بازگشت", callback_data="panel")]
        ])
        await update.message.reply_photo(cover_id, caption=f"{context.user_data['caption']}\n\nمشاهده\n\n🔥@hottof | تُفِ داغ", reply_markup=btn)
        context.user_data.clear()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if context.user_data.get('step') == 'caption':
        context.user_data['caption'] = text
        context.user_data['step'] = 'cover'
        await update.message.reply_text("کاور (عکس) را ارسال کنید:")
    elif context.user_data.get('set_force'):
        CHANNELS.append(text)
        context.user_data.pop('set_force')
        await update.message.reply_text("کانال اضافه شد")

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "panel":
        await panel(update, context)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("panel", panel))
application.add_handler(CallbackQueryHandler(handle_buttons))
application.add_handler(CallbackQueryHandler(handle_query))
application.add_handler(MessageHandler(filters.VIDEO, handle_video))
application.add_handler(MessageHandler(filters.PHOTO, handle_video))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

application.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    webhook_url='https://your-app-name.onrender.com/uploader'
      )
