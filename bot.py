import os
import logging
import traceback
from datetime import timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from telegram import Update, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackContext
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405, 7827493126, 6039863213]

WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WATERMARK_TEXT = "Hottof"
WATERMARK_POSITION = 'e'  # default position

async def post_init(application: Application):
    _ = application.job_queue

application = Application.builder().token(TOKEN).post_init(post_init).build()

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
        [['a', 'b', 'c'], ['d', 'e']],
        resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        file = await context.bot.get_file(file_id)
        image_bytes = await file.download_as_bytearray()
        watermarked = apply_watermark(image_bytes, WATERMARK_POSITION)
        context.user_data['photo_bytes'] = watermarked
        await update.message.reply_photo(InputFile(watermarked), caption=final_caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(file_id, caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

def apply_watermark(image_bytes: bytes, position: str) -> BytesIO:
    with Image.open(BytesIO(image_bytes)).convert("RGBA") as im:
        txt_layer = Image.new("RGBA", im.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        font_size = int(min(im.size) * 0.04)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = WATERMARK_TEXT
        text_width, text_height = draw.textsize(text, font=font)
        margin = 20

        positions = {
            'a': (margin, margin),
            'b': (im.width - text_width - margin, margin),
            'c': (margin, im.height - text_height - margin),
            'd': (im.width - text_width - margin, im.height - text_height - margin),
            'e': ((im.width - text_width) // 2, (im.height - text_height) // 2),
        }

        pos = positions.get(position, positions['e'])

        draw.text((pos[0]+1, pos[1]+1), text, font=font, fill=(0,0,0,100))
        draw.text(pos, text, font=font, fill=(255,255,255,77))

        combined = Image.alpha_composite(im, txt_layer).convert("RGB")
        output = BytesIO()
        output.name = 'watermarked.jpg'
        combined.save(output, 'JPEG')
        output.seek(0)
        return output

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ['a', 'b', 'c', 'd', 'e']:
        WATERMARK_POSITION = text
        await update.message.reply_text(f'موقعیت واترمارک به {text} تغییر کرد.')
        return WAITING_FOR_CAPTION
    elif text == 'ارسال در کانال':
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
    except Exception:
        logger.error("خطا در handle_schedule:\n%s", traceback.format_exc())
        await update.message.reply_text('خطا در زمان‌بندی. فقط عدد وارد کنید یا دوباره تلاش کنید.')
        return WAITING_FOR_SCHEDULE

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    media_type = data['media_type']
    caption = data['caption']

    if media_type == 'photo':
        photo_bytes = data.get('photo_bytes')
        if photo_bytes:
            await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=InputFile(photo_bytes), caption=caption)
    elif media_type == 'video':
        file_id = data['file_id']
        await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)

async def send_scheduled(context: CallbackContext):
    try:
        data = context.job.data
        media_type = data['media_type']
        caption = data['caption']

        if media_type == 'photo':
            photo_bytes = data.get('photo_bytes')
            if photo_bytes:
                await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=InputFile(photo_bytes), caption=caption)
        elif media_type == 'video':
            file_id = data['file_id']
            await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)
    except Exception:
        logger.error("خطا در send_scheduled:\n%s", traceback.format_exc())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
