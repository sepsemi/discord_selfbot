import logging

from .client import Client
from .client import run_clients

# setup logger

def logger(level="info"):
    # setup a basic logger

    logger = logging.getLogger(__name__)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(
        '[%(asctime)s][%(levelname)s] %(name)s - %(message)s'))
    logger.addHandler(sh)
    logger.setLevel(getattr(logging, level.upper()))

    return logger
