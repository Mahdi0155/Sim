# main.py

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums import ParseMode
from aiohttp import web
from config import BOT_TOKEN, CHANNEL_ID, OWNER_ID

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# وضعیت‌های ربات برای ذخیره عکس/ویدیو و کپشن
class UploadStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_caption = State()

# ساخت دکمه‌های چک عضویت
def join_channel_keyboard():
    buttons = [
        [InlineKeyboardButton(text="عضویت در کانال", url=f"https://t.me/c/{str(CHANNEL_ID)[4:]}")],
        [InlineKeyboardButton(text="بررسی عضویت", callback_data="check_subscribe")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# بررسی عضویت کاربر
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        await state.set_state(UploadStates.waiting_for_media)
        await message.answer("یک عکس یا ویدیو ارسال کن.")
    else:
        if await is_subscribed(message.from_user.id):
            await message.answer("به ربات خوش آمدید! فایل آماده نیست.")
        else:
            await message.answer("لطفا ابتدا در کانال عضو شوید:", reply_markup=join_channel_keyboard())

@dp.callback_query(Text("check_subscribe"))
async def check_subscription(callback_query: types.CallbackQuery):
    if await is_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("عضویت تایید شد! حالا /start رو بزنید.")
    else:
        await callback_query.message.edit_text("هنوز عضو نشدی! لطفا عضو شو و دوباره چک کن.", reply_markup=join_channel_keyboard())
    await callback_query.answer()

@dp.message(UploadStates.waiting_for_media)
async def media_handler(message: types.Message, state: FSMContext):
    if message.content_type in ["photo", "video"]:
        file_id = message.photo[-1].file_id if message.photo else message.video.file_id
        await state.update_data(file_id=file_id, file_type=message.content_type)
        await state.set_state(UploadStates.waiting_for_caption)
        await message.answer("حالا کپشن فایل رو بفرست.")
    else:
        await message.answer("فقط عکس یا ویدیو بفرست.")

@dp.message(UploadStates.waiting_for_caption)
async def caption_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = data.get("file_id")
    file_type = data.get("file_type")
    caption = message.text

    button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="مشاهده فایل", url=f"https://t.me/{(await bot.get_me()).username}?start=viewfile")]
        ]
    )

    await state.clear()

    if file_type == "photo":
        await message.answer_photo(file_id, caption=f"{caption}\n\n👇 مشاهده فایل 👇", reply_markup=button)
    elif file_type == "video":
        await message.answer_video(file_id, caption=f"{caption}\n\n👇 مشاهده فایل 👇", reply_markup=button)

# وبهوک ستاپ
async def on_startup(app):
    await bot.set_webhook("https://your-webhook-url/webhook")

async def on_shutdown(app):
    await bot.delete_webhook()

async def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    web.run_app(main(), host="0.0.0.0", port=10000)
