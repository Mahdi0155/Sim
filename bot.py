from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from utils import admins, files_db, generate_file_key, clean_message_later

TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class SuperPost(StatesGroup):
    waiting_video = State()
    waiting_caption = State()
    waiting_cover = State()

class SimplePost(StatesGroup):
    waiting_forward = State()
    waiting_caption = State()

@dp.message(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("خوش آمدید!")

@dp.message(commands=['panel'])
async def cmd_panel(message: types.Message):
    if message.from_user.id not in admins:
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("سوپر"), KeyboardButton("پست"))
    await message.answer("پنل ادمین", reply_markup=kb)

@dp.message(lambda msg: msg.text == "سوپر" and msg.from_user.id in admins)
async def handle_super(message: types.Message, state: FSMContext):
    await message.answer("لطفاً ویدیو را ارسال کنید.")
    await state.set_state(SuperPost.waiting_video)

@dp.message(SuperPost.waiting_video, content_types=types.ContentType.VIDEO)
async def super_got_video(message: types.Message, state: FSMContext):
    await state.update_data(video=message.video.file_id)
    await message.answer("لطفاً کپشن را وارد کنید.")
    await state.set_state(SuperPost.waiting_caption)

@dp.message(SuperPost.waiting_caption)
async def super_got_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("کاور ندارم", callback_data="no_cover")]])
    await message.answer("لطفاً کاور را بفرستید یا روی دکمه زیر بزنید.", reply_markup=kb)
    await state.set_state(SuperPost.waiting_cover)

@dp.callback_query(lambda c: c.data == "no_cover")
async def super_no_cover(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await send_super_preview(callback_query.message, state)

@dp.message(SuperPost.waiting_cover, content_types=types.ContentType.PHOTO)
async def super_got_cover(message: types.Message, state: FSMContext):
    await state.update_data(cover=message.photo[-1].file_id)
    await send_super_preview(message, state)

async def send_super_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    video_id = data['video']
    caption = data['caption']
    cover = data.get('cover')
    key = generate_file_key()
    files_db[key] = video_id
    text = f"{caption}\n\n[مشاهده](https://t.me/{(await bot.get_me()).username}?start={key})\n🔥@hottof | تُفِ داغ"
    await message.answer_photo(photo=cover if cover else video_id, caption=text, parse_mode='Markdown')
    await state.clear()
    kb = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("سوپر"), KeyboardButton("پست"))
    await message.answer("برگشت به پنل", reply_markup=kb)

@dp.message(lambda msg: msg.text == "پست" and msg.from_user.id in admins)
async def handle_post(message: types.Message, state: FSMContext):
    await message.answer("لطفاً پیام فوروارد شده را ارسال کنید.")
    await state.set_state(SimplePost.waiting_forward)

@dp.message(SimplePost.waiting_forward, content_types=[types.ContentType.PHOTO, types.ContentType.VIDEO])
async def post_got_media(message: types.Message, state: FSMContext):
    await state.update_data(media=message)
    await message.answer("لطفاً کپشن را بنویسید.")
    await state.set_state(SimplePost.waiting_caption)

@dp.message(SimplePost.waiting_caption)
async def post_got_caption(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_msg = data['media']
    caption = f"{message.text}\n\n🔥@hottof | تُفِ داغ"
    if media_msg.photo:
        await message.answer_photo(media_msg.photo[-1].file_id, caption=caption)
    elif media_msg.video:
        await message.answer_video(media_msg.video.file_id, caption=caption)
    await state.set_state(SimplePost.waiting_forward)
    await message.answer("دوباره پیام فوروارد شده بفرست یا برای برگشت به پنل از دکمه زیر استفاده کن.",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("بازگشت به پنل")))

@dp.message(lambda msg: msg.text == "بازگشت به پنل")
async def back_to_panel(message: types.Message):
    await cmd_panel(message)

@dp.message(commands=['start'])
async def handle_start_link(message: types.Message):
    if message.text.startswith("/start "):
        key = message.text.split(" ")[1]
        if key in files_db:
            video_id = files_db[key]
            msg = await message.answer_video(video_id)
            await message.answer("این محتوا تا ۲۰ ثانیه دیگر حذف می‌شود.")
            await clean_message_later(chat_id=message.chat.id, message_id=msg.message_id, delay=20)

async def handle_update(data):
    update = types.Update.to_object(data)
    return await dp.feed_update(bot, update)
