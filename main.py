# main.py
import asyncio
import httpx
from workers import tx_worker
from utils.log import setup_logger, logger
from utils import WalletDispatcher
from bot import dp, bot
from db import init_db
from solana_tracker import parse_transaction
from config import config

async def main():
    setup_logger()
    logger.info("🚀 Bot starting...")

    await init_db()
    logger.info("✅ Database initialized")


    queue = asyncio.Queue()

    limits = httpx.Limits(
        max_connections=8,
        max_keepalive_connections=2
    )

    timeout = httpx.Timeout(15.0)

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        http2=False
    ) as client:
        wallet_dispatcher = WalletDispatcher(queue)

        tasks = [
            asyncio.create_task(wallet_dispatcher.run()),   # 👈 ВАЖНО
            asyncio.create_task(tx_worker(queue, client)),
            asyncio.create_task(tx_worker(queue, client)),
            asyncio.create_task(dp.start_polling(bot)),
        ]

        await asyncio.gather(*tasks)

asyncio.run(main())