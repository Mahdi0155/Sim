import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest
from aiogram import BaseMiddleware
from aiogram.types import FSInputFile
from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, CHANNEL_LINK

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# وضعیت‌ها (States)
class UploadStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_broadcast_text = State()

# کیبورد عضویت
def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="بررسی عضویت", callback_data="check_subscribe")]
    ])

# چک عضویت
async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

# میدلور چک عضویت
class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if hasattr(event, 'message') and event.message:
            try:
                member = await event.bot.get_chat_member(CHANNEL_ID, event.message.from_user.id)
                if member.status not in ["member", "administrator", "creator"]:
                    await event.message.answer(
                        "برای استفاده از ربات باید عضو کانال شوید.",
                        reply_markup=subscribe_keyboard()
                    )
                    return
            except TelegramBadRequest:
                pass
        await handler(event, data)

# دستور start
async def start_command(message: Message, command: CommandStart, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        await message.answer("سلام مدیر عزیز! لطفا فایل یا متن تبلیغاتی را بفرستید.")
        return
    
    if command.args:
        file_id = command.args
        is_sub = await is_subscribed(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                "برای دیدن فایل باید عضو کانال شوید.",
                reply_markup=subscribe_keyboard()
            )
            return
        await send_file_with_delete(message, file_id)
    else:
        is_sub = await is_subscribed(message.bot, message.from_user.id)
        if is_sub:
            await message.answer("خوش آمدید!")
        else:
            await message.answer(
                "برای استفاده از ربات باید عضو کانال شوید.",
                reply_markup=subscribe_keyboard()
            )

# ارسال فایل با حذف بعد از ۱۵ ثانیه
async def send_file_with_delete(message: Message, file_id: str):
    try:
        msg = await message.answer_photo(photo=file_id)
    except Exception:
        try:
            msg = await message.answer_video(video=file_id)
        except Exception:
            await message.answer("فایل معتبر نیست.")
            return
    warning = await message.answer("⏳ این فایل را ذخیره کنید، تا ۱۵ ثانیه دیگر حذف می‌شود.")
    await asyncio.sleep(15)
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=warning.message_id)
    except Exception:
        pass

# دریافت فایل از مدیر
async def file_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("فایل دریافت شد. لطفا کپشن فایل را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_caption)

# دریافت کپشن فایل
async def caption_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = data.get("file_id")
    caption = message.text

    buttons = [
        [InlineKeyboardButton(text="دریافت فایل", url=f"https://t.me/{message.bot.username}?start={file_id}")]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await message.bot.send_photo(chat_id=OWNER_ID, photo=file_id, caption=caption, reply_markup=markup)
    except Exception:
        await message.bot.send_video(chat_id=OWNER_ID, video=file_id, caption=caption, reply_markup=markup)
    
    await message.answer("فایل و کپشن آماده شد و لینک ساخته شد!")
    await state.clear()

# دستور broadcast
async def broadcast_command(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("متن تبلیغاتی را بفرستید:")
    await state.set_state(UploadStates.waiting_for_broadcast_text)

# ارسال تبلیغ
async def handle_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    # اینجا باید لیست کاربران رو داشته باشی و ارسال کنی
    await message.answer("تبلیغ ارسال شد (اینجا ارسال به کاربران باید اضافه بشه).")
    await state.clear()

# بررسی دکمه عضویت
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_sub = await is_subscribed(callback.bot, user_id)
    if is_sub:
        await callback.message.answer("شما عضو شدید! حالا دوباره /start رو بزنید.")
    else:
        await callback.message.answer("هنوز عضو نشدید. لطفا عضو شوید و دوباره تلاش کنید.")

# ثبت هندلرها
dp.message.register(start_command, CommandStart())
dp.message.register(file_handler, F.content_type.in_({"photo", "video"}))
dp.message.register(caption_handler, UploadStates.waiting_for_caption)
dp.message.register(broadcast_command, Command("broadcast"))
dp.message.register(handle_broadcast_text, UploadStates.waiting_for_broadcast_text)
dp.callback_query.register(check_subscription, F.data == "check_subscribe")

# برنامه اصلی
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
