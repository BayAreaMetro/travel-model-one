"""Bridge ActivitySim demand into the Cube highway/transit assignment.

ActivitySim's ``write_trip_matrices`` step emits one OMX per time period
(``trips_{ea,am,md,pm,ev}.omx``) holding 23 person-trip tables, already
sample-rate-expanded to full population and already split by period.  The legacy
Cube assignment instead consumes ``main/trips{PERIOD}.tpp`` — the 29-table matrix
that ``PrepAssign.job`` built from the CT-RAMP trip lists.

:func:`build_trip_matrices` is the faithful replacement for PrepAssign (steps 3-5)
in the ActivitySim flow.  It maps the ActivitySim tables to the Cube assignment
class names HwyAssign/TransitAssign read by name, applying two conversions the
legacy PrepAssign did and a straight rename would miss:

* ActivitySim's shared-ride OMX tables are already VEHICLE trips
  (``write_trip_matrices`` divides by occupancy), but ``trips{P}.tpp`` holds PERSON
  trips that HwyAssign divides again (``mi.1.sr2 / 2``) -- so sr2/sr3 are restored
  to person trips (x2, x3.25) here.
* ride-hail (taxi/TNC) person trips are folded across occupancy bins: taxi into
  the toll classes, TNC into the da_tnc/s2_tnc/s3_tnc classes, with the
  zero-passenger deadhead vehicles in da_tnc (PrepAssign steps 3-5).

Only the owned-AV classes (da_av/s2_av/s3_av) are unmodelled and written as zeros.
Shares/occupancy/ZPV come from ``base-models/assignment/aeq_params.yaml``.
"""

import logging
import shutil
from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio import write_tpp
from tm1.assignment.cube.runner import run_cube_job

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

# Cube Cluster node counts: HwyAssign distributes 5 periods (DistributeMultistep)
# AND parallelises within each period (DistributeIntrastep) up to node 48
# (see HwyIntraStep.block); the skim/feedback jobs only distribute the 5 periods.
_NODES_ASSIGN = 48
_NODES_PERIOD = 5

# ActivitySim write_trip_matrices table base-name -> trips{PERIOD}.tpp table name,
# for the classes that pass through UNCHANGED (walk, bike, the 15 transit access/
# line-haul/egress combos).  The period suffix is appended to the ActivitySim name
# (e.g. WALK_LOC_WALK_AM).  These are person trips in both OMX and the tpp.
_DIRECT_MAP: dict[str, str] = {
    "WALK": "walk",
    "BIKE": "bike",
    "WALK_LOC_WALK": "wlk_loc_wlk",
    "WALK_LRF_WALK": "wlk_lrf_wlk",
    "WALK_EXP_WALK": "wlk_exp_wlk",
    "WALK_HVY_WALK": "wlk_hvy_wlk",
    "WALK_COM_WALK": "wlk_com_wlk",
    "DRIVE_LOC_WALK": "drv_loc_wlk",
    "DRIVE_LRF_WALK": "drv_lrf_wlk",
    "DRIVE_EXP_WALK": "drv_exp_wlk",
    "DRIVE_HVY_WALK": "drv_hvy_wlk",
    "DRIVE_COM_WALK": "drv_com_wlk",
    "WALK_LOC_DRIVE": "wlk_loc_drv",
    "WALK_LRF_DRIVE": "wlk_lrf_drv",
    "WALK_EXP_DRIVE": "wlk_exp_drv",
    "WALK_DRIVE_HVY": "wlk_hvy_drv",  # ActivitySim's name for walk-heavyrail-drive
    "WALK_COM_DRIVE": "wlk_com_drv",
}

# Owned-AV classes HwyAssign references but this ActivitySim config does not model
# -> always zero.  (The da_tnc/s2_tnc/s3_tnc TNC classes ARE modelled and are built
# from the ride-hail demand below; they are NOT zero.)
_ZERO_CLASSES: tuple[str, ...] = ("da_av", "s2_av", "s3_av")

# Canonical 29-table order (PrepAssign.job step five): auto, walk/bike, 15 transit,
# TNC, owned-AV.  HwyAssign/TransitAssign read tables by name.
_AUTO_CLASSES: tuple[str, ...] = ("da", "datoll", "sr2", "sr2toll", "sr3", "sr3toll")
_TNC_CLASSES: tuple[str, ...] = ("da_tnc", "s2_tnc", "s3_tnc")
_TABLE_ORDER: tuple[str, ...] = (
    *_AUTO_CLASSES, *_DIRECT_MAP.values(), *_TNC_CLASSES, *_ZERO_CLASSES,
)


