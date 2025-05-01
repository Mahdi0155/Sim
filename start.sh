#!/bin/bash

echo "در حال اجرای ربات اصلی..."
python uploader_bot.py &

echo "در حال اجرای ربات آپلودر..."
python bot.py &  # برای ربات آپلودر از همون نام استفاده می‌کنیم

echo "در حال اجرای ربات ارسال‌کننده..."
python sender_bot.py &

echo "در حال اجرای ربات عضویت..."
python membership_bot.py &

wait
