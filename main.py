# main.py
from flask import Flask
import requests
from config import TOKEN, WEBHOOK_URL
from bot import app

API_URL = f"https://api.telegram.org/bot{TOKEN}"

# تنظیم وب‌هوک در زمان اجرای برنامه
@app.before_first_request
def set_webhook():
    requests.get(f"{API_URL}/deleteWebhook")
    requests.get(f"{API_URL}/setWebhook?url={WEBHOOK_URL}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
