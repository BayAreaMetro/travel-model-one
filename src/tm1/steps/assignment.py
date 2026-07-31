"""Assignment step -- run the Cube half of a global iteration.

Sequences the stock Cube ``.job`` scripts in ``RunIteration.bat`` order:
``PrepAssign -> HwyAssign -> transit -> feedback -> HwySkims``, leaving
``hwy/avgLOAD{PERIOD}.net`` and refreshed skims ready for the next iteration's
demand model.

Normally declared inside the feedback loop, since an iteration is demand plus
assignment::

    steps:
      iterate:
        count: 3
        steps:
          simulate_ctramp: {...}
          assignment:
            run_dir: "{run_dir}"
            demand: "{run_dir}/main/trips{PERIOD}.tpp"   # optional; this is the default
            model_year: 2023     # see below -- both are legacy names
            future: PBA50
            do_nonres: true      # internal/external, truck, air, HSR models
            do_transit: true
            build_skims: true    # rebuild highway skims + accessibility after
            sampleshare: 0.15    # optional; defaults to simulate_ctramp's rate,
                                 # else RunModel.bat's ramp for this iteration

``demand`` names the artifact this step consumes, rather than the step that
produced it: the demand model and the assignment engine meet at a named file
instead of at each other's internals.  ``{PERIOD}`` expands to each of
``EA/AM/MD/PM/EV``; ``{run_dir}`` is already expanded by ``resolve_templates``
before the step sees it.  Declaring it also makes a silent ``PrepAssign.job``
failure loud -- see :func:`~tm1.assignment.cube.ctramp.run_prep_assign`.

``model_year`` and ``future`` keep their legacy names because the Cube jobs read
them as ``%MODEL_YEAR%`` / ``%FUTURE%``.  ``RunModel.bat`` derives both by slicing
the project *folder name*: ``2023_TM161_IPA_35`` yields ``2023`` from characters
1-4 and the project code ``IPA`` from 12-14, which a lookup maps to a future.
Setting them explicitly here means a run's results no longer depend on how its
output directory happens to be spelled.

``model_year``
    The forecast year.  ``IxForecasts_horizon.job`` uses it to choose the
    internal-external trip forecast: 2005 and 2015 are fixed tables, 2021 is the
    base year, and later years extrapolate linearly from it
    (``year_delta = model_year - 2021``).  Years before 2021 other than 2015 are
    unsupported.

``future``
    Not a year.  The name of a planning-scenario family, selecting which growth
    assumptions the forecast applies.  ``IPA``/``DBP``/``FBP``/``EIR``/``SEN``/
    ``STP``/``NGF``/``TIP``/``TRR`` all map to ``PBA50``, the only one
    implemented; ``PPA`` runs instead use ``RisingTidesFallingFortunes``,
    ``CleanAndGreen`` or ``BackToTheFuture``.

Demand must already be in ``main/`` -- this runs *after* ``simulate_ctramp``.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from tm1.assignment import has_period_placeholder
from tm1.assignment.cube.ctramp import run_iteration
from tm1.assignment.cube.highway import PERIODS
from tm1.project.config import step_config

log = logging.getLogger(__name__)

#: Where assignment reads its demand when the project does not say, relative to the
#: Cube project dir.  CT-RAMP's ``PrepAssign.job`` writes here, so this is the
#: conventional location rather than a choice; naming it makes the seam explicit and
#: lets a different demand model point the engine somewhere else without either
#: knowing about the other.
_DEFAULT_DEMAND = "main/trips{PERIOD}.tpp"


def _resolve_iteration(cfg: dict, step_cfg: dict, kwargs: dict) -> int:  # noqa: ARG001
    """Iteration to assign, supplied by the runner from the enclosing block.

    ``warmstart:`` gives 0, ``iterate:`` gives the round, so there is nothing to
    infer here.  Note that a demand step's iteration *count* is not its iteration
    *number*: reading one as the other would assign the last round's number to
    every round.  The ``step_cfg`` lookup serves direct calls only -- the runner
    refuses a config that states its own ``iteration:``.
    """
    if step_cfg.get("iteration") is not None:
        return int(step_cfg["iteration"])
    if kwargs.get("iteration") is not None:
        return int(kwargs["iteration"])
    return 1


def _resolve_sampleshare(cfg: dict, step_cfg: dict, iteration: int) -> float:
    """Sample rate the demand model ran at, so PrepAssign can expand the trips.

    Must match what ``simulate_ctramp`` used for *this* iteration, or PrepAssign
    expands the trip lists by the wrong factor.
    """
    if step_cfg.get("sampleshare") is not None:
        return float(step_cfg["sampleshare"])

    sim = step_config(cfg, "simulate_ctramp")
    if sim.get("sample_rate") is not None:
        return float(sim["sample_rate"])

    # No explicit rate: CT-RAMP's per-iteration ramp (RunModel.bat).
    return {1: 0.15, 2: 0.30}.get(iteration, 0.50)


def _resolve_demand(run_dir: Path, step_cfg: dict) -> str:
    """The demand artifact this assignment consumes, as a per-period path pattern.

    ``{PERIOD}`` is deliberately left unexpanded -- the backend substitutes it once
    per time period.  ``resolve_templates`` uses ``str.replace``, so it passes over
    placeholders it has no value for; ``{run_dir}`` is already expanded by then, and
    is deliberately *not* re-expanded here.  ``assignment.run_dir`` is the Cube project
    scaffold, which stops being the run's own directory as soon as the demand model is
    not CT-RAMP -- substituting it again would silently point the seam at the wrong tree.
    """
    pattern = str(step_cfg.get("demand") or (run_dir / _DEFAULT_DEMAND))
    if not has_period_placeholder(pattern):
        msg = (
            f"assignment `demand` must contain '{{PERIOD}}' or '{{period}}' -- assignment "
            f"reads one demand matrix per time period ({', '.join(PERIODS)}). "
            f"Got: {pattern}"
        )
        raise ValueError(msg)
    return pattern


def _run_cube_from_ctramp(
    run_dir: Path, iteration: int, sampleshare: float, demand: str, step_cfg: dict,
) -> None:
    """Cube Voyager: ``RunIteration.bat``'s sequence, every ``.job`` unmodified."""
    scripts = run_dir / "CTRAMP" / "scripts"
    if not scripts.is_dir():
        msg = (
            f"Cube job scripts not found at {scripts}. The assignment step needs "
            f"CTRAMP/scripts, hwy/ and nonres/ copied into the project directory -- "
            f"see copy_inputs in the project config."
        )
        raise FileNotFoundError(msg)

    # Defaulted from the project by `run` before dispatch, so a step key is only
    # needed to override the run-wide value.
    model_year = step_cfg.get("model_year")
    future = step_cfg.get("future")
    if model_year is None or future is None:
        msg = (
            "The project config needs `model_year` and `future` at the top level -- the "
            "non-residential models branch on them (IxForecasts_horizon.job), and "
            "the Cube jobs read them as %MODEL_YEAR% / %FUTURE%. RunModel.bat "
            "derives them from the project folder name; set them explicitly in the "
            "project config instead."
        )
        raise ValueError(msg)

    run_iteration(
        run_dir,
        iteration,
        model_year=int(model_year),
        future=str(future),
        sampleshare=sampleshare,
        demand=demand,
        build_skims=step_cfg.get("build_skims", True),
        do_nonres=step_cfg.get("do_nonres", True),
        do_transit=step_cfg.get("do_transit", True),
        cluster_nodes=step_cfg.get("cluster_nodes", 48),
        transit_nodes=step_cfg.get("transit_nodes", 15),
    )


