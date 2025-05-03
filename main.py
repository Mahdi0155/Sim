import json
import uuid
import time
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# اطلاعات پایه
ADMIN_ID = 6387942633  # آیدی عددی ادمین
DATA_FILE = "files.json"

# بارگذاری فایل دیتابیس
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# دستور استارت
def start(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("سلام! برای دریافت فایل، از لینکی که دریافت کردید استفاده کنید.")
        return

    token = args[0]
    data = load_data()

    if token not in data:
        update.message.reply_text("فایل مورد نظر یافت نشد یا منقضی شده.")
        return

    file_id = data[token]["file_id"]
    file_type = data[token]["file_type"]

    if file_type == "photo":
        msg = update.message.reply_photo(file_id)
    elif file_type == "video":
        msg = update.message.reply_video(file_id)
    else:
        update.message.reply_text("خطا: نوع فایل پشتیبانی نمی‌شود.")
        return

    # حذف پیام بعد از ۲۰ ثانیه
    context.job_queue.run_once(lambda c: msg.delete(), 20)

# پنل ادمین
def panel(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    update.message.reply_text("فایل عکس یا ویدیو رو بفرست تا لینکش ساخته بشه.")

# دریافت فایل از ادمین
def handle_file(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    file = None
    file_type = None

    if update.message.photo:
        file = update.message.photo[-1]
        file_type = "photo"
    elif update.message.video:
        file = update.message.video
        file_type = "video"

    if not file:
        update.message.reply_text("فقط عکس یا ویدیو بفرست.")
        return

    file_id = file.file_id
    token = str(uuid.uuid4())[:8]

    data = load_data()
    data[token] = {
        "file_id": file_id,
        "file_type": file_type,
        "timestamp": time.time()
    }
    save_data(data)

    link = f"https://t.me/{context.bot.username}?start={token}"
    update.message.reply_text(f"لینک فایل آماده‌ست:\n{link}")

# شروع ربات
def main():
    TOKEN = "7413532622:AAGmb4UihdcGROnhhSVwTwz_0jy9DaovjWo"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("panel", panel))
    dp.add_handler(MessageHandler(Filters.photo | Filters.video, handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
