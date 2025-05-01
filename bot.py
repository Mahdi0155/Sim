import os
import json
import time
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN") or "توکن_ربات_تو"
ADMIN_IDS = [123456789]
CHANNEL_TAG = "@hottof | تُفِ داغ"

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

DATA_FILE = "data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

user_state = {}
temp_data = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    update.message.reply_text("خوش اومدی")
    if is_admin(user_id):
        show_panel(update)

def show_panel(update: Update):
    keyboard = [[KeyboardButton("سوپر")], [KeyboardButton("پست")]]
    update.message.reply_text("پنل مدیریت:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text

    if not is_admin(user_id):
        return

    if text == "سوپر":
        user_state[user_id] = "awaiting_video"
        update.message.reply_text("ویدیو را ارسال کنید:")
    elif text == "پست":
        user_state[user_id] = "awaiting_forward"
        update.message.reply_text("لطفاً پیام فورواردی یا رسانه را ارسال کنید:")
    elif text == "بازگشت":
        show_panel(update)

def handle_video(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state == "awaiting_video":
        temp_data[user_id] = {"file_id": update.message.video.file_id}
        user_state[user_id] = "awaiting_caption"
        update.message.reply_text("کپشن را ارسال کنید:")
    elif state == "awaiting_cover":
        temp_data[user_id]["cover_id"] = update.message.video.file_id
        finalize_super(update, context, user_id)

def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state == "awaiting_cover":
        temp_data[user_id]["cover_id"] = update.message.photo[-1].file_id
        finalize_super(update, context, user_id)

def handle_caption(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state == "awaiting_caption":
        temp_data[user_id]["caption"] = update.message.text
        user_state[user_id] = "awaiting_cover"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ندارم", callback_data="no_cover")]])
        update.message.reply_text("کاور را ارسال کنید یا بزنید ندارم:", reply_markup=keyboard)
    elif state == "awaiting_post_caption":
        temp_data[user_id]["caption"] = update.message.text
        send_post_preview(update, context, user_id)

def handle_forward(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state == "awaiting_forward":
        if update.message.video:
            temp_data[user_id] = {"file_id": update.message.video.file_id}
        elif update.message.photo:
            temp_data[user_id] = {"file_id": update.message.photo[-1].file_id}
        else:
            update.message.reply_text("فقط عکس یا ویدیو ارسال کنید.")
            return
        user_state[user_id] = "awaiting_post_caption"
        update.message.reply_text("کپشن را بنویسید:")

def finalize_super(update: Update, context: CallbackContext, user_id):
    data = load_data()
    code = str(int(time.time()))
    file_id = temp_data[user_id]["file_id"]
    caption = temp_data[user_id].get("caption", "")

    data[code] = {"file_id": file_id, "caption": caption}
    save_data(data)

    link = f"https://t.me/{context.bot.username}?start={code}"
    text = f"{caption}\n\n[مشاهده]({link})\n\n{CHANNEL_TAG}"

    if "cover_id" in temp_data[user_id]:
        bot.send_photo(user_id, temp_data[user_id]["cover_id"], caption=text, parse_mode="Markdown")
    else:
        bot.send_message(user_id, text, parse_mode="Markdown")

    user_state[user_id] = None
    temp_data.pop(user_id, None)
    show_panel(update)

def send_post_preview(update: Update, context: CallbackContext, user_id):
    file_id = temp_data[user_id]["file_id"]
    caption = temp_data[user_id].get("caption", "")

    if update.message.video:
        bot.send_video(user_id, file_id, caption=f"{caption}\n\n{CHANNEL_TAG}")
    else:
        bot.send_photo(user_id, file_id, caption=f"{caption}\n\n{CHANNEL_TAG}")

    user_state[user_id] = "awaiting_forward"

def callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "no_cover":
        query.message.delete()
        finalize_super(update, context, user_id)

def handle_start_code(update: Update, context: CallbackContext):
    if context.args:
        code = context.args[0]
        data = load_data()

        if code in data:
            file_id = data[code]["file_id"]
            caption = data[code]["caption"]
            msg = bot.send_video(update.effective_chat.id, file_id, caption=caption)
            alert = bot.send_message(update.effective_chat.id, "این محتوا تا ۲۰ ثانیه دیگر حذف خواهد شد.")
            context.job_queue.run_once(delete_messages, 20, context=(update.effective_chat.id, [msg.message_id, alert.message_id]))

def delete_messages(context: CallbackContext):
    chat_id, message_ids = context.job.context
    for message_id in message_ids:
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("start", handle_start_code, pass_args=True))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(MessageHandler(Filters.video & ~Filters.forwarded, handle_video))
dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.forwarded, handle_photo))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_caption))
dispatcher.add_handler(MessageHandler(Filters.forwarded & (Filters.video | Filters.photo), handle_forward))
dispatcher.add_handler(CallbackQueryHandler(callback_query))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'OK'

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running!'

bot.delete_webhook()
bot.set_webhook(url='https://sim-dtlp.onrender.com/webhook')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
