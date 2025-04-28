import logging
import json
import os
from uuid import uuid4
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

# اطلاعات حساس
TOKEN = "7086274656:AAEkxL0Xwktb_PVddppdNZ8S88ggGNpRMqI"
ADMINS = [6387942633, 6039863213]
DATA_FILE = 'files.json'

# استیج‌های گفتگو
WAITING_FOR_FILE, WAITING_FOR_CAPTION, WAITING_FOR_COVER = range(3)

# لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# بارگذاری داده‌ها
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

# ذخیره داده‌ها
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

data = load_data()

# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMINS:
        await update.message.reply_text("سلام ادمین عزیز! برای ورود به پنل دستور /panel را وارد کنید.")
    else:
        await update.message.reply_text("خوش آمدید!")

# پنل ادمین
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return

    keyboard = [
        [InlineKeyboardButton("آپلود فایل", callback_data="upload_file")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("پنل ادمین:", reply_markup=reply_markup)

# شروع آپلود فایل
async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "upload_file":
        await query.message.reply_text("لطفاً عکس یا ویدیو مورد نظر را ارسال کنید (حداکثر ۲۰۰ مگابایت).")
        return WAITING_FOR_FILE

# دریافت فایل
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.photo[-1] if update.message.photo else update.message.video

    if not file:
        await update.message.reply_text("فقط عکس یا ویدیو مجاز است!")
        return WAITING_FOR_FILE

    file_size = file.file_size
    if file_size > 200 * 1024 * 1024:
        await update.message.reply_text("فایل بزرگتر از ۲۰۰ مگابایت است!")
        return WAITING_FOR_FILE

    context.user_data['file_id'] = file.file_id
    await update.message.reply_text("حالا کپشن فایل را وارد کنید:")
    return WAITING_FOR_CAPTION

# دریافت کپشن
async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['caption'] = update.message.text
    await update.message.reply_text("حالا کاور فایل را ارسال کنید (یک عکس):")
    return WAITING_FOR_COVER

# دریافت کاور
async def receive_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفاً فقط عکس بفرستید.")
        return WAITING_FOR_COVER

    cover_file_id = update.message.photo[-1].file_id
    file_id = context.user_data['file_id']
    caption = context.user_data['caption']

    # ساخت شناسه اختصاصی
    unique_id = str(uuid4())

    # ذخیره داده
    data[unique_id] = {
        'file_id': file_id,
        'caption': caption,
        'cover_id': cover_file_id
    }
    save_data(data)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={unique_id}"

    await update.message.reply_text(f"فایل با موفقیت ذخیره شد!\n\nلینک اختصاصی:\n{link}")

    return ConversationHandler.END

# مدیریت لینک اختصاصی
async def handle_start_with_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        return

    file_code = args[0]
    if file_code not in data:
        await update.message.reply_text("فایل مورد نظر یافت نشد.")
        return

    file_info = data[file_code]
    keyboard = [
        [InlineKeyboardButton("مشاهده فایل", url=f"https://t.me/{(await context.bot.get_me()).username}?start={file_code}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=file_info['cover_id'],
        caption=file_info['caption'],
        reply_markup=reply_markup
    )

    # بعد از کاور، فایل اصلی هم میفرسته
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_info['file_id'],
        caption=file_info['caption']
    )

# کنسل کردن گفتگو
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

# ران کردن
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(panel_callback)],
        states={
            WAITING_FOR_FILE: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_file)],
            WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT, receive_caption)],
            WAITING_FOR_COVER: [MessageHandler(filters.PHOTO, receive_cover)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('panel', panel))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.ALL, handle_start_with_id))

    app.run_polling()

if __name__ == '__main__':
    main()
