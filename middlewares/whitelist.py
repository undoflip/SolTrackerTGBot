# middlewares/whitelist.py
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from config import config

class WhitelistMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = getattr(event, "from_user", None)
        if not user or user.id not in config.whitelisted_user_ids:
            return
        return await handler(event, data)
