import json
import os
import time
from threading import Thread
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = "7413532622:AAHTJUCRfKxehH7Qltb9pTkayakpjoLqQdk"
ADMIN_IDS = [7189616405, 6387942633, 5459406429]
bot = Bot(token=TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def handle_upload(update: Update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        update.message.reply_text("دسترسی نداری.")
        return

    if not context.args:
        update.message.reply_text("فرمت: /upload name")
        return

    name = context.args[0]
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    else:
        update.message.reply_text("فقط ویدیو یا عکس بفرست.")
        return

    data[name] = {"file_id": file_id, "type": file_type}
    save_data(data)
    link = f"https://your-domain.com/get/{name}"
    update.message.reply_text(f"فایل ذخیره شد!\nلینک: {link}")

def handle_get(update: Update, context):
    if not context.args:
        update.message.reply_text("فرمت: /get name")
        return
    name = context.args[0]
    if name not in data:
        update.message.reply_text("فایلی با این اسم نداریم.")
        return

    file_info = data[name]
    if file_info["type"] == "video":
        msg = update.message.reply_video(file_info["file_id"])
    else:
        msg = update.message.reply_photo(file_info["file_id"])

    def delete_later(chat_id, message_id):
        time.sleep(20)
        bot.delete_message(chat_id=chat_id, message_id=message_id)

    Thread(target=delete_later, args=(msg.chat_id, msg.message_id)).start()

# Webhook endpoint
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok"

# Set webhook once (optional route)
@app.route("/setwebhook")
def set_webhook():
    webhook_url = f"https://your-domain.com/webhook/{TOKEN}"
    bot.set_webhook(webhook_url)
    return f"Webhook set to {webhook_url}"

# Dispatcher and handlers
from telegram.ext import Updater
dp = Dispatcher(bot, None, workers=0)
dp.add_handler(CommandHandler("upload", handle_upload))
dp.add_handler(CommandHandler("get", handle_get))
dp.add_handler(MessageHandler(Filters.video | Filters.photo, handle_upload))

if __name__ == "__main__":
    app.run(port=5000)
