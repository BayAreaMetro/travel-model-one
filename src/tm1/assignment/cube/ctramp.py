"""One CT-RAMP global iteration on Cube, replacing ``RunIteration.bat``.

``RunIteration.bat`` runs, per global iteration:

1. ``HwySkims.job`` + ``Accessibility.job`` -- level-of-service from the previous
   iteration's loaded network (skipped at iteration 0, where the warm-start
   network is used as-is)
2. the CT-RAMP java demand model (:mod:`tm1.steps.simulate_ctramp`)
3. the non-residential models -- internal/external, trucks, air passengers, HSR
4. ``PrepAssign.job`` to fold the CT-RAMP trip lists into ``trips{PERIOD}.tpp``,
   then ``HwyAssign.job`` and the transit assignment
5. the feedback block -- rename, MSA-average volumes, recompute congested
   speeds, test convergence, merge

This module covers everything except step 2, which the ``simulate_ctramp`` step
owns.  Every job is the stock script, unmodified, launched through
:func:`~tm1.assignment.cube.runner.run_cube_job`.

CT-RAMP writes its own demand to ``trips{PERIOD}.tpp`` via ``PrepAssign.job`` --
a Cube job -- so nothing here reads or writes matrix content, and this module
does not depend on :mod:`cubeio`.  (The ActivitySim path *does* need a Python
bridge, because ActivitySim emits OMX; that lives in
:mod:`tm1.assignment.cube.asim_bridge`.)
"""

import logging
from pathlib import Path

from tm1.assignment.cube.highway import (
    _NODES_ASSIGN,
    _NODES_PERIOD,
    _job,
    run_highway_assignment,
    run_highway_feedback,
    run_highway_skims,
)
from tm1.assignment.cube.runner import run_cube_job
from tm1.assignment.cube.transit import run_transit

log = logging.getLogger(__name__)

#: ``RunIteration.bat`` step 3, in order.  Frozen for a base-year run: each job
#: reads the current skims and rewrites its own ``nonres/`` demand matrices.
NONRES_JOBS: tuple[str, ...] = (
    "IxForecasts_horizon.job",
    "IxTimeOfDay.job",
    "IxTollChoice.job",
    "TruckTripGeneration.job",
    "TruckTripDistribution.job",
    "TruckTimeOfDay.job",
    "TruckTollChoice.job",
    "HsrTransitSubmodeChoice.job",
    "MoveAirPaxTrips_IfNoFreePath.job",
)


def run_skims(proj_dir: str | Path, *, accessibility: bool = True) -> None:
    """``RunIteration.bat`` step 1 -- highway skims, then accessibility."""
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_highway_skims(proj_dir)
    if accessibility:
        run_cube_job(_job(scripts, "skims", "Accessibility.job"), proj_dir,
                     cluster_nodes=_NODES_PERIOD)


def run_nonres(proj_dir: str | Path, *, jobs: tuple[str, ...] = NONRES_JOBS) -> None:
    """``RunIteration.bat`` step 3 -- internal/external, truck, air, HSR models."""
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    for name in jobs:
        run_cube_job(_job(scripts, "nonres", name), proj_dir)


def run_prep_assign(proj_dir: str | Path) -> None:
    """Fold the CT-RAMP trip lists into ``main/trips{PERIOD}.tpp``.

    This is the CT-RAMP counterpart of
    :func:`~tm1.assignment.cube.asim_bridge.build_trip_matrices`: same output,
    but produced by Cube from CT-RAMP's own trip lists rather than converted
    from ActivitySim's OMX.
    """
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_cube_job(_job(scripts, "assign", "PrepAssign.job"), proj_dir)


def run_iteration(
    proj_dir: str | Path,
    iteration: int,
    *,
    build_skims: bool = True,
    do_nonres: bool = True,
    do_transit: bool = True,
    cluster_nodes: int = _NODES_ASSIGN,
    transit_nodes: int = 15,
) -> None:
    """Run the Cube half of one CT-RAMP global iteration.

    Call after the demand model for ``iteration`` has finished.  Sequence:
    ``PrepAssign -> HwyAssign -> transit -> feedback -> HwySkims`` -- leaving
    ``hwy/avgLOAD{PERIOD}.net`` and refreshed skims for the next round.

    Parameters
    ----------
    iteration
        Current global iteration (>= 1).
    build_skims
        Rebuild highway skims (and accessibility) after feedback, ready for the
        next iteration's demand model.  Set False on the final iteration.
    do_nonres
        Re-run the non-residential models before assignment.  They are commonly
        frozen after the first iteration in a base-year run.

    Notes:
    -----
    Transit runs *before* the feedback block, matching ``RunIteration.bat``
    (transit is step 4, feedback is step 5), so it sees the previous iteration's
    ``avgLOAD{PERIOD}.net`` bus speeds.  :func:`tm1.assignment.cube.transit.run_transit`
    documents the opposite order, because the ActivitySim loop calls it after
    feedback.  **Unverified against a live Cube run** -- confirm which ordering
    reproduces the reference run before trusting the transit skims.
    """
    proj_dir = Path(proj_dir)
    log.info("=== CT-RAMP assignment iteration %d ===", iteration)

    if do_nonres:
        run_nonres(proj_dir)

    run_prep_assign(proj_dir)
    run_highway_assignment(proj_dir, cluster_nodes=cluster_nodes)

    if do_transit:
        run_transit(proj_dir, iteration, cluster_nodes=transit_nodes)

    run_highway_feedback(proj_dir, iteration)

    if build_skims:
        run_skims(proj_dir)
