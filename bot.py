import os
import logging
import traceback
from datetime import timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

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

# محل واترمارک‌ها
WATERMARK_POSITIONS = {
    'A': (10, 10),
    'B': (10, 100),
    'C': (10, 200),
    'D': (100, 10),
    'E': (100, 100),
}

# تابع برای اعمال واترمارک روی تصویر
def apply_watermark(image_bytes, position='E'):
    try:
        # تبدیل بایت‌ها به تصویر
        image = Image.open(BytesIO(image_bytes))
        
        # استفاده از یک فونت پیش‌فرض
        font = ImageFont.load_default()
        draw = ImageDraw.Draw(image)
        
        # رنگ و شفافیت (opacity) واترمارک
        watermark_text = "Hottof"
        text_width, text_height = draw.textsize(watermark_text, font=font)
        text_position = WATERMARK_POSITIONS.get(position, (100, 100))  # موقعیت پیش‌فرض 'E'
        
        # اعمال رنگ سفید با حاشیه مشکی
        draw.text((text_position[0] + 2, text_position[1] + 2), watermark_text, font=font, fill="black")
        draw.text((text_position[0] - 2, text_position[1] - 2), watermark_text, font=font, fill="black")
        draw.text(text_position, watermark_text, font=font, fill="white")

        # تبدیل دوباره به بایت‌ها
        output = BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        print(f"Error applying watermark: {e}")
        return image_bytes  # اگر مشکلی بود، تصویر اصلی رو برمی‌گرداند


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

    # دانلود فایل عکس
    file = await context.bot.get_file(file_id)
    image_bytes = await file.download_as_bytearray()

    # اعمال واترمارک روی عکس
    watermarked_image = apply_watermark(image_bytes, 'E')  # انتخاب موقعیت پیش‌فرض E

    # ذخیره تصویر واترمارک‌دار در حافظه
    context.user_data['photo_bytes'] = watermarked_image

    await update.message.reply_text('لطفاً کپشن مورد نظر خود را بنویسید:')
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    final_caption = caption + "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = final_caption

    keyboard = ReplyKeyboardMarkup(
        [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']],
        resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        await update.message.reply_photo(context.user_data['photo_bytes'], caption=final_caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(file_id, caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

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

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    media_type = data['media_type']
    caption = data['caption']

    # استفاده از تصویر واترمارک‌دار که در حافظه ذخیره شده
    watermarked_image = data['photo_bytes']

    # ارسال تصویر واترمارک‌دار
    if media_type == 'photo':
        await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=watermarked_image, caption=caption)
    elif media_type == 'video':
        await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=watermarked_image, caption=caption)

    # بعد از ارسال، داده‌ها از حافظه پاک می‌شود
    del context.user_data['photo_bytes']

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
