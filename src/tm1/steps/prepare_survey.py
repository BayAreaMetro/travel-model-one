"""Prepare survey data via the travel-diary-survey-tools pipeline.

Reads ``cfg["steps"]["prepare_survey"]`` from scenario_config.yaml.
"""

import importlib.util
import logging
import tempfile
import urllib.request
from pathlib import Path

from data_canon.models import ctramp, daysim
from pipeline.pipeline import Pipeline
from processing import (
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

log = logging.getLogger(__name__)


def run(
    scenario_dir: Path,
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Run the survey preparation pipeline."""
    step_cfg = cfg.get("steps", {}).get("prepare_survey", {}) or {}
    force = bool(kwargs.get("force"))

    # Resolve config path and check existence
    config_path = step_cfg.get("config_path")
    if not config_path:
        msg = "prepare_survey requires 'config_path' in scenario_config.yaml"
        raise ValueError(msg)
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = scenario_dir / config_path
    if not config_path.exists():
        msg = f"Survey pipeline config not found: {config_path}"
        raise FileNotFoundError(msg)

    # Skip if outputs already exist
    check = step_cfg.get("check_outputs", [])
    if not force and check and all(Path(p).exists() for p in check):
        log.info("All check_outputs exist — skipping (use --force to re-run)")
        return "skipped"

    # Load project-specific clean steps (local paths or URLs)
    clean_steps = []
    for entry in step_cfg.get("clean_steps", []):
        func = _load_step(entry, scenario_dir)
        clean_steps.append(func)

    # Run pipeline
    log.info("Running survey pipeline from %s", config_path)
    survey_pipe = Pipeline(
        config_path=config_path,
        steps=[
            load_data, *clean_steps, add_zone_ids, link_trips,
            detect_joint_trips, imputation, extract_tours,
            format_ctramp, format_daysim, write_data,
            add_existing_weights, compute_weights,
        ],
        caching=False,  # Force no caching, since we handle skipping externally
        data_models={
            "households_daysim": daysim.HouseholdDaysimModel,
            "persons_daysim": daysim.PersonDaysimModel,
            "days_daysim": daysim.PersonDayDaysimModel,
            "linked_trips_daysim": daysim.LinkedTripDaysimModel,
            "tours_daysim": daysim.TourDaysimModel,
            "households_ctramp": ctramp.HouseholdCTRAMPModel,
            "persons_ctramp": ctramp.PersonCTRAMPModel,
            "mandatory_locations_ctramp": ctramp.MandatoryLocationCTRAMPModel,
            "individual_tours_ctramp": ctramp.IndividualTourCTRAMPModel,
            "individual_trips_ctramp": ctramp.IndividualTripCTRAMPModel,
            "joint_tours_ctramp": ctramp.JointTourCTRAMPModel,
            "joint_trips_ctramp": ctramp.JointTripCTRAMPModel,
            "cdap_results_ctramp": ctramp.CDAPResultsCTRAMPModel,
        },
    )
    survey_pipe.run()
    log.info("Survey pipeline finished")


def _load_step(entry: str | dict, scenario_dir: Path) -> object:
    """Load a step function from a local path or URL.

    *entry* is either a string (path/URL, function name = file stem) or a dict
    with ``path``/``url`` and ``function`` keys.
    """
    if isinstance(entry, dict):
        source = entry.get("url") or entry.get("path")
        func_name = entry["function"]
    else:
        source = entry
        func_name = Path(source.split("/")[-1]).stem

    if not isinstance(source, str):
        msg = f"Invalid source type: {type(source)}"
        raise TypeError(msg)

    if source.startswith(("https://", "http://")):
        log.info("Fetching step from %s", source)
        with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
            code = resp.read()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(code)
            path = Path(tmp.name)
        try:
            return _load_module_func(path, func_name)
        finally:
            path.unlink(missing_ok=True)

    path = Path(source)
    if not path.is_absolute():
        path = scenario_dir / path
    return _load_module_func(path, func_name)


def _load_module_func(path: Path, func_name: str) -> object:
    """Load a module from *path* and return the function named *func_name*."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        msg = f"Could not create module spec for {path}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    func = getattr(mod, func_name, None)
    if func is None:
        msg = f"{path} has no function '{func_name}'"
        raise ImportError(msg)
    return func
