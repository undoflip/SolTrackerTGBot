# config.py
from pydantic import BaseModel, Field, field_validator
from os import getenv
from dotenv import load_dotenv

load_dotenv()


class Config(BaseModel):
    bot_token: str
    whitelisted_user_ids: list[int]
    wss_solana_rpc_url: str
    wss_helius_rpc_url: str
    helius_api_key: str
    database_path: str = "sqlite+aiosqlite:///./data/tracker.db"
    max_subscriptions: int = 100
    log_level: str = "INFO"
    semaphore_limit: int = 8
    max_retry: int = 5

    @field_validator("whitelisted_user_ids", mode="before")
    @classmethod
    def parse_user_ids(cls, value):
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",")]
        return value


config = Config(
    bot_token=getenv("TELEGRAM_BOT_TOKEN"),
    whitelisted_user_ids=getenv("WHITELISTED_USER_IDS"),
    wss_solana_rpc_url=getenv("WSS_SOLANA_RPC_URL"),
    wss_helius_rpc_url=getenv("WSS_HELIUS_RPC_URL"),
    helius_api_key=getenv("HELIUS_API_KEY"),
    database_path=getenv("DATABASE_PATH", "sqlite+aiosqlite:///./data/tracker.db"),
    max_subscriptions=int(getenv("MAX_SUBSCRIPTIONS", 100)),
    log_level=getenv("LOG_LEVEL", "INFO"),
    semaphore_limit=int(getenv("SEMAPHORE_LIMIT", 8)),
    max_retry=int(getenv("MAX_RETRY", 5))
)

PHANTOM_FEE_ACCOUNTS = {
    "9yj3zvLS3fDMqi1F8zhkaWfq8TZpZWHe6cz1Sgt7djXf"
}

TOKEN_SYMBOLS = {
    "WETZjtprkDMCcUxPi9PfWnowMRZkiGGHDb9rABuRZ2U": "WET",
    "WET": "WETZjtprkDMCcUxPi9PfWnowMRZkiGGHDb9rABuRZ2U",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "So11111111111111111111111111111111111111112": "WSOL",
    "WSOL": "So11111111111111111111111111111111111111112",
    "SOL": "So11111111111111111111111111111111111111112"
}

AGGREGATORS = {
    "DFLOW": "DFlow Aggregator v4",
    "JUPITER": "Jupiter",
    "ORCA": "Orca",
    "RAYDIUM": "Raydium",
}