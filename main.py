# main.py

from flask import Flask, request
import requests
import threading
import time
from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, CHANNEL_TAG, PING_INTERVAL
from utils import save_file, get_file

app = Flask(__name__)
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
users = {}
pinging = True

def send(method, data):
    return requests.post(f"{URL}/{method}", json=data)

def delete(chat_id, message_id):
    send("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def edit_reply_markup(chat_id, message_id):
    send("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})

def ping():
    while pinging:
        try:
            requests.get(WEBHOOK_URL)
        except:
            pass
        time.sleep(PING_INTERVAL)

threading.Thread(target=ping, daemon=True).start()

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        msg = update["message"]
        uid = msg["from"]["id"]
        cid = msg["chat"]["id"]
        mid = msg["message_id"]
        text = msg.get("text", "")
        user_state = users.get(uid, {})

        if text == "/start":
            send("sendMessage", {"chat_id": cid, "text": "خوش اومدی!"})
        elif text == "/panel" and uid in ADMIN_IDS:
            kb = {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "پنل مدیریت", "reply_markup": kb})
        elif text == "سوپر" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_video"}
            send("sendMessage", {"chat_id": cid, "text": "لطفاً ویدیو رو ارسال کن"})
        elif text == "پست" and uid in ADMIN_IDS:
            users[uid] = {"step": "awaiting_forward"}
            send("sendMessage", {"chat_id": cid, "text": "یه پیام فوروارد شده (عکس یا ویدیو) برام بفرست"})
        elif user_state.get("step") == "awaiting_video" and "video" in msg:
            users[uid]["step"] = "awaiting_caption"
            users[uid]["file_id"] = msg["video"]["file_id"]
            send("sendMessage", {"chat_id": cid, "text": "کپشن رو وارد کن"})
        elif user_state.get("step") == "awaiting_caption":
            users[uid]["step"] = "awaiting_cover"
            users[uid]["caption"] = text
            kb = {"inline_keyboard": [[{"text": "کاور ندارم", "callback_data": "no_cover"}]]}
            send("sendMessage", {"chat_id": cid, "text": "کاور رو بفرست یا بزن کاور ندارم", "reply_markup": kb})
        elif user_state.get("step") == "awaiting_cover" and "photo" in msg:
            file_id = users[uid]["file_id"]
            caption = users[uid]["caption"]
            cover_id = msg["photo"][-1]["file_id"]
            code = save_file(file_id)
            users.pop(uid)
            text = f"<a href='https://t.me/{BOT_TOKEN.split(':')[0]}?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            send("sendPhoto", {"chat_id": cid, "photo": cover_id, "caption": caption + "\n\n" + text, "parse_mode": "HTML"})
            kb = {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "پیش‌نمایش ارسال شد", "reply_markup": kb})
        elif user_state.get("step") == "awaiting_forward" and ("video" in msg or "photo" in msg) and "forward_from" in msg:
            users[uid]["step"] = "awaiting_post_caption"
            users[uid]["post_msg"] = msg
            send("sendMessage", {"chat_id": cid, "text": "کپشن پست رو بفرست"})
        elif user_state.get("step") == "awaiting_post_caption":
            post_msg = users[uid]["post_msg"]
            cap = text + "\n\n" + CHANNEL_TAG
            if "video" in post_msg:
                file_id = post_msg["video"]["file_id"]
                send("sendVideo", {"chat_id": cid, "video": file_id, "caption": cap})
            else:
                file_id = post_msg["photo"][-1]["file_id"]
                send("sendPhoto", {"chat_id": cid, "photo": file_id, "caption": cap})
            users[uid]["step"] = "awaiting_forward"
            send("sendMessage", {"chat_id": cid, "text": "برای پست بعدی پیام فوروارد شده رو بفرست"})
        elif text in ["بازگشت", "بازگشت به پنل"] and uid in ADMIN_IDS:
            users.pop(uid, None)
            kb = {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "بازگشتی به پنل", "reply_markup": kb})
    elif "callback_query" in update:
        cb = update["callback_query"]
        uid = cb["from"]["id"]
        mid = cb["message"]["message_id"]
        cid = cb["message"]["chat"]["id"]
        data = cb["data"]
        if data == "no_cover" and users.get(uid, {}).get("step") == "awaiting_cover":
            file_id = users[uid]["file_id"]
            caption = users[uid]["caption"]
            code = save_file(file_id)
            users.pop(uid)
            text = f"<a href='https://t.me/{BOT_TOKEN.split(':')[0]}?start={code}'>مشاهده</a>\n\n{CHANNEL_TAG}"
            delete(cid, mid)
            send("sendMessage", {"chat_id": cid, "text": caption + "\n\n" + text, "parse_mode": "HTML"})
            kb = {"keyboard": [[{"text": "سوپر"}], [{"text": "پست"}]], "resize_keyboard": True}
            send("sendMessage", {"chat_id": cid, "text": "پیش‌نمایش ارسال شد", "reply_markup": kb})
    elif "message" in update and "text" in update["message"] and update["message"]["text"].startswith("/start "):
        msg = update["message"]
        cid = msg["chat"]["id"]
        code = msg["text"].split("/start ")[1]
        file_id = get_file(code)
        if file_id:
            m = send("sendVideo", {"chat_id": cid, "video": file_id})
            if "result" in m:
                mid = m["result"]["message_id"]
                send("sendMessage", {"chat_id": cid, "text": "این محتوا تا ۲۰ ثانیه دیگر حذف می‌شود"})
                threading.Timer(20, delete, args=(cid, mid)).start()
    return "ok"
