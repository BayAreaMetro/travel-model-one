"""Interpolate high-speed-rail trip tables to the model year (RunModel.bat step 3).

Native replacement for ``HsrTripGeneration.job``.  The California HSR model
supplies trip tables for 2040 and 2050 only; Travel Model One assumes no HSR
trips before the opening year and interpolates linearly after it.

The Cube job spreads that over two ``MATRIX`` passes and an intermediate file,
carrying a slope and intercept scaled by 100 to protect precision::

    m = 100 * (v2050 - v2040) / (2050 - 2040)
    b = 100 * (v2040 - m * 0.01 * 2040)
    out = 0.01 * b + m * 0.01 * model_year

The scaling cancels exactly, so this is a plain two-point interpolation, done
here in one pass with no intermediate ``.tpp``::

    out = v2040 + (v2050 - v2040) * (model_year - 2040) / 10

Everything is zero when the model year precedes 2040, or when
``HSR_Interregional_Disable`` is set -- a switch ``configure_ctramp`` writes
into ``trnParam.block``, which is where this step reads it from, so the two
cannot disagree.

Config::

    build_hsr_trips:
      from: "{reference_run}/INPUT/nonres"
      to: "{proj_dir}/nonres"
      model_year: 2023
      trn_param: "{proj_dir}/CTRAMP/scripts/block/trnParam.block"

.. warning:: CUBE-ERA FILE FORMAT, PERMANENT MODEL CONTENT.

    The interpolation is a property of the HSR forecast and outlives Cube; only
    the ``.tpp`` container is Cube-specific.  When the demand seam moves to OMX,
    change the reader/writer here, not the arithmetic.
"""

import logging
import re
from pathlib import Path

import numpy as np

from cubeio import read_tpp, write_tpp
from tm1.steps.build import resolve_path

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")

#: The two forecast years the California HSR model delivers.
_BASE_YEAR, _HORIZON_YEAR = 2040, 2050

#: Written table order, matching HsrTripGeneration.job's second MATRIX pass.
_TABLES: tuple[str, ...] = ("da_veh", "sr2_veh", "taxi_veh", "transit", "walk")


def hsr_disabled(trn_param: Path) -> bool:
    """Read ``HSR_Interregional_Disable`` from ``trnParam.block``.

    Absent means enabled: the Cube job reads the block unconditionally, so a
    missing switch would have been a Cube error rather than a silent default.
    """
    if not trn_param.exists():
        msg = f"build_hsr_trips: {trn_param} not found (configure_ctramp writes it)"
        raise FileNotFoundError(msg)
    match = re.search(
        r"\nHSR_Interregional_Disable[ \t]*=[ \t]*(\S+)",
        trn_param.read_text(encoding="utf-8"), flags=re.IGNORECASE,
    )
    if match is None:
        msg = f"build_hsr_trips: HSR_Interregional_Disable not set in {trn_param}"
        raise ValueError(msg)
    return int(float(match.group(1))) == 1


def interpolate(base: dict, horizon: dict, model_year: int) -> dict[str, np.ndarray]:
    """Linear two-point interpolation between the 2040 and 2050 tables."""
    fraction = (model_year - _BASE_YEAR) / (_HORIZON_YEAR - _BASE_YEAR)
    return {
        name: base["data"][name]
        + (horizon["data"][name] - base["data"][name]) * fraction
        for name in _TABLES
    }


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Write ``nonres/tripsHsr{PERIOD}.tpp`` for the scenario's model year."""
    step_cfg = cfg.get("steps", {}).get("build_hsr_trips", {}) or {}
    src_dir = resolve_path(step_cfg, cfg, "from", "nonres")
    out_dir = resolve_path(step_cfg, cfg, "to", "nonres")
    model_year = int(step_cfg["model_year"])
    trn_param = resolve_path(
        step_cfg, cfg, "trn_param", "CTRAMP", "scripts", "block", "trnParam.block"
    )

    targets = [out_dir / f"tripsHsr{period}.tpp" for period in PERIODS]
    if not kwargs.get("force", False) and all(t.exists() for t in targets):
        log.info("HSR trip tables already built in %s", out_dir)
        return "skipped"

    out_dir.mkdir(parents=True, exist_ok=True)
    disabled = hsr_disabled(trn_param)
    before_opening = model_year < _BASE_YEAR

    for period, target in zip(PERIODS, targets, strict=True):
        base = read_tpp(src_dir / f"tripsHsr{period}_{_BASE_YEAR}.tpp")
        if disabled or before_opening:
            zones = base["zones"]
            tables = {name: np.zeros((zones, zones)) for name in _TABLES}
        else:
            horizon = read_tpp(src_dir / f"tripsHsr{period}_{_HORIZON_YEAR}.tpp")
            if horizon["zones"] != base["zones"]:
                msg = (
                    f"tripsHsr{period}: {_BASE_YEAR} has {base['zones']} zones, "
                    f"{_HORIZON_YEAR} has {horizon['zones']}"
                )
                raise ValueError(msg)
            tables = interpolate(base, horizon, model_year)
        write_tpp(target, tables, zones=base["zones"])

    why = (
        "HSR_Interregional_Disable=1" if disabled
        else f"model year {model_year} precedes the {_BASE_YEAR} opening"
        if before_opening else None
    )
    log.info(
        "Wrote %d HSR trip tables to %s (%s)", len(targets), out_dir,
        f"all zero: {why}" if why else f"interpolated to {model_year}",
    )
    return None
