# handlers/callbacks.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import CHANNEL_ID, CHANNEL_LINK
from utils.check_subscription import check_user_subscription
from keyboards.subscribe import subscribe_keyboard

router = Router()

@router.callback_query(F.data == "check_subscribe")
async def check_subscription(callback: CallbackQuery):
    is_subscribed = await check_user_subscription(callback.bot, callback.from_user.id)
    if is_subscribed:
        await callback.message.edit_text(
            "✅ عضویت شما تأیید شد!\nحالا میتوانید از ربات استفاده کنید."
        )
    else:
        await callback.message.edit_text(
            "❗ شما هنوز عضو کانال نیستید.\nلطفا ابتدا عضو شوید.",
            reply_markup=subscribe_keyboard()
        )
