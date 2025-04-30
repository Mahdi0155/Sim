import os
import logging
import traceback
from datetime import timedelta
from PIL import Image, ImageDraw, ImageFont
import io

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackContext
)

# اطلاعات ربات
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405, 7827493126, 6039863213]

# مراحل گفتگو
WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(4)

# لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# post_init برای فعال‌سازی job_queue
async def post_init(application: Application):
    _ = application.job_queue

# تعریف ربات
application = Application.builder().token(TOKEN).post_init(post_init).build()

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return ConversationHandler.END
    await update.message.reply_text('سلام! لطفاً یک عکس یا ویدیو فوروارد کن.')
    return WAITING_FOR_MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return ConversationHandler.END

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = 'photo'
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = 'video'
    else:
        await update.message.reply_text('فقط عکس یا ویدیو قابل قبول است.')
        return WAITING_FOR_MEDIA

    context.user_data['file_id'] = file_id
    context.user_data['media_type'] = media_type

    await update.message.reply_text('لطفاً کپشن مورد نظر خود را بنویسید:')
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    final_caption = caption + "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = final_caption

    keyboard = ReplyKeyboardMarkup(
        [['ارسال در کانال', 'ارسال در آینده'], ['تنظیم واترمارک', 'حذف واترمارک'], ['برگشت به ابتدا']],
        resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        await update.message.reply_photo(file_id, caption=final_caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(file_id, caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

# ذخیره واترمارک جدید
async def set_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return

    if update.message.photo:
        watermark_file = update.message.photo[-1].file_id
        context.user_data['watermark'] = watermark_file
        await update.message.reply_text('واترمارک جدید ذخیره شد.')
    else:
        await update.message.reply_text('لطفاً یک عکس به عنوان واترمارک ارسال کنید.')

# حذف واترمارک
async def remove_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return

    if 'watermark' in context.user_data:
        del context.user_data['watermark']
        await update.message.reply_text('واترمارک حذف شد.')
    else:
        await update.message.reply_text('هیچ واترمارکی ذخیره نشده است.')

# اضافه کردن واترمارک به تصویر
def apply_watermark(image, watermark_file):
    img = Image.open(io.BytesIO(image))  # تبدیل عکس دریافتی به شیء تصویر
    watermark = Image.open(io.BytesIO(watermark_file))  # بارگذاری واترمارک

    # ابعاد تصویر اصلی و واترمارک
    img_width, img_height = img.size
    watermark_width, watermark_height = watermark.size

    # تنظیم موقعیت واترمارک (مثلاً در گوشه پایین راست)
    position = (img_width - watermark_width - 10, img_height - watermark_height - 10)

    # تنظیم شفافیت واترمارک
    watermark = watermark.convert("RGBA")
    watermark_with_opacity = watermark.copy()
    watermark_with_opacity.putalpha(128)  # 128 میزان شفافیت (50% opacity)

    # اعمال واترمارک روی تصویر
    img.paste(watermark_with_opacity, position, watermark_with_opacity)

    # بازگشت تصویر با واترمارک
    return img

# ارسال تصویر با واترمارک به کانال
async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    media_type = data['media_type']
    file_id = data['file_id']
    caption = data['caption']

    # بررسی وجود واترمارک
    watermark = data.get('watermark', None)

    # دانلود فایل و اعمال واترمارک
    if watermark:
        file = await context.bot.get_file(file_id)
        file_data = await file.download_as_bytearray()
        img = apply_watermark(file_data, watermark)

        # ذخیره تصویر با واترمارک
        output = io.BytesIO()
        img.save(output, format='PNG')
        output.seek(0)

        # ارسال تصویر به کانال
        await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=output, caption=caption)
    else:
        # بدون واترمارک، فقط ارسال عکس
        if media_type == 'photo':
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
        elif media_type == 'video':
            await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)

# ارسال پیام زمان‌بندی شده
async def send_scheduled(context: CallbackContext):
    try:
        data = context.job.data
        media_type = data['media_type']
        file_id = data['file_id']
        caption = data['caption']

        if media_type == 'photo':
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
        elif media_type == 'video':
            await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)
    except Exception as e:
        logger.error("خطا در send_scheduled:\n%s", traceback.format_exc())

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == 'ارسال در کانال':
        await send_to_channel(context)
        await update.message.reply_text('پیام ارسال شد. لطفاً مدیا بعدی را بفرستید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif text == 'ارسال در آینده':
        await update.message.reply_text('زمان ارسال (به دقیقه) را وارد کنید:', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    elif text == 'برگشت به ابتدا':
        await update.message.reply_text('لغو شد. لطفاً دوباره مدیا بفرستید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif text == 'تنظیم واترمارک':
        await update.message.reply_text('لطفاً واترمارک خود را ارسال کنید:')
        return WAITING_FOR_MEDIA  # منتظر دریافت واترمارک
    elif text == 'حذف واترمارک':
        await remove_watermark(update, context)
        return WAITING_FOR_MEDIA
    else:
        await update.message.reply_text('یکی از گزینه‌ها را انتخاب کنید.')
        return WAITING_FOR_ACTION

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        job_data = context.user_data.copy()

        context.job_queue.run_once(
            send_scheduled,
            when=timedelta(minutes=minutes),
            data=job_data
        )

        await update.message.reply_text(
            f'پیام برای {minutes} دقیقه بعد زمان‌بندی شد.\n\nلطفاً پیام بعدی را ارسال کنید.',
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_MEDIA
    except Exception as e:
        logger.error("خطا در handle_schedule:\n%s", traceback.format_exc())
        await update.message.reply_text('خطا در زمان‌بندی. فقط عدد وارد کنید یا دوباره تلاش کنید.')
        return WAITING_FOR_SCHEDULE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# اجرای اصلی
def main():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)],
            WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            WAITING_FOR_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
            WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    WEBHOOK_URL = 'https://sim-dtlp.onrender.com'

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
