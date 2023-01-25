import logging

from .client import Client

# Yeah we should?
logging.getLogger(__name__).addHandler(logging.NullHandler())
