# utils/rate_limit.py
import asyncio
from config import config

semaphore = asyncio.Semaphore(config.semaphore_limit)