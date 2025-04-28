from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.states import UploadStates
from config import OWNER_ID

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("سلام مدیر عزیز! لطفا فایل (عکس یا ویدیو) را بفرستید.")
    else:
        await message.answer("شما مجاز به استفاده از این بخش نیستید.")

@router.message(F.content_type.in_({"photo", "video"}))
async def file_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        print(f"Unauthorized user tried to send file: {message.from_user.id}")
        return
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    await state.update_data(file_id=file_id)
    await message.answer("فایل دریافت شد. حالا لطفا کپشن فایل را ارسال کنید.")
    await state.set_state(UploadStates.waiting_for_caption.state)

@router.message(UploadStates.waiting_for_caption)
async def caption_handler(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        print(f"Unauthorized user tried to send caption: {message.from_user.id}")
        return
    data = await state.get_data()
    file_id = data.get("file_id")
    caption = message.text

    bot_info = await message.bot.get_me()
    file_link = f"https://t.me/{bot_info.username}?start={file_id}"

    await message.answer(
        f"{caption}\n\n👉 [مشاهده فایل]({file_link})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await state.clear()
