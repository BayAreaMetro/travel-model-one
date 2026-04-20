"""Run an ActivitySim scenario end-to-end.

Calls setup_scenario to prepare the data directory (idempotent), then
launches ActivitySim via subprocess.

Usage::

    python scripts/run_model.py scenarios/base_2023
    python scripts/run_model.py scenarios/base_2023 --force-setup
"""

import argparse
import csv
import logging
import subprocess
import sys
import time
from pathlib import Path

import yaml

from setup_scenario import setup
from tm1.config import load_config
import tm1.slack as slack
from tm1.slack import notify

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent


# TODO: Consider formalizing into src/tm1/__main__.py to make it the CLI runner. 
# For now keeping it as a standalone script until migration settles down.
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

        # Read ActivitySim settings from the config chain (first dir wins)
        asim_settings = {}
        for c in reversed(config_dirs):
            sf = c / "settings.yaml"
            if sf.exists():
                with open(sf) as f:
                    asim_settings.update(yaml.safe_load(f) or {})

        sample = asim_settings.get("households_sample_size", 0)
        nproc = asim_settings.get("num_processes", 1)
        sample_str = "all" if sample == 0 else f"{sample:,}"
        notify(f"Starting {label} (HH sample: {sample_str}, processes: {nproc})")
        log.info("Running: %s", " ".join(cmd))

        _NOTIFY_INTERVAL = 300  # seconds between Slack notifications
        last_notify_time = time.monotonic() - _NOTIFY_INTERVAL  # ensure first step notifies

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout: # pyright: ignore[reportOptionalIterable]
            sys.stdout.write(line)
            # ActivitySim logs "time to execute run.{step}" after each step
            if "time to execute run." in line.lower():
                # Read RSS from the last row of mem.csv
                rss_str = ""
                mem_csv = output_dir / "mem.csv"
                if mem_csv.exists():
                    with open(mem_csv) as f:
                        for row in csv.DictReader(f):
                            pass  # advance to last row
                        rss_bytes = int(row.get("rss", "0").replace("_", ""))
                        rss_gb = rss_bytes / (1024 ** 3)
                        rss_str = f" | RSS: {rss_gb:.1f} GB"

                # Extract step name from "time to execute run.{step} : ..."
                part = line.lower().split("time to execute run.")[1]
                step = part.split()[0].strip()

                now = time.monotonic()
                if now - last_notify_time >= _NOTIFY_INTERVAL:
                    notify(f"Completed {step}{rss_str}")
                    last_notify_time = now
                else:
                    log.info("Completed %s%s", step, rss_str)
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
