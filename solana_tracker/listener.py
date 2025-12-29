# solana_tracker/listener.py
import asyncio
import json
from websockets import connect
from config import config
from loguru import logger

WSS_URL = f"wss://mainnet.helius-rpc.com/?api-key={config.helius_api_key}"

async def listen_wallet(wallet: str, queue: asyncio.Queue):
    async with connect(WSS_URL, ping_interval=30, ping_timeout=30) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [wallet]},
                {"commitment": "confirmed"}
            ]
        }))

        logger.info(f"📡 Listening wallet: {wallet}")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if data.get("method") != "logsNotification":
                continue

            value = data["params"]["result"]["value"]
            if value["err"] is None:
                signature = value["signature"]
                logger.info(f"🔍 New tx for {wallet}: {signature}")
                await queue.put((signature, wallet))
