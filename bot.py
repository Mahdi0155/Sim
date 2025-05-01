from flask import Flask, request
import requests

TOKEN = "YOUR_TOKEN_HERE"
BOT_USERNAME = "HotTofBot"
URL = f"https://api.telegram.org/bot{TOKEN}/"
WEBHOOK_URL = "https://sim-dtlp.onrender.com"
admin_ids = [7189616405, 6039863213, 5459406429, 6387942633]

app = Flask(__name__)

user_states = {}
video_data = {}

WELCOME_MSG = "خوش آمدید!"
CHANNEL_TAG = "\n\n🔥@hottof | تُفِ داغ"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        handle_message(data["message"])
    elif "callback_query" in data:
        handle_callback(data["callback_query"])
    return "ok"

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(URL + "sendMessage", json=payload)

def delete_message(chat_id, message_id):
    requests.post(URL + "deleteMessage", json={"chat_id": chat_id, "message_id": message_id})

def send_video(chat_id, file_id, caption, thumb=None):
    payload = {
        "chat_id": chat_id,
        "video": file_id,
        "caption": caption + CHANNEL_TAG,
        "parse_mode": "HTML"
    }
    if thumb:
        payload["thumb"] = thumb
    requests.post(URL + "sendVideo", json=payload)

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text")
    message_id = msg["message_id"]

    state = user_states.get(user_id)

    if text == "/start":
        send_message(chat_id, WELCOME_MSG)
        return

    if text == "/panel" and user_id in admin_ids:
        reply_markup = {
            "keyboard": [[{"text": "سوپر"}, {"text": "پست"}]],
            "resize_keyboard": True
        }
        send_message(chat_id, "پنل مدیریت:", reply_markup)
        return

    if state == "awaiting_video":
        if "video" in msg:
            file_id = msg["video"]["file_id"]
            video_data[user_id] = {"file_id": file_id}
            user_states[user_id] = "awaiting_caption"
            send_message(chat_id, "کپشن را وارد کنید:")
        else:
            send_message(chat_id, "لطفاً یک ویدیو ارسال کنید.")
        return

    if state == "awaiting_caption":
        video_data[user_id]["caption"] = text
        user_states[user_id] = "awaiting_cover"
        reply_markup = {
            "inline_keyboard": [[{"text": "ندارم", "callback_data": "no_cover"}]]
        }
        send_message(chat_id, "کاور را ارسال کنید یا دکمه زیر را بزنید:", reply_markup)
        return

    if state == "awaiting_cover":
        if "photo" in msg:
            thumb_file_id = msg["photo"][-1]["file_id"]
            video_data[user_id]["thumb"] = thumb_file_id
        else:
            send_message(chat_id, "لطفاً یک عکس ارسال کنید یا دکمه نداشت را بزنید.")
            return
        preview_and_reset(user_id, chat_id)
        return

    if text == "سوپر" and user_id in admin_ids:
        user_states[user_id] = "awaiting_video"
        send_message(chat_id, "لطفاً ویدیو را ارسال کنید:")
        return

    if text == "پست" and user_id in admin_ids:
        user_states[user_id] = "awaiting_forward"
        send_message(chat_id, "یک پیام فوروارد شده (عکس یا ویدیو) ارسال کنید:")
        return

    if state == "awaiting_forward":
        if "video" in msg or "photo" in msg:
            media = msg.get("video") or msg.get("photo")[-1]
            file_id = media["file_id"]
            media_type = "video" if "video" in msg else "photo"
            video_data[user_id] = {"file_id": file_id, "type": media_type}
            user_states[user_id] = "awaiting_post_caption"
            send_message(chat_id, "کپشن را وارد کنید:")
        else:
            send_message(chat_id, "لطفاً یک پیام معتبر ارسال کنید.")
        return

    if state == "awaiting_post_caption":
        caption = text + CHANNEL_TAG
        file_id = video_data[user_id]["file_id"]
        media_type = video_data[user_id]["type"]
        if media_type == "video":
            send_video(chat_id, file_id, caption)
        else:
            requests.post(URL + "sendPhoto", json={
                "chat_id": chat_id,
                "photo": file_id,
                "caption": caption,
                "parse_mode": "HTML"
            })
        user_states[user_id] = "awaiting_forward"
        send_message(chat_id, "برای ارسال پست بعدی، یک پیام دیگر فوروارد کنید یا به پنل بازگردید.")
        return

def handle_callback(callback):
    user_id = callback["from"]["id"]
    chat_id = callback["message"]["chat"]["id"]
    message_id = callback["message"]["message_id"]
    data = callback["data"]

    if data == "no_cover":
        video_data[user_id]["thumb"] = None
        delete_message(chat_id, message_id)
        preview_and_reset(user_id, chat_id)

def preview_and_reset(user_id, chat_id):
    file_id = video_data[user_id]["file_id"]
    caption = video_data[user_id]["caption"]
    thumb = video_data[user_id].get("thumb")
    button_link = f"https://t.me/{BOT_USERNAME}?start={file_id}"
    caption_text = f"<b>{caption}</b>\n\n<a href=\"{button_link}\">مشاهده</a>{CHANNEL_TAG}"
    send_video(chat_id, file_id, caption_text, thumb)
    user_states[user_id] = None

def set_webhook():
    requests.get(URL + f"setWebhook?url={WEBHOOK_URL}")

# Webhook باید خارج از main تنظیم شود تا در Render اجرا شود
set_webhook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
