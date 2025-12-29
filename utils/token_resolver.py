import aiohttp
from config import config

async def resolve_token(mint):
    url = f"https://api.helius.xyz/v0/token-metadata?api-key={config.helius_api_key}"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"mintAccounts": [mint]}) as r:
            data = await r.json()
            return data[0]["symbol"]
