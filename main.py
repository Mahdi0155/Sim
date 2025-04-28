import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.middleware import BaseMiddleware
from aiogram import Router
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, CHANNEL_LINK, WEBHOOK_URL

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class UploadStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_broadcast_text = State()

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if event.message is None:
            return await handler(event, data)
        try:
            member = await event.bot.get_chat_member(CHANNEL_ID, event.message.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await event.message.answer(
                    "You must join the channel to use the bot.",
                    reply_markup=subscribe_keyboard()
                )
                return
        except TelegramBadRequest:
            pass
        await handler(event, data)

def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="Check Subscription", callback_data="check_subscribe")]
    ])

async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

async def start_command(message: Message, command: CommandStart):
    if message.from_user.id == OWNER_ID:
        await message.answer("Welcome Admin! Please send a file or text for broadcast.")
        return
    if command.args:
        file_id = command.args
        is_sub = await is_subscribed(message.bot, message.from_user.id)
        if not is_sub:
            await message.answer(
                "You must join the channel to view the file.",
                reply_markup=subscribe_keyboard()
            )
            return
        try:
            sent = await message.answer_photo(photo=file_id)
        except:
            try:
                sent = await message.answer_video(video=file_id)
            except:
                await message.answer("File error.")
                return
        await message.answer("Please save the file, it will be deleted in 15 seconds.")
        await asyncio.sleep(15)
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=sent.message_id)
        except:
            pass
        return
    is_sub = await is_subscribed(message.bot, message.from_user.id)
    if is_sub:
        await message.answer("Welcome!")
    else:
        await message.answer(
            "You must join the channel to use the bot.",
            reply_markup=subscribe_keyboard()
        )

async def file_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("File received. Now send the caption.")
    await state.set_state(UploadStates.waiting_for_caption)

async def caption_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    file_id = data.get("file_id")
    caption = message.text
    link = f"https://t.me/{(await bot.get_me()).username}?start={file_id}"
    try:
        await message.bot.send_photo(chat_id=message.chat.id, photo=file_id, caption=f"{caption}\n\n🔗 {link}")
    except:
        try:
            await message.bot.send_video(chat_id=message.chat.id, video=file_id, caption=f"{caption}\n\n🔗 {link}")
        except:
            await message.answer("Failed to send media.")
    await state.clear()

async def broadcast_command(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Send the message to broadcast to all users.")
    await state.set_state(UploadStates.waiting_for_broadcast_text)

users = set()

async def handle_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    text = message.text
    success = 0
    fail = 0
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            success += 1
        except:
            fail += 1
    await message.answer(f"Broadcast completed!\nSuccess: {success}\nFailed: {fail}")
    await state.clear()

async def check_subscription(callback: CallbackQuery):
    is_sub = await is_subscribed(callback.bot, callback.from_user.id)
    if is_sub:
        await callback.message.answer("Subscription verified. Please use /start again.")
    else:
        await callback.message.answer(
            "You are not subscribed yet.",
            reply_markup=subscribe_keyboard()
        )

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    await bot.set_my_commands([types.BotCommand(command="start", description="Start the bot"), types.BotCommand(command="broadcast", description="Broadcast a message")])

async def on_shutdown(app):
    await bot.delete_webhook()

dp.message.middleware(CheckSubscriptionMiddleware())
dp.message.register(start_command, CommandStart())
dp.message.register(file_handler, F.content_type.in_({"photo", "video"}))
dp.message.register(caption_handler, UploadStates.waiting_for_caption)
dp.message.register(broadcast_command, Command("broadcast"))
dp.message.register(handle_broadcast_text, UploadStates.waiting_for_broadcast_text)
dp.callback_query.register(check_subscription, F.data == "check_subscribe")

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=10000)
