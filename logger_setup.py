from loguru import logger
import sys
from datetime import datetime
import os

def setup_logger(level: str = "INFO"):
    logger.remove()
    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    log_path = os.getenv("LOG_PATH", "logs")
    os.makedirs(log_path, exist_ok=True)
    # Console
    logger.add(sys.stderr, level=level, format=fmt)
    # Rotation file
    logger.add(f"{log_path}/bot_{{time:YYYY-MM-DD}}.log", rotation="10 MB", retention="7 days", level=level, format=fmt)
    return logger
