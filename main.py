import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, BotCommand
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN = "7086274656:AAEpviQqS2hKPeyvsHt4rQSXIgrehlW2Ums"
OWNER_ID = 6387942633
CHANNEL_ID = -1002207109791
CHANNEL_LINK = "https://t.me/hottof"
WEBHOOK_URL = "https://sim-n0vy.onrender.com/webhook"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

class UploadStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_broadcast = State()

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="بررسی عضویت", callback_data="check_sub")]
    ])
    @dp.message(CommandStart())
async def start_command(message: Message, command: CommandStart, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        await message.answer(
            "سلام مدیر عزیز\n"
            "میتوانید فایل آپلود کنید یا پیام همگانی ارسال کنید."
        )

        if command.args:
            is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
            if not is_subscribed:
                await message.answer(
                    "برای مشاهده فایل ابتدا باید عضو کانال شوید.",
                    reply_markup=subscribe_keyboard()
                )
                return

            try:
                await message.answer_chat_action("upload_photo")
                # ادامه کدها...
            msg = await message.answer_photo(photo=command.args)
            await asyncio.sleep(15)
            await msg.delete()
            await message.answer("این فایل ۱۵ ثانیه پس از ارسال حذف شد.")
        except Exception:
            try:
                await message.answer_chat_action("upload_video")
                msg = await message.answer_video(video=command.args)
                await asyncio.sleep(15)
                await msg.delete()
                await message.answer("این فایل ۱۵ ثانیه پس از ارسال حذف شد.")
            except Exception:
                await message.answer("فایل معتبر نیست.")
        return

    is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
    if is_subscribed:
        await message.answer("خوش آمدید.")
    else:
        await message.answer(
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.",
            reply_markup=subscribe_keyboard()
            )
       @dp.message(F.text == "پیام همگانی")
async def mass_message_request(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("لطفا متن پیام همگانی را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_mass_message)

@dp.message(UploadStates.waiting_for_mass_message)
async def mass_message_send(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    text = message.text
    users = await get_all_users()
    for user_id in users:
        try:
            await message.bot.send_message(chat_id=user_id, text=text)
            await asyncio.sleep(0.05)
        except Exception:
            continue
    await message.answer("پیام به همه کاربران ارسال شد.")
    await state.clear()

@dp.message(F.content_type.in_({"photo", "video"}))
async def file_upload(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("فایل دریافت شد. لطفاً کپشن فایل را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_caption)

@dp.message(UploadStates.waiting_for_caption)
async def file_caption(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    file_id = data.get("file_id")
    caption = message.text
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={file_id}"
    await message.answer(
        f"{caption}\n\n👉 [مشاهده فایل]({link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await state.clear() 
@router.message(CommandStart())
async def start_command(message: Message, command: CommandStart):
    if message.from_user.id == OWNER_ID:
        await message.answer("سلام مدیر عزیز!")
        return
    if command.args:
        file_id = command.args
        is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
        if not is_subscribed:
            await message.answer("برای مشاهده فایل عضو کانال شوید.", reply_markup=subscribe_keyboard())
            return
        try:
            sent = await message.answer_photo(photo=file_id)
        except:
            try:
                sent = await message.answer_video(video=file_id)
            except:
                await message.answer("فایل نامعتبر است.")
                return
        await message.answer("این فایل را ذخیره کنید! تا ۱۵ ثانیه دیگر حذف می‌شود.")
        await asyncio.sleep(15)
        try:
            await message.bot.delete_message(message.chat.id, sent.message_id)
        except:
            pass
        return
    is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
    if is_subscribed:
        await message.answer("خوش آمدید!")
    else:
        await message.answer("لطفا ابتدا عضو کانال شوید.", reply_markup=subscribe_keyboard())

@router.callback_query(F.data == "check_subscribe")
async def check_subscription(callback: CallbackQuery):
    is_subscribed = await check_user_subscription(callback.bot, callback.from_user.id)
    if is_subscribed:
        await callback.message.edit_text("✅ عضویت شما تأیید شد!")
    else:
        await callback.message.edit_text(
            "❗ شما هنوز عضو کانال نیستید.\nلطفاً ابتدا عضو شوید.",
            reply_markup=subscribe_keyboard()
        )
        @router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("لطفا متن پیام همگانی را ارسال کنید:")
    await state.set_state(UploadStates.waiting_for_broadcast)

@router.message(UploadStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    text = message.text
    await state.clear()
    await message.answer("در حال ارسال پیام به همه کاربران...")
    try:
        with open("users.txt", "r") as f:
            user_ids = f.read().splitlines()
    except FileNotFoundError:
        await message.answer("هیچ کاربری پیدا نشد.")
        return
    sent = 0
    for user_id in user_ids:
        try:
            await message.bot.send_message(chat_id=int(user_id), text=text)
            sent += 1
        except:
            continue
    await message.answer(f"پیام به {sent} نفر ارسال شد.")

@router.message()
async def save_users(message: Message):
    if message.from_user.id == OWNER_ID:
        return
    try:
        with open("users.txt", "r") as f:
            user_ids = f.read().splitlines()
    except FileNotFoundError:
        user_ids = []
    if str(message.from_user.id) not in user_ids:
        with open("users.txt", "a") as f:
            f.write(str(message.from_user.id) + "\n")
