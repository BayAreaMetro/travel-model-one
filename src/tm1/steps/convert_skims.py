"""Convert Cube TPP skims to a single ActivitySim OMX file.

Reads ``cfg["convert_skims"]`` for source TPP directory and output path.
Idempotent: skips if OMX already has all expected keys unless ``force=True``.

This step can be dropped once native assignment produces OMX skims directly.
"""

import logging
import sys
from pathlib import Path

from cubeio import find_latest_iter
from cubeio.omx import tpp_to_omx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TM1 skim conversion: Cube TPP table names → ActivitySim OMX keys
# See docs/skim_conversion_mapping.md for the full reference.
# ---------------------------------------------------------------------------

_HWY_MODES = {"DA": "SOV", "S2": "HOV2", "S3": "HOV3"}
_HWY_FREE = ("TIME", "DIST", "BTOLL")
_HWY_TOLL = ("TIME", "DIST", "BTOLL", "VTOLL")

HWY_TABLE_MAP = {}
for _csuf, _apre in _HWY_MODES.items():
    for _comp in _HWY_FREE:
        HWY_TABLE_MAP[f"{_comp}{_csuf}"] = f"{_apre}_{_comp}"
    for _comp in _HWY_TOLL:
        HWY_TABLE_MAP[f"TOLL{_comp}{_csuf}"] = f"{_apre}TOLL_{_comp}"

PERIODS = ("EA", "AM", "MD", "PM", "EV")
MODES = ("loc", "lrf", "exp", "hvy", "com", "trn")
ACCESS_EGRESS = (
    ("wlk", "wlk"),
    ("drv", "wlk"),
    ("wlk", "drv"),
)

_TRANSIT_COMPONENTS = {
    "ivt": "TOTIVT",
    "iwait": "IWAIT",
    "xwait": "XWAIT",
    "wacc": "WACC",
    "waux": "WAUX",
    "wegr": "WEGR",
    "fare": "FAR",
    "boards": "BOARDS",
}
_TRANSIT_DRIVE_ONLY = {
    "dtime": "DTIM",
    "ddist": "DDIST",
}
_KEYIVT_SOURCE = {
    "com": "ivtCOM",
    "hvy": "ivtHVY",
    "exp": "ivtEXP",
    "lrf": "ivtLRF",
}

NONMOT_TABLES = ("DISTWALK", "DISTBIKE", "DIST")


def _transit_omx_keys(access, mode, egress, period):
    """Return ``{cube_table: omx_key}`` for one transit TPP file."""
    prefix = f"{access.upper()}_{mode.upper()}_{egress.upper()}"
    suffix = f"__{period}"
    keys = {c: f"{prefix}_{k}{suffix}" for c, k in _TRANSIT_COMPONENTS.items()}
    if access == "drv" or egress == "drv":
        keys.update({c: f"{prefix}_{k}{suffix}" for c, k in _TRANSIT_DRIVE_ONLY.items()})
    if mode in _KEYIVT_SOURCE:
        keys[_KEYIVT_SOURCE[mode]] = f"{prefix}_KEYIVT{suffix}"
    if mode == "lrf":
        keys["ivtFerry"] = f"{prefix}_FERRYIVT{suffix}"
    return keys


def build_file_map(skims_dir):
    """Build ``{tpp_path: {cube_name: omx_key}}`` for all TM1 skims."""
    skims_dir = Path(skims_dir)
    fm: dict[Path, dict[str, str]] = {}

    for period in PERIODS:
        fm[skims_dir / f"HWYSKM{period}.tpp"] = {
            c: f"{a}__{period}" for c, a in HWY_TABLE_MAP.items()
        }
        for access, egress in ACCESS_EGRESS:
            for mode in MODES:
                stem = f"trnskm{period.lower()}_{access}_{mode}_{egress}"
                tpp = find_latest_iter(skims_dir, stem)
                if tpp:
                    fm[tpp] = _transit_omx_keys(access, mode, egress, period)

    fm[skims_dir / "nonmotskm.tpp"] = {t: t for t in NONMOT_TABLES}
    return fm


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Convert Cube TPP skims to OMX."""
    force = kwargs.get("force", False)

    skim_cfg = cfg.get("convert_skims", {})
    tpp_dir = Path(skim_cfg["skim_tpp_dir"])
    skims_path = Path(skim_cfg["output"])

    need_build = force or not skims_path.exists()

    if not need_build:
        import openmatrix as omx
        expected = {k for table_map in build_file_map(tpp_dir).values() for k in table_map.values()}
        try:
            with omx.open_file(str(skims_path), "r") as f:
                actual = set(f.list_matrices())
        except Exception:
            log.warning("Cannot read %s, rebuilding", skims_path)
            need_build = True
        else:
            missing = expected - actual
            if missing:
                log.warning("Skims incomplete — missing %d keys, rebuilding", len(missing))
                need_build = True
            else:
                log.info("Skims OK: %s (%d matrices)", skims_path, len(actual))

    if need_build:
        if not tpp_dir.is_dir():
            sys.exit(f"TPP skim directory not found: {tpp_dir}")
        log.info("Building skims: %s -> %s", tpp_dir, skims_path)
        skims_path.parent.mkdir(parents=True, exist_ok=True)
        file_map = build_file_map(tpp_dir)
        tpp_to_omx(file_map, skims_path)
