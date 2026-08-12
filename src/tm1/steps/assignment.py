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
            proj_dir: "{proj_dir}"
            demand: "{proj_dir}/main/trips{PERIOD}.tpp"   # optional; this is the default
            model_year: 2023     # see below -- both are legacy names
            future: PBA50
            do_nonres: true      # internal/external, truck, air, HSR models
            do_transit: true
            build_skims: true    # rebuild highway skims + accessibility after
            iteration: 1         # optional; the runner supplies the current one
            sampleshare: 0.15    # optional; defaults to simulate_ctramp's rate,
                                 # else RunModel.bat's ramp for this iteration

``demand`` names the artifact this step consumes, rather than the step that
produced it: the demand model and the assignment engine meet at a named file
instead of at each other's internals.  ``{PERIOD}`` expands to each of
``EA/AM/MD/PM/EV``; ``{proj_dir}`` is already expanded by ``resolve_templates``
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

from tm1.assignment.cube.ctramp import run_iteration
from tm1.assignment.cube.highway import PERIODS
from tm1.config import step_config

log = logging.getLogger(__name__)

#: Where assignment reads its demand when the scenario does not say.  CT-RAMP's
#: ``PrepAssign.job`` writes here, so this is the conventional location rather than
#: a choice; naming it makes the seam explicit and lets a different demand model
#: point the engine somewhere else without either knowing about the other.
_DEFAULT_DEMAND = "{proj_dir}/main/trips{PERIOD}.tpp"


def _resolve_iteration(cfg: dict, step_cfg: dict, kwargs: dict) -> int:  # noqa: ARG001
    """Iteration to assign: the runner's, unless this step overrides it.

    The runner drives the global feedback loop and passes the current iteration,
    so there is nothing to infer here.  Note that a demand step's iteration *count*
    is not its iteration *number*: reading one as the other would assign the last
    round's number to every round.
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


def _resolve_demand(proj_dir: Path, step_cfg: dict) -> str:
    """The demand artifact this assignment consumes, as a per-period path pattern.

    ``{PERIOD}`` is deliberately left unexpanded -- the backend substitutes it once
    per time period.  ``resolve_templates`` uses ``str.replace``, so it passes over
    placeholders it has no value for; only ``{proj_dir}`` is expanded by the time
    this runs.
    """
    pattern = str(step_cfg.get("demand") or _DEFAULT_DEMAND)
    pattern = pattern.replace("{proj_dir}", str(proj_dir))
    if "{PERIOD}" not in pattern:
        msg = (
            f"assignment `demand` must contain '{{PERIOD}}' -- assignment reads one "
            f"demand matrix per time period ({', '.join(PERIODS)}). Got: {pattern}"
        )
        raise ValueError(msg)
    return pattern


def _run_cube(
    proj_dir: Path, iteration: int, sampleshare: float, demand: str, step_cfg: dict,
) -> None:
    """Cube Voyager: ``RunIteration.bat``'s sequence, every ``.job`` unmodified."""
    scripts = proj_dir / "CTRAMP" / "scripts"
    if not scripts.is_dir():
        msg = (
            f"Cube job scripts not found at {scripts}. The assignment step needs "
            f"CTRAMP/scripts, hwy/ and nonres/ copied into the project directory -- "
            f"see copy_inputs in the scenario config."
        )
        raise FileNotFoundError(msg)

    # Defaulted from the scenario by `run` before dispatch, so a step key is only
    # needed to override the run-wide value.
    model_year = step_cfg.get("model_year")
    future = step_cfg.get("future")
    if model_year is None or future is None:
        msg = (
            "Scenario needs `model_year` and `future` at the top level -- the "
            "non-residential models branch on them (IxForecasts_horizon.job), and "
            "the Cube jobs read them as %MODEL_YEAR% / %FUTURE%. RunModel.bat "
            "derives them from the project folder name; set them explicitly in the "
            "scenario config instead."
        )
        raise ValueError(msg)

    run_iteration(
        proj_dir,
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


#: Assignment engines, keyed by the ``backend:`` value that selects them.
#:
#: Cube and AequilibraE solve the same problem -- multi-class user equilibrium
#: over the same network from the same demand -- so they belong behind one step
#: rather than under separate names.  ``aeq`` is not registered here: the
#: AequilibraE runner and its OMX demand path arrive with the ActivitySim
#: swap-in.  Adding it is an entry in this table, not a new step.
#:
#: Every backend takes the same five arguments -- project dir, iteration, the sample
#: rate the demand ran at, the demand artifact, and its own config block -- because
#: assignment has one contract regardless of engine: demand and a network in, a
#: loaded network and skims out.
_BACKENDS: dict[str, Callable[[Path, int, float, str, dict], None]] = {
    "cube": _run_cube,
}


def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Run one assignment + feedback pass for the current iteration."""
    step_cfg = step_config(cfg, "assignment", kwargs)

    # `model_year` and `future` describe the run, not this step: the pre-process
    # reads them too (HsrTripGeneration.job wants %MODEL_YEAR% before any assignment
    # exists).  Defaulted from the scenario here so every backend sees them without
    # widening the `_BACKENDS` signature; a step key still wins.
    step_cfg = {
        **{k: cfg[k] for k in ("model_year", "future") if cfg.get(k) is not None},
        **step_cfg,
    }

    proj_dir = step_cfg.get("proj_dir") or cfg.get("proj_dir")
    if not proj_dir:
        msg = "assignment step needs `proj_dir` (or a top-level proj_dir)"
        raise ValueError(msg)
    proj_dir = Path(proj_dir)

    backend = str(step_cfg.get("backend", "cube")).lower()
    if backend not in _BACKENDS:
        available = ", ".join(sorted(_BACKENDS))
        extra = (
            " AequilibraE arrives with the ActivitySim swap-in, which brings the "
            "engine and the OMX demand path it reads."
            if backend == "aeq"
            else ""
        )
        msg = f"Unknown assignment backend {backend!r}; available: {available}.{extra}"
        raise ValueError(msg)

    iteration = _resolve_iteration(cfg, step_cfg, kwargs)
    sampleshare = _resolve_sampleshare(cfg, step_cfg, iteration)
    demand = _resolve_demand(proj_dir, step_cfg)

    log.info("Assignment iteration %d via backend %r, demand %s", iteration, backend, demand)
    _BACKENDS[backend](proj_dir, iteration, sampleshare, demand, step_cfg)
    return None
