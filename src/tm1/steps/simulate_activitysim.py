"""Simulate step: demand model (ActivitySim) + assignment loop.

For ``iterations: 0`` (default), runs ActivitySim once with static skims.
For ``iterations: N``, runs N rounds of ActivitySim → assignment → skim update.
Assignment is not yet implemented.
"""

import logging
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import yaml

log = logging.getLogger(__name__)

_PERIODS = ("ea", "am", "md", "pm", "ev")


def _archive_pre_assignment(arch_dir: Path, skims_omx: Path, asim_output_dir: Path,
                            iteration: int) -> None:
    """Archive loop provenance BEFORE assignment runs.

    ``skims_iter0.omx`` = the seed skims the first ActivitySim run consumed (copied
    once); ``trips_{p}_iter{N}.omx`` = the demand matrices ActivitySim run N produced
    (the demand assignment iteration N is about to load). Copies are cheap (~1 GB
    skims, ~25 MB demand) and make every iteration's inputs reconstructible.
    """
    arch_dir.mkdir(parents=True, exist_ok=True)
    seed = arch_dir / "skims_iter0.omx"
    if iteration == 1 and skims_omx.exists() and not seed.exists():
        shutil.copy2(skims_omx, seed)
    for period in _PERIODS:
        src = asim_output_dir / f"trips_{period}.omx"
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
    """Run one faithful Cube highway assignment + feedback iteration.

    Reads ``steps.simulate_activitysim.assignment``:

    * ``cube_proj_dir`` — Cube project scaffold (hwy nets, CTRAMP/scripts, frozen
      ``nonres/`` demand). Required to run assignment; if absent, assignment is
      skipped (ActivitySim then just re-runs against the same static skims).
    * ``cluster_nodes`` — local Cube Cluster size (must match ``HwyIntraStep.block``;
      default 12).
    * ``assign_job`` — assignment job script (default ``HwyAssign.job``).

    The bridged demand comes from this iteration's ActivitySim ``trips_{period}.omx``
    (in the ActivitySim ``output_dir``); the refreshed skims are written back to the
    ActivitySim ``data_dir``'s ``skims.omx`` for the next ActivitySim run.

    Two backends are selected by ``assignment.backend``:

    * ``"cube"`` (default) — the faithful legacy Cube Voyager loop (needs
      ``cube_proj_dir`` + a local Cube install).
    * ``"aeq"`` — the open-source AequilibraE highway assignment + skims (needs
      ``network_csv`` and frozen ``nonres_dir``); no Cube license required.

    ``archive`` (default true) keeps per-iteration provenance copies under
    ``archive_dir`` (default ``{skims dir}/skim_archive``): ``skims_iter{N}.omx``
    (produced by assignment N, consumed by ActivitySim run N+1; ``iter0`` = the seed)
    and ``trips_{p}_iter{N}.omx`` (demand from ActivitySim run N).
    """
    sim_cfg = cfg["steps"].get("simulate_activitysim", cfg["steps"].get("simulate", {}))
    asim_cfg = sim_cfg.get("activitysim", sim_cfg)
    asn = sim_cfg.get("assignment")
    if not asn:
        log.warning(
            "No assignment config — skipping assignment for iteration %d "
            "(ActivitySim will re-run against static skims)", iteration,
        )
        return

    backend = asn.get("backend", "cube")
    asim_output_dir = Path(asim_cfg["output_dir"])
    skims_omx = Path(asn.get("skims_omx", Path(asim_cfg["data_dir"]) / "skims.omx"))
    # per-iteration provenance snapshots (skims_iter{N}.omx + demand); the canonical
    # skims.omx name never changes -- ActivitySim always reads the same path
    archive = asn.get("archive", True)
    arch_dir = Path(asn.get("archive_dir", skims_omx.parent / "skim_archive"))
    if archive:
        _archive_pre_assignment(arch_dir, skims_omx, asim_output_dir, iteration)

    if backend == "aeq":
        from tm1.assignment.aeq.runner import run_assignment_iteration  # noqa: PLC0415

        if not asn.get("network_csv"):
            log.warning(
                "backend=aeq but no assignment.network_csv configured — skipping "
                "assignment for iteration %d", iteration,
            )
            return
        run_assignment_iteration(
            asim_output_dir,
            asn["network_csv"],
            asn.get("nonres_dir", ""),
            skims_omx,
            iteration=iteration,
            max_iter=asn.get("max_iter", 100),
            gap_target=asn.get("gap_target", 1e-4),
            cores=asn.get("cores"),
            transit_inputs_dir=asn.get("transit_inputs_dir"),
            params_path=asn.get("params"),
        )
        if archive:
            _archive_post_assignment(arch_dir, skims_omx, iteration)
        return

    from tm1.assignment.cube.asim_bridge import run_assignment_iteration  # noqa: PLC0415

    if not asn.get("cube_proj_dir"):
        log.warning(
            "No assignment.cube_proj_dir configured — skipping highway assignment "
            "for iteration %d (ActivitySim will re-run against static skims)",
            iteration,
        )
        return

    proj_dir = Path(asn["cube_proj_dir"])
    run_assignment_iteration(
        proj_dir,
        asim_output_dir,
        iteration,
        skims_omx_path=skims_omx,
        cluster_nodes=asn.get("cluster_nodes", 12),
        assign_job=asn.get("assign_job", "HwyAssign.job"),
        do_transit=asn.get("transit", True),
        transit_nodes=asn.get("transit_nodes", 15),
    )
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