def build_trip_matrices(
    asim_output_dir: str | Path,
    main_dir: str | Path,
    *,
    periods: tuple[str, ...] = PERIODS,
) -> list[Path]:
    """Convert ActivitySim trip OMX into Cube ``main/trips{PERIOD}.tpp`` demand.

    Parameters
    ----------
    asim_output_dir
        ActivitySim output dir containing ``trips_{period}.omx``.
    main_dir
        Destination ``main/`` dir; ``trips{PERIOD}.tpp`` are written here.
    periods
        Time periods to build (default all five).

    Returns:
        The written ``trips{PERIOD}.tpp`` paths.
    """
    asim_output_dir = Path(asim_output_dir)
    main_dir = Path(main_dir)
    main_dir.mkdir(parents=True, exist_ok=True)

    # Ride-hail / occupancy policy (PrepAssign.job steps 3-5), from aeq_params.yaml
    # so the Cube and aeq demand paths share one source of truth.
    from tm1.assignment.aeq.params import load_aeq_params  # noqa: PLC0415

    hw = load_aeq_params().highway
    occ2, occ3 = hw.occupancy["sr2"], hw.occupancy["sr3"]
    rh = hw.ridehail

    written: list[Path] = []
    for period in periods:
        omx_path = asim_output_dir / f"trips_{period.lower()}.omx"
        if not omx_path.exists():
            msg = f"ActivitySim trip matrix not found: {omx_path}"
            raise FileNotFoundError(msg)

        with omx.open_file(str(omx_path), "r") as f:
            avail = set(f.list_matrices())
            zones = f.shape()[0]
            zero = np.zeros((zones, zones), dtype=np.float64)
            missing: list[str] = []

            def _t(asim_name: str) -> np.ndarray:
                """Read an ActivitySim OMX table for this period (0 if absent)."""
                key = f"{asim_name}_{period}"
                if key in avail:
                    return np.asarray(f[key], dtype=np.float64)
                missing.append(key)
                return zero

            data: dict[str, np.ndarray] = {}
            # Pass-through classes (walk, bike, transit): person trips, unchanged.
            for asim_name, cube_name in _DIRECT_MAP.items():
                data[cube_name] = _t(asim_name)

            # Auto classes: ActivitySim OMX shared-ride tables are VEHICLE trips
            # (write_trip_matrices already divides by occupancy); the Cube tpp holds
            # PERSON trips (HwyAssign divides again by /2, /3.25). Restore persons.
            # Taxi folds into the toll classes by occupancy share (PrepAssign step 5).
            taxi = _t(rh.tables["taxi"])
            single = _t(rh.tables["single"])
            shared = _t(rh.tables["shared"])
            ts = rh.shares["taxi"]
            data["da"] = _t("DRIVEALONEFREE")
            data["datoll"] = _t("DRIVEALONEPAY") + taxi * ts["da"]
            data["sr2"] = _t("SHARED2FREE") * occ2
            data["sr2toll"] = _t("SHARED2PAY") * occ2 + taxi * ts["s2"]
            data["sr3"] = _t("SHARED3FREE") * occ3
            data["sr3toll"] = _t("SHARED3PAY") * occ3 + taxi * ts["s3"]

            # TNC classes: split each mode's person trips across occupancy bins.
            # da_tnc holds only the zero-passenger deadhead (occ-1 share is 0): the
            # per-occupancy person trips converted to vehicles, transposed to the
            # return leg, times the ZPV factor. s2_tnc/s3_tnc stay as person trips
            # (HwyAssign divides them). da/s2/s3_av are unmodelled -> zero.
            ss, sh = rh.shares["single"], rh.shares["shared"]
            s2_tnc = single * ss["s2"] + shared * sh["s2"]
            s3_tnc = single * ss["s3"] + shared * sh["s3"]
            data["da_tnc"] = (s2_tnc / occ2 + s3_tnc / occ3).T * rh.zpv_factor
            data["s2_tnc"] = s2_tnc
            data["s3_tnc"] = s3_tnc
            for cls in _ZERO_CLASSES:
                data[cls] = zero

        if missing:
            log.warning("%s: %d ActivitySim tables absent, zero-filled: %s",
                        omx_path.name, len(missing), ", ".join(missing))

        ordered = {name: data[name] for name in _TABLE_ORDER}
        out = main_dir / f"trips{period}.tpp"
        write_tpp(out, ordered, zones=zones)
        total = sum(float(m.sum()) for m in data.values())
        log.info("Wrote %s (%d zones, %d tables, %.0f total person-trips)",
                 out.name, zones, len(ordered), total)
        written.append(out)

    return written


# ---------------------------------------------------------------------------
# Cube highway assignment + feedback (faithful RunIteration.bat replication)
# ---------------------------------------------------------------------------


def _job(scripts_dir: Path, *parts: str) -> Path:
    return scripts_dir.joinpath(*parts)


