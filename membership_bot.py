# File: membership_bot.py

import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN_MEMBERSHIP")
ADMINS = [6387942633]
CHANNEL_RULES = {  # {bot: [ (channel, expire_date or count_limit) ]}
    'uploader': [],
    'sender': []
}

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("دسترسی ندارید")
        return
    keyboard = [
        [InlineKeyboardButton("عضویت اجباری آپلودر", callback_data="set_uploader")],
        [InlineKeyboardButton("عضویت اجباری ارسال‌کننده", callback_data="set_sender")]
    ]
    await update.message.reply_text("انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("set_"):
        bot = query.data.split("_")[1]
        context.user_data['set_bot'] = bot
        await query.message.reply_text("لینک کانال را ارسال کنید:")

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.user_data.get('set_bot')
    if not bot:
        return
    text = update.message.text.strip()
    context.user_data['channel'] = text
    keyboard = [
        [InlineKeyboardButton("محدودیت بر اساس تعداد عضو", callback_data="limit_count")],
        [InlineKeyboardButton("محدودیت بر اساس زمان", callback_data="limit_time")],
    ]
    await update.message.reply_text("نوع محدودیت را انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "limit_count":
        context.user_data['limit_type'] = 'count'
        await query.message.reply_text("تعداد عضو مورد نظر را بفرست:")
    elif query.data == "limit_time":
        context.user_data['limit_type'] = 'time'
        await query.message.reply_text("تعداد روز معتبر بودن عضویت را بفرست:")

async def finalize_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.user_data.get('set_bot')
    channel = context.user_data.get('channel')
    limit_type = context.user_data.get('limit_type')
    value = update.message.text.strip()

    if limit_type == 'count':
        CHANNEL_RULES[bot].append((channel, int(value)))
    elif limit_type == 'time':
        expire_date = datetime.now() + timedelta(days=int(value))
        CHANNEL_RULES[bot].append((channel, expire_date))

    await update.message.reply_text("ذخیره شد")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_query))
application.add_handler(CallbackQueryHandler(handle_limit))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^@"), add_channel))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^[0-9]+$"), finalize_limit))

application.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    webhook_url='https://your-app-name.onrender.com/membership'
)
