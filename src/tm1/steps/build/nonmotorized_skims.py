"""Build the walk/bike distance skims (RunModel.bat step 4).

Two stock Cube jobs, run as-is:

- ``CreateNonMotorizedNetwork.job``  ``hwy/freeflow.net`` -> ``hwy/nonMotorized.net``
  (flags every non-freeway link walkable/bikeable, plus the explicit bridge
  allowances; no cluster)
- ``NonMotorizedSkims.job``  -> ``skims/nonmotskm.tpp`` with DISTWALK / DISTBIKE /
  DIST tables.  The job hard-codes ``distributeintrastep processid='ctramp',
  processlist=1-4``, so a 4-node cluster is started around it.

The skim is built once per run — bikes and pedestrians do not congest the
network, so nothing in the feedback loop ever rewrites it.

Config::

    build_nonmotorized_skims:
      proj_dir: "{proj_dir}"

.. warning:: CUBE-ERA IMPLEMENTATION — DELETE WITH CUBE, KEEP THE STEP'S JOB.

    The walk/bike/all-links distance tables are a permanent artifact — the
    demand models read DISTWALK/DISTBIKE regardless of assignment engine.  The
    two ``.job`` scripts are not: a non-Cube engine skims shortest-path
    distance natively in a few lines.  If both engines ever coexist here,
    follow ``assignment``'s ``backend:`` pattern (same artifact contract, two
    solvers); otherwise replace this module's body wholesale when Cube goes.
"""

import logging
from pathlib import Path

from tm1.assignment.cube.runner import run_cube_job

log = logging.getLogger(__name__)

#: NonMotorizedSkims.job distributes over ``processlist = 1-4`` (fixed in the
#: script), so the cluster must run exactly nodes 1-4.
_NODES = 4


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Build hwy/nonMotorized.net, then skim it to skims/nonmotskm.tpp."""
    step_cfg = cfg.get("steps", {}).get("build_nonmotorized_skims", {}) or {}
    proj_dir = Path(step_cfg.get("proj_dir") or cfg["proj_dir"])
    skim = proj_dir / "skims" / "nonmotskm.tpp"

    if not kwargs.get("force", False) and skim.exists():
        log.info("Non-motorized skims already built: %s", skim)
        return "skipped"

    freeflow = proj_dir / "hwy" / "freeflow.net"
    if not freeflow.exists():
        msg = f"build_nonmotorized_skims input missing: {freeflow}"
        raise FileNotFoundError(msg)
    (proj_dir / "skims").mkdir(parents=True, exist_ok=True)

    scripts = proj_dir / "CTRAMP" / "scripts" / "skims"
    run_cube_job(scripts / "CreateNonMotorizedNetwork.job", proj_dir, timeout=1800)
    run_cube_job(
        scripts / "NonMotorizedSkims.job", proj_dir,
        cluster_nodes=_NODES, commpath=proj_dir / "commpath", timeout=7200,
    )

    if not skim.exists() or skim.stat().st_size == 0:
        msg = f"NonMotorizedSkims.job finished but produced no {skim}"
        raise FileNotFoundError(msg)
    return None
