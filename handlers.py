# handlers.py

import json
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMINS, DB_FILE
import os
import string
import random

# --- FSM States ---
class SuperPost(StatesGroup):
    waiting_video = State()
    waiting_caption = State()
    waiting_buttons = State()

class PostForward(StatesGroup):
    waiting_forward = State()
    waiting_caption = State()

# --- Database functions ---
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def generate_file_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# --- Keyboards ---
def admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="سوپر", callback_data="super")],
        [InlineKeyboardButton(text="پست", callback_data="post")]
    ])

def back_to_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="بازگشت به پنل", callback_data="back_to_panel")]
    ])

# --- Handlers ---

def setup_handlers(dp: Dispatcher):

    @dp.message(F.text == "/start")
    async def start(msg: Message):
        if msg.from_user.id in ADMINS:
            await msg.answer("به پنل ادمین خوش آمدید.", reply_markup=admin_panel())
        else:
            await msg.answer("خوش آمدید!")

    @dp.callback_query(F.data == "back_to_panel")
    async def back(query: CallbackQuery):
        await query.message.edit_text("به پنل برگشتید.", reply_markup=admin_panel())

    # --- سوپر ---

    @dp.callback_query(F.data == "super")
    async def super_start(query: CallbackQuery, state: FSMContext):
        await query.message.edit_text("لطفاً ویدیوی خود را ارسال کنید:", reply_markup=back_to_panel())
        await state.set_state(SuperPost.waiting_video)

    @dp.message(SuperPost.waiting_video, F.video)
    async def super_video(msg: Message, state: FSMContext):
        await state.update_data(video=msg.video.file_id)
        await msg.answer("لطفاً کپشن را وارد کنید:", reply_markup=back_to_panel())
        await state.set_state(SuperPost.waiting_caption)

    @dp.message(SuperPost.waiting_caption)
    async def super_caption(msg: Message, state: FSMContext):
        await state.update_data(caption=msg.text)
        await msg.answer("در حال ساخت پیام...")
        data = await state.get_data()
        file_key = generate_file_key()
        db = load_db()
        db[file_key] = data["video"]
        save_db(db)
        preview = f"{data['caption']}\n\n[مشاهده](https://t.me/{msg.bot.username}?start={file_key})\n🔥@hottof | تُفِ داغ"
        await msg.answer_video(video=data["video"], caption=preview, parse_mode="Markdown")
        await state.clear()
        await msg.answer("به پنل برگشتید.", reply_markup=admin_panel())

    # --- پست ---

    @dp.callback_query(F.data == "post")
    async def post_start(query: CallbackQuery, state: FSMContext):
        await query.message.edit_text("لطفاً پیام را فوروارد کنید (عکس/ویدیو):", reply_markup=back_to_panel())
        await state.set_state(PostForward.waiting_forward)

    @dp.message(PostForward.waiting_forward, F.content_type.in_({"photo", "video"}))
    async def post_forward(msg: Message, state: FSMContext):
        await state.update_data(file=msg.photo[-1].file_id if msg.photo else msg.video.file_id,
                                type="photo" if msg.photo else "video")
        await msg.answer("لطفاً کپشن را وارد کنید:", reply_markup=back_to_panel())
        await state.set_state(PostForward.waiting_caption)

    @dp.message(PostForward.waiting_caption)
    async def post_caption(msg: Message, state: FSMContext):
        data = await state.get_data()
        text = f"{msg.text}\n\n🔥@hottof | تُفِ داغ"
        if data["type"] == "photo":
            await msg.answer_photo(photo=data["file"], caption=text)
        else:
            await msg.answer_video(video=data["file"], caption=text)
        await msg.answer("برای ارسال مجدد پیام جدید، لطفاً فوروارد کنید:", reply_markup=back_to_panel())
        await state.set_state(PostForward.waiting_forward)

    # --- Handle /start with file key ---
    @dp.message(F.text.startswith("/start "))
    async def start_with_key(msg: Message):
        key = msg.text.split(" ", 1)[1]
        db = load_db()
        if key in db:
            await msg.answer_video(video=db[key], caption="🔥@hottof | تُفِ داغ")
            await msg.answer("این محتوا تا ۲۰ ثانیه دیگر پاک خواهد شد")
            await asyncio.sleep(20)
            try:
                await msg.bot.delete_message(msg.chat.id, msg.message_id + 1)
                await msg.bot.delete_message(msg.chat.id, msg.message_id + 2)
            except:
                pass
        else:
            await msg.answer("محتوا یافت نشد یا منقضی شده است.")
