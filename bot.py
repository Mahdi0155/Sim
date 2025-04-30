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
WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE, WAITING_FOR_WATERMARK = range(5)

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
        [['ارسال در کانال', 'ارسال در آینده'], ['اضافه کردن واترمارک', 'برگشت به ابتدا']],
        resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        await update.message.reply_photo(file_id, caption=final_caption, reply_markup=keyboard)
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
    elif text == 'اضافه کردن واترمارک':
        await update.message.reply_text('لطفاً محل قرارگیری واترمارک را انتخاب کنید: A, B, C, D, E')
        return WAITING_FOR_WATERMARK
    elif text == 'برگشت به ابتدا':
        await update.message.reply_text('لغو شد. لطفاً دوباره مدیا بفرستید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    else:
        await update.message.reply_text('یکی از گزینه‌ها را انتخاب کنید.')
        return WAITING_FOR_ACTION

async def handle_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watermark_position = update.message.text.strip().upper()

    if watermark_position not in ['A', 'B', 'C', 'D', 'E']:
        await update.message.reply_text('لطفاً یکی از گزینه‌های معتبر (A, B, C, D, E) را وارد کنید.')
        return WAITING_FOR_WATERMARK

    context.user_data['watermark_position'] = watermark_position

    await update.message.reply_text('واترمارک اضافه شد. اکنون لطفاً گزینه‌های بعدی را انتخاب کنید.', reply_markup=ReplyKeyboardRemove())
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
    file_id = data['file_id']
    caption = data['caption']
    watermark_position = data.get('watermark_position', 'E')

    # Apply watermark to the image/video
    file = await context.bot.get_file(file_id)
    file_path = await file.download()

    if media_type == 'photo':
        image = Image.open(file_path)
        image = apply_watermark(image, watermark_position)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_byte_arr, caption=caption)
    elif media_type == 'video':
        await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_path, caption=caption)

async def send_scheduled(context: CallbackContext):
    try:
        data = context.job.data
        media_type = data['media_type']
        file_id = data['file_id']
        caption = data['caption']
        watermark_position = data.get('watermark_position', 'E')

        # Apply watermark to the image/video
        file = await context.bot.get_file(file_id)
        file_path = await file.download()

        if media_type == 'photo':
            image = Image.open(file_path)
            image = apply_watermark(image, watermark_position)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_byte_arr, caption=caption)
        elif media_type == 'video':
            await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_path, caption=caption)
    except Exception as e:
        logger.error("خطا در send_scheduled:\n%s", traceback.format_exc())

def apply_watermark(image: Image, position: str) -> Image:
    watermark_text = "تُفِ داغ"
    opacity = 100  # می‌توان میزان شفافیت را تغییر داد
    font = ImageFont.load_default()
    draw = ImageDraw.Draw(image, 'RGBA')

    text_width, text_height = draw.textsize(watermark_text, font=font)
    width, height = image.size

    # موقعیت قرارگیری واترمارک
    if position == 'A':
        x, y = 10, 10
    elif position == 'B':
        x, y = width - text_width - 10, 10
    elif position == 'C':
        x, y = width - text_width - 10, height - text_height - 10
    elif position == 'D':
        x, y = 10, height - text_height - 10
    elif position == 'E':
        x, y = (width - text_width) // 2, (height - text_height) // 2

    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, opacity))

    return image

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
            WAITING_FOR_WATERMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_watermark)],
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
