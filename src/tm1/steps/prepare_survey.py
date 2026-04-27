"""Prepare survey data via the travel-diary-survey-tools pipeline.

Reads ``cfg["steps"]["prepare_survey"]`` with keys:

- ``config_path``: Path to the survey pipeline YAML config
  (resolved relative to *scenario_dir*).
- ``check_outputs``: list of file paths; skip if all exist.
- ``cache_dir``: Pipeline cache directory (default ``.cache/survey``).

Project-specific cleaning steps (``clean_*.py``) are auto-discovered
next to the config file.
"""

import importlib
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def run(
    scenario_dir: Path,
    cfg: dict,
    **kwargs: object,
) -> None:
    """Run the survey preparation pipeline."""
    step_cfg = cfg.get("steps", {}).get("prepare_survey", {}) or {}

    config_path = _resolve_config(scenario_dir, step_cfg)
    if config_path is None:
        return

    if _should_skip(step_cfg, force=bool(kwargs.get("force"))):
        return

    # Make clean_*.py modules importable from config's directory
    project_dir = str(config_path.parent)
    added = project_dir not in sys.path
    if added:
        sys.path.insert(0, project_dir)
    try:
        _run_pipeline(config_path, step_cfg)
    finally:
        if added:
            sys.path.remove(project_dir)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _resolve_config(scenario_dir: Path, step_cfg: dict) -> Path | None:
    config_path = step_cfg.get("config_path")
    if not config_path:
        log.warning("No config_path for prepare_survey — skipping")
        return None
    p = Path(config_path)
    if not p.is_absolute():
        p = scenario_dir / p
    if not p.exists():
        sys.exit(f"Survey pipeline config not found: {p}")
    return p


def _should_skip(step_cfg: dict, *, force: bool) -> bool:
    if force:
        return False
    check = step_cfg.get("check_outputs", [])
    if check and all(Path(p).exists() for p in check):
        log.info("All check_outputs exist — skipping prepare_survey (use --force to re-run)")
        return True
    return False


def _discover_project_steps(config_dir: Path) -> list:
    """Import ``clean_*.py`` from *config_dir*; return their step functions."""
    steps = []
    for py in sorted(config_dir.glob("clean_*.py")):
        name = py.stem
        mod = importlib.import_module(name)
        func = getattr(mod, name, None)
        if func is not None:
            log.info("Discovered project step: %s", name)
            steps.append(func)
        else:
            log.warning("%s has no function %s — skipping", name, name)
    return steps


def _run_pipeline(config_path: Path, step_cfg: dict) -> None:
    from data_canon.models import ctramp as cm  # noqa: PLC0415
    from data_canon.models import daysim as dm  # noqa: PLC0415
    from pipeline.pipeline import Pipeline  # noqa: PLC0415
    from processing import (  # noqa: PLC0415
        add_existing_weights,
        add_zone_ids,
        compute_weights,
        detect_joint_trips,
        extract_tours,
        format_ctramp,
        format_daysim,
        imputation,
        link_trips,
        load_data,
        write_data,
    )

    project_steps = _discover_project_steps(config_path.parent)

    log.info("Running survey pipeline from %s", config_path)
    Pipeline(
        config_path=config_path,
        steps=[
            load_data, *project_steps, add_zone_ids, link_trips,
            detect_joint_trips, imputation, extract_tours,
            format_ctramp, format_daysim, write_data,
            add_existing_weights, compute_weights,
        ],
        caching=Path(step_cfg.get("cache_dir", ".cache/survey")),
        data_models={
            "households_daysim": dm.HouseholdDaysimModel,
            "persons_daysim": dm.PersonDaysimModel,
            "days_daysim": dm.PersonDayDaysimModel,
            "linked_trips_daysim": dm.LinkedTripDaysimModel,
            "tours_daysim": dm.TourDaysimModel,
            "households_ctramp": cm.HouseholdCTRAMPModel,
            "persons_ctramp": cm.PersonCTRAMPModel,
            "mandatory_locations_ctramp": cm.MandatoryLocationCTRAMPModel,
            "individual_tours_ctramp": cm.IndividualTourCTRAMPModel,
            "individual_trips_ctramp": cm.IndividualTripCTRAMPModel,
            "joint_tours_ctramp": cm.JointTourCTRAMPModel,
            "joint_trips_ctramp": cm.JointTripCTRAMPModel,
        },
    ).run()
    log.info("Survey pipeline finished")
