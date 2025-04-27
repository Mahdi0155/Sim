from aiogram import BaseMiddleware
from aiogram.types import Message
from config import CHANNEL_ID
from aiogram.exceptions import TelegramBadRequest

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        bot = data["bot"]
        try:
            member = await bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ("member", "administrator", "creator"):
                return await handler(event, data)
            else:
                await event.answer(
                    "برای استفاده از ربات باید در کانال عضو شوید.",
                    reply_markup=join_channel
                )
        except TelegramBadRequest:
            await event.answer(
                "مشکلی در بررسی عضویت پیش آمد. لطفا دوباره تلاش کنید.",
                reply_markup=join_channel
            )
