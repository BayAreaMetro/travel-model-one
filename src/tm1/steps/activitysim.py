"""ActivitySim demand-model step.

Builds the ``activitysim run`` command from scenario config, launches it as a
subprocess, and monitors checkpoint progress.
"""

import logging
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

log = logging.getLogger(__name__)


def _check_checkpoints(checkpoints_file: Path, seen: set[str]):
    """Return list of newly completed checkpoints."""
    if not checkpoints_file.exists():
        return []
    try:
        df = pd.read_parquet(checkpoints_file, columns=["checkpoint_name"])
        names = set(df["checkpoint_name"]) - {"init"}
        new = sorted(names - seen)
        seen.update(new)
        return new
    except Exception:
        return []


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Launch ActivitySim and stream output.

    Parameters
    ----------
    scenario_dir : Path
        Resolved scenario directory.
    cfg : dict
        Full scenario config.
    **kwargs
        ``base_model_dir`` (Path): for resolving relative config paths.
        ``on_checkpoint`` (callable): called with checkpoint name string.
    """
    base_model_dir = kwargs.get("base_model_dir", scenario_dir.parent.parent)
    on_checkpoint = kwargs.get("on_checkpoint")

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
    log.info("ActivitySim: HH sample=%s, processes=%s", sample_str, nproc)
    log.info("Running: %s", " ".join(cmd))

    checkpoints_file = output_dir / "pipeline.parquetpipeline" / "checkpoints.parquet"
    seen: set[str] = set()

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    for line in proc.stdout:  # pyright: ignore[reportOptionalIterable]
        sys.stdout.write(line)
        for cp in _check_checkpoints(checkpoints_file, seen):
            if on_checkpoint:
                on_checkpoint(cp)

    rc = proc.wait()
    for cp in _check_checkpoints(checkpoints_file, seen):
        if on_checkpoint:
            on_checkpoint(cp)

    if rc != 0:
        raise RuntimeError(f"ActivitySim exited with code {rc}")
