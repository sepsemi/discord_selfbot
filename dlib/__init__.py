import logging

from .utils import yield_token
from .client import (
    Client, 
    run_clients
)

"""
logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger("websockets")
_logger.setLevel(logging.DEBUG)
"""

def logger(level="info"):
    # setup a basic logger

    logger = logging.getLogger(__name__)

    log_formatter = logging.Formatter('[%(levelname)s][%(asctime)s]%(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    file_handler = logging.FileHandler('etc/discord.log')
    file_handler.setFormatter(log_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.setLevel(getattr(logging, level.upper()))

    return logger
