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
import tm1.slack as slack
from tm1.slack import notify

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent


# Major pipeline steps to notify on (subset to avoid spam)
_MILESTONE_STEPS = {
    "initialize_landuse",
    "compute_accessibility",
    "workplace_location",
    "mandatory_tour_frequency",
    "non_mandatory_tour_frequency",
    "tour_mode_choice_simulate",
    "trip_mode_choice",
    "write_tables",
}


def run(scenario_dir: Path, force_setup: bool = False, notify_slack: bool = True) -> int:
    slack.enabled = notify_slack
    scenario_dir = Path(scenario_dir).resolve()
    label = str(scenario_dir)
    try:
        notify(f"Setting up {label}")
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

        notify(f"Starting {label}")
        log.info("Running: %s", " ".join(cmd))

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            # ActivitySim logs "Running model 'step_name'"
            if "Running model '" in line:
                step = line.split("Running model '")[1].split("'")[0]
                if step in _MILESTONE_STEPS:
                    notify(f"Running {step} in {label}")
        rc = proc.wait()

    except Exception as e:
        notify(f":exclamation: {label} crashed: {e}")
        raise

    if rc == 0:
        notify(f"Finished {label} :white_check_mark:")
    else:
        notify(f":exclamation: Error in {label} (exit code {rc})")
    return rc


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
    parser.add_argument(
        "--no-slack", action="store_true",
        help="Disable Slack notifications",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(run(args.scenario_dir, force_setup=args.force_setup, notify_slack=not args.no_slack))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(run(
        scenario_dir=_REPO_ROOT / "scenarios" / "base_2023",
        force_setup=False,
        notify_slack=False,        
        )
    )
