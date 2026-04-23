"""Calibration summaries for travel model submodels."""

import logging
from pathlib import Path

from .auto_ownership import AutoOwnershipCalibration
from .daily_activity_pattern import DailyActivityPatternCalibration
from .usual_work_school_location import WorkSchoolLocationCalibration

log = logging.getLogger(__name__)


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> None:
    """Produce calibration summaries from ActivitySim outputs.

    Dispatches to individual submodel calibration classes based on
    the ``steps.summaries.calibration`` section in scenario config.
    """
    submodels = {
        "usual_work_school_location": WorkSchoolLocationCalibration,
        "auto_ownership": AutoOwnershipCalibration,
        "daily_activity_pattern": DailyActivityPatternCalibration,
    }

    calib_cfg = cfg.get("steps", {}).get("summaries", {}).get("calibration", {}) or {}
    config_file = calib_cfg.get("config_file")
    requested = calib_cfg.get("submodels", list(submodels))

    for name in requested:
        cls = submodels.get(name)
        if cls is None:
            log.warning("Unknown calibration submodel: %s — skipping", name)
            continue
        log.info("Running calibration submodel: %s", name)
        instance = cls(config_file=config_file)
        instance.run()
