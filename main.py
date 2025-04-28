import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, WEBHOOK_URL
from middlewares.check_subscription import CheckSubscriptionMiddleware
from handlers.start import router as start_router

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# اضافه کردن middleware بررسی عضویت
dp.update.middleware(CheckSubscriptionMiddleware())

# ثبت روت‌های مربوط به هندلرها
dp.include_router(start_router)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    await bot.set_my_commands([
        BotCommand(command="start", description="شروع ربات"),
    ])

async def on_shutdown(app):
    await bot.delete_webhook()

async def create_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    return app

if __name__ == "__main__":
    # اصلاح اینجا:
    app = asyncio.run(create_app())
    web.run_app(app, host="0.0.0.0", port=10000)
