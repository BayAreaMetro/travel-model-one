"""Calibration summaries: lightweight Python-based summaries for model calibration."""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Produce calibration summaries from ActivitySim outputs."""
    log.warning("calibration_summaries not yet implemented — skipping")
