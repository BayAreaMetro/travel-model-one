"""Run an ActivitySim scenario end-to-end.

Calls setup_scenario to prepare the data directory (idempotent), then
launches ActivitySim via subprocess.

Usage::

    python scripts/run_model.py scenarios/base_2023
    python scripts/run_model.py scenarios/base_2023 --force-setup
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from setup_scenario import setup
from tm1.config import load_config

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def run(scenario_dir: Path, force_setup: bool = False) -> int:
    setup(scenario_dir, force=force_setup)

    cfg = load_config(scenario_dir)
    asim = cfg["activitysim"]
    data_dir = Path(asim["data_dir"])
    output_dir = Path(asim["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    config_dirs: list[Path] = []
    for c in asim.get("configs", []):
        p = Path(c)
        if not p.is_absolute():
            p = _REPO_ROOT / p
        config_dirs.append(p)

    cmd = [
        sys.executable, "-m", "activitysim", "run",
        "-d", str(data_dir),
        "-o", str(output_dir),
    ]
    for c in config_dirs:
        cmd.extend(["-c", str(c)])

    log.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario_dir", type=Path,
        help="Path to the scenario directory (e.g. scenarios/base_2023)",
    )
    parser.add_argument(
        "--force-setup", action="store_true",
        help="Re-copy data files even if they already exist",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(run(args.scenario_dir, force_setup=args.force_setup))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(run(_REPO_ROOT / "scenarios" / "base_2023"))
