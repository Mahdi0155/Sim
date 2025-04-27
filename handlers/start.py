# handlers/start.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from keyboards.subscribe import subscribe_keyboard
from utils.check_subscription import check_user_subscription
from config import OWNER_ID

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id

    if user_id == OWNER_ID:
        await message.answer("سلام ادمین عزیز!\nلطفاً یک عکس یا ویدیو ارسال کنید.")
    else:
        is_subscribed = await check_user_subscription(user_id)
        if is_subscribed:
            await message.answer("خوش آمدید! لطفاً منتظر دریافت فایل باشید.")
        else:
            await message.answer("برای استفاده از ربات، ابتدا در کانال عضو شوید.", reply_markup=subscribe_keyboard())

@router.callback_query(F.data == "check_subscribe")
async def check_subscribe_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(user_id)

    if is_subscribed:
        await callback.message.edit_text("عضویت شما تایید شد! لطفاً دوباره استارت کنید /start")
    else:
        await callback.message.edit_text("هنوز عضو نشدید، لطفاً ابتدا عضو شوید.", reply_markup=subscribe_keyboard())
