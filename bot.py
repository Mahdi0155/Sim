from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from config import BOT_TOKEN, ADMINS
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from db import save_video, get_video
import uuid
import asyncio

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# وضعیت‌ها
class SuperPostState(StatesGroup):
    waiting_video = State()
    waiting_caption = State()
    waiting_cover = State()

class PostForwardState(StatesGroup):
    waiting_forward = State()
    waiting_caption = State()

# دکمه برگشت
def back_to_panel():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="بازگشت به پنل")]
    ], resize_keyboard=True)

# دکمه پنل اصلی
panel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="سوپر"), KeyboardButton(text="پست")]
    ],
    resize_keyboard=True
)

# دکمه شیشه‌ای بدون کاور
skip_cover_markup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="بدون کاور", callback_data="skip_cover")]]
)

# هندلر استارت
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("خوش آمدید!", reply_markup=None)

# پنل ادمین
@dp.message(Command("panel"))
async def admin_panel(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("وارد پنل شدید.", reply_markup=panel_keyboard)
    else:
        await message.answer("شما دسترسی ندارید.")

# شروع سوپر
@dp.message(lambda m: m.text == "سوپر")
async def super_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.set_state(SuperPostState.waiting_video)
    await message.answer("لطفاً ویدیوی خود را ارسال کنید.", reply_markup=back_to_panel())

@dp.message(SuperPostState.waiting_video, lambda m: m.video)
async def super_get_video(message: types.Message, state: FSMContext):
    await state.update_data(video=message.video.file_id)
    await state.set_state(SuperPostState.waiting_caption)
    await message.answer("کپشن را وارد کنید:")

@dp.message(SuperPostState.waiting_caption)
async def super_get_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await state.set_state(SuperPostState.waiting_cover)
    await message.answer("کاور ویدیو را ارسال کنید یا گزینه زیر را بزنید:", reply_markup=skip_cover_markup)

@dp.message(SuperPostState.waiting_cover, lambda m: m.photo)
async def super_get_cover(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cover = message.photo[-1].file_id
    await finish_super(message, data, cover)
    await state.clear()

@dp.callback_query(lambda c: c.data == "skip_cover")
async def skip_cover_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await finish_super(callback.message, data, None)
    await callback.message.delete()
    await state.clear()

async def finish_super(message, data, cover):
    file_id = data["video"]
    caption = data["caption"]
    file_key = str(uuid.uuid4())

    save_video(file_key, file_id, caption, cover)

    link = f"https://t.me/{(await bot.me()).username}?start={file_key}"
    text = f"{caption or ''}\n\n[مشاهده]({link})\n🔥hottof | تُفِ داغ"

    await message.answer_photo(
        photo=cover if cover else file_id,
        caption=text,
        parse_mode="Markdown",
        reply_markup=panel_keyboard
    )

# کاربر استارت با لینک
@dp.message(CommandStart(deep_link=True))
async def deep_link_start(message: types.Message, command: CommandStart):
    key = command.args
    data = get_video(key)

    if not data:
        await message.answer("این محتوا یافت نشد.")
        return

    msg = await message.answer_video(
        video=data["video"],
        caption=(data["caption"] + "\n🔥hottof | تُفِ داغ") if data["caption"] else "🔥hottof | تُفِ داغ"
    )

    await message.answer("این محتوا تا ۲۰ ثانیه دیگر حذف خواهد شد.")
    await asyncio.sleep(20)
    await bot.delete_message(message.chat.id, msg.message_id)

# دکمه پست
@dp.message(lambda m: m.text == "پست")
async def post_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.set_state(PostForwardState.waiting_forward)
    await message.answer("لطفاً یک پیام فوروارد شده یا مدیا ارسال کنید.", reply_markup=back_to_panel())

@dp.message(PostForwardState.waiting_forward, lambda m: m.photo or m.video)
async def post_get_media(message: types.Message, state: FSMContext):
    media = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(media=media, type="photo" if message.photo else "video")
    await state.set_state(PostForwardState.waiting_caption)
    await message.answer("کپشن را وارد کنید:")

@dp.message(PostForwardState.waiting_caption)
async def post_get_caption(message: types.Message, state: FSMContext):
    data = await state.get_data()
    caption = message.text + "\n🔥@hottof | تُفِ داغ"

    if data["type"] == "photo":
        await message.answer_photo(photo=data["media"], caption=caption)
    else:
        await message.answer_video(video=data["media"], caption=caption)

    await state.set_state(PostForwardState.waiting_forward)
    await message.answer("دوباره پیام جدید را فوروارد کنید یا مدیا بفرستید.", reply_markup=back_to_panel())
