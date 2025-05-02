# main.py

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request
from config import BOT_TOKEN, WEBHOOK_URL
from handlers import setup_handlers

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

setup_handlers(dp)

@app.post("/")
async def webhook_handler(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"status": "ok"}

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown():
    await bot.delete_webhook()

if __name__ == "__main__":
    import uvicorn
    @app.on_event("startup")
async def startup_event():
    await on_startup()
    uvicorn.run(app, host="0.0.0.0", port=8000)
    asyncio.run(on_shutdown())
