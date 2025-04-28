from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from keyboards.subscribe import subscribe_keyboard
from utils.check_subscription import check_user_subscription
from config import OWNER_ID

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    if message.from_user.id == OWNER_ID:
        return  # مدیر نیازی به این هندلر نداره
    
    is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
    if is_subscribed:
        await message.answer("خوش آمدید.")
    else:
        await message.answer(
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.", 
            reply_markup=subscribe_keyboard()
        )
