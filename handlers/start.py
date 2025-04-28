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

    # چک عضویت کاربر
    is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
    if not is_subscribed:
        await message.answer(
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.", 
            reply_markup=subscribe_keyboard()
        )
        return

    # چک پیلود (آیا کاربر از لینک "مشاهده فایل" وارد شده؟)
    payload = message.text.split(' ')
    if len(payload) > 1:
        file_id = payload[1]
        try:
            # سعی کن فایل رو به عنوان عکس ارسال کنی
            await message.answer_chat_action("upload_photo")
            await message.answer_photo(photo=file_id)
        except:
            try:
                # اگر عکس نبود، سعی کن ویدیو بفرستی
                await message.answer_chat_action("upload_video")
                await message.answer_video(video=file_id)
            except:
                await message.answer("متاسفم، فایل قابل ارسال نیست.")
        return

    # اگر پیلود نداشت (یعنی فقط /start بود)
    await message.answer("خوش آمدید.")
