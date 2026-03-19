"""
Logging configuration and utilities.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

from app.config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()

    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("face_attendance")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    if logger.handlers:
        return logger

    formatter = logging.Formatter(settings.LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = settings.LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("face_attendance")
