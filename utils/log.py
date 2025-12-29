# utils/log.py
from loguru import logger
import sys

def setup_logger():
    logger.remove()

    # 🔹 Консоль
    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level}</level> | "
               "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>"
    )

    # 🔹 Файл
    logger.add(
        "./logs/log_file.log",
        level="INFO",
        rotation="10 MB",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}"
    )
