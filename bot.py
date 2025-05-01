import os
import logging
from datetime import timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackContext, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@hottof'
ADMINS = [6387942633, 5459406429, 7189616405, 7827493126, 6039863213]

(
    SELECT_MODE, WAITING_FOR_MEDIA, WAITING_FOR_CAPTION,
    WAITING_FOR_ACTION, WAITING_FOR_SCHEDULE,
    WAITING_FOR_VIDEO, WAITING_FOR_COVER, WAITING_FOR_ALT_CAPTION
) = range(8)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("شما دسترسی ندارید.")
        return ConversationHandler.END

    keyboard = [['ارسال ساده', 'ارسال با کاور']]
    await update.message.reply_text(
        "یکی از حالت‌های زیر را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return SELECT_MODE

async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = update.message.text
    if mode == 'ارسال ساده':
        context.user_data.clear()
        context.user_data['mode'] = 'simple'
        await update.message.reply_text("لطفاً عکس یا ویدیو ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_MEDIA
    elif mode == 'ارسال با کاور':
        context.user_data.clear()
        context.user_data['mode'] = 'with_cover'
        await update.message.reply_text("لطفاً ویدیو را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_VIDEO
    else:
        await update.message.reply_text("گزینه معتبر نیست.")
        return SELECT_MODE

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['media_type'] = 'photo'
        context.user_data['file_id'] = update.message.photo[-1].file_id
    elif update.message.video:
        context.user_data['media_type'] = 'video'
        context.user_data['file_id'] = update.message.video.file_id
    else:
        await update.message.reply_text("فقط عکس یا ویدیو بفرستید.")
        return WAITING_FOR_MEDIA

    await update.message.reply_text("لطفاً کپشن را وارد کنید:")
    return WAITING_FOR_CAPTION

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text.strip()
    caption += "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = caption

    keyboard = [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']]
    media_type = context.user_data['media_type']
    file_id = context.user_data['file_id']

    if media_type == 'photo':
        await update.message.reply_photo(file_id, caption=caption, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        await update.message.reply_video(file_id, caption=caption, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    return WAITING_FOR_ACTION

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("فقط ویدیو بفرستید.")
        return WAITING_FOR_VIDEO

    context.user_data['video_file_id'] = update.message.video.file_id
    await update.message.reply_text("حالا کاور (عکس) را ارسال کنید.")
    return WAITING_FOR_COVER

async def handle_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("فقط عکس ارسال کنید.")
        return WAITING_FOR_COVER

    context.user_data['cover_file_id'] = update.message.photo[-1].file_id
    await update.message.reply_text("لطفاً کپشن را وارد کنید:")
    return WAITING_FOR_ALT_CAPTION

async def handle_alt_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text.strip()
    caption += "\n\n🔥@hottof | تُفِ داغ"
    context.user_data['caption'] = caption

    keyboard = [['ارسال در کانال', 'ارسال در آینده'], ['برگشت به ابتدا']]
    cover_id = context.user_data['cover_file_id']

    await update.message.reply_photo(cover_id, caption=caption, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return WAITING_FOR_ACTION

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'ارسال در کانال':
        await send_to_channel(context)
        return await start(update, context)
    elif choice == 'ارسال در آینده':
        await update.message.reply_text("زمان ارسال (به دقیقه) را وارد کنید:", reply_markup=ReplyKeyboardRemove())
        return WAITING_FOR_SCHEDULE
    elif choice == 'برگشت به ابتدا':
        return await start(update, context)
    else:
        await update.message.reply_text("گزینه معتبر نیست.")
        return WAITING_FOR_ACTION

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text.strip())
        data = context.user_data.copy()
        context.job_queue.run_once(send_scheduled, timedelta(minutes=minutes), data=data)

        await update.message.reply_text(
            f"پیام برای {minutes} دقیقه بعد زمان‌بندی شد.",
            reply_markup=ReplyKeyboardMarkup([['ارسال ساده', 'ارسال با کاور']], resize_keyboard=True)
        )
        return SELECT_MODE
    except:
        await update.message.reply_text("لطفاً فقط عدد وارد کنید.")
        return WAITING_FOR_SCHEDULE

async def send_to_channel(context: CallbackContext):
    data = context.user_data
    if data.get('mode') == 'simple':
        if data['media_type'] == 'photo':
            await context.bot.send_photo(CHANNEL_USERNAME, data['file_id'], caption=data['caption'])
        else:
            await context.bot.send_video(CHANNEL_USERNAME, data['file_id'], caption=data['caption'])
    elif data.get('mode') == 'with_cover':
        cover_id = data['cover_file_id']
        video_id = data['video_file_id']
        full_caption = f"{data['caption']}\n\n[مشاهده](https://t.me/{context.bot.username}?start={video_id})\n\n🔥@hottof | تُفِ داغ"
        await context.bot.send_photo(CHANNEL_USERNAME, photo=cover_id, caption=full_caption, parse_mode='Markdown')

async def send_scheduled(context: CallbackContext):
    context.user_data = context.job.data
    await send_to_channel(context)

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        video_id = args[0]
        loading = await update.message.reply_text("در حال ارسال فایل...")
        sent = await update.message.reply_video(video=video_id)
        context.job_queue.run_once(delete_later, 20, data={'chat_id': sent.chat_id, 'message_id': sent.message_id})
        context.job_queue.run_once(delete_later, 20, data={'chat_id': loading.chat_id, 'message_id': loading.message_id})
    else:
        return await start(update, context)

async def delete_later(context: CallbackContext):
    try:
        data = context.job.data
        await context.bot.delete_message(data['chat_id'], data['message_id'])
    except:
        pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handle_start_command)],
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
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    WEBHOOK_URL = 'https://sim-dtlp.onrender.com'
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
