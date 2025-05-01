from flask import Flask, request
import requests
import json
import threading
import time

app = Flask(__name__)

TOKEN = 'توکن_ربات'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_IDS = [123456789]
CHANNEL_TAG = '@hottof | تُفِ داغ'

DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

data = load_data()
user_states = {}

def send(method, payload):
    requests.post(URL + method, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        user_id = msg['from']['id']
        text = msg.get('text', '')
        if text == '/start':
            send('sendMessage', {'chat_id': chat_id, 'text': 'خوش اومدی'})
        elif text == '/panel' and user_id in ADMIN_IDS:
            kb = {'keyboard': [[{'text': 'سوپر'}, {'text': 'پست'}]], 'resize_keyboard': True}
            send('sendMessage', {'chat_id': chat_id, 'text': 'پنل مدیریت:', 'reply_markup': kb})
        elif text == 'سوپر' and user_id in ADMIN_IDS:
            user_states[user_id] = {'step': 'await_video'}
            send('sendMessage', {'chat_id': chat_id, 'text': 'ویدیو رو ارسال کن'})
        elif text == 'پست' and user_id in ADMIN_IDS:
            user_states[user_id] = {'step': 'await_post'}
            send('sendMessage', {'chat_id': chat_id, 'text': 'پیام فوروارد شده یا مدیا رو بفرست'})
        elif text == 'بازگشت' and user_id in ADMIN_IDS:
            kb = {'keyboard': [[{'text': 'سوپر'}, {'text': 'پست'}]], 'resize_keyboard': True}
            send('sendMessage', {'chat_id': chat_id, 'text': 'بازگشت به پنل:', 'reply_markup': kb})
        elif user_id in user_states:
            state = user_states[user_id]
            if state['step'] == 'await_video' and 'video' in msg:
                state['video'] = msg['video']['file_id']
                state['step'] = 'await_caption'
                send('sendMessage', {'chat_id': chat_id, 'text': 'کپشن رو بفرست'})
            elif state['step'] == 'await_caption':
                state['caption'] = text
                state['step'] = 'await_thumb'
                ikb = {'inline_keyboard': [[{'text': 'ندارم', 'callback_data': 'no_thumb'}]]}
                send('sendMessage', {'chat_id': chat_id, 'text': 'کاور رو بفرست یا بزن ندارم', 'reply_markup': ikb})
            elif state['step'] == 'await_thumb' and 'photo' in msg:
                state['thumb'] = msg['photo'][-1]['file_id']
                finish_super(chat_id, user_id)
            elif state['step'] == 'await_post' and ('video' in msg or 'photo' in msg or 'document' in msg):
                state['media'] = msg
                state['step'] = 'await_post_caption'
                send('sendMessage', {'chat_id': chat_id, 'text': 'کپشن رو وارد کن'})
            elif state['step'] == 'await_post_caption':
                m = state['media']
                caption = text + f'\n\n{CHANNEL_TAG}'
                if 'video' in m:
                    send('sendVideo', {'chat_id': chat_id, 'video': m['video']['file_id'], 'caption': caption})
                elif 'photo' in m:
                    send('sendPhoto', {'chat_id': chat_id, 'photo': m['photo'][-1]['file_id'], 'caption': caption})
                elif 'document' in m:
                    send('sendDocument', {'chat_id': chat_id, 'document': m['document']['file_id'], 'caption': caption})
                kb = {'keyboard': [[{'text': 'بازگشت'}]], 'resize_keyboard': True}
                send('sendMessage', {'chat_id': chat_id, 'text': 'دوباره پیام فوروارد شده رو بفرست', 'reply_markup': kb})
                del user_states[user_id]
    elif 'callback_query' in update:
        q = update['callback_query']
        user_id = q['from']['id']
        data_cb = q['data']
        msg_id = q['message']['message_id']
        chat_id = q['message']['chat']['id']
        if data_cb == 'no_thumb' and user_id in user_states:
            send('deleteMessage', {'chat_id': chat_id, 'message_id': msg_id})
            finish_super(chat_id, user_id)

    elif 'message' in update and 'text' in update['message']:
        text = update['message']['text']
        if text.startswith('/get_') and update['message']['chat']['type'] == 'private':
            key = text.split('_', 1)[1]
            if key in data:
                file_id = data[key]['file_id']
                cap = data[key]['caption']
                msg = send('sendVideo', {'chat_id': update['message']['chat']['id'], 'video': file_id, 'caption': cap})
                warn = send('sendMessage', {'chat_id': update['message']['chat']['id'], 'text': 'این محتوا تا ۲۰ ثانیه دیگر حذف خواهد شد'})
                def delete_later(chat, mid1, mid2):
                    time.sleep(20)
                    send('deleteMessage', {'chat_id': chat, 'message_id': mid1})
                    send('deleteMessage', {'chat_id': chat, 'message_id': mid2})
                t = threading.Thread(target=delete_later, args=(update['message']['chat']['id'], msg.json()['result']['message_id'], warn.json()['result']['message_id']))
                t.start()

    return 'ok'

def finish_super(chat_id, user_id):
    state = user_states[user_id]
    file_id = state['video']
    caption = state['caption']
    thumb = state.get('thumb')
    key = str(int(time.time()))
    data[key] = {'file_id': file_id, 'caption': caption}
    save_data(data)
    link = f'https://t.me/YourBotUsername?start=get_{key}'
    view_text = f'{caption}\n\n[مشاهده]({link})\n{CHANNEL_TAG}'
    send('sendPhoto', {'chat_id': chat_id, 'photo': thumb if thumb else file_id, 'caption': view_text, 'parse_mode': 'Markdown'})
    kb = {'keyboard': [[{'text': 'سوپر'}, {'text': 'پست'}]], 'resize_keyboard': True}
    send('sendMessage', {'chat_id': chat_id, 'text': 'به پنل برگشتی', 'reply_markup': kb})
    del user_states[user_id]

if __name__ == '__main__':
    app.run()
