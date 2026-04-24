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
        "usual_work_school_location": ("calibration_01", WorkSchoolLocationCalibration),
        "auto_ownership": ("calibration_02", AutoOwnershipCalibration),
        "daily_activity_pattern": ("calibration_04", DailyActivityPatternCalibration),
    }

    calib_cfg = cfg.get("steps", {}).get("summaries", {}).get("calibration", {}) or {}
    config_file = calib_cfg.get("config_file")
    # Default: only run submodels whose calibration_XX section exists in config
    requested = calib_cfg.get(
        "submodels",
        [name for name, (section, _cls) in submodels.items() if section in calib_cfg],
    )

    for name in requested:
        entry = submodels.get(name)
        if entry is None:
            log.warning("Unknown calibration submodel: %s — skipping", name)
            continue
        _section, cls = entry
        log.info("Running calibration submodel: %s", name)
        instance = cls(config_file=config_file, config=calib_cfg)
        instance.run()
