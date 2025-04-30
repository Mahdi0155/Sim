import os
import logging
import traceback
from datetime import timedelta
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters,
    ContextTypes, ConversationHandler, CallbackContext
)
from watermark import add_watermark  # فایل خارجی که واترمارک را اعمال می‌کند

# اطلاعات ربات
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405, 7827493126, 6039863213]

# مراحل گفتگو
WAITING_FOR_MEDIA, ASK_WATERMARK, ASK_POSITION, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(6)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# قبل از شروع، پوشه temp را ایجاد می‌کنیم اگر وجود نداشته باشد
temp_dir = "temp"
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

async def post_init(application: Application):
    _ = application.job_queue

application = Application.builder().token(TOKEN).post_init(post_init).build()

# تابع برای مدیریت خطاها
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"استثنا در پردازش: {context.error}")
    # لاگ کردن traceback کامل برای دیباگ بهتر
    traceback_str = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(f"جزئیات خطا: {traceback_str}")

# اضافه کردن error handler به application
application.add_error_handler(error_handler)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return ConversationHandler.END
    await update.message.reply_text('سلام! لطفاً یک عکس یا ویدیو فوروارد کن.')
    return WAITING_FOR_MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['file_id'] = file_id
        context.user_data['media_type'] = 'photo'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="watermark_yes"), InlineKeyboardButton("❌ خیر", callback_data="watermark_no")]
        ])
        await update.message.reply_text("آیا می‌خواهید واترمارک روی عکس باشد؟", reply_markup=keyboard)
        return ASK_WATERMARK
    elif update.message.video:
        context.user_data['file_id'] = update.message.video.file_id
        context.user_data['media_type'] = 'video'
        await update.message.reply_text('لطفاً کپشن مورد نظر خود را بنویسید:')
        return WAITING_FOR_CAPTION
    else:
        await update.message.reply_text('فقط عکس یا ویدیو قابل قبول است.')
        return WAITING_FOR_MEDIA

async def handle_watermark_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'watermark_no':
        context.user_data['add_watermark'] = False
        await query.edit_message_text("لطفاً کپشن مورد نظر خود را بنویسید:")
        return WAITING_FOR_CAPTION
    else:
        context.user_data['add_watermark'] = True
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("A", callback_data='pos_a'), InlineKeyboardButton("B", callback_data='pos_b')],
            [InlineKeyboardButton("E", callback_data='pos_e')],
            [InlineKeyboardButton("C", callback_data='pos_c'), InlineKeyboardButton("D", callback_data='pos_d')],
        ])
        await query.edit_message_text("موقعیت واترمارک را انتخاب کنید:", reply_markup=keyboard)
        return ASK_POSITION

async def handle_watermark_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    position_code = query.data.replace('pos_', '')
    context.user_data['watermark_position'] = position_code

    file_id = context.user_data['file_id']
    photo = await context.bot.get_file(file_id)
    path = f"temp/{file_id}.jpg"
    await photo.download_to_drive(path)
    result_path = add_watermark(path, position_code)
    context.user_data['processed_image_path'] = result_path

    await query.edit_message_text("لطفاً کپشن مورد نظر خود را بنویسید:")
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text + "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = caption

    keyboard = ReplyKeyboardMarkup(
        [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']], resize_keyboard=True
    )

    media_type = context.user_data['media_type']
    if media_type == 'photo' and context.user_data.get('add_watermark'):
        with open(context.user_data['processed_image_path'], 'rb') as img:
            await update.message.reply_photo(img, caption=caption, reply_markup=keyboard)
    elif media_type == 'photo':
        await update.message.reply_photo(context.user_data['file_id'], caption=caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(context.user_data['file_id'], caption=caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'ارسال در کانال':
        await send_to_channel(context)
        await update.message.reply_text('ارسال شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif update.message.text == 'ارسال در آینده':
        await update.message.reply_text('زمان ارسال (دقیقه):', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    else:
        await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        context.job_queue.run_once(send_scheduled, timedelta(minutes=minutes), data=context.user_data.copy())
        await update.message.reply_text('پیام زمان‌بندی شد.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    except:
        await update.message.reply_text('عدد وارد کن.')
        return WAITING_FOR_SCHEDULE

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if data['media_type'] == 'photo' and data.get('add_watermark'):
        path = data['processed_image_path']
        with open(path, 'rb') as f:
            await context.bot.send_photo(CHANNEL_USERNAME, photo=f, caption=data['caption'])
        try: os.remove(path)
        except Exception as e: logger.error(f"حذف نشد: {e}")
    elif data['media_type'] == 'photo':
        await context.bot.send_photo(CHANNEL_USERNAME, photo=data['file_id'], caption=data['caption'])
    elif data['media_type'] == 'video':
        await context.bot.send_video(CHANNEL_USERNAME, video=data['file_id'], caption=data['caption'])

async def send_scheduled(context: CallbackContext):
    data = context.job.data
    if data['media_type'] == 'photo' and data.get('add_watermark'):
        path = data['processed_image_path']
        with open(path, 'rb') as f:
            await context.bot.send_photo(CHANNEL_USERNAME, photo=f, caption=data['caption'])
        try: os.remove(path)
        except Exception as e: logger.error(f"حذف نشد: {e}")
    elif data['media_type'] == 'photo':
        await context.bot.send_photo(CHANNEL_USERNAME, photo=data['file_id'], caption=data['caption'])
    elif data['media_type'] == 'video':
        await context.bot.send_video(CHANNEL_USERNAME, video=data['file_id'], caption=data['caption'])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)],
            ASK_WATERMARK: [CallbackQueryHandler(handle_watermark_choice)],
            ASK_POSITION: [CallbackQueryHandler(handle_watermark_position)],
            WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            WAITING_FOR_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
            WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    WEBHOOK_URL = 'https://sim-dtlp.onrender.com'
    application.run_webhook(listen="0.0.0.0", port=int(os.environ.get("PORT", 8080)), webhook_url=WEBHOOK_URL)

if __name__ == '__main__':
    main()
