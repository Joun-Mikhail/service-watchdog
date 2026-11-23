"""Logging setup: rotating log file plus console output."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(log_file="logs/watchdog.log", level=logging.INFO):
    """Return the 'watchdog' logger writing to log_file (rotated at 1 MB, 5 backups) and stdout."""
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    logger = logging.getLogger("watchdog")
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
