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
    PERIODS,
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

#: Of the above, the ones that fan their per-period steps out over the cluster
#: (``DistributeMultistep`` + ``Wait4Files CTRAMP1-5.script.end``).  They need a
#: 5-node cluster; the rest are single-threaded and get none.  Cube does *not*
#: fail when the cluster is absent -- it quietly runs every period serially in
#: the master, which is correct but roughly 5x slower.
_NONRES_CLUSTERED: frozenset[str] = frozenset({
    "IxTollChoice.job",
    "TruckTollChoice.job",
    "HsrTransitSubmodeChoice.job",
    "MoveAirPaxTrips_IfNoFreePath.job",
})


def run_skims(proj_dir: str | Path, *, accessibility: bool = True) -> None:
    """``RunIteration.bat`` step 1 -- highway skims, then accessibility."""
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_highway_skims(proj_dir)
    if accessibility:
        run_cube_job(_job(scripts, "skims", "Accessibility.job"), proj_dir,
                     cluster_nodes=_NODES_PERIOD)


def run_nonres(
    proj_dir: str | Path,
    *,
    model_year: int,
    future: str,
    jobs: tuple[str, ...] = NONRES_JOBS,
) -> None:
    """``RunIteration.bat`` step 3 -- internal/external, truck, air, HSR models.

    ``IxForecasts_horizon.job`` branches on ``%MODEL_YEAR%`` and ``%FUTURE%``.
    ``RunModel.bat`` derives both by slicing the project *folder name*
    (``2023_TM161_IPA_35`` -> year 2023, project IPA -> future PBA50); they are
    passed explicitly here instead, so a run does not depend on how its output
    directory happens to be named.
    """
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    env = {"MODEL_YEAR": model_year, "FUTURE": future}
    for name in jobs:
        run_cube_job(
            _job(scripts, "nonres", name), proj_dir, env_extra=env,
            cluster_nodes=_NODES_PERIOD if name in _NONRES_CLUSTERED else None,
        )


def _verify_demand(demand: str) -> None:
    """Fail loudly if ``PrepAssign.job`` did not produce the demand assignment reads.

    PrepAssign exits 0 even when the CT-RAMP trip lists it expects are absent, so
    without this check a missing or empty ``trips{PERIOD}.tpp`` surfaces much later
    as an obscure ``HwyAssign.job`` failure, several minutes into the run.
    """
    missing = [
        path
        for path in (Path(demand.replace("{PERIOD}", period)) for period in PERIODS)
        if not path.exists() or path.stat().st_size == 0
    ]
    if missing:
        names = ", ".join(str(p) for p in missing)
        msg = (
            f"PrepAssign.job returned cleanly but produced no demand at: {names}. "
            f"Check that this iteration's CT-RAMP trip lists (indivTripData_*.csv, "
            f"jointTripData_*.csv) are in main/."
        )
        raise FileNotFoundError(msg)


def run_prep_assign(
    proj_dir: str | Path, iteration: int, sampleshare: float, demand: str,
) -> None:
    """Fold the CT-RAMP trip lists into ``main/trips{PERIOD}.tpp``.

    The CT-RAMP counterpart of
    :func:`~tm1.assignment.cube.asim_bridge.build_trip_matrices`: same output,
    but produced by Cube from CT-RAMP's own trip lists rather than converted
    from ActivitySim's OMX.

    ``PrepAssign.job`` reads ``%ITER%`` to pick the trip-list suffix and
    ``%SAMPLESHARE%`` to expand the sampled trips back to full population.

    It distributes its per-period steps over the cluster
    (``DistributeMultistep processNum = @period@``, ``Wait4Files
    CTRAMP1-5.script.end``), so it needs a 5-node cluster like the other
    period-looped jobs.  Without one Cube silently falls back to running all five
    periods serially in the master -- correct output, ~5x the wall time.
    """
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_cube_job(
        _job(scripts, "assign", "PrepAssign.job"), proj_dir,
        env_extra={"ITER": iteration, "SAMPLESHARE": sampleshare},
        cluster_nodes=_NODES_PERIOD,
    )
    _verify_demand(demand)


def run_iteration(  # noqa: PLR0913
    proj_dir: str | Path,
    iteration: int,
    *,
    model_year: int,
    future: str,
    sampleshare: float,
    demand: str,
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
        Current global iteration.  ``0`` is the warm start: the demand comes
        from ``INPUT/warmstart`` rather than a demand model, so ``PrepAssign``
        and the non-residential models are skipped and only the demand is
        verified -- matching ``RunIteration.bat``'s jump to ``:hwyAssign``.
    model_year, future
        Passed to the non-residential models; see :func:`run_nonres`.
    sampleshare
        Household sample rate the demand model ran at, so ``PrepAssign.job`` can
        expand the trip lists back to full population.
    demand
        Per-period path pattern for the demand matrices this assignment consumes
        (``{PERIOD}`` -> ``EA``/``AM``/...).  PrepAssign writes them; checking them
        here turns a silent PrepAssign no-op into an immediate, named failure.
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
    feedback.

    This ordering has been run against live Cube for iteration 1 of the 2023 base
    year: every job returned cleanly and produced a full skim set.  That
    establishes the *sequencing* works; it does not establish numerical parity --
    the resulting skims have not been compared against the reference run.
    """
    proj_dir = Path(proj_dir)
    log.info("=== CT-RAMP assignment iteration %d ===", iteration)

    # Iteration 0 is the warm start: RunIteration.bat jumps straight to
    # :hwyAssign, over the skim, demand *and* nonres blocks.  Its demand comes
    # from INPUT/warmstart -- already assignment-ready and already including
    # truck/IX trips -- so PrepAssign has nothing to fold and nonres must not run.
    warm_start = iteration == 0

    if do_nonres and not warm_start:
        run_nonres(proj_dir, model_year=model_year, future=future)

    if warm_start:
        _verify_demand(demand)
    else:
        run_prep_assign(proj_dir, iteration, sampleshare, demand)
    run_highway_assignment(proj_dir, cluster_nodes=cluster_nodes)

    if do_transit:
        run_transit(proj_dir, iteration, cluster_nodes=transit_nodes)

    run_highway_feedback(proj_dir, iteration)

    if build_skims:
        run_skims(proj_dir)
