import os
from flask import Flask, request
import threading
import time
import json
import requests

TOKEN = os.getenv("BOT_TOKEN") or "PUT_YOUR_TOKEN_HERE"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
ADMIN_IDS = [7189616405, 6039863213, 5459406429, 6387942633]
CHANNEL_TAG = "@hottof | تُفِ داغ"
BOT_USERNAME = "HotTofBot"
DB_PATH = "data.json"
app = Flask(__name__)

user_states = {}
session_data = {}

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_PATH) as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, "w") as f:
        json.dump(data, f)

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"): 
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BOT_URL}/sendMessage", data=data)

def delete_message(chat_id, message_id):
    requests.post(f"{BOT_URL}/deleteMessage", data={"chat_id": chat_id, "message_id": message_id})

def send_video(chat_id, file_id, caption=None, thumbnail=None, reply_markup=None):
    data = {"chat_id": chat_id, "video": file_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    if thumbnail:
        data["thumb"] = thumbnail
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return requests.post(f"{BOT_URL}/sendVideo", data=data).json()

def send_photo(chat_id, file_id, caption=None):
    data = {"chat_id": chat_id, "photo": file_id, "caption": caption, "parse_mode": "HTML"}
    return requests.post(f"{BOT_URL}/sendPhoto", data=data).json()

def build_panel():
    return {"keyboard": [[{"text": "سوپر"}, {"text": "پست"}]], "resize_keyboard": True}

def auto_delete(chat_id, message_id):
    time.sleep(20)
    delete_message(chat_id, message_id)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")
        file_id = None

        if text == "/start":
            send_message(chat_id, "خوش اومدی به ربات")

        elif text == "/panel" and user_id in ADMIN_IDS:
            user_states[user_id] = None
            send_message(chat_id, "پنل مدیریت", build_panel())

        elif text == "سوپر" and user_id in ADMIN_IDS:
            user_states[user_id] = "awaiting_video"
            session_data[user_id] = {}
            send_message(chat_id, "لطفا ویدیوی مورد نظر را ارسال کنید")

        elif text == "پست" and user_id in ADMIN_IDS:
            user_states[user_id] = "awaiting_forward"
            session_data[user_id] = {}
            send_message(chat_id, "لطفاً یک پیام فوروارد شده بفرستید")

        elif user_states.get(user_id) == "awaiting_video" and "video" in msg:
            file_id = msg["video"]["file_id"]
            session_data[user_id]["video"] = file_id
            user_states[user_id] = "awaiting_caption"
            send_message(chat_id, "لطفاً کپشن را وارد کنید")

        elif user_states.get(user_id) == "awaiting_caption":
            session_data[user_id]["caption"] = text
            user_states[user_id] = "awaiting_cover"
            keyboard = {"inline_keyboard": [[{"text": "ندارم", "callback_data": "no_cover"}]]}
            send_message(chat_id, "اگر کاور دارید ارسال کنید، اگر نه روی دکمه زیر بزنید", keyboard)

        elif user_states.get(user_id) == "awaiting_cover" and "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            session_data[user_id]["cover"] = file_id
            finalize_super(chat_id, user_id)

        elif user_states.get(user_id) == "awaiting_caption_fwd":
            session_data[user_id]["caption"] = text
            file = session_data[user_id]["file"]
            typ = session_data[user_id]["type"]
            if typ == "video":
                send_video(chat_id, file, caption=f"{text}\n\n🔥{CHANNEL_TAG}")
            else:
                send_photo(chat_id, file, caption=f"{text}\n\n🔥{CHANNEL_TAG}")
            user_states[user_id] = "awaiting_forward"
            send_message(chat_id, "منتظر پیام بعدی هستم یا بازگشت به پنل", build_panel())

        elif user_states.get(user_id) == "awaiting_forward" and ("video" in msg or "photo" in msg):
            if "video" in msg:
                file = msg["video"]["file_id"]
                typ = "video"
            else:
                file = msg["photo"][-1]["file_id"]
                typ = "photo"
            session_data[user_id]["file"] = file
            session_data[user_id]["type"] = typ
            user_states[user_id] = "awaiting_caption_fwd"
            send_message(chat_id, "لطفاً کپشن را وارد کنید")

    elif "callback_query" in update:
        q = update["callback_query"]
        user_id = q["from"]["id"]
        chat_id = q["message"]["chat"]["id"]
        data = q["data"]
        msg_id = q["message"]["message_id"]
        if data == "no_cover":
            delete_message(chat_id, msg_id)
            finalize_super(chat_id, user_id)

    return "ok"

def finalize_super(chat_id, user_id):
    video = session_data[user_id].get("video")
    caption = session_data[user_id].get("caption")
    cover = session_data[user_id].get("cover")
    code = str(int(time.time() * 1000))[-6:]
    db = load_db()
    db[code] = video
    save_db(db)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    msg = f"{caption}\n\n<a href=\"{link}\">مشاهده</a>\n\n🔥{CHANNEL_TAG}"
    send_video(chat_id, video, caption=msg, thumbnail=cover)
    user_states[user_id] = None
    send_message(chat_id, "به پنل برگشتید", build_panel())

@app.route("/", methods=["GET"])
def root():
    return "Bot is running."

def delete_after_delay(chat_id, message_id):
    time.sleep(20)
    delete_message(chat_id, message_id)

@app.route(f"/{TOKEN}_hook", methods=["POST"])
def start_handler():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start") and len(text.split()) == 2:
            code = text.split()[1]
            db = load_db()
            video = db.get(code)
            if video:
                res = send_video(chat_id, video)
                if res.get("ok"):
                    mid = res["result"]["message_id"]
                    send_message(chat_id, "این محتوا تا ۲۰ ثانیه دیگر حذف می‌شود")
                    threading.Thread(target=delete_after_delay, args=(chat_id, mid)).start()

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
