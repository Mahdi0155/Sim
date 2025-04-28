from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from keyboards.subscribe import subscribe_keyboard
from utils.check_subscription import check_user_subscription
from config import OWNER_ID
from aiogram.types import FSInputFile

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    if message.from_user.id == OWNER_ID:
        return  # مدیر نیازی به این هندلر نداره

    # اگر فایل آی‌دی همراه استارت بود
    if command.args:
        file_id = command.args
        
        # چک عضویت قبل از ارسال فایل
        is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
        if not is_subscribed:
            await message.answer(
                "برای مشاهده فایل ابتدا باید عضو کانال شوید.",
                reply_markup=subscribe_keyboard()
            )
            return
        
        # فرض می‌کنیم فایل ممکنه عکس یا ویدیو باشه
        try:
            await message.answer_chat_action("upload_photo")
            await message.answer_photo(photo=file_id)
        except Exception:
            try:
                await message.answer_chat_action("upload_video")
                await message.answer_video(video=file_id)
            except Exception:
                await message.answer("فایل قابل ارسال نیست یا معتبر نمی‌باشد.")
        
        return

    # اگر بدون آرگومان استارت زده بود (معمولی)
    is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
    if is_subscribed:
        await message.answer("خوش آمدید.")
    else:
        await message.answer(
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.",
            reply_markup=subscribe_keyboard()
        )
