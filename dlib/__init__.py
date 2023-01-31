import logging

from .utils import yield_token
from .client import (
    Client, 
    run_clients
)

def logger(level="info"):
    # setup a basic logger

    logger = logging.getLogger(__name__)


    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(
        '[%(levelname)s][%(asctime)s]%(message)s'))
    logger.addHandler(sh)
    logger.setLevel(getattr(logging, level.upper()))

    return logger
