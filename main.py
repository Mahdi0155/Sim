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

@app.on_event("startup")
async def startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown():
    await bot.session.close()
