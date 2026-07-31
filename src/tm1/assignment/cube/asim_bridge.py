"""Bridge ActivitySim demand into the Cube highway/transit assignment.

ActivitySim's ``write_trip_matrices`` step emits one OMX per time period
(``trips_{ea,am,md,pm,ev}.omx``) holding 23 person-trip tables, already
sample-rate-expanded and split by period.  The legacy Cube assignment instead
consumes ``main/trips{PERIOD}.tpp`` -- the 29-table matrix that
``PrepAssign.job`` built from the CT-RAMP trip lists.

:func:`build_trip_matrices` is the faithful replacement for PrepAssign
(steps 3-5) in the ActivitySim flow, applying two conversions a straight rename
would miss:

* ActivitySim's shared-ride OMX tables are already VEHICLE trips
  (``write_trip_matrices`` divides by occupancy), but ``trips{P}.tpp`` holds
  PERSON trips that HwyAssign divides again (``mi.1.sr2 / 2``) -- so sr2/sr3 are
  restored to person trips (x2, x3.25) here.
* ride-hail (taxi/TNC) person trips are folded across occupancy bins: taxi into
  the toll classes, TNC into da_tnc/s2_tnc/s3_tnc, with zero-passenger deadhead
  vehicles in da_tnc (PrepAssign steps 3-5).

Only the owned-AV classes (da_av/s2_av/s3_av) are unmodelled, written as zeros.
Shares/occupancy/ZPV come from ``default-configs/assignment/params.yaml``.

The CT-RAMP path needs none of this -- ``PrepAssign.job`` produces the same tpp
from CT-RAMP's own trip lists.  See :mod:`tm1.assignment.cube.ctramp`.
"""

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio import write_tpp
from tm1.assignment import expand_period
from tm1.assignment.cube.highway import (
    _NODES_ASSIGN,
    PERIODS,
    run_highway_assignment,
    run_highway_feedback,
    run_highway_skims,
)

log = logging.getLogger(__name__)


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
    demand: str,
    main_dir: str | Path,
    *,
    periods: tuple[str, ...] = PERIODS,
) -> list[Path]:
    """Convert ActivitySim trip OMX into Cube ``main/trips{PERIOD}.tpp`` demand.

    Parameters
    ----------
    demand
        Per-period path pattern for the ActivitySim trip matrices, as declared by
        the assignment step's ``demand:`` key (e.g.
        ``".../output/trips_{period}.omx"``).  Read rather than reconstructed, so
        the seam stays the single statement of where demand lives.
    main_dir
        Destination ``main/`` dir; ``trips{PERIOD}.tpp`` are written here.
    periods
        Time periods to build (default all five).

    Returns:
        The written ``trips{PERIOD}.tpp`` paths.
    """
    main_dir = Path(main_dir)
    main_dir.mkdir(parents=True, exist_ok=True)

    # Ride-hail / occupancy policy (PrepAssign.job steps 3-5), from params.yaml
    # so the Cube and aeq demand paths share one source of truth.
    from tm1.assignment.params import load_aeq_params  # noqa: PLC0415

    hw = load_aeq_params().highway
    occ2, occ3 = hw.occupancy["sr2"], hw.occupancy["sr3"]
    rh = hw.ridehail

    written: list[Path] = []
    for period in periods:
        omx_path = Path(expand_period(demand, period))
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




def refresh_skims_omx(run_dir: str | Path, skims_omx_path: str | Path) -> Path:
    """Rebuild the ActivitySim skims OMX from the project's Cube TPP skims.

    Reuses :mod:`tm1.steps.convert_skims`' mapping.  Highway skims (``HWYSKM*``)
    are always present after :func:`run_highway_skims`; transit (``trnskm*``) and
    non-motorized (``nonmotskm``) skims are whatever is currently in ``skims/`` —
    for the highway-only loop these are frozen from a reference run.  Any mapped
    TPP that is absent is skipped with a warning (never silently dropped).
    """
    from cubeio import tpp_to_omx  # noqa: PLC0415
    from tm1.steps.convert_skims import build_file_map  # noqa: PLC0415

    run_dir = Path(run_dir)
    skims_dir = run_dir / "skims"
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
    run_dir: str | Path,
    demand: str,
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

    Bridge ActivitySim trips -> ``main/trips{P}.tpp`` -> HwyAssign -> feedback
    (-> ``hwy/avgLOAD{P}.net``) -> HwySkims -> transit -> refresh ``skims.omx`` for
    the next ActivitySim run.

    .. warning::

       **THIS SEQUENCE DIVERGES FROM THE CT-RAMP ONE AND MUST BE RECONCILED BEFORE
       PARITY IS CLAIMED.**  ``RunIteration.bat`` -- and therefore
       :func:`tm1.assignment.cube.ctramp.run_iteration` -- runs *transit before
       feedback* (transit is step 4, feedback step 5), so transit reads the
       *previous* round's ``hwy/avgload{period}.net``.  This function runs transit
       *after* feedback, so it reads *this* round's recomputed congested speeds.

       ``PrepHwyNet.job`` line 96 reads that network to derive bus speeds, so the
       two orders give different transit level of service and different boardings,
       diverging most at iteration 1 where the alternative is a warm-start network.

       The order here is an artifact of when transit was added, not a modelling
       decision: ``refresh_skims_omx`` has to run last, and transit was inserted
       beside the other skim-producing step.  Nothing forces it --
       ``HwyAssign -> transit -> feedback -> HwySkims -> refresh`` satisfies both
       constraints.  It is left alone deliberately: correcting it moves ActivitySim
       transit results, and the AequilibraE parity work is calibrated against the
       current numbers.  Fix it and re-validate as one deliberate change, not as a
       side effect of a refactor.

    Parameters
    ----------
    demand
        Per-period path pattern for this round's ActivitySim trip matrices, from
        the assignment step's ``demand:`` key.
    skims_omx_path
        Where to (re)write the ActivitySim skims OMX (required when
        ``build_skims``).
    """
    run_dir = Path(run_dir)
    log.info("=== Assignment iteration %d ===", iteration)
    build_trip_matrices(demand, run_dir / "main")
    run_highway_assignment(run_dir, cluster_nodes=cluster_nodes, assign_job=assign_job)
    run_highway_feedback(
        run_dir, iteration,
        prev_iteration=prev_iteration, wgt=wgt, prev_wgt=prev_wgt,
    )
    if build_skims:
        run_highway_skims(run_dir)
        if do_transit:
            from tm1.assignment.cube.transit import run_transit  # noqa: PLC0415
            run_transit(run_dir, iteration, cluster_nodes=transit_nodes)
        if skims_omx_path is None:
            msg = "skims_omx_path is required when build_skims=True"
            raise ValueError(msg)
        refresh_skims_omx(run_dir, skims_omx_path)
