from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

BOT_TOKEN = 'توکن رباتت'
OWNER_ID = 123456789  # آیدی عددی ادمین

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# دیتابیس موقت فایل ها
file_storage = {}

@dp.message(CommandStart(deep_link=True))
async def start(message: Message, command: CommandStart):
    if command.args:
        file_id = command.args
        file_info = file_storage.get(file_id)
        if file_info:
            if file_info["type"] == "photo":
                await message.answer_photo(file_info["file_id"], caption=file_info["caption"])
            elif file_info["type"] == "video":
                await message.answer_video(file_info["file_id"], caption=file_info["caption"])
        else:
            await message.answer("فایل پیدا نشد یا منقضی شده.")
    else:
        await message.answer("سلام! فایل خاصی انتخاب نکردید.")

@dp.message()
async def handle_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("شما دسترسی ندارید.")
        return

    if message.photo or message.video:
        file_id = message.photo[-1].file_id if message.photo else message.video.file_id
        file_type = "photo" if message.photo else "video"

        # ذخیره فایل برای مرحله بعد
        file_storage[message.from_user.id] = {"file_id": file_id, "type": file_type}
        await message.answer("باشه! حالا کپشن رو بفرست.")
    
    elif message.text and message.from_user.id in file_storage:
        file_storage[message.from_user.id]["caption"] = message.text

        file_data = file_storage[message.from_user.id]
        send_id = f"{message.from_user.id}_{int(asyncio.get_running_loop().time())}"

        # ذخیره نهایی با send_id
        file_storage[send_id] = {
            "file_id": file_data["file_id"],
            "caption": file_data["caption"],
            "type": file_data["type"]
        }

        bot_info = await bot.get_me()
        bot_username = bot_info.username

        button = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="مشاهده فایل", url=f"https://t.me/{bot_username}?start={send_id}")]
            ]
        )

        await message.answer(f"{file_data['caption']}\n\n", reply_markup=button)

        # پاک کردن موقت
        del file_storage[message.from_user.id]
    else:
        await message.answer("لطفا اول عکس یا ویدیو بفرست.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
