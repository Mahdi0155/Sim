import asyncio
import random
import string

# Admin IDs
admins = [7189616405, 6387942633, 5459406429]

# File DB: key => Telegram file_id
files_db = {}

def generate_file_key(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def clean_message_later(chat_id, message_id, delay=20):
    await asyncio.sleep(delay)
    from bot import bot
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass
