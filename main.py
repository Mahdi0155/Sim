import os
import json
import logging
import traceback
import threading
import time
import asyncio
from datetime import timedelta
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, CallbackContext, filters
)

# تنظیمات
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405]
DATA_FILE = "data.json"
WEBHOOK_URL = "https://sim-1-yqxq.onrender.com/webhook"

WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(4)

flask_app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

application = Application.builder().token(TOKEN).build()

# --- handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی ندارید.')
        return ConversationHandler.END
    await update.message.reply_text('سلام! لطفاً یک عکس یا ویدیو فوروارد کن.')
    return WAITING_FOR_MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return ConversationHandler.END

    if update.message.photo:
        context.user_data['file_id'] = update.message.photo[-1].file_id
        context.user_data['media_type'] = 'photo'
    elif update.message.video:
        context.user_data['file_id'] = update.message.video.file_id
        context.user_data['media_type'] = 'video'
    else:
        await update.message.reply_text('فقط عکس یا ویدیو قابل قبول است.')
        return WAITING_FOR_MEDIA

    await update.message.reply_text('لطفاً کپشن را وارد کنید:')
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    final_caption = caption + "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = final_caption

    keyboard = ReplyKeyboardMarkup(
        [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']],
        resize_keyboard=True
    )

    if context.user_data['media_type'] == 'photo':
        await update.message.reply_photo(context.user_data['file_id'], caption=final_caption, reply_markup=keyboard)
    else:
        await update.message.reply_video(context.user_data['file_id'], caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'ارسال در کانال':
        await send_to_channel(context)
        await update.message.reply_text('ارسال شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif text == 'ارسال در آینده':
        await update.message.reply_text('زمان به دقیقه را وارد کن:', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    elif text == 'برگشت به ابتدا':
        return WAITING_FOR_MEDIA
    else:
        return WAITING_FOR_ACTION

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        context.job_queue.run_once(
            send_scheduled,
            when=timedelta(minutes=minutes),
            data=context.user_data.copy()
        )
        await update.message.reply_text('زمان‌بندی شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    except Exception:
        await update.message.reply_text('خطا در زمان وارد شده.')
        return WAITING_FOR_SCHEDULE

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    if d['media_type'] == 'photo':
        await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=d['file_id'], caption=d['caption'])
    else:
        await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=d['file_id'], caption=d['caption'])

async def send_scheduled(context: CallbackContext):
    d = context.job.data
    try:
        if d['media_type'] == 'photo':
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=d['file_id'], caption=d['caption'])
        else:
            await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=d['file_id'], caption=d['caption'])
    except Exception as e:
        logger.error("Scheduled Error: %s", e)

async def uploadlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("دسترسی نداری.")
        return
    if not context.args:
        await update.message.reply_text("فرمت: /uploadlink name (با فایل)")
        return
    name = context.args[0]
    msg = update.message
    if msg.photo:
        file_id = msg.photo[-1].file_id
        media_type = "photo"
    elif msg.video:
        file_id = msg.video.file_id
        media_type = "video"
    else:
        await msg.reply_text("فقط عکس یا ویدیو.")
        return
    data[name] = {"file_id": file_id, "type": media_type}
    save_data(data)
    await msg.reply_text(f"فایل ذخیره شد.\nلینک: https://sim-1-yqxq.onrender.com/get/{name}")

# --- register handlers ---
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)],
        WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
        WAITING_FOR_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
        WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule)],
    },
    fallbacks=[]
))
application.add_handler(CommandHandler("uploadlink", uploadlink))

# --- Flask endpoint برای لینک دریافت فایل ---
@flask_app.route("/get/<name>", methods=["GET"])
def serve_file(name):
    user_id = request.args.get("user_id", type=int)
    if name not in data:
        return "فایل پیدا نشد.", 404
    file = data[name]
    bot = application.bot
    if user_id:
        msg = None
        if file["type"] == "photo":
            msg = bot.send_photo(chat_id=user_id, photo=file["file_id"])
        else:
            msg = bot.send_video(chat_id=user_id, video=file["file_id"])
        threading.Thread(target=lambda: (time.sleep(20), bot.delete_message(chat_id=user_id, message_id=msg.message_id))).start()
        return "ارسال شد"
    return "user_id لازم است", 400

# --- اجرای ربات و Flask همزمان ---
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

async def run_bot():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.updater.start_polling()  # اختیاری: فقط برای تست local

def main():
    threading.Thread(target=run_flask).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
