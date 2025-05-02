import logging
from aiohttp import web
from bot import bot, dp, handle_update

logging.basicConfig(level=logging.INFO)

async def webhook_handler(request):
    data = await request.json()
    await handle_update(data)
    return web.Response()

async def on_startup(app):
    webhook_url = 'https://sim-dtlp.onrender.com'
    await bot.set_webhook(webhook_url)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post('/', webhook_handler)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, port=8080)
