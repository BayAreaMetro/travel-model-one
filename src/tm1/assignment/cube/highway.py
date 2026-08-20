"""Faithful Cube Voyager highway assignment, skims and feedback.

Drives the existing ``.job`` scripts as-is through
:func:`~tm1.assignment.cube.runner.run_cube_job` -- the same scripts
``RunIteration.bat`` calls, in the same order, with the same cluster settings.

Nothing here reads or writes matrix *content*, so this module has no dependency
on :mod:`cubeio`; it launches jobs and moves files.  Converting a Python demand
model's output into Cube demand is a separate concern and lives in
:mod:`tm1.assignment.cube.asim_bridge`.
"""

import logging
import shutil
from pathlib import Path

from tm1.assignment.cube.runner import run_cube_job

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

# Cube Cluster node counts: HwyAssign distributes 5 periods (DistributeMultistep)
# AND parallelises within each period (DistributeIntrastep) up to node 48
# (see HwyIntraStep.block); the skim/feedback jobs only distribute the 5 periods.
_NODES_ASSIGN = 48
_NODES_PERIOD = 5


def _job(scripts_dir: Path, *parts: str) -> Path:
    return scripts_dir.joinpath(*parts)


def run_highway_assignment(
    run_dir: str | Path,
    *,
    cluster_nodes: int = _NODES_ASSIGN,
    timeout: float = 14400,
    assign_job: str = "HwyAssign.job",
) -> None:
    """Assign ``main/trips{P}.tpp`` + frozen nonres demand to the network.

    Runs ``HwyAssign.job`` (faithful, as-is), producing ``hwy/LOAD{P}.net`` for
    each period.  Requires ``main/trips{P}.tpp`` (see :func:`build_trip_matrices`)
    and the non-residential demand (``nonres/trips{Ix,Trk,AirPax,Hsr}{P}.tpp``)
    to be in place.  ``assign_job`` selects the job script (e.g. a reduced-iteration
    ``HwyAssign_smoke.job`` for quick mechanics checks).  ``cluster_nodes`` must
    match the intrastep node range in ``HwyIntraStep.block``.
    """
    run_dir = Path(run_dir)
    scripts = run_dir / "CTRAMP" / "scripts"
    run_cube_job(
        _job(scripts, "assign", assign_job), run_dir,
        cluster_nodes=cluster_nodes, timeout=timeout,
    )


def run_highway_feedback(
    run_dir: str | Path,
    iteration: int,
    *,
    prev_iteration: int | None = None,
    wgt: float | None = None,
    prev_wgt: float | None = None,
) -> None:
    """Replicate RunIteration.bat's feedback block for one global iteration.

    Moves the loaded networks into ``hwy/iter{N}/``, renames the assignment
    variables, MSA-averages volumes against the previous iteration (iter > 1),
    recomputes congested speeds, tests convergence and merges the five
    period networks — leaving ``hwy/avgLOAD{P}.net`` ready for the next round.

    Parameters
    ----------
    iteration
        Current global iteration (>= 1).
    prev_iteration
        Previous iteration to average/compare against (defaults to ``iteration - 1``,
        floored at 0).
    wgt, prev_wgt
        MSA weights for this and the previous iteration's volumes (defaults to the
        legacy ramp ``1/iteration`` / ``1 - 1/iteration``).
    """
    run_dir = Path(run_dir)
    scripts = run_dir / "CTRAMP" / "scripts"
    hwy = run_dir / "hwy"
    prev_iteration = max(0, iteration - 1) if prev_iteration is None else prev_iteration
    if wgt is None:
        wgt = 1.0 / iteration
    if prev_wgt is None:
        prev_wgt = 1.0 - wgt

    iterdir = hwy / f"iter{iteration}"
    iterdir.mkdir(parents=True, exist_ok=True)

    # Move the freshly loaded networks into the iteration directory.
    for per in PERIODS:
        src = hwy / f"LOAD{per}.net"
        if not src.exists():
            msg = f"Loaded network missing (did HwyAssign run?): {src}"
            raise FileNotFoundError(msg)
        shutil.move(str(src), str(iterdir / f"LOAD{per}.net"))

    env = {
        "ITER": iteration,
        "PREV_ITER": prev_iteration,
        "WGT": f"{wgt:.4f}",
        "PREV_WGT": f"{prev_wgt:.4f}",
        "COMMPATH": str(run_dir / "commpath"),
    }

    run_cube_job(_job(scripts, "feedback", "RenameAssignmentVariables.job"),
                 run_dir, env_extra=env)

    if iteration > 1:
        run_cube_job(_job(scripts, "feedback", "AverageNetworkVolumes.job"),
                     run_dir, env_extra=env)
        run_cube_job(_job(scripts, "feedback", "CalculateSpeeds.job"),
                     run_dir, env_extra=env, cluster_nodes=_NODES_PERIOD)
    else:
        # First iteration: the renamed loaded network IS the averaged network.
        for per in PERIODS:
            shutil.copy2(iterdir / f"LOAD{per}_renamed.net",
                         iterdir / f"avgLOAD{per}.net")

    run_cube_job(_job(scripts, "feedback", "TestNetworkConvergence.job"),
                 run_dir, env_extra=env)
    run_cube_job(_job(scripts, "feedback", "MergeNetworks.job"),
                 run_dir, env_extra=env)

    # Publish the averaged networks for the next iteration's skims/assignment.
    for per in PERIODS:
        shutil.copy2(iterdir / f"avgLOAD{per}.net", hwy / f"avgLOAD{per}.net")
    log.info("Feedback iter %d complete: hwy/avgLOAD{EA..EV}.net refreshed", iteration)


def run_highway_skims(
    run_dir: str | Path,
    *,
    cluster_nodes: int = _NODES_PERIOD,
    timeout: float = 3600,
) -> None:
    """Build highway skims from the averaged networks (``HwySkims.job``, as-is)."""
    run_dir = Path(run_dir)
    scripts = run_dir / "CTRAMP" / "scripts"
    run_cube_job(
        _job(scripts, "skims", "HwySkims.job"), run_dir,
        cluster_nodes=cluster_nodes, timeout=timeout,
    )


