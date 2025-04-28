import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, CHANNEL_LINK, WEBHOOK_URL

bot = Bot(token=BOT_TOKEN)
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
    ])from aiogram.types import FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

OWNER_ID = 6387942633
CHANNEL_ID = -1002207109791
CHANNEL_LINK = "https://t.me/hottof"

class UploadStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_broadcast_text = State()

async def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="بررسی عضویت", callback_data="check_subscribe")]
    ])

async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        if event.message is None:
            return await handler(event, data)
        try:
            member = await event.bot.get_chat_member(CHANNEL_ID, event.message.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await event.message.answer(
                    "برای استفاده از ربات باید عضو کانال شوید.",
                    reply_markup=await subscribe_keyboard()
                )
                return
        except TelegramBadRequest:
            pass
        await handler(event, data)

dp.message.register(start_command, CommandStart())
dp.message.register(file_handler, F.content_type.in_({"photo", "video"}))
dp.message.register(caption_handler, UploadStates.waiting_for_caption)
dp.message.register(broadcast_command, Command("broadcast"))
dp.message.register(handle_broadcast_text, UploadStates.waiting_for_broadcast_text)
dp.callback_query.register(check_subscription, F.data == "check_subscribe")async def start_command(message: Message, command: CommandStart):
    if message.from_user.id == OWNER_ID:
        await message.answer("سلام مدیر عزیز! لطفا فایل یا متن تبلیغاتی را بفرستید.")
        return
    if command.args:
        file_id = command.args
        is_sub = await is_subscribed(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                "برای دیدن فایل باید عضو کانال شوید.",
                reply_markup=await subscribe_keyboard()
            )
            return
        try:
            sent = await message.answer_photo(photo=file_id)
        except Exception:
            try:
                sent = await message.answer_video(video=file_id)
            except Exception:
                await message.answer("مشکلی در ارسال فایل پیش آمد.")
                return
        await message.answer("لطفاً فایل را ذخیره کنید، تا ۱۵ ثانیه دیگر حذف می‌شود!")
        await asyncio.sleep(15)
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent.message_id)
        except Exception:
            pass
        return
    is_sub = await is_subscribed(message.bot, message.from_user.id)
    if is_sub:
        await message.answer("خوش آمدید!")
    else:
        await message.answer(
            "برای استفاده از ربات باید عضو کانال شوید.",
            reply_markup=await subscribe_keyboard()
        )

async def file_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("فایل دریافت شد. لطفا کپشن فایل را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_caption)async def start_command(message: Message, command: CommandStart):
    if message.from_user.id == OWNER_ID:
        await message.answer("سلام مدیر عزیز! لطفا فایل یا متن تبلیغاتی را بفرستید.")
        return
    if command.args:
        file_id = command.args
        is_sub = await is_subscribed(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                "برای دیدن فایل باید عضو کانال شوید.",
                reply_markup=await subscribe_keyboard()
            )
            return
        try:
            sent = await message.answer_photo(photo=file_id)
        except Exception:
            try:
                sent = await message.answer_video(video=file_id)
            except Exception:
                await message.answer("مشکلی در ارسال فایل پیش آمد.")
                return
        await message.answer("لطفاً فایل را ذخیره کنید، تا ۱۵ ثانیه دیگر حذف می‌شود!")
        await asyncio.sleep(15)
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent.message_id)
        except Exception:
            pass
        return
    is_sub = await is_subscribed(message.bot, message.from_user.id)
    if is_sub:
        await message.answer("خوش آمدید!")
    else:
        await message.answer(
            "برای استفاده از ربات باید عضو کانال شوید.",
            reply_markup=await subscribe_keyboard()
        )

async def file_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("فایل دریافت شد. لطفا کپشن فایل را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_caption)async def send_file_with_delete(message: Message, file_id: str):
    try:
        msg = await message.answer_photo(photo=file_id)
    except:
        try:
            msg = await message.answer_video(video=file_id)
        except:
            await message.answer("فایل معتبر نیست.")
            return
    warning = await message.answer("⏳ این فایل را ذخیره کنید، تا ۱۵ ثانیه دیگر حذف می‌شود.")
    await asyncio.sleep(15)
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        await message.bot.delete_message(chat_id=message.chat.id, message_id=warning.message_id)
    except:
        pass

if __name__ == "__main__":
    import asyncio
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=10000)
