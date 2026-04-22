import logging

from dotenv import load_dotenv

load_dotenv()

LOG_FORMAT = "%(message)s"


def setup_logging(level=logging.INFO):
    """Configure root logger. Call once from CLI entry points."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
