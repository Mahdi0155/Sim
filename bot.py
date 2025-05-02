import os
import json
import requests
from flask import Flask, request
from config import TOKEN, ADMINS, CHANNEL_TAG, DATA_FILE, WEBHOOK_URL

API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# بارگذاری دیتابیس ساده
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", data=data)

def send_video(chat_id, file_id, caption, thumbnail=None, reply_markup=None):
    data = {
        'chat_id': chat_id,
        'video': file_id,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    if thumbnail:
        data['thumb'] = thumbnail
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendVideo", data=data)

def delete_message(chat_id, message_id):
    requests.post(f"{API_URL}/deleteMessage", data={'chat_id': chat_id, 'message_id': message_id})

user_states = {}
user_data = {}

# تنظیم وب‌هوک در زمان اجرای برنامه
@app.before_first_request
def set_webhook():
    requests.get(f"{API_URL}/deleteWebhook")
    requests.get(f"{API_URL}/setWebhook?url={WEBHOOK_URL}")

@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    if 'message' in update:
        handle_message(update['message'])
    elif 'callback_query' in update:
        handle_callback(update['callback_query'])
    return 'ok'

def handle_message(msg):
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    text = msg.get('text', '')

    if text == '/start':
        send_message(chat_id, "خوش آمدید!")
        return

    if text == '/پنل' and user_id in ADMINS:
        keyboard = {'keyboard': [["سوپر", "پست"]], 'resize_keyboard': True}
        send_message(chat_id, "پنل مدیریت فعال شد.", keyboard)
        return

    state = user_states.get(user_id)
    if text == 'سوپر':
        user_states[user_id] = 'awaiting_video'
        send_message(chat_id, "لطفا ویدیو را ارسال کنید.")
    elif text == 'پست':
        user_states[user_id] = 'awaiting_forward'
        send_message(chat_id, "لطفا یک پیام فوروارد شده ارسال کنید.")
    elif state == 'awaiting_video' and 'video' in msg:
        user_data[user_id] = {'video': msg['video']['file_id']}
        user_states[user_id] = 'awaiting_caption'
        send_message(chat_id, "لطفا کپشن را وارد کنید.")
    elif state == 'awaiting_caption':
        user_data[user_id]['caption'] = text
        user_states[user_id] = 'awaiting_cover'
        keyboard = {
            'inline_keyboard': [[{'text': 'بدون کاور', 'callback_data': 'no_cover'}]]
        }
        send_message(chat_id, "اگر کاور دارید ارسال کنید یا دکمه بدون کاور را بزنید.", keyboard)
    elif state == 'awaiting_cover' and 'photo' in msg:
        user_data[user_id]['cover'] = msg['photo'][-1]['file_id']
        finalize_super(chat_id, user_id)
    elif state == 'awaiting_forward' and 'forward_from' in msg or 'forward_from_chat' in msg:
        user_data[user_id] = {'forward_msg': msg}
        user_states[user_id] = 'awaiting_post_caption'
        send_message(chat_id, "لطفا کپشن پست را وارد کنید.")
    elif state == 'awaiting_post_caption':
        fmsg = user_data[user_id]['forward_msg']
        caption = f"{text}\n\n🔥{CHANNEL_TAG}"
        forward_id = fmsg['message_id']
        from_chat_id = fmsg['chat']['id']
        requests.post(f"{API_URL}/copyMessage", data={
            'chat_id': chat_id,
            'from_chat_id': from_chat_id,
            'message_id': forward_id,
            'caption': caption,
            'parse_mode': 'HTML'
        })
        send_message(chat_id, "پست ارسال شد. برای ارسال پست جدید، یک پیام فورواردی دیگر ارسال کنید یا برگشت به پنل را بزنید.")


def handle_callback(query):
    user_id = query['from']['id']
    chat_id = query['message']['chat']['id']
    message_id = query['message']['message_id']
    if query['data'] == 'no_cover':
        user_data[user_id]['cover'] = None
        finalize_super(chat_id, user_id)
    delete_message(chat_id, message_id)


def finalize_super(chat_id, user_id):
    data = user_data[user_id]
    file_id = data['video']
    caption = data['caption']
    cover = data.get('cover')
    unique_id = f"v_{str(user_id)}_{str(hash(file_id))}"

    db = load_data()
    db[unique_id] = file_id
    save_data(db)

    link = f"https://t.me/{os.environ.get('BOT_USERNAME')}?start={unique_id}"
    caption_final = f"{caption}\n\n<a href='{link}'>مشاهده</a>\n🔥{CHANNEL_TAG}"

    send_video(chat_id, file_id, caption_final, thumbnail=cover)
    send_message(chat_id, "پیش‌نمایش آماده شد. اکنون به پنل بازمی‌گردید.")
    user_states[user_id] = None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
