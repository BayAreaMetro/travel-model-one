"""Set up a TM1 ActivitySim scenario: build skims, copy inputs, verify data.

Reads ``scenarios/<name>/scenario_config.yaml`` and ensures the data directory
is fully populated — converts TPP skims to OMX, copies CSV inputs, strips
legacy Ctrl-Z bytes.  Idempotent: skips files that already exist unless
``--force`` is passed.

Usage::

    python scripts/setup_scenario.py scenarios/base_2023
    python scripts/setup_scenario.py scenarios/base_2023 --force
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

from cubeio import find_latest_iter
from cubeio.omx import tpp_to_omx
from tm1.config import load_config, resolve_templates

log = logging.getLogger(__name__)


# data_sources key → filename in the ActivitySim data directory
CSV_FILE_MAP = {
    "land_use": "land_use.csv",
    "households": "households.csv",
    "persons": "persons.csv",
    # Skims get combined from separate TPP files into a single skim.omx, so no direct copy.
}


# ---------------------------------------------------------------------------
# TM1 skim conversion: Cube TPP table names → ActivitySim OMX keys
# See docs/skim_conversion_mapping.md for the full reference.
# ---------------------------------------------------------------------------

# Highway (Cube name → ActivitySim key base; period appended as __EA etc.)
# Pattern: {COMPONENT}{MODE} → {ASIM_MODE}_{COMPONENT}  (free)
#          TOLL{COMPONENT}{MODE} → {ASIM_MODE}TOLL_{COMPONENT}  (toll)
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
MODES = ("loc", "lrf", "exp", "hvy", "com")
ACCESS_EGRESS = (
    ("wlk", "wlk"),
    ("drv", "wlk"),
    ("wlk", "drv")
)

# Transit skim components (Cube column → ActivitySim suffix)
_TRANSIT_COMPONENTS = {
    "ivt": "TOTIVT",
    "iwait": "IWAIT",
    "xwait": "XWAIT",
    "waux": "WAUX",
    "fare": "FAR",
    "boards": "BOARDS",
}
_TRANSIT_DRIVE_ONLY = {
    "dtime": "DTIM",
    "ddist": "DDIST"
}
_KEYIVT_SOURCE = {
    "com": "ivtCOM",
    "hvy": "ivtHVY",
    "exp": "ivtEXP",
    "lrf": "ivtLRF",
}

# Non-motorized (no period suffix)
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
        # Highway
        fm[skims_dir / f"HWYSKM{period}.tpp"] = {
            c: f"{a}__{period}" for c, a in HWY_TABLE_MAP.items()
        }
        # Transit
        for access, egress in ACCESS_EGRESS:
            for mode in MODES:
                stem = f"trnskm{period.lower()}_{access}_{mode}_{egress}"
                tpp = find_latest_iter(skims_dir, stem)
                if tpp:
                    fm[tpp] = _transit_omx_keys(access, mode, egress, period)

    # Non-motorized (no period suffix)
    fm[skims_dir / "nonmotskm.tpp"] = {t: t for t in NONMOT_TABLES}
    return fm


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def _strip_ctrl_z(path: Path):
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with open(path, "r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def setup(scenario_dir: Path, force: bool = False):
    """Assemble the data directory for *scenario_dir*.  Idempotent."""
    cfg = load_config(scenario_dir)
    asim = cfg["activitysim"]
    data_dir = Path(asim["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    sources = resolve_templates(cfg["data_sources"])

    # -- Build skims if missing or incomplete -----------------------------------
    skims_path = Path(sources["skims"])
    tpp_dir = Path(sources["skim_tpp_dir"])
    need_build = force or not skims_path.exists()

    if not need_build:
        # Check that existing OMX has all expected keys
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
        file_map = build_file_map(tpp_dir)
        tpp_to_omx(file_map, skims_path)

    # -- Copy CSVs -------------------------------------------------------------
    for key, dest_name in CSV_FILE_MAP.items():
        src = Path(sources[key])
        dest = data_dir / dest_name
        if not force and dest.exists():
            log.info("Already exists: %s", dest.name)
            continue
        if not src.exists():
            sys.exit(f"Source not found: {src}")
        log.info("Copying %s -> %s", src, dest)
        shutil.copy2(src, dest)
        _strip_ctrl_z(dest)

    # -- Summary ---------------------------------------------------------------
    log.info("--- Data directory: %s ---", data_dir)
    for p in sorted(data_dir.iterdir()):
        size_mb = p.stat().st_size / 1_048_576
        log.info("  %-20s %8.1f MB", p.name, size_mb)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario_dir", type=Path,
        help="Path to the scenario directory (e.g. scenarios/base_2023)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Rebuild skims and re-copy files even if they already exist",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    setup(args.scenario_dir, force=args.force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    setup(_REPO_ROOT / "scenarios" / "base_2023")

