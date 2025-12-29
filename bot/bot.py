# bot.py
from aiogram import Bot, Dispatcher

from bot.handlers import router
from middlewares import WhitelistMiddleware
from config import config

bot = Bot(config.bot_token)
dp = Dispatcher()

dp.message.middleware(WhitelistMiddleware())
dp.callback_query.middleware(WhitelistMiddleware())

dp.include_router(router)  # 👈 ВАЖНО



