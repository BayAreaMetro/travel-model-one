"""Run an ActivitySim scenario end-to-end.

Handles config loading, command building, subprocess launch,
checkpoint monitoring, and Slack notifications.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

import tm1.slack as slack
from tm1.config import load_config
from tm1.slack import notify

log = logging.getLogger(__name__)


def _check_checkpoints(checkpoints_file: Path, seen: set[str]):
    """Notify on new pipeline checkpoints."""
    if not checkpoints_file.exists():
        return
    try:
        df = pd.read_parquet(checkpoints_file, columns=["checkpoint_name"])
        names = set(df["checkpoint_name"]) - {"init"}
        new = names - seen
        for name in sorted(new):
            notify(f"Completed {name}", verbose_only=True)
        seen.update(new)
    except Exception:
        pass  # file may be mid-write


def run(
    scenario_dir: Path,
    setup_fn: Callable[[Path, bool], None],
    base_model_dir: Path,
    force_setup: bool = False,
    slack_level: str = "minimal",
) -> int:
    """Run an ActivitySim scenario.

    Parameters
    ----------
    scenario_dir : Path
        Path to the scenario directory.
    setup_fn : callable
        Function to prepare the data directory, e.g. ``setup_scenario.setup``.
    base_model_dir : Path
        Base directory for resolving relative config paths.
    force_setup : bool
        Re-copy data files even if they already exist.
    slack_level : str
        "false", "minimal", or "verbose".
    """
    slack.level = slack_level
    scenario_dir = Path(scenario_dir).resolve()
    label = str(scenario_dir)
    try:
        notify(f"Setting up {label}")
        setup_fn(scenario_dir, force_setup)

        cfg = load_config(scenario_dir)
        asim = cfg["activitysim"]
        data_dir = Path(asim["data_dir"])
        output_dir = Path(asim["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        config_dirs: list[Path] = []
        for c in asim.get("configs", []):
            p = Path(c)
            if not p.is_absolute():
                p = base_model_dir / p
            config_dirs.append(p)

        cmd = [
            sys.executable, "-m", "activitysim", "run",
            "-d", str(data_dir),
            "-o", str(output_dir),
        ]
        for c in config_dirs:
            cmd.extend(["-c", str(c)])

        # Read ActivitySim settings from the config chain (first dir wins)
        asim_settings: dict = {}
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

        checkpoints_file = output_dir / "pipeline.parquetpipeline" / "checkpoints.parquet"
        seen: set[str] = set()

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:  # pyright: ignore[reportOptionalIterable]
            sys.stdout.write(line)
            _check_checkpoints(checkpoints_file, seen)
        rc = proc.wait()
        _check_checkpoints(checkpoints_file, seen)

    except KeyboardInterrupt:
        notify(f":no_entry_sign: {label} cancelled by user")
        raise
    except Exception as e:
        notify(f":exclamation: {label} crashed: {e}")
        raise

    if rc == 0:
        notify(f"Finished {label} :white_check_mark:")
    else:
        notify(f":exclamation: Error in {label} (exit code {rc})")
    return rc