def _run_cube_from_omx(
    run_dir: Path, iteration: int, sampleshare: float, demand: str, step_cfg: dict,  # noqa: ARG001
) -> None:
    """Cube Voyager, fed by a demand model that emits OMX rather than TPP.

    ``sampleshare`` is unused: ActivitySim's ``write_trip_matrices`` has already
    expanded its sample to full population, so there is nothing for the assignment
    to scale.  The CT-RAMP path needs it because ``PrepAssign.job`` does that
    expansion itself.
    """
    from tm1.assignment.cube.asim_bridge import run_assignment_iteration  # noqa: PLC0415

    skims_omx = step_cfg.get("skims_omx")
    if not skims_omx:
        msg = (
            "assignment needs `skims_omx` when demand is OMX -- the engine writes the "
            "refreshed skims back to the single file the demand model reads."
        )
        raise ValueError(msg)

    run_assignment_iteration(
        run_dir,
        demand,
        iteration,
        skims_omx_path=skims_omx,
        cluster_nodes=step_cfg.get("cluster_nodes", 12),
        assign_job=step_cfg.get("assign_job", "HwyAssign.job"),
        do_transit=step_cfg.get("do_transit", True),
        transit_nodes=step_cfg.get("transit_nodes", 15),
    )


#: The Cube engine only ever reads TPP.  Which route gets it there depends on what
#: wrote the demand -- CT-RAMP's trip lists are folded in by ``PrepAssign.job``, a
#: Cube job, while ActivitySim's OMX needs a Python bridge.  Selecting on the demand
#: artifact rather than on a separate switch keeps the seam the single source of
#: truth about who feeds the engine.
_CUBE_ROUTES: dict[str, Callable[[Path, int, float, str, dict], None]] = {
    ".tpp": _run_cube_from_ctramp,
    ".omx": _run_cube_from_omx,
}


