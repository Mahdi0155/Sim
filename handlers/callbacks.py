# handlers/callbacks.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import CHANNEL_ID
from utils.check_sub import is_subscribed

router = Router()

@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    if not await is_subscribed(callback.bot, callback.from_user.id, CHANNEL_ID):
        join_button = [{"text": "عضویت در کانال", "url": f"https://t.me/c/{str(CHANNEL_ID)[4:]}"},
                       {"text": "بررسی عضویت", "callback_data": "check_sub"}]
        await callback.message.edit_text(
            "شما هنوز عضو کانال نیستید، لطفا ابتدا عضو شوید.",
            reply_markup={"inline_keyboard": [[join_button[0]], [join_button[1]]]}
        )
    else:
        await callback.message.edit_text("عضویت شما تأیید شد! حالا میتوانید فایل را دریافت کنید.")
