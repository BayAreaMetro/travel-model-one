"""Bridge ActivitySim demand into the Cube highway/transit assignment.

ActivitySim's ``write_trip_matrices`` step emits one OMX per time period
(``trips_{ea,am,md,pm,ev}.omx``) holding 23 person-trip tables, already
sample-rate-expanded to full population and already split by period.  The legacy
Cube assignment instead consumes ``main/trips{PERIOD}.tpp`` — the 29-table matrix
that ``PrepAssign.job`` built from the CT-RAMP trip lists.

:func:`build_trip_matrices` is the faithful replacement for PrepAssign in the
ActivitySim flow: it renames the 23 ActivitySim tables to the Cube assignment
class names HwyAssign/TransitAssign read by name, and appends the 6 TNC/AV
classes HwyAssign references as zeros (this ActivitySim config folds TNC/taxi/AV
demand into the drive-alone/shared-ride modes, so they carry no separate trips).
"""

import logging
from pathlib import Path

import numpy as np
import openmatrix as omx

from cubeio import write_tpp

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

# ActivitySim write_trip_matrices table base-name -> trips{PERIOD}.tpp table name
# (the period suffix is appended to the ActivitySim name, e.g. DRIVEALONEFREE_AM).
# Order matches PrepAssign.job's final mato; HwyAssign/TransitAssign read by name.
_ASIM_TO_CUBE: dict[str, str] = {
    "DRIVEALONEFREE": "da",
    "DRIVEALONEPAY": "datoll",
    "SHARED2FREE": "sr2",
    "SHARED2PAY": "sr2toll",
    "SHARED3FREE": "sr3",
    "SHARED3PAY": "sr3toll",
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

# The 6 TNC/AV classes HwyAssign references but this ActivitySim config does not
# model separately -> written as zero tables so the name lookups resolve.
_ZERO_CLASSES: tuple[str, ...] = ("da_tnc", "s2_tnc", "s3_tnc", "da_av", "s2_av", "s3_av")

# Canonical 29-table order (PrepAssign.job step five).
_TABLE_ORDER: tuple[str, ...] = (*_ASIM_TO_CUBE.values(), *_ZERO_CLASSES)


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
            data: dict[str, np.ndarray] = {}
            missing: list[str] = []
            for asim_name, cube_name in _ASIM_TO_CUBE.items():
                key = f"{asim_name}_{period}"
                if key in avail:
                    data[cube_name] = np.asarray(f[key], dtype=np.float64)
                else:
                    data[cube_name] = zero
                    missing.append(key)
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
