# handlers/user.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from config import CHANNEL_ID
from utils.check_sub import is_subscribed

router = Router()

@router.message(CommandStart(deep_link=True))
async def send_file(message: Message):
    if not await is_subscribed(message.bot, message.from_user.id, CHANNEL_ID):
        join_button = [{"text": "عضویت در کانال", "url": f"https://t.me/c/{str(CHANNEL_ID)[4:]}"},
                       {"text": "بررسی عضویت", "callback_data": "check_sub"}]
        await message.answer(
            "برای دریافت فایل باید در کانال عضو شوید.",
            reply_markup={"inline_keyboard": [[join_button[0]], [join_button[1]]]}
        )
        return

    file_id = message.text.split(' ')[1]
    try:
        await message.bot.send_photo(chat_id=message.chat.id, photo=file_id)
    except:
        await message.bot.send_video(chat_id=message.chat.id, video=file_id)

    await message.answer("فایل دریافت شد، موفق باشید!")
