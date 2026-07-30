"""Assignment step -- run the Cube half of a global iteration.

Sequences the stock Cube ``.job`` scripts in ``RunIteration.bat`` order:
``PrepAssign -> HwyAssign -> transit -> feedback -> HwySkims``, leaving
``hwy/avgLOAD{PERIOD}.net`` and refreshed skims ready for the next iteration's
demand model.

Configured under ``steps.assignment`` in ``scenario_config.yaml``::

    assignment:
      proj_dir: "{proj_dir}"
      model_year: 2023      # IxForecasts_horizon.job branches on this
      future: PBA50         # ditto -- PBA50 for IPA/DBP/FBP/EIR/SEN/STP/NGF/TIP/TRR
      iteration: 1          # defaults to steps.simulate_ctramp's iteration
      sampleshare: 0.15     # defaults to simulate_ctramp's sample_rate
      do_nonres: true       # internal/external, truck, air, HSR models
      do_transit: true
      build_skims: true     # rebuild highway skims + accessibility afterwards

`model_year` and `future` are explicit here.  ``RunModel.bat`` slices them out of
the project *folder name* (``2023_TM161_IPA_35`` -> 2023 / IPA -> PBA50), which
makes a run depend on how its output directory is spelled; this does not.

Demand must already be in ``main/`` -- this runs *after* ``simulate_ctramp``.
"""

import logging
from pathlib import Path

from tm1.assignment.cube.ctramp import run_iteration

log = logging.getLogger(__name__)


def _resolve_iteration(cfg: dict, step_cfg: dict, kwargs: dict) -> int:  # noqa: ARG001
    """Iteration to assign: the runner's, unless this step overrides it.

    The runner drives the global feedback loop and passes the current iteration,
    so there is nothing to infer.  An earlier version read
    ``simulate_ctramp.iterations`` -- a *count* -- as an iteration *number*, which
    silently assigned iteration 3 of a 3-iteration plan while the demand model had
    looped internally without any assignment between rounds.
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

    sim = cfg.get("steps", {}).get("simulate_ctramp", {}) or {}
    if sim.get("sample_rate") is not None:
        return float(sim["sample_rate"])

    # No explicit rate: CT-RAMP's per-iteration ramp (RunModel.bat).
    return {1: 0.15, 2: 0.30}.get(iteration, 0.50)


def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Run one Cube assignment + feedback pass for the current iteration."""
    step_cfg = cfg.get("steps", {}).get("assignment", {}) or {}

    proj_dir = step_cfg.get("proj_dir") or cfg.get("proj_dir")
    if not proj_dir:
        msg = "assignment step needs `proj_dir` (or a top-level proj_dir)"
        raise ValueError(msg)
    proj_dir = Path(proj_dir)

    scripts = proj_dir / "CTRAMP" / "scripts"
    if not scripts.is_dir():
        msg = (
            f"Cube job scripts not found at {scripts}. The assignment step needs "
            f"CTRAMP/scripts, hwy/ and nonres/ copied into the project directory -- "
            f"see copy_inputs in the scenario config."
        )
        raise FileNotFoundError(msg)

    model_year = step_cfg.get("model_year")
    future = step_cfg.get("future")
    if model_year is None or future is None:
        msg = (
            "assignment step needs `model_year` and `future` -- the "
            "non-residential models branch on them (IxForecasts_horizon.job). "
            "RunModel.bat derives them from the project folder name; set them "
            "explicitly in the scenario config instead."
        )
        raise ValueError(msg)

    iteration = _resolve_iteration(cfg, step_cfg, kwargs)
    sampleshare = _resolve_sampleshare(cfg, step_cfg, iteration)

    run_iteration(
        proj_dir,
        iteration,
        model_year=int(model_year),
        future=str(future),
        sampleshare=sampleshare,
        build_skims=step_cfg.get("build_skims", True),
        do_nonres=step_cfg.get("do_nonres", True),
        do_transit=step_cfg.get("do_transit", True),
        cluster_nodes=step_cfg.get("cluster_nodes", 48),
        transit_nodes=step_cfg.get("transit_nodes", 15),
    )
    return None
