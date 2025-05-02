import uvicorn
from fastapi import FastAPI, Request
from aiogram import Bot, types
from bot import dp, bot
from config import WEBHOOK_URL

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("Webhook deleted")

@app.post("/webhook")
async def handle_webhook(request: Request):
    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
