"""Travel Model One (TM1) — MTC's activity-based travel demand model."""

import logging

from dotenv import load_dotenv

load_dotenv()

LOG_FORMAT = "%(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger. Call once from CLI entry points."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
