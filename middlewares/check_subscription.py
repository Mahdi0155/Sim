# middlewares/check_subscription.py

from aiogram import BaseMiddleware
from aiogram.types import Message
from config import CHANNEL_ID
from aiogram.exceptions import TelegramBadRequest

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        try:
            member = await event.bot.get_chat_member(CHANNEL_ID, event.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                from bot.keyboards.subscribe import subscribe_keyboard
                await event.answer(
                    "برای استفاده از ربات باید عضو کانال شوید.",
                    reply_markup=subscribe_keyboard()
                )
                return
        except TelegramBadRequest:
            pass
        await handler(event, data)
