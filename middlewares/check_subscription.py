from aiogram import BaseMiddleware
from aiogram.types import Update
from config import CHANNEL_ID
from aiogram.exceptions import TelegramBadRequest
from keyboards.subscribe import subscribe_keyboard  # فقط مسیر رو درست کردم

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        if event.message is None:  # همون شرط خودت، دست نزدم
            return await handler(event, data)

        try:
            member = await event.bot.get_chat_member(CHANNEL_ID, event.message.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await event.message.answer(
                    "برای استفاده از ربات باید عضو کانال شوید.",
                    reply_markup=subscribe_keyboard
                )
                return
        except TelegramBadRequest:
            pass

        await handler(event, data)
