"""Simulate step: demand model (ActivitySim) + assignment loop.

For ``iterations: 0`` (default), runs ActivitySim once against static skims.
For ``iterations: N``, runs N further rounds of assignment → ActivitySim.  The
engine is chosen and configured through :mod:`tm1.steps.assignment`, the same
backend table the CT-RAMP path uses.

.. warning::

   **THIS LOOP'S SHAPE DIFFERS FROM THE CT-RAMP ONE AND MUST BE RECONCILED BEFORE
   PARITY IS CLAIMED.**  This step drives its own loop and runs demand first::

       iterations: 2  ->  D  A  D  A  D      (3 demand runs, 2 assignments)

   The CT-RAMP path is driven by the runner's ``iterate:`` block, which pairs the
   two::

       count: 2       ->  D  A  D  A         (2 demand runs, 2 assignments)

   So an ActivitySim run currently ends on a demand model whose trips were never
   assigned, while a CT-RAMP run ends on an assignment.  Aligning them changes
   which trip set is final, and therefore the results.

   Left alone deliberately: it is the same class of change as the transit/feedback
   ordering in :func:`tm1.assignment.cube.asim_bridge.run_assignment_iteration`,
   and the AequilibraE parity work is calibrated against the current behaviour.
   Resolve both together and re-validate together, rather than as a side effect of
   a refactor.
"""

import logging
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import yaml

from tm1.assignment import expand_period

log = logging.getLogger(__name__)

_PERIODS = ("ea", "am", "md", "pm", "ev")


def _archive_pre_assignment(arch_dir: Path, skims_omx: Path, demand: str,
                            iteration: int) -> None:
    """Archive loop provenance BEFORE assignment runs.

    ``skims_iter0.omx`` = the seed skims the first ActivitySim run consumed (copied
    once); ``trips_{p}_iter{N}.omx`` = the demand matrices ActivitySim run N produced
    (the demand assignment iteration N is about to load). Copies are cheap (~1 GB
    skims, ~25 MB demand) and make every iteration's inputs reconstructible.

    Reads the same ``demand`` pattern the assignment does, so a scenario that points
    the seam somewhere non-default still archives the file that was actually used.
    """
    arch_dir.mkdir(parents=True, exist_ok=True)
    seed = arch_dir / "skims_iter0.omx"
    if iteration == 1 and skims_omx.exists() and not seed.exists():
        shutil.copy2(skims_omx, seed)
    for period in _PERIODS:
        src = Path(expand_period(demand, period))
        if src.exists():
            shutil.copy2(src, arch_dir / f"trips_{period}_iter{iteration}.omx")


def _archive_post_assignment(arch_dir: Path, skims_omx: Path, iteration: int) -> None:
    """Archive the skims produced by assignment iteration N as ``skims_iter{N}.omx``.

    The canonical ``skims.omx`` (what ActivitySim's config points at) is already
    atomically replaced by the assignment; this copy is the per-iteration snapshot
    that the next ActivitySim run (N+1) will consume.
    """
    if skims_omx.exists():
        arch_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skims_omx, arch_dir / f"skims_iter{iteration}.omx")


def _check_checkpoints(checkpoints_file: Path, seen: set[str]) -> list[str]:
    """Return list of newly completed checkpoints."""
    if not checkpoints_file.exists():
        return []
    try:
        df = pd.read_parquet(checkpoints_file, columns=["checkpoint_name"])
        names = set(df["checkpoint_name"]) - {"init"}
        new = sorted(names - seen)
        seen.update(new)
    except Exception:  # noqa: BLE001
        return []
    else:
        return new


def _run_activitysim(  # noqa: C901
    cfg: dict, base_model_dir: Path, on_checkpoint: Callable | None = None
) -> None:
    """Launch ActivitySim subprocess and stream output."""
    sim_cfg = cfg["steps"].get("simulate_activitysim", cfg["steps"].get("simulate", {}))
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
            with sf.open() as f:
                asim_settings.update(yaml.safe_load(f) or {})

    sample = asim_settings.get("households_sample_size", 0)
    nproc = asim_settings.get("num_processes", 1)
    sample_str = "all" if sample == 0 else f"{sample:,}"
    log.info("ActivitySim: HH sample=%s, processes=%s", sample_str, nproc)

    # Warn if existing pipeline found and resume_after is not explicitly set
    resume = asim_settings.get("resume_after")
    pipeline_dir = output_dir / "pipeline.parquetpipeline"
    if not resume and pipeline_dir.exists():
        log.warning(
            "Existing pipeline found at %s. ActivitySim will run from scratch, "
            "overwriting previous results. To resume instead, set "
            "'resume_after: _' in your scenario's activitysim/settings.yaml.",
            pipeline_dir,
        )

    log.info("Running: %s", " ".join(cmd))

    checkpoints_file = output_dir / "pipeline.parquetpipeline" / "checkpoints.parquet"
    seen: set[str] = set()

    proc = subprocess.Popen(  # noqa: S603
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
        msg = f"ActivitySim exited with code {rc}"
        raise RuntimeError(msg)


def _run_assignment(
    cfg: dict,
    iteration: int,
) -> None:
    """Run one assignment + feedback pass for this iteration of the loop.

    The engine choice, its config keys and its backend table all live in
    :mod:`tm1.steps.assignment`, shared with the CT-RAMP path -- there is one
    ``backend:`` and one set of key names regardless of which demand model is
    driving.  Reads ``steps.simulate_activitysim.assignment``.

    Two things stay here because they belong to the loop rather than to the engine:

    * **Defaults drawn from the ActivitySim block.** ``demand`` defaults to this
      round's ``trips_{period}.omx`` in the ActivitySim ``output_dir``, and
      ``skims_omx`` to ``skims.omx`` in its ``data_dir`` -- the file the next
      ActivitySim run reads.
    * **Provenance.** ``archive`` (default true) snapshots each round under
      ``archive_dir`` (default ``{skims dir}/skim_archive``): ``skims_iter{N}.omx``
      (produced by assignment N, consumed by ActivitySim run N+1; ``iter0`` is the
      seed) and ``trips_{p}_iter{N}.omx`` (demand from ActivitySim run N).
    """
    from tm1.steps.assignment import run_backend  # noqa: PLC0415

    sim_cfg = cfg["steps"].get("simulate_activitysim", cfg["steps"].get("simulate", {}))
    asim_cfg = sim_cfg.get("activitysim", sim_cfg)
    asn = sim_cfg.get("assignment")
    if not asn:
        log.warning(
            "No assignment config — skipping assignment for iteration %d "
            "(ActivitySim will re-run against static skims)", iteration,
        )
        return

    # Copied so the defaults below never mutate the loaded scenario config.
    asn = dict(asn)
    asn.setdefault("demand", str(Path(asim_cfg["output_dir"]) / "trips_{period}.omx"))
    skims_omx = Path(asn.get("skims_omx") or Path(asim_cfg["data_dir"]) / "skims.omx")
    asn["skims_omx"] = str(skims_omx)

    # per-iteration provenance snapshots (skims_iter{N}.omx + demand); the canonical
    # skims.omx name never changes -- ActivitySim always reads the same path
    archive = asn.get("archive", True)
    arch_dir = Path(asn.get("archive_dir", skims_omx.parent / "skim_archive"))
    if archive:
        _archive_pre_assignment(arch_dir, skims_omx, asn["demand"], iteration)

    run_backend(asn, cfg, iteration)

    if archive:
        _archive_post_assignment(arch_dir, skims_omx, iteration)


def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> None:
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

    sim_cfg = cfg["steps"].get("simulate_activitysim", cfg["steps"].get("simulate", {}))
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
