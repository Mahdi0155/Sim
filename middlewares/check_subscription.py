from aiogram import BaseMiddleware
from aiogram.types import Update
from config import CHANNEL_ID
from aiogram.exceptions import TelegramBadRequest

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        if event.message is None:  # اگر پیام نبود (مثلا CallbackQuery یا چیز دیگه بود)، بیخیال شو
            return await handler(event, data)

        try:
            member = await event.bot.get_chat_member(CHANNEL_ID, event.message.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                from bot.keyboards.subscribe import subscribe_keyboard
                await event.message.answer(
                    "برای استفاده از ربات باید عضو کانال شوید.",
                    reply_markup=subscribe_keyboard()
                )
                return
        except TelegramBadRequest:
            pass
        await handler(event, data)
