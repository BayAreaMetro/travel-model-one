"""Summarize step (stub).

Will shim ActivitySim outputs for legacy R summarizers, then later
replace with native Python summaries.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run(scenario_dir: Path, cfg: dict, **kwargs):
    log.info("Summarize: not yet implemented")
