"""Assignment step -- run the Cube half of a global iteration.

Sequences the stock Cube ``.job`` scripts in ``RunIteration.bat`` order:
``PrepAssign -> HwyAssign -> transit -> feedback -> HwySkims``, leaving
``hwy/avgLOAD{PERIOD}.net`` and refreshed skims ready for the next iteration's
demand model.

Configured under ``steps.assignment`` in ``scenario_config.yaml``::

    assignment:
      proj_dir: "{proj_dir}"
      iteration: 1          # defaults to steps.simulate_ctramp's iteration
      do_nonres: true       # internal/external, truck, air, HSR models
      do_transit: true
      build_skims: true     # rebuild highway skims + accessibility afterwards

Demand must already be in ``main/`` -- this runs *after* ``simulate_ctramp``.
"""

import logging
from pathlib import Path

from tm1.assignment.cube.ctramp import run_iteration

log = logging.getLogger(__name__)


def _resolve_iteration(cfg: dict, step_cfg: dict, kwargs: dict) -> int:
    """Iteration to assign: explicit setting, else the demand model's last one."""
    if step_cfg.get("iteration") is not None:
        return int(step_cfg["iteration"])
    if kwargs.get("iteration") is not None:
        return int(kwargs["iteration"])

    sim = cfg.get("steps", {}).get("simulate_ctramp", {}) or {}
    if sim.get("iteration") is not None:
        return int(sim["iteration"])
    if sim.get("iterations") is not None:
        return int(sim["iterations"])
    return 1


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
            f"see setup.copy_inputs in the scenario config."
        )
        raise FileNotFoundError(msg)

    iteration = _resolve_iteration(cfg, step_cfg, kwargs)

    run_iteration(
        proj_dir,
        iteration,
        build_skims=step_cfg.get("build_skims", True),
        do_nonres=step_cfg.get("do_nonres", True),
        do_transit=step_cfg.get("do_transit", True),
        cluster_nodes=step_cfg.get("cluster_nodes", 48),
        transit_nodes=step_cfg.get("transit_nodes", 15),
    )
    return None
