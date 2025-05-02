import os
import logging
from uuid import uuid4
from datetime import timedelta
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
                      ReplyKeyboardRemove)
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler,
                          ContextTypes, ConversationHandler)

TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://sim-dtlp.onrender.com"
ADMINS = [7189616405, 6387942633, 5459406429]
CHANNEL_TAG = "🔥@hottof | تُفِ داغ"

SUPER_VIDEO, SUPER_CAPTION, SUPER_COVER = range(3)
POST_FORWARD, POST_CAPTION = range(2)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
application = Application.builder().token(TOKEN).build()

VIDEO_DB = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("به ربات خوش آمدید.")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    keyboard = ReplyKeyboardMarkup([
        ['سوپر', 'پست']
    ], resize_keyboard=True)
    await update.message.reply_text("پنل مدیریت:", reply_markup=keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'سوپر':
        await update.message.reply_text("یک ویدیو ارسال کن:", reply_markup=ReplyKeyboardRemove())
        return SUPER_VIDEO
    elif text == 'پست':
        await update.message.reply_text("لطفاً یک پیام فورواردی ارسال کنید:", reply_markup=ReplyKeyboardRemove())
        return POST_FORWARD

# --------------------- SUPER ---------------------

async def super_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("فقط ویدیو قابل قبول است.")
        return SUPER_VIDEO
    context.user_data['video_id'] = update.message.video.file_id
    context.user_data['video_unique'] = str(uuid4())[:8]
    await update.message.reply_text("کپشن مورد نظر را وارد کن:")
    return SUPER_CAPTION

async def super_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['caption'] = update.message.text
    await update.message.reply_text("حالا کاور (عکس) را بفرست:")
    return SUPER_COVER

async def super_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("فقط عکس قابل قبول است.")
        return SUPER_COVER

    video_id = context.user_data['video_id']
    caption = context.user_data['caption']
    code = context.user_data['video_unique']
    cover_id = update.message.photo[-1].file_id

    VIDEO_DB[code] = video_id
    btn = InlineKeyboardMarkup.from_button(InlineKeyboardButton("مشاهده", url=f"https://t.me/hottofbot?start={code}"))

    await update.message.reply_photo(
        photo=cover_id,
        caption=f"{caption}\n\n{CHANNEL_TAG}",
        reply_markup=btn
    )
    await update.message.reply_text("بازگشت به پنل.", reply_markup=ReplyKeyboardMarkup([['سوپر', 'پست']], resize_keyboard=True))
    return ConversationHandler.END

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        code = context.args[0]
        if code in VIDEO_DB:
            msg = await update.message.reply_video(VIDEO_DB[code])
            context.job_queue.run_once(delete_sent_message, 20, data={
                'chat_id': msg.chat_id,
                'message_id': msg.message_id
            })
            await update.message.reply_text("این محتوا تا ۲۰ ثانیه دیگر حذف می‌شود.")
        else:
            await update.message.reply_text("محتوا یافت نشد.")
    else:
        await start(update, context)

async def delete_sent_message(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    try:
        await context.bot.delete_message(chat_id=job_data['chat_id'], message_id=job_data['message_id'])
    except:
        pass

# --------------------- POST ---------------------

async def post_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.forward_from_chat and not update.message.video and not update.message.photo:
        await update.message.reply_text("فقط پیام فورواردی یا عکس/ویدیو معتبر است.")
        return POST_FORWARD
    context.user_data['forward'] = update.message
    await update.message.reply_text("کپشن مورد نظر را وارد کن:")
    return POST_CAPTION

async def post_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = context.user_data['forward']
    caption = update.message.text + f"\n\n{CHANNEL_TAG}"
    if msg.photo:
        await update.message.reply_photo(msg.photo[-1].file_id, caption=caption)
    elif msg.video:
        await update.message.reply_video(msg.video.file_id, caption=caption)
    await update.message.reply_text("برای فوروارد بعدی پیام فورواردی بفرست:")
    
    keyboard = ReplyKeyboardMarkup([['بازگشت به پنل']], resize_keyboard=True)
    await update.message.reply_text("بازگشت به پنل.", reply_markup=keyboard)
    return POST_FORWARD

# --------------------- MAIN ---------------------

def main():
    conv = ConversationHandler(
        entry_points=[CommandHandler("panel", panel), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
        states={
            SUPER_VIDEO: [MessageHandler(filters.VIDEO, super_video)],
            SUPER_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, super_caption)],
            SUPER_COVER: [MessageHandler(filters.PHOTO, super_cover)],
            POST_FORWARD: [MessageHandler(filters.ALL, post_forward)],
            POST_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_caption)]
        },
        fallbacks=[]
    )
    application.add_handler(conv)
    application.add_handler(CommandHandler("start", start_handler))
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=BASE_URL
    )

if __name__ == '__main__':
    main()
