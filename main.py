import json
import uuid
import time
from telegram import Update, InputMediaPhoto, ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
)

ADMIN_ID = 6387942633  # آیدی عددی ادمین
DATA_FILE = "files.json"
STATES = {
    "WAIT_FILE": 1,
    "WAIT_COVER": 2,
    "WAIT_CAPTION": 3,
}

user_sessions = {}

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# شروع پنل
def panel(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    user_sessions[update.effective_user.id] = {}
    update.message.reply_text("لطفاً ویدیو یا عکس اصلی را ارسال کن.")
    return STATES["WAIT_FILE"]

# گرفتن فایل اصلی
def handle_file(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    msg = update.message
    file_data = {}

    if msg.video:
        file_data["file_id"] = msg.video.file_id
        file_data["file_type"] = "video"
    elif msg.photo:
        file_data["file_id"] = msg.photo[-1].file_id
        file_data["file_type"] = "photo"
    else:
        update.message.reply_text("فقط عکس یا ویدیو بفرست.")
        return STATES["WAIT_FILE"]

    user_sessions[update.effective_user.id] = file_data

    if file_data["file_type"] == "video":
        update.message.reply_text("ویدیو دریافت شد. لطفاً کاور (یک عکس) ارسال کن.")
        return STATES["WAIT_COVER"]
    else:
        update.message.reply_text("عکس دریافت شد. لطفاً کپشن فایل رو ارسال کن.")
        return STATES["WAIT_CAPTION"]

# گرفتن کاور
def handle_cover(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message.photo:
        update.message.reply_text("فقط عکس ارسال کن.")
        return STATES["WAIT_COVER"]

    user_sessions[update.effective_user.id]["thumb_id"] = update.message.photo[-1].file_id
    update.message.reply_text("کاور دریافت شد. لطفاً کپشن رو ارسال کن.")
    return STATES["WAIT_CAPTION"]

# گرفتن کپشن و ساخت لینک
def handle_caption(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return ConversationHandler.END

    caption = update.message.text
    session = user_sessions.get(uid, {})
    session["caption"] = caption
    token = str(uuid.uuid4())[:8]
    session["token"] = token

    # ذخیره فایل
    data = load_data()
    data[token] = {
        "file_id": session["file_id"],
        "file_type": session["file_type"],
        "thumb_id": session.get("thumb_id"),
        "caption": caption,
        "timestamp": time.time()
    }
    save_data(data)

    bot_username = context.bot.username
    link = f"https://t.me/{bot_username}?start={token}"

    # ساخت پیش‌نمایش
    final_caption = f"""{caption}

مشاهده: [کلیک کنید]({link})

🔥@hottof | تُفِ داغ"""

    if session["file_type"] == "video":
        context.bot.send_photo(
            chat_id=uid,
            photo=session["thumb_id"],
            caption=final_caption,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        context.bot.send_photo(
            chat_id=uid,
            photo=session["file_id"],
            caption=final_caption,
            parse_mode=ParseMode.MARKDOWN
        )

    update.message.reply_text("پیش‌نمایش ساخته شد. پیام رو کپی کن و توی کانال ارسال کن.")
    return ConversationHandler.END

# دستور /start برای کاربران
def start(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("برای دریافت فایل، از لینکی که دریافت کردید وارد شوید.")
        return

    token = args[0]
    data = load_data()

    if token not in data:
        update.message.reply_text("فایل مورد نظر یافت نشد یا منقضی شده.")
        return

    item = data[token]
    file_type = item["file_type"]
    file_id = item["file_id"]
    caption = item["caption"]

    # هشدار قبل از ارسال
    warning = update.message.reply_text("توجه: این فایل پس از ۲۰ ثانیه حذف خواهد شد.")

    if file_type == "photo":
        sent = update.message.reply_photo(photo=file_id, caption=caption)
    else:
        thumb = item.get("thumb_id")
        sent = update.message.reply_video(video=file_id, thumb=thumb, caption=caption)

    # حذف پس از ۲۰ ثانیه
    context.job_queue.run_once(lambda c: sent.delete(), 20)
    context.job_queue.run_once(lambda c: warning.delete(), 20)

# کنسل کردن
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END

# شروع ربات
def main():
    TOKEN = "7413532622:AAGmb4UihdcGROnhhSVwTwz_0jy9DaovjWo"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler("panel", panel)],
        states={
            STATES["WAIT_FILE"]: [MessageHandler(Filters.photo | Filters.video, handle_file)],
            STATES["WAIT_COVER"]: [MessageHandler(Filters.photo, handle_cover)],
            STATES["WAIT_CAPTION"]: [MessageHandler(Filters.text, handle_caption)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(conv)
    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