def _run_cube(
    run_dir: Path, iteration: int, sampleshare: float, demand: str, step_cfg: dict,
) -> None:
    """Cube Voyager, routed by the format of the demand it was pointed at."""
    suffix = Path(demand).suffix.lower()
    route = _CUBE_ROUTES.get(suffix)
    if route is None:
        supported = ", ".join(sorted(_CUBE_ROUTES))
        msg = (
            f"assignment `demand` has unsupported format {suffix!r} ({demand}). "
            f"The cube backend reads: {supported}."
        )
        raise ValueError(msg)
    route(run_dir, iteration, sampleshare, demand, step_cfg)


def _run_aeq(
    proj_dir: Path, iteration: int, sampleshare: float, demand: str, step_cfg: dict,  # noqa: ARG001
) -> None:
    """AequilibraE: multi-class user equilibrium and skims, no Cube licence.

    ``proj_dir`` and ``sampleshare`` are unused.  There is no Cube project tree to
    run jobs out of -- the network arrives as ``network_csv`` -- and ActivitySim has
    already expanded its sample to full population.
    """
    from tm1.assignment.aeq.runner import run_assignment_iteration  # noqa: PLC0415

    missing = [key for key in ("network_csv", "skims_omx") if not step_cfg.get(key)]
    if missing:
        msg = (
            f"assignment backend 'aeq' needs {', '.join(f'`{k}`' for k in missing)}. "
            f"`network_csv` is the link table it assigns over; `skims_omx` is where "
            f"the refreshed skims are written for the next demand run."
        )
        raise ValueError(msg)

    run_assignment_iteration(
        demand,
        step_cfg["network_csv"],
        step_cfg.get("nonres_dir", ""),
        step_cfg["skims_omx"],
        iteration=iteration,
        max_iter=step_cfg.get("max_iter", 100),
        gap_target=step_cfg.get("gap_target", 1e-4),
        cores=step_cfg.get("cores"),
        transit_inputs_dir=step_cfg.get("transit_inputs_dir"),
        params_path=step_cfg.get("params"),
    )


#: Assignment engines, keyed by the ``backend:`` value that selects them.
#:
#: Cube and AequilibraE solve the same problem -- multi-class user equilibrium over
#: the same network from the same demand -- so they sit behind one step rather than
#: under separate names.  Adding a third engine is an entry in this table.
#:
#: Every backend takes the same five arguments -- project dir, iteration, the sample
#: rate the demand ran at, the demand artifact, and its own config block -- because
#: assignment has one contract regardless of engine: demand and a network in, a
#: loaded network and skims out.  An engine ignores what it does not need.
_BACKENDS: dict[str, Callable[[Path, int, float, str, dict], None]] = {
    "cube": _run_cube,
    "aeq": _run_aeq,
}


def run_backend(step_cfg: dict, cfg: dict, iteration: int) -> None:
    """Run one assignment pass with whichever engine *step_cfg* selects.

    Shared by the ``assignment`` step and by the ActivitySim demand loop, so both
    demand models reach the engines through one backend table and one set of config
    keys.  The caller supplies ``iteration``, because what counts as an iteration
    belongs to the loop rather than to the engine.
    """
    # `MODEL_YEAR` and `FUTURE` describe the run, not this step: the pre-process reads
    # them too (HsrTripGeneration.job wants %MODEL_YEAR% before any assignment exists).
    # They live in the project's `env:` block because that is what they are -- variables
    # the legacy jobs read from the environment.  Read from there here so every backend
    # sees them without widening the `_BACKENDS` signature; a step key still wins.
    project_env = cfg.get("env") or {}
    step_cfg = {
        **{
            key: project_env[name]
            for key, name in (("model_year", "MODEL_YEAR"), ("future", "FUTURE"))
            if project_env.get(name) is not None
        },
        **step_cfg,
    }

    run_dir = step_cfg.get("run_dir") or cfg.get("run_dir")
    if not run_dir:
        msg = "assignment step needs `run_dir` (or a top-level run_dir)"
        raise ValueError(msg)
    run_dir = Path(run_dir)

    backend = str(step_cfg.get("backend", "cube")).lower()
    if backend not in _BACKENDS:
        available = ", ".join(sorted(_BACKENDS))
        msg = f"Unknown assignment backend {backend!r}; available: {available}."
        raise ValueError(msg)

    sampleshare = _resolve_sampleshare(cfg, step_cfg, iteration)
    demand = _resolve_demand(run_dir, step_cfg)

    log.info("Assignment iteration %d via backend %r, demand %s", iteration, backend, demand)
    _BACKENDS[backend](run_dir, iteration, sampleshare, demand, step_cfg)


def run(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Run one assignment + feedback pass for the current iteration."""
    step_cfg = step_config(cfg, "assignment", kwargs)
    run_backend(step_cfg, cfg, _resolve_iteration(cfg, step_cfg, kwargs))
    return None
