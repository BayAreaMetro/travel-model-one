"""Calibration summaries: lightweight Python-based summaries for model calibration."""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,  # noqa: ARG001
    **kwargs: object,  # noqa: ARG001
) -> None:
    """Produce calibration summaries from ActivitySim outputs."""
    log.warning("calibration_summaries not yet implemented — skipping")
