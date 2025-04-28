import logging
import random
import string
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = '7086274656:AAEkxL0Xwktb_PVddppdNZ8S88ggGNpRMqI'

ADMINS = [6387942633, 6039863213, 5459406429, 7189616405]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# حافظه ساده برای نگه داشتن اطلاعات فایل‌ها
file_storage = {}

# حالت‌ها
user_states = {}

# متن ثابت
FIXED_TEXT = "@hottof | تُفِ داغ"

# دکمه پنل ادمین
admin_panel_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
admin_panel_keyboard.add(types.KeyboardButton("➕ آپلود فایل"))

# مرحله گرفتن اطلاعات
class UploadStep:
    WAITING_FILE = 1
    WAITING_CAPTION = 2
    WAITING_COVER = 3

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    args = message.get_args()
    if args.startswith('f_'):
        file_code = args[2:]
        file_info = file_storage.get(file_code)
        if file_info:
            try:
                await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_VIDEO)
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="حال میکنی عضویت اجباری ندارماا😁",
                )
                await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_DOCUMENT)
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=file_info['file_id']
                )
            except Exception as e:
                await message.answer("خطایی رخ داد!")
        else:
            await message.answer("فایل یافت نشد یا منقضی شده است.")
    else:
        await message.answer("خوش آمدید!")

@dp.message_handler(commands=['panel'])
async def panel_command(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("سلام آقا مدیر شومبولت دهنم", reply_markup=admin_panel_keyboard)
    else:
        await message.answer("بچه خوشکل بیا کیرمو بخور")

@dp.message_handler(lambda message: message.text == "➕ آپلود فایل")
async def upload_file_start(message: types.Message):
    if message.from_user.id in ADMINS:
        user_states[message.from_user.id] = {'step': UploadStep.WAITING_FILE}
        await message.answer("سوپر رو بفرست قربون خایه هات برم 🥚🥚")

@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return

    state = user_states.get(user_id)

    if not state:
        return

    step = state['step']

    if step == UploadStep.WAITING_FILE:
        if message.content_type not in ['photo', 'video', 'document']:
            await message.answer(" داداش سوپر رو بده بیاد 🫣")
            return
        
        # بررسی سایز فایل
        file_size = 0
        if message.document:
            file_size = message.document.file_size
        elif message.video:
            file_size = message.video.file_size
        elif message.photo:
            file_size = message.photo[-1].file_size

        if file_size > 200 * 1024 * 1024:
            await message.answer("حجم فایل نباید بیشتر از ۲۰۰ مگابایت باشد.")
            return
        
        # ذخیره اطلاعات فایل
        if message.document:
            state['file_id'] = message.document.file_id
        elif message.video:
            state['file_id'] = message.video.file_id
        elif message.photo:
            state['file_id'] = message.photo[-1].file_id

        state['step'] = UploadStep.WAITING_CAPTION
        await message.answer("ارباب کپشن سکسیتو بزن 🤤 آیدی چنلو خودم میزنم")

    elif step == UploadStep.WAITING_CAPTION:
        state['caption'] = message.text
        state['step'] = UploadStep.WAITING_COVER
        await message.answer("عکس کاور هم بفرست شومبول طلا")

    elif step == UploadStep.WAITING_COVER:
        if message.content_type != 'photo':
            await message.answer("چیکار داری میکنی دلقک عکس کاور بفرست")
            return

        cover_file_id = message.photo[-1].file_id
        file_id = state['file_id']
        caption_text = f"{state['caption']}\n\n{FIXED_TEXT}"

        # ساخت کد اختصاصی
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        file_storage[code] = {
            'file_id': file_id,
        }

        # ساخت لینک
        link = f"https://t.me/{(await bot.get_me()).username}?start=f_{code}"

        # دکمه مشاهده فایل
        buttons = InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="مشاهده فایل", url=link)
        )

        # ارسال پیام نهایی
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=cover_file_id,
            caption=caption_text,
            reply_markup=buttons
        )

        await message.answer("بفرما قربان فایل نهایی خدمت شما 🍌")

        # پاک کردن وضعیت کاربر
        user_states.pop(user_id, None)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
