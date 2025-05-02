import logging
import time
import json
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# تنظیمات اولیه
TOKEN = '7413532622:AAHTJUCRfKxehH7Qltb9pTkayakpjoLqQdk'  # توکن ربات خود را اینجا وارد کنید
ADMIN_IDS = [7189616405, 6387942633, 5459406429]  # آیدی ادمین‌ها
CHANNEL_TAG = "🔥@hottof | تُفِ داغ"
DB_FILE = "data.json"  # فایل ذخیره داده‌ها

# تنظیمات لاگینگ برای دیباگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# بارگذاری دیتابیس
def load_data():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# ذخیره دیتابیس
def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ارسال پیام به ادمین
def send_message(chat_id, text):
    bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

# دستور شروع
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('سلام! خوش آمدید.\nاز /panel برای دسترسی به پنل استفاده کنید.')

# دسترسی به پنل
def panel(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text('شما دسترسی به این پنل ندارید.')
        return
    update.message.reply_text("پنل مدیریتی:\n1. /super - ارسال محتوا (سوپر)\n2. /post - ارسال پست")

# حالت پست
def handle_post(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text('شما دسترسی به این پنل ندارید.')
        return
    
    # دریافت پیام فوروارد شده
    forwarded_message = update.message.forward_from
    caption = ' '.join(context.args)  # دریافت کپشن از کاربر
    
    # ارسال نتیجه به ادمین
    send_message(user_id, f"پست آماده شد:\n{caption}\n🔥@hottof | تُفِ داغ")
    send_message(user_id, f"پست فوروارد شده: {forwarded_message.text}\nکپشن: {caption}\n🔥@hottof | تُفِ داغ")

# حالت سوپر
def handle_super(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text('شما دسترسی به این پنل ندارید.')
        return

    file_id = update.message.video.file_id if update.message.video else update.message.document.file_id
    unique_id = f"v_{str(user_id)}_{str(hash(file_id))}"
    
    # ذخیره نام فایل در دیتابیس
    db = load_data()
    db[unique_id] = file_id
    save_data(db)
    
    # دریافت کپشن از کاربر
    caption = ' '.join(context.args)  # کپشن از کاربر
    
    # ساخت لینک مشاهده
    link = f"https://t.me/hottofbot?start={unique_id}"
    
    # ارسال لینک به ادمین
    caption_final = f"{caption}\n\n<a href='{link}'>مشاهده</a>\n🔥@hottof | تُفِ داغ"
    send_message(user_id, f"نتیجه نهایی آماده شد. شما می‌توانید لینک را در کانال خود قرار دهید.")
    send_message(user_id, caption_final)
    
    # نمایش نتیجه نهایی
    send_message(user_id, "لینک مشاهده آماده شد. این محتوا بعد از ۲۰ ثانیه از چت حذف خواهد شد.")
    
    # حذف پیام از چت کاربر بعد از ۲۰ ثانیه
    time.sleep(20)
    update.message.delete()

# راه اندازی ربات
def main():
    updater = Updater(TOKEN)

    # دستورات
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("panel", panel))
    dispatcher.add_handler(CommandHandler("super", handle_super))
    dispatcher.add_handler(CommandHandler("post", handle_post))

    # پیام‌های ورودی
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_post))
    dispatcher.add_handler(MessageHandler(Filters.video | Filters.document, handle_super))

    # شروع ربات
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
