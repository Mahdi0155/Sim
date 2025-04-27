from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID

join_channel = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="عضویت در کانال",
                url=f"https://t.me/c/{str(CHANNEL_ID)[4:]}"  # تبدیل -100 به لینک t.me
            )
        ],
        [
            InlineKeyboardButton(
                text="بررسی عضویت",
                callback_data="check_membership"
            )
        ]
    ]
)
