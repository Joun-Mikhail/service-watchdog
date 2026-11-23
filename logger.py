import logging
import os


def setup_logger():
    """Configure and return a logger that writes to logs/watchdog.log.

    Creates the logs directory if it does not exist. Each log entry includes
    a timestamp, log level, and message.
    """
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("watchdog")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler("logs/watchdog.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
