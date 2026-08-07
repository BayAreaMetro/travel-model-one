"""Faithful Cube transit assignment + skims (RunModel ``trnAssign.bat``, FAST config).

RunModel runs transit with ``TRNCONFIG=FAST`` -> ``MAXTRNITERS=0``, so the inner
assignment/dwell loop converges in a single pass.  This module replays that single
pass with the as-is Cube jobs, run from a per-iteration working directory
``trn/TransitAssignment.iter{ITER}/`` exactly as the batch file does:

    PrepHwyNet -> BuildTransitNetworks -> (TransitAssign -> TransitSkims ->
    transitDwellAccess.py per period) -> copy trnskm*.tpp up to skims/

``transitDwellAccess.py`` needs the (Python-3) NetworkWrangler library, which is
not a package dependency of ``tm1``; its location is passed in via ``wrangler_path``
and injected on the child process's ``PYTHONPATH``.
"""

import logging
import shutil
from pathlib import Path

from tm1.assignment.cube.runner import run_cube_job

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

# BuildTransitNetworks shells out to gawk (reverseLinks/Select_PNRs/createLocalBusKNRs
# .awk) via Cube ``*`` SYS commands; gawk ships with Git for Windows but isn't on the
# scheduled task's PATH, so we prepend its dir for the transit jobs.
_GAWK_DIR = r"C:\Program Files\Git\usr\bin"


def _gawk_path() -> str:
    """PATH value that prepends gawk's dir (resolved, with a Git-for-Windows default)."""
    d = shutil.which("gawk")
    gdir = str(Path(d).parent) if d else _GAWK_DIR
    return f"{gdir};%PATH%"

# TransitAssign/TransitSkims distribute accegg(3) x path(5) = up to 15 tasks per
# period via DistributeMultistep (the job caps at <=18); the cluster must have at
# least that many nodes.
_NODES_TRANSIT = 15


def _scripts(proj_dir: Path) -> Path:
    return proj_dir / "CTRAMP" / "scripts"


def _stage_lines(trn_dir: Path, ta_dir: Path) -> None:
    """Seed the iteration dir with this round's transit line files.

    Faithful to trnAssign.bat's first global iteration: start from the
    period-specific ``transitOriginal{P}.lin`` (built at model setup), copying it to
    ``transit{P}_0.lin`` and the working ``transit{P}.lin``.
    """
    for per in PERIODS:
        orig = trn_dir / f"transitOriginal{per}.lin"
        if not orig.exists():
            msg = f"Transit line file missing: {orig}"
            raise FileNotFoundError(msg)
        shutil.copy2(orig, ta_dir / f"transit{per}_0.lin")
        shutil.copy2(orig, ta_dir / f"transit{per}.lin")


def run_prep_hwynet(proj_dir: Path, ta_dir: Path, iteration: int) -> None:
    """PrepHwyNet.job — bus times + transit access/transfer links (no cluster)."""
    env = {"MODEL_DIR": str(proj_dir), "ITER": iteration}
    run_cube_job(
        _scripts(proj_dir) / "skims" / "PrepHwyNet.job", ta_dir,
        env_extra=env, timeout=1800,
    )


def run_build_transit_networks(proj_dir: Path, ta_dir: Path) -> None:
    """BuildTransitNetworks.job — trnbuild + gawk -> transit support links (.dat)."""
    env = {"MODEL_DIR": str(proj_dir), "PATH": _gawk_path()}
    run_cube_job(
        _scripts(proj_dir) / "skims" / "BuildTransitNetworks.job", ta_dir,
        env_extra=env, timeout=3600,
    )


def run_transit_assignment(
    proj_dir: Path, ta_dir: Path, *, cluster_nodes: int = _NODES_TRANSIT
) -> None:
    """TransitAssign.job — assign ``main/trips{P}.tpp`` transit demand to the network.

    Distributes accegg(3) x path(5) = 15 tasks per period over the cluster
    (``processnum`` 1-15), producing per-task ``trnlink*``/``trnline*`` volumes that
    the skim + dwell steps consume.
    """
    env = {"MODEL_DIR": str(proj_dir)}
    run_cube_job(
        _scripts(proj_dir) / "assign" / "TransitAssign.job", ta_dir,
        env_extra=env, cluster_nodes=cluster_nodes, commpath=proj_dir / "commpath",
        timeout=7200,
    )


