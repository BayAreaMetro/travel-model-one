"""Convert Cube TPP skim matrices to a single ActivitySim-compatible skims.omx.

Reads highway, transit, and non-motorized TPP files from a TM1 model run and
writes a single ``skims.omx`` with skim keys matching the ActivitySim UEC
naming convention.  See ``docs/skim_conversion_mapping.md`` for the full
mapping reference.

Matrices are streamed one TPP file at a time to keep memory usage bounded
(peak = one TPP file's worth of float64 arrays, not all ~730 at once).

Usage::

    python scripts/build_omx_skims.py \\\\MODEL3-C\\...\\skims -o skims.omx
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import numpy as np
import openmatrix as omx

from tm1.tpp import read_tpp

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Highway table mapping (Cube name -> ActivitySim key)
# ---------------------------------------------------------------------------

HWY_TABLE_MAP = {
    # Drive alone -- free facility
    "TIMEDA":       "SOV_TIME",
    "DISTDA":       "SOV_DIST",
    "BTOLLDA":      "SOV_BTOLL",
    # Drive alone -- toll facility
    "TOLLTIMEDA":   "SOVTOLL_TIME",
    "TOLLDISTDA":   "SOVTOLL_DIST",
    "TOLLBTOLLDA":  "SOVTOLL_BTOLL",
    "TOLLVTOLLDA":  "SOVTOLL_VTOLL",
    # Shared ride 2 -- free
    "TIMES2":       "HOV2_TIME",
    "DISTS2":       "HOV2_DIST",
    "BTOLLS2":      "HOV2_BTOLL",
    # Shared ride 2 -- toll
    "TOLLTIMES2":   "HOV2TOLL_TIME",
    "TOLLDISTS2":   "HOV2TOLL_DIST",
    "TOLLBTOLLS2":  "HOV2TOLL_BTOLL",
    "TOLLVTOLLS2":  "HOV2TOLL_VTOLL",
    # Shared ride 3+ -- free
    "TIMES3":       "HOV3_TIME",
    "DISTS3":       "HOV3_DIST",
    "BTOLLS3":      "HOV3_BTOLL",
    # Shared ride 3+ -- toll
    "TOLLTIMES3":   "HOV3TOLL_TIME",
    "TOLLDISTS3":   "HOV3TOLL_DIST",
    "TOLLBTOLLS3":  "HOV3TOLL_BTOLL",
    "TOLLVTOLLS3":  "HOV3TOLL_VTOLL",
}

# ---------------------------------------------------------------------------
# Transit constants
# ---------------------------------------------------------------------------

PERIODS = ("EA", "AM", "MD", "PM", "EV")
MODES = ("loc", "lrf", "exp", "hvy", "com")
ACCESS_EGRESS = (("wlk", "wlk"), ("drv", "wlk"), ("wlk", "drv"))

# Common components emitted for every transit path
_TRANSIT_COMMON = {
    "ivt": "TOTIVT", "iwait": "IWAIT", "xwait": "XWAIT",
    "waux": "WAUX", "fare": "FAR", "boards": "BOARDS",
}

# Additional components for drive-access or drive-egress paths only
_TRANSIT_DRIVE = {"dtime": "DTIM", "ddist": "DDIST"}

# Which IVT column becomes KEYIVT for each mode (LOC excluded -- uses TOTIVT)
_KEYIVT_SOURCE = {
    "com": "ivtCOM", "hvy": "ivtHVY", "exp": "ivtEXP", "lrf": "ivtLRF",
}

# ---------------------------------------------------------------------------
# Non-motorized (no period suffix)
# ---------------------------------------------------------------------------

NONMOT_TABLES = ("DISTWALK", "DISTBIKE", "DIST")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_transit_tpp(
    skims_dir: Path, period: str, access: str, mode: str, egress: str,
) -> Path | None:
    """Find the transit TPP, preferring highest ``.avg.iter{N}``."""
    stem = f"trnskm{period}_{access}_{mode}_{egress}"

    # Averaged iterations (highest wins -- most converged)
    candidates = sorted(
        skims_dir.glob(f"{stem}.avg.iter*.tpp"),
        key=lambda p: int(re.search(r"iter(\d+)", p.name).group(1)),
        reverse=True,
    )
    if candidates:
        return candidates[0]

    plain = skims_dir / f"{stem}.tpp"
    if plain.exists():
        return plain

    return None


def _transit_omx_keys(
    access: str, mode: str, egress: str, period: str,
) -> dict[str, str]:
    """Return {cube_table: omx_key} for one transit TPP file."""
    prefix = f"{access.upper()}_{mode.upper()}_{egress.upper()}"
    suffix = f"__{period.upper()}"

    mapping = {}

    # Common components (all paths)
    for cube_col, component in _TRANSIT_COMMON.items():
        mapping[cube_col] = f"{prefix}_{component}{suffix}"

    # Drive time/dist (drive-access or drive-egress only)
    if access == "drv" or egress == "drv":
        for cube_col, component in _TRANSIT_DRIVE.items():
            mapping[cube_col] = f"{prefix}_{component}{suffix}"

    # KEYIVT: mode-specific IVT (not LOC -- configs use TOTIVT directly)
    if mode in _KEYIVT_SOURCE:
        mapping[_KEYIVT_SOURCE[mode]] = f"{prefix}_KEYIVT{suffix}"

    # FERRYIVT: only LRF paths
    if mode == "lrf":
        mapping["ivtFerry"] = f"{prefix}_FERRYIVT{suffix}"

    return mapping


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def build_omx(skims_dir: Path, output: Path) -> None:
    """Read TPP skims from *skims_dir* and write *output* as OMX."""
    skims_dir = Path(skims_dir)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    zones: int | None = None
    count = 0
    seen: set[str] = set()

    with omx.open_file(str(output), "w") as f:

        def _write(omx_key: str, data: np.ndarray) -> None:
            nonlocal zones, count
            n = data.shape[0]
            if zones is None:
                zones = n
                f.create_mapping("zone", np.arange(1, zones + 1))
            if omx_key in seen:
                log.warning("duplicate key %s, skipping", omx_key)
                return
            seen.add(omx_key)
            f[omx_key] = data.astype(np.float32)
            count += 1

        # -- Highway -------------------------------------------------------
        log.info("Highway skims")
        for period in PERIODS:
            log.info("--- Period %s ---", period)
            tpp_path = skims_dir / f"HWYSKM{period}.tpp"
            if not tpp_path.exists():
                log.warning("%s not found, skipping", tpp_path.name)
                continue
            result = read_tpp(tpp_path)
            for cube_name, asim_key in HWY_TABLE_MAP.items():
                omx_key = f"{asim_key}__{period}"
                _write(omx_key, result["data"][cube_name])
                log.info("  %s/%s -> %s", tpp_path.name, cube_name, omx_key)

        # -- Transit -------------------------------------------------------
        log.info("Transit skims")
        for period in PERIODS:
            log.info("--- Period %s ---", period)
            per_lower = period.lower()
            for access, egress in ACCESS_EGRESS:
                for mode in MODES:
                    tpp_path = _find_transit_tpp(
                        skims_dir, per_lower, access, mode, egress,
                    )
                    if tpp_path is None:
                        continue
                    result = read_tpp(tpp_path)
                    mapping = _transit_omx_keys(access, mode, egress, period)
                    for cube_col, omx_key in mapping.items():
                        if cube_col in result["data"]:
                            _write(omx_key, result["data"][cube_col])
                            log.info("  %s/%s -> %s", tpp_path.name, cube_col, omx_key)

        # -- Non-motorized -------------------------------------------------
        log.info("Non-motorized skims")
        nonmot = skims_dir / "nonmotskm.tpp"
        if nonmot.exists():
            result = read_tpp(nonmot)
            for table in NONMOT_TABLES:
                _write(table, result["data"][table])
                log.info("  %s/%s -> %s", nonmot.name, table, table)
        else:
            log.warning("nonmotskm.tpp not found, skipping")

    log.info("Wrote %d matrices (%s zones) to %s", count, zones, output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert TM1 Cube TPP skims to ActivitySim OMX format.",
    )
    parser.add_argument(
        "skims_dir", type=Path,
        help="Directory containing TPP skim files from a TM1 model run",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("skims.omx"),
        help="Output OMX file path (default: skims.omx)",
    )
    args = parser.parse_args()

    if not args.skims_dir.is_dir():
        parser.error(f"Not a directory: {args.skims_dir}")

    build_omx(args.skims_dir, args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    SKIMS_DIR = Path(r"\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun\skims")
    OUTPUT = Path(r"E:\tm1a_test\skims\skims.omx")
    build_omx(SKIMS_DIR, OUTPUT)
