# main.py

import uvicorn
from fastapi import FastAPI, Request
from aiogram import types
from bot import dp, bot
from config import WEBHOOK_URL, BOT_TOKEN

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print("وبهوک تنظیم شد")


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("وبهوک حذف شد")


@app.post("/webhook")
async def telegram_webhook(update: Request):
    telegram_update = types.Update.model_validate(await update.json())
    await dp.feed_update(bot=bot, update=telegram_update)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