def run_transit_skims(
    proj_dir: Path,
    ta_dir: Path,
    *,
    trnassign_iter: int = 0,
    prev_trnassign_iter: str = "NEG1",
    cluster_nodes: int = _NODES_TRANSIT,
) -> None:
    """TransitSkims.job — skim the assigned transit network (cluster).

    Produces ``trnskm{period}_{access}_{path}_{egress}.avg.iter{N}.tpp`` per task —
    the MSA-averaged level-of-service skims.  For the FAST single pass the averaging
    over one iteration is effectively the raw skim, so these are the skims the copy-up
    delivers to ``skims/``.
    """
    env = {
        "MODEL_DIR": str(proj_dir),
        "TRNASSIGNITER": trnassign_iter,
        "PREVTRNASSIGNITER": prev_trnassign_iter,
    }
    run_cube_job(
        _scripts(proj_dir) / "skims" / "TransitSkims.job", ta_dir,
        env_extra=env, cluster_nodes=cluster_nodes, commpath=proj_dir / "commpath",
        timeout=7200,
    )


def copy_transit_skims(ta_dir: Path, skims_dir: Path) -> int:
    """Copy the MSA-averaged transit skims up to ``skims/`` (trnAssign.bat copyup).

    Keeps the ``.avg.iter{N}`` suffix so ``convert_skims``' ``find_latest_iter``
    resolves them.  Returns the number of files copied.
    """
    skims_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in ta_dir.glob("trnskm*.avg.iter*.tpp"):
        shutil.copy2(f, skims_dir / f.name)
        n += 1
    return n


def run_transit(
    proj_dir: str | Path,
    iteration: int,
    *,
    cluster_nodes: int = _NODES_TRANSIT,
    trnassign_iter: int = 0,
) -> None:
    """One faithful transit assignment + skim pass (RunModel FAST config).

    Replays trnAssign.bat's single pass from ``trn/TransitAssignment.iter{N}/``:
    stage lines -> PrepHwyNet -> BuildTransitNetworks -> TransitAssign ->
    TransitSkims -> copy the averaged skims up to ``skims/``.

    ``PrepHwyNet.job`` reads ``hwy/avgLOAD{P}.net`` to derive bus speeds, and
    :func:`~tm1.assignment.cube.highway.run_highway_feedback` rewrites that file --
    so *which* round's speeds this sees is decided by the caller, not here.
    :func:`tm1.assignment.cube.ctramp.run_iteration` calls this **before** feedback,
    matching ``RunIteration.bat``, and therefore uses the previous round's network;
    :func:`tm1.assignment.cube.asim_bridge.run_assignment_iteration` calls it
    **after**.  That divergence is known and unresolved -- see the warning on the
    latter.

    The bus-dwell feedback (``transitDwellAccess.py`` Complex mode) only affects the
    *next* global iteration's bus speeds and is not yet wired; a single global
    iteration's transit skims are unaffected.
    """
    proj_dir = Path(proj_dir)
    trn = proj_dir / "trn"
    ta_dir = trn / f"TransitAssignment.iter{iteration}"
    ta_dir.mkdir(parents=True, exist_ok=True)
    log.info("--- Transit assignment pass (iter %d) ---", iteration)

    _stage_lines(trn, ta_dir)
    run_prep_hwynet(proj_dir, ta_dir, iteration)
    run_build_transit_networks(proj_dir, ta_dir)
    run_transit_assignment(proj_dir, ta_dir, cluster_nodes=cluster_nodes)
    run_transit_skims(proj_dir, ta_dir, trnassign_iter=trnassign_iter,
                      cluster_nodes=cluster_nodes)
    n = copy_transit_skims(ta_dir, proj_dir / "skims")
    log.info("Transit pass complete: copied %d skim files to skims/", n)
