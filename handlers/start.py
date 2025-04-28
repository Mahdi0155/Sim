@router.message(CommandStart())
async def start_command(message: Message):
    if message.from_user.id == OWNER_ID:
        return  # مدیر نیازی به این هندلر نداره، ولش کنه
    # اینجا فقط کاربرای معمولی هندل میشن
    is_subscribed = await check_user_subscription(message.from_user.id)
    if is_subscribed:
        await message.answer("خوش آمدید.")
    else:
        await message.answer(
            "برای استفاده از ربات، ابتدا در کانال عضو شوید.", 
            reply_markup=subscribe_keyboard()
        )
