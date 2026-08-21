"""Travel Model One (TM1) — MTC's activity-based travel demand model."""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

#: Console: bare messages, so a run reads cleanly in a terminal.
LOG_FORMAT = "%(message)s"

#: Run log file: timestamped and attributed, so a failure can be traced after
#: the fact.  ``RunModel.bat`` appended milestones to ``logs/feedback.rpt`` with
#: ``echo``; this keeps a full record instead.
FILE_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)-28s  %(message)s"
FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"

#: Third-party loggers that are noisy at DEBUG and say nothing useful about a
#: model run.  Pinned to WARNING so the run log stays readable.
_NOISY = ("matplotlib", "PIL", "urllib3", "numexpr", "asyncio", "fiona", "rasterio")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure console logging.  Call once from a CLI entry point.

    The root logger is left at DEBUG so a file handler added later can capture
    more than the console shows; the console handler itself is pinned to
    *level*.
    """
    logging.basicConfig(level=level, format=LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in root.handlers:
        handler.setLevel(level)
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)


def add_run_logfile(path: str | Path, level: int = logging.DEBUG) -> logging.Handler:
    """Tee the run to *path*, and return the handler so it can be detached.

    Records at *level* and above reach the file even when the console is quieter,
    so a completed run leaves behind more detail than was printed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=FILE_DATEFMT))
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)
    return handler


def remove_run_logfile(handler: logging.Handler | None) -> None:
    """Detach and close a handler from :func:`add_run_logfile`.

    Called in a ``finally`` so repeated ``run_model`` calls in one process do not
    stack handlers and write every run into every earlier run's log.
    """
    if handler is None:
        return
    logging.getLogger().removeHandler(handler)
    handler.close()


#: One minute, and one hour, in seconds -- the two thresholds a duration is
#: rendered against.
_MINUTE = 60
_HOUR = 3600


def fmt_elapsed(seconds: float) -> str:
    """A duration, as a person reads it: ``45s``, ``7.5m``, ``3h04m``.

    Here rather than in the runner or in status because both render durations and
    neither should import the other to do it.
    """
    if seconds < _MINUTE:
        return f"{seconds:.0f}s"
    if seconds < _HOUR:
        return f"{seconds / _MINUTE:.1f}m"
    hours = int(seconds // _HOUR)
    minutes = int((seconds % _HOUR) // _MINUTE)
    return f"{hours}h{minutes:02d}m"
