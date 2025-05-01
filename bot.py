import os
import logging
import traceback
from datetime import timedelta
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackContext, CallbackQueryHandler
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405, 7827493126, 6039863213]

SELECT_MODE, WAITING_FOR_MEDIA, WAITING_FOR_CAPTION, WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE = range(5, 10)
WAITING_FOR_VIDEO, WAITING_FOR_COVER, WAITING_FOR_ALT_CAPTION = range(10, 13)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def post_init(application: Application):
    _ = application.job_queue

application = Application.builder().token(TOKEN).post_init(post_init).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text('شما دسترسی به این ربات ندارید.')
        return ConversationHandler.END
    keyboard = ReplyKeyboardMarkup([['ارسال ساده', 'ارسال با کاور']], resize_keyboard=True)
    await update.message.reply_text('یکی از حالت‌های زیر را انتخاب کنید:', reply_markup=keyboard)
    return SELECT_MODE

async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'ارسال ساده':
        await update.message.reply_text('لطفاً یک عکس یا ویدیو ارسال کنید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif text == 'ارسال با کاور':
        await update.message.reply_text('لطفاً ویدیوی مورد نظر را ارسال کنید.', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_VIDEO
    else:
        await update.message.reply_text('گزینه معتبر نیست.')
        return SELECT_MODE

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await update.message.reply_text('لطفاً کپشن مورد نظر را وارد کنید:')
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
        await update.message.reply_photo(file_id, caption=final_caption, reply_markup=keyboard)
    elif media_type == 'video':
        await update.message.reply_video(file_id, caption=final_caption, reply_markup=keyboard)

    return WAITING_FOR_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == 'ارسال در کانال':
        await send_to_channel(context)
        await update.message.reply_text('پیام ارسال شد. لطفاً رسانه بعدی را بفرستید.', reply_markup=ReplyKeyboardRemove())
        return SELECT_MODE
    elif text == 'ارسال در آینده':
        await update.message.reply_text('زمان ارسال (به دقیقه) را وارد کنید:', reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    elif text == 'برگشت به ابتدا':
        await update.message.reply_text('لغو شد. لطفاً یکی از حالت‌ها را انتخاب کنید.', reply_markup=ReplyKeyboardRemove())
        return SELECT_MODE
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
            f'پیام برای {minutes} دقیقه بعد زمان‌بندی شد.\n\nلطفاً یکی از حالت‌ها را انتخاب کنید.',
            reply_markup=ReplyKeyboardRemove()
        )
        return SELECT_MODE
    except:
        await update.message.reply_text('خطا در زمان‌بندی. فقط عدد وارد کنید.')
        return WAITING_FOR_SCHEDULE

async def send_to_channel(context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    media_type = data['media_type']
    file_id = data['file_id']
    caption = data['caption']

    if media_type == 'photo':
        await context.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
    elif media_type == 'video':
        await context.bot.send_video(chat_id=CHANNEL_USERNAME, video=file_id, caption=caption)

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
    except:
        pass

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text('لطفاً فقط یک ویدیو ارسال کنید.')
        return WAITING_FOR_VIDEO

    context.user_data['video_file_id'] = update.message.video.file_id
    await update.message.reply_text('حالاً کاور (عکس) را ارسال کنید.')
    return WAITING_FOR_COVER

async def handle_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text('لطفاً فقط عکس ارسال کنید.')
        return WAITING_FOR_COVER

    context.user_data['cover_file_id'] = update.message.photo[-1].file_id
    await update.message.reply_text('لطفاً کپشن را بنویسید:')
    return WAITING_FOR_ALT_CAPTION

async def handle_alt_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption_text = update.message.text
    video_id = context.user_data['video_file_id']
    cover_id = context.user_data['cover_file_id']
    preview_caption = f"{caption_text}\n\n[مشاهده](https://t.me/{context.bot.username}?start={video_id})\n\n🔥@hottof | تُفِ داغ"

    await update.message.reply_photo(
        photo=cover_id,
        caption=preview_caption,
        parse_mode='Markdown'
    )

    await update.message.reply_text('ارسال شد. لطفاً یکی از حالت‌ها را انتخاب کنید.', reply_markup=ReplyKeyboardMarkup([['ارسال ساده', 'ارسال با کاور']], resize_keyboard=True))
    return SELECT_MODE

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        file_id = args[0]
        message = await update.message.reply_text('در حال ارسال فایل، این پیام پس از ۲۰ ثانیه حذف می‌شود...')
        sent = await update.message.reply_video(video=file_id)
        context.job_queue.run_once(delete_later, 20, data={'chat_id': sent.chat_id, 'message_id': sent.message_id})
        context.job_queue.run_once(delete_later, 20, data={'chat_id': message.chat_id, 'message_id': message.message_id})
    else:
        await start(update, context)

async def delete_later(context: CallbackContext):
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data['chat_id'], message_id=data['message_id'])
    except:
        pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('لغو شد.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', handle_start_command)],
        states={
            SELECT_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_mode)],
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)],
            WAITING_FOR_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            WAITING_FOR_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
            WAITING_FOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule)],
            WAITING_FOR_VIDEO: [MessageHandler(filters.VIDEO, handle_video)],
            WAITING_FOR_COVER: [MessageHandler(filters.PHOTO, handle_cover)],
            WAITING_FOR_ALT_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alt_caption)],
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
