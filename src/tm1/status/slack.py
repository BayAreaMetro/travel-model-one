"""Slack webhook notifications for TM1 model runs.

The webhook URL comes from one of two places, checked in order:

1. ``SLACK_WEBHOOK_URL`` -- the URL itself;
2. ``TM1_SLACK_WEBHOOK_FILE`` -- a file holding it, for a shared team webhook
   nobody wants to paste onto every machine.

Both live in `.env`.  With neither, runs log their milestones and send nothing,
which is a working configuration and not an error.
"""

import logging
import os
import socket
from pathlib import Path

import requests

log = logging.getLogger(__name__)

#: The file holding the webhook URL.  The **whole path** is configured, not a name
#: under some assumed share: neither the share nor the file name is guaranteed to
#: stay where it is, and a path this code cannot see is one nobody can fix from
#: `.env`.
_WEBHOOK_FILE_VAR = "TM1_SLACK_WEBHOOK_FILE"


def _webhook_file() -> Path | None:
    """The file holding the webhook URL, or None when `.env` does not name one."""
    configured = os.environ.get(_WEBHOOK_FILE_VAR)
    return Path(configured) if configured else None

level = "minimal"  # "off", "minimal" (start/stop/failure), or "verbose" (every step)


def _get_webhook_url() -> str | None:
    """Resolve the Slack webhook URL from env var or MTC default file."""
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        return url.strip()

    path = _webhook_file()
    if path and path.exists():
        try:
            return path.read_text().strip()
        except OSError:
            log.warning("Cannot read webhook file: %s", path)

    return None


def _get_prefix() -> str:
    """Build a message prefix from INSTANCE env var or hostname."""
    instance = os.environ.get("INSTANCE")
    if instance:
        return f"*{instance}*"
    return f"*{socket.gethostname()}*"


def notify(message: str, *, verbose_only: bool = False) -> None:
    """Post a message to Slack. Falls back to logging if no webhook.

    Parameters
    ----------
    verbose_only : bool
        If True, only send when level is "verbose".
    """
    full = f"{_get_prefix()}: {message}"
    log.info(full)

    if level in ("off", "false"):
        return
    if verbose_only and level != "verbose":
        return

    url = _get_webhook_url()
    if not url:
        log.warning("No Slack webhook configured, skipping")
        return

    try:
        r = requests.post(url, json={"text": full}, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("Slack notification failed: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    notify("Testing 1...2...3... Hello from TM1-ActivitySim!")
