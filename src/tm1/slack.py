"""Slack webhook notifications for TM1 model runs.

Configuration (any one of these, checked in order):
  1. ``SLACK_WEBHOOK_URL`` environment variable
  2. ``SLACK_WEBHOOK_FILE`` environment variable pointing to a text file
  3. MTC default file: ``M:\\Software\\Slack\\TravelModel_SlackWebhook.txt``

If none are available, messages are logged but not sent.

Set ``TM1_SLACK=0`` to disable sending (messages are still logged).
"""

import logging
import os
import socket
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_MTC_WEBHOOK_FILE = Path(r"\\models.ad.mtc.ca.gov\data\models\Software\Slack\TravelModel_SlackWebhook.txt")


enabled = True

def _get_webhook_url():
    """Resolve the Slack webhook URL from env var or MTC default file."""
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        return url.strip()

    if _MTC_WEBHOOK_FILE.exists():
        try:
            return _MTC_WEBHOOK_FILE.read_text().strip()
        except OSError:
            log.warning("Cannot read webhook file: %s", _MTC_WEBHOOK_FILE)

    return None


def _get_prefix():
    """Build a message prefix from INSTANCE env var or hostname."""
    instance = os.environ.get("INSTANCE")
    if instance:
        return f"*{instance}*"
    return f"*{socket.gethostname()}*"


def notify(message):
    """Post a message to Slack. Falls back to logging if no webhook."""
    full = f"{_get_prefix()}: {message}"
    log.info(full)

    if not enabled:
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


# Slack test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    notify("Testing 1...2...3... Hello from TM1-ActivitySim!")