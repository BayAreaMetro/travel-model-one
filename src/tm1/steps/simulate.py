"""Simulate step: demand model (ActivitySim) + assignment loop.

For ``iterations: 0`` (default), runs ActivitySim once with static skims.
For ``iterations: N``, runs N rounds of ActivitySim → assignment → skim update.
Assignment is not yet implemented.
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


def _run_activitysim(cfg: dict, base_model_dir: Path, on_checkpoint=None):
    """Launch ActivitySim subprocess and stream output."""
    sim_cfg = cfg["steps"]["simulate"]
    asim_cfg = sim_cfg.get("activitysim", sim_cfg)  # nested or flat
    data_dir = Path(asim_cfg["data_dir"])
    output_dir = Path(asim_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    config_dirs: list[Path] = []
    for c in asim_cfg.get("configs", []):
        p = Path(c)
        if not p.is_absolute():
            p = base_model_dir / p
        config_dirs.append(p)

    cmd = [
        sys.executable,
        "-m",
        "activitysim",
        "run",
        "-d",
        str(data_dir),
        "-o",
        str(output_dir),
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
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
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


def _run_assignment(cfg: dict, iteration: int):
    """Run highway/transit assignment (not yet implemented)."""
    log.warning("Assignment not yet implemented — skipping iteration %d", iteration)


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Run the simulate loop.

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

    sim_cfg = cfg["steps"]["simulate"]
    iterations = (
        kwargs.get("iterations")
        if kwargs.get("iterations") is not None
        else sim_cfg.get("iterations", 0)
    )

    # Always run ActivitySim at least once
    log.info("Running ActivitySim (iterations=%d)", iterations)
    _run_activitysim(cfg, base_model_dir, on_checkpoint=on_checkpoint)

    # Demand ↔ assignment feedback loop
    for i in range(1, iterations + 1):
        log.info("--- Iteration %d / %d ---", i, iterations)
        _run_assignment(cfg, i)
        _run_activitysim(cfg, base_model_dir, on_checkpoint=on_checkpoint)