def run_highway_assignment(
    proj_dir: str | Path,
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
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_cube_job(
        _job(scripts, "assign", assign_job), proj_dir,
        cluster_nodes=cluster_nodes, timeout=timeout,
    )


def run_highway_feedback(
    proj_dir: str | Path,
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
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    hwy = proj_dir / "hwy"
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
        "COMMPATH": str(proj_dir / "commpath"),
    }

    run_cube_job(_job(scripts, "feedback", "RenameAssignmentVariables.job"),
                 proj_dir, env_extra=env)

    if iteration > 1:
        run_cube_job(_job(scripts, "feedback", "AverageNetworkVolumes.job"),
                     proj_dir, env_extra=env)
        run_cube_job(_job(scripts, "feedback", "CalculateSpeeds.job"),
                     proj_dir, env_extra=env, cluster_nodes=_NODES_PERIOD)
    else:
        # First iteration: the renamed loaded network IS the averaged network.
        for per in PERIODS:
            shutil.copy2(iterdir / f"LOAD{per}_renamed.net",
                         iterdir / f"avgLOAD{per}.net")

    run_cube_job(_job(scripts, "feedback", "TestNetworkConvergence.job"),
                 proj_dir, env_extra=env)
    run_cube_job(_job(scripts, "feedback", "MergeNetworks.job"),
                 proj_dir, env_extra=env)

    # Publish the averaged networks for the next iteration's skims/assignment.
    for per in PERIODS:
        shutil.copy2(iterdir / f"avgLOAD{per}.net", hwy / f"avgLOAD{per}.net")
    log.info("Feedback iter %d complete: hwy/avgLOAD{EA..EV}.net refreshed", iteration)


def run_highway_skims(
    proj_dir: str | Path,
    *,
    cluster_nodes: int = _NODES_PERIOD,
    timeout: float = 3600,
) -> None:
    """Build highway skims from the averaged networks (``HwySkims.job``, as-is)."""
    proj_dir = Path(proj_dir)
    scripts = proj_dir / "CTRAMP" / "scripts"
    run_cube_job(
        _job(scripts, "skims", "HwySkims.job"), proj_dir,
        cluster_nodes=cluster_nodes, timeout=timeout,
    )


def refresh_skims_omx(proj_dir: str | Path, skims_omx_path: str | Path) -> Path:
    """Rebuild the ActivitySim skims OMX from the project's Cube TPP skims.

    Reuses :mod:`tm1.steps.convert_skims`' mapping.  Highway skims (``HWYSKM*``)
    are always present after :func:`run_highway_skims`; transit (``trnskm*``) and
    non-motorized (``nonmotskm``) skims are whatever is currently in ``skims/`` —
    for the highway-only loop these are frozen from a reference run.  Any mapped
    TPP that is absent is skipped with a warning (never silently dropped).
    """
    from cubeio import tpp_to_omx  # noqa: PLC0415
    from tm1.steps.convert_skims import build_file_map  # noqa: PLC0415

    proj_dir = Path(proj_dir)
    skims_dir = proj_dir / "skims"
    skims_omx_path = Path(skims_omx_path)

    file_map = build_file_map(skims_dir)
    present = {p: m for p, m in file_map.items() if Path(p).exists()}
    missing = [Path(p).name for p in file_map if not Path(p).exists()]
    if missing:
        log.warning("refresh_skims_omx: %d mapped TPP skims absent, skipped: %s",
                    len(missing), ", ".join(sorted(missing)))

    skims_omx_path.parent.mkdir(parents=True, exist_ok=True)
    tpp_to_omx(present, skims_omx_path)
    log.info("Refreshed %s from %d TPP skim files", skims_omx_path.name, len(present))
    return skims_omx_path


def run_assignment_iteration(  # noqa: PLR0913
    proj_dir: str | Path,
    asim_output_dir: str | Path,
    iteration: int,
    *,
    skims_omx_path: str | Path | None = None,
    prev_iteration: int | None = None,
    wgt: float | None = None,
    prev_wgt: float | None = None,
    build_skims: bool = True,
    cluster_nodes: int = _NODES_ASSIGN,
    assign_job: str = "HwyAssign.job",
    do_transit: bool = True,
    transit_nodes: int = 15,
) -> None:
    """One full global feedback iteration of the faithful Cube assignment loop.

    bridge ActivitySim trips -> ``main/trips{P}.tpp`` -> HwyAssign -> feedback
    (-> ``hwy/avgLOAD{P}.net``) -> HwySkims -> refresh ``skims.omx`` for the next
    ActivitySim run.  Transit assignment is not yet wired; transit/non-motorized
    skims are taken as frozen in ``skims/``.

    Parameters
    ----------
    asim_output_dir
        ActivitySim output dir holding this round's ``trips_{period}.omx``.
    skims_omx_path
        Where to (re)write the ActivitySim skims OMX (required when
        ``build_skims``).
    """
    proj_dir = Path(proj_dir)
    log.info("=== Assignment iteration %d ===", iteration)
    build_trip_matrices(asim_output_dir, proj_dir / "main")
    run_highway_assignment(proj_dir, cluster_nodes=cluster_nodes, assign_job=assign_job)
    run_highway_feedback(
        proj_dir, iteration,
        prev_iteration=prev_iteration, wgt=wgt, prev_wgt=prev_wgt,
    )
    if build_skims:
        run_highway_skims(proj_dir)
        if do_transit:
            from tm1.assignment.cube.transit import run_transit  # noqa: PLC0415
            run_transit(proj_dir, iteration, cluster_nodes=transit_nodes)
        if skims_omx_path is None:
            msg = "skims_omx_path is required when build_skims=True"
            raise ValueError(msg)
        refresh_skims_omx(proj_dir, skims_omx_path)
