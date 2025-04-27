# utils/check_subscription.py

from aiogram import Bot
from config import CHANNEL_ID

async def check_user_subscription(user_id: int) -> bool:
    from loader import bot

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False
