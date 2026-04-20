"""Assemble an ActivitySim data directory from a scenario config.

Reads ``scenarios/<name>/scenario_config.yaml``, copies the three input CSVs
into the ActivitySim data directory, and verifies the skims file exists.

Usage::

    python scripts/setup_scenario.py scenarios/base_2023
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

# Maps data_sources key → destination filename in the data directory.
FILE_MAP = {
    "land_use": "land_use.csv",
    "households": "households.csv",
    "persons": "persons.csv",
}


def resolve_templates(sources: dict[str, str]) -> dict[str, str]:
    """Expand ``{reference_run}`` placeholders in *sources* values."""
    ref = sources.get("reference_run", "")
    return {k: v.replace("{reference_run}", ref) for k, v in sources.items()}


def setup(scenario_dir: Path) -> None:
    cfg_path = scenario_dir / "scenario_config.yaml"
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")

    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    asim = cfg.get("activitysim", {})
    data_dir = Path(asim["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    sources = resolve_templates(cfg.get("data_sources", {}))

    # --- Copy CSVs -----------------------------------------------------------
    for key, dest_name in FILE_MAP.items():
        src = Path(sources[key])
        dest = data_dir / dest_name
        if not src.exists():
            log.error("Source not found: %s", src)
            sys.exit(1)
        log.info("Copying %s -> %s", src, dest)
        shutil.copy2(src, dest)
        size_mb = dest.stat().st_size / 1_048_576
        log.info("  %.1f MB", size_mb)

    # --- Verify skims ---------------------------------------------------------
    skims_path = Path(sources["skims"])
    if skims_path.exists():
        size_mb = skims_path.stat().st_size / 1_048_576
        log.info("Skims OK: %s (%.0f MB)", skims_path, size_mb)
    else:
        log.warning("Skims NOT found: %s — run build_omx_skims.py first", skims_path)

    # --- Summary --------------------------------------------------------------
    log.info("--- Data directory: %s ---", data_dir)
    for p in sorted(data_dir.iterdir()):
        size_mb = p.stat().st_size / 1_048_576
        log.info("  %-20s %8.1f MB", p.name, size_mb)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario_dir",
        type=Path,
        help="Path to the scenario directory (e.g. scenarios/base_2023)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    setup(args.scenario_dir)


if __name__ == "__main__":
    main()
