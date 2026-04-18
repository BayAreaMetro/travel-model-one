"""Convert Cube TPP skim matrices to a single ActivitySim-compatible skims.omx.

Reads highway, transit, and non-motorized TPP files from a TM1 model run and
writes a single ``skims.omx`` with skim keys matching the ActivitySim UEC
naming convention.  See ``docs/skim_conversion_mapping.md`` for the full
mapping reference.

Matrices are streamed one TPP file at a time to keep memory usage bounded
(peak ≈ one TPP file's worth of float32 arrays, not all 793 at once).

Usage::

    python scripts/build_omx_skims.py \\\\MODEL3-C\\...\\skims -o skims.omx
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import openmatrix as omx

from tm1.tpp import read_tpp

# ── Highway table mapping (Cube → ActivitySim) ──────────────────────────

HWY_TABLE_MAP = {
    "TIMEDA":      "SOV_TIME",      "DISTDA":      "SOV_DIST",      "BTOLLDA":      "SOV_BTOLL",
    "TOLLTIMEDA":  "SOVTOLL_TIME",  "TOLLDISTDA":  "SOVTOLL_DIST",
    "TOLLBTOLLDA": "SOVTOLL_BTOLL", "TOLLVTOLLDA": "SOVTOLL_VTOLL",
    "TIMES2":      "HOV2_TIME",     "DISTS2":      "HOV2_DIST",     "BTOLLS2":      "HOV2_BTOLL",
    "TOLLTIMES2":  "HOV2TOLL_TIME", "TOLLDISTS2":  "HOV2TOLL_DIST",
    "TOLLBTOLLS2": "HOV2TOLL_BTOLL","TOLLVTOLLS2": "HOV2TOLL_VTOLL",
    "TIMES3":      "HOV3_TIME",     "DISTS3":      "HOV3_DIST",     "BTOLLS3":      "HOV3_BTOLL",
    "TOLLTIMES3":  "HOV3TOLL_TIME", "TOLLDISTS3":  "HOV3TOLL_DIST",
    "TOLLBTOLLS3": "HOV3TOLL_BTOLL","TOLLVTOLLS3": "HOV3TOLL_VTOLL",
}

# ── Transit table mapping ────────────────────────────────────────────────

# Common components emitted for every transit path
_TRANSIT_COMMON = {
    "ivt": "TOTIVT", "iwait": "IWAIT", "xwait": "XWAIT",
    "waux": "WAUX", "fare": "FAR", "boards": "BOARDS",
}

# Additional components for drive-access/egress paths only
_TRANSIT_DRIVE = {"dtime": "DTIM", "ddist": "DDIST"}

# Mode → Cube IVT column for KEYIVT.  LOC excluded (uses TOTIVT directly).
_KEYIVT_SOURCE = {
    "com": "ivtCOM", "hvy": "ivtHVY", "exp": "ivtEXP", "lrf": "ivtLRF",
}

PERIODS = ("EA", "AM", "MD", "PM", "EV")
MODES = ("loc", "lrf", "exp", "hvy", "com")
ACCESS_EGRESS = (("wlk", "wlk"), ("drv", "wlk"), ("wlk", "drv"))


def _find_transit_tpp(
    skims_dir: Path, period: str, access: str, mode: str, egress: str,
) -> Path | None:
    """Find the best transit TPP, preferring highest ``.avg.iter{N}``."""
    stem = f"trnskm{period}_{access}_{mode}_{egress}"

    # Averaged iterations (highest wins — most converged)
    candidates = sorted(
        skims_dir.glob(f"{stem}.avg.iter*.tpp"),
        key=lambda p: int(re.search(r"iter(\d+)", p.name).group(1)),
        reverse=True,
    )
    if candidates:
        return candidates[0]

    # Plain (un-averaged) fallback
    plain = skims_dir / f"{stem}.tpp"
    if plain.exists():
        return plain

    return None


def _transit_table_mapping(
    access: str, mode: str, egress: str, period: str,
) -> dict[str, str]:
    """Return ``{cube_table: omx_key}`` for one transit TPP file."""
    prefix = f"{access.upper()}_{mode.upper()}_{egress.upper()}"
    per = f"__{period.upper()}"

    mapping = {}

    for cube_col, suffix in _TRANSIT_COMMON.items():
        mapping[cube_col] = f"{prefix}_{suffix}{per}"

    if access == "drv" or egress == "drv":
        for cube_col, suffix in _TRANSIT_DRIVE.items():
            mapping[cube_col] = f"{prefix}_{suffix}{per}"

    if mode in _KEYIVT_SOURCE:
        mapping[_KEYIVT_SOURCE[mode]] = f"{prefix}_KEYIVT{per}"

    if mode == "lrf":
        mapping["ivtFerry"] = f"{prefix}_FERRYIVT{per}"

    return mapping


def build_omx(skims_dir: Path, output: Path) -> None:
    """Read TPP skims from *skims_dir* and write *output* as OMX."""
    skims_dir = Path(skims_dir)
    output = Path(output)

    zones: int | None = None
    count = 0
    seen_keys: set[str] = set()

    with omx.open_file(str(output), "w") as f:

        def _write(omx_key: str, data: np.ndarray) -> None:
            nonlocal zones, count
            n = data.shape[0]
            if zones is None:
                zones = n
                f.create_mapping("zone", np.arange(1, zones + 1))
            elif n != zones:
                raise ValueError(
                    f"Zone count mismatch: expected {zones}, got {n} "
                    f"while writing '{omx_key}'"
                )
            if omx_key in seen_keys:
                raise ValueError(f"Duplicate OMX key: {omx_key}")
            seen_keys.add(omx_key)
            f[omx_key] = data.astype(np.float32)
            count += 1

        # ── Highway ──────────────────────────────────────────────────
        print("Highway skims:")
        for period in PERIODS:
            tpp_path = skims_dir / f"HWYSKM{period}.tpp"
            if not tpp_path.exists():
                print(f"  WARNING: {tpp_path.name} not found, skipping",
                      file=sys.stderr)
                continue
            result = read_tpp(tpp_path)
            for cube_name, asim_name in HWY_TABLE_MAP.items():
                _write(f"{asim_name}__{period}", result["data"][cube_name])
            print(f"  {tpp_path.name}  ({len(HWY_TABLE_MAP)} tables)")

        # ── Transit ──────────────────────────────────────────────────
        print("Transit skims:")
        for period in PERIODS:
            per_lower = period.lower()
            for access, egress in ACCESS_EGRESS:
                for mode in MODES:
                    tpp_path = _find_transit_tpp(
                        skims_dir, per_lower, access, mode, egress,
                    )
                    if tpp_path is None:
                        print(
                            f"  WARNING: trnskm{per_lower}_{access}_{mode}"
                            f"_{egress}.tpp not found, skipping",
                            file=sys.stderr,
                        )
                        continue
                    result = read_tpp(tpp_path)
                    mapping = _transit_table_mapping(access, mode, egress, period)
                    wrote = 0
                    for cube_col, omx_key in mapping.items():
                        if cube_col not in result["data"]:
                            print(
                                f"  WARNING: table '{cube_col}' missing from "
                                f"{tpp_path.name}, skipping {omx_key}",
                                file=sys.stderr,
                            )
                            continue
                        _write(omx_key, result["data"][cube_col])
                        wrote += 1
                    print(f"  {tpp_path.name}  ({wrote} tables)")

        # ── Non-motorized ────────────────────────────────────────────
        print("Non-motorized skims:")
        nonmot = skims_dir / "nonmotskm.tpp"
        if nonmot.exists():
            result = read_tpp(nonmot)
            for table in ("DISTWALK", "DISTBIKE", "DIST"):
                _write(table, result["data"][table])
            print(f"  {nonmot.name}  (3 tables)")
        else:
            print("  WARNING: nonmotskm.tpp not found, skipping",
                  file=sys.stderr)

    print(f"\nWrote {count} matrices ({zones} zones) to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert TM1 Cube TPP skims to ActivitySim OMX format.",
    )
    parser.add_argument(
        "skims_dir",
        type=Path,
        help="Directory containing TPP skim files",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("skims.omx"),
        help="Output OMX file path (default: skims.omx)",
    )
    args = parser.parse_args()

    if not args.skims_dir.is_dir():
        parser.error(f"Not a directory: {args.skims_dir}")

    build_omx(args.skims_dir, args.output)


if __name__ == "__main__":
    main()
"""Build a single skims.omx from TM1 Cube TPP skim files for ActivitySim.

Reads highway, transit, and non-motorized TPP skims from a TM1 model run
directory, renames tables to ActivitySim conventions, and writes everything
into a single OMX file with double-underscore time period suffixes
(e.g. SOV_TIME__AM) as expected by ActivitySim's skim_dict_factory.

Usage:
    python scripts/build_omx_skims.py <skims_dir> <output_omx>

Example:
    python scripts/build_omx_skims.py \\\\MODEL3-C\\...\\skims .working/skims.omx

See also: docs/skim_conversion_mapping.md for the full mapping reference.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import openmatrix as omx

# ---------------------------------------------------------------------------
# Table-name mapping: Cube TPP table name → ActivitySim skim key
#
# See docs/skim_conversion_mapping.md for the authoritative reference.
# ---------------------------------------------------------------------------

# Highway skims: HWYSKM{PERIOD}.tpp  (PERIOD = EA, AM, MD, PM, EV)
# 21 personal-vehicle tables per file.
HWYSKIM_TABLE_MAP: dict[str, str] = {
    # Drive alone — free facility
    "TIMEDA":       "SOV_TIME",
    "DISTDA":       "SOV_DIST",
    "BTOLLDA":      "SOV_BTOLL",
    # Drive alone — toll facility
    "TOLLTIMEDA":   "SOVTOLL_TIME",
    "TOLLDISTDA":   "SOVTOLL_DIST",
    "TOLLBTOLLDA":  "SOVTOLL_BTOLL",
    "TOLLVTOLLDA":  "SOVTOLL_VTOLL",
    # Shared ride 2 — free facility
    "TIMES2":       "HOV2_TIME",
    "DISTS2":       "HOV2_DIST",
    "BTOLLS2":      "HOV2_BTOLL",
    # Shared ride 2 — toll facility
    "TOLLTIMES2":   "HOV2TOLL_TIME",
    "TOLLDISTS2":   "HOV2TOLL_DIST",
    "TOLLBTOLLS2":  "HOV2TOLL_BTOLL",
    "TOLLVTOLLS2":  "HOV2TOLL_VTOLL",
    # Shared ride 3+ — free facility
    "TIMES3":       "HOV3_TIME",
    "DISTS3":       "HOV3_DIST",
    "BTOLLS3":      "HOV3_BTOLL",
    # Shared ride 3+ — toll facility
    "TOLLTIMES3":   "HOV3TOLL_TIME",
    "TOLLDISTS3":   "HOV3TOLL_DIST",
    "TOLLBTOLLS3":  "HOV3TOLL_BTOLL",
    "TOLLVTOLLS3":  "HOV3TOLL_VTOLL",
}

# Transit skims: trnskm{period}_{access}_{mode}_{egress}[.avg.iter{N}].tpp
# 27 tables per file.  Only those referenced by ActivitySim configs are mapped.
TRNSKM_TABLE_MAP: dict[str, str] = {
    "ivt":      "TOTIVT",
    "iwait":    "IWAIT",
    "xwait":    "XWAIT",
    "waux":     "WAUX",
    "dtime":    "DTIM",
    "ddist":    "DDIST",
    "fare":     "FAR",
    "boards":   "BOARDS",
    # Mode-specific IVT tables → KEYIVT (one per mode, see _KEYIVT_SOURCE)
    "ivtLOC":   "KEYIVT",
    "ivtLRF":   "KEYIVT",
    "ivtEXP":   "KEYIVT",
    "ivtHVY":   "KEYIVT",
    "ivtCOM":   "KEYIVT",
    # Ferry IVT — only used for LRF paths
    "ivtFerry": "FERRYIVT",
}
# NOTE: wacc, wegr, wait, ivtMUNILoc, ivtMUNIMet, distLOC..distRegFar, firstMode
# are present in the TPP files but NOT referenced by ActivitySim configs.

# Transit path parameters
TRANSIT_ACCESS_EGRESS_COMBOS = [
    ("wlk", "wlk"),  # walk / walk
    ("drv", "wlk"),  # drive / walk
    ("wlk", "drv"),  # walk / drive
]
TRANSIT_MODES = ["com", "hvy", "exp", "lrf", "loc"]  # "trn" excluded (generic accessibility only)
TRANSIT_LABEL = {
    "wlk": "WLK", "drv": "DRV",
    "com": "COM", "hvy": "HVY", "exp": "EXP", "lrf": "LRF", "loc": "LOC",
}

# Which mode-specific IVT table → KEYIVT for each transit mode
_KEYIVT_SOURCE = {
    "loc": "ivtLOC",
    "lrf": "ivtLRF",
    "exp": "ivtEXP",
    "hvy": "ivtHVY",
    "com": "ivtCOM",
}

# Non-motorized skims: nonmotskm.tpp (no time period, no suffix)
NONMOT_TABLE_MAP: dict[str, str] = {
    "DISTWALK": "DISTWALK",
    "DISTBIKE": "DISTBIKE",
    "DIST":     "DIST",
}

TIME_PERIODS = ["EA", "AM", "MD", "PM", "EV"]


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class SkimConverter:
    """Reads TM1 Cube TPP skims and writes a single ActivitySim skims.omx."""

    def __init__(self, skims_dir: Path, output_path: Path):
        self.skims_dir = Path(skims_dir)
        self.output_path = Path(output_path)
        self.nzones = None
        self._count = 0       # running total of tables written

    # -- file finders -------------------------------------------------------

    def _find(self, name: str) -> Path | None:
        """Case-insensitive file lookup in skims_dir."""
        p = self.skims_dir / name
        if p.exists():
            return p
        for f in self.skims_dir.iterdir():
            if f.name.lower() == name.lower():
                return f
        return None

    def _find_transit(self, period: str, access: str, mode: str, egress: str) -> Path | None:
        """Find transit TPP, preferring MSA-averaged (.avg.iter{N}) files."""
        base = f"trnskm{period}_{access}_{mode}_{egress}"
        avg = sorted(self.skims_dir.glob(f"{base}.avg.iter*.tpp"), reverse=True)
        if avg:
            return avg[0]
        return self._find(f"{base}.tpp")

    def _read(self, path: Path) -> dict[str, np.ndarray]:
        """Read a TPP and set self.nzones on first call."""
        from tm1.tpp import read_tpp
        result = read_tpp(path)
        if self.nzones is None:
            self.nzones = result["zones"]
        return result["data"]

    def _write(self, out: omx.File, omx_key: str, data: np.ndarray):
        """Write one matrix to the OMX file (skip if already written)."""
        if omx_key not in out.list_matrices():
            out.create_matrix(omx_key, obj=data)
            self._count += 1

    # -- highway ------------------------------------------------------------

    def _convert_highway(self, out: omx.File):
        """HWYSKM{PERIOD}.tpp  →  SOV_TIME__AM, HOV2_DIST__PM, etc."""
        for period in TIME_PERIODS:
            path = self._find(f"HWYSKM{period}.tpp")
            if path is None:
                print(f"  WARNING: HWYSKM{period}.tpp not found, skipping")
                continue

            print(f"  {path.name}")
            tables = self._read(path)

            for cube_name, asim_key in HWYSKIM_TABLE_MAP.items():
                if cube_name in tables:
                    self._write(out, f"{asim_key}__{period}", tables[cube_name])

    # -- transit ------------------------------------------------------------

    def _convert_transit(self, out: omx.File):
        """trnskm{per}_{acc}_{mode}_{egr}.tpp  →  WLK_COM_WLK_TOTIVT__AM, etc."""
        missing = 0
        for period in TIME_PERIODS:
            per = period.lower()
            for acc, egr in TRANSIT_ACCESS_EGRESS_COMBOS:
                for mode in TRANSIT_MODES:
                    path = self._find_transit(per, acc, mode, egr)
                    if path is None:
                        missing += 1
                        continue

                    print(f"  {path.name}")
                    tables = self._read(path)
                    prefix = f"{TRANSIT_LABEL[acc]}_{TRANSIT_LABEL[mode]}_{TRANSIT_LABEL[egr]}"

                    for cube_tbl, component in TRNSKM_TABLE_MAP.items():
                        if cube_tbl not in tables:
                            continue

                        # KEYIVT: use only the mode-matching source table;
                        # LOC has no KEYIVT (configs use TOTIVT directly)
                        if component == "KEYIVT":
                            if mode == "loc" or cube_tbl != _KEYIVT_SOURCE.get(mode):
                                continue

                        # FERRYIVT only meaningful for LRF paths
                        if component == "FERRYIVT" and mode != "lrf":
                            continue

                        # Drive time/dist only for drive-access or drive-egress
                        if component in ("DTIM", "DDIST") and acc != "drv" and egr != "drv":
                            continue

                        self._write(out, f"{prefix}_{component}__{period}", tables[cube_tbl])

        if missing:
            print(f"  ({missing} transit TPP files not found)")

    # -- non-motorized ------------------------------------------------------

    def _convert_nonmot(self, out: omx.File):
        """nonmotskm.tpp  →  DISTWALK, DISTBIKE, DIST  (no period suffix)."""
        path = self._find("nonmotskm.tpp")
        if path is None:
            print("  WARNING: nonmotskm.tpp not found, skipping")
            return

        print(f"  {path.name}")
        tables = self._read(path)

        for cube_name, asim_key in NONMOT_TABLE_MAP.items():
            if cube_name in tables:
                self._write(out, asim_key, tables[cube_name])

    # -- entry point --------------------------------------------------------

    def run(self):
        """Read all TPP skims and write skims.omx."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Source: {self.skims_dir}")
        print(f"Output: {self.output_path}\n")

        # Probe zone count from first available file
        for period in TIME_PERIODS:
            p = self._find(f"HWYSKM{period}.tpp")
            if p is not None:
                self._read(p)
                break
        if self.nzones is None:
            p = self._find("nonmotskm.tpp")
            if p is not None:
                self._read(p)
        if self.nzones is None:
            print("ERROR: no skim files found", file=sys.stderr)
            sys.exit(1)

        print(f"Zones: {self.nzones}\n")

        with omx.open_file(str(self.output_path), "w") as out:
            out.create_mapping("zone", list(range(1, self.nzones + 1)))

            print("Highway skims...")
            self._convert_highway(out)

            print("\nTransit skims...")
            self._convert_transit(out)

            print("\nNon-motorized skims...")
            self._convert_nonmot(out)

            print(f"\n{'='*60}")
            print(f"Done.  {self._count} skim tables → {self.output_path.name}")
            print(f"{'='*60}")


# ---------------------------------------------------------------------------
# CLI / convenience
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build a single skims.omx for ActivitySim from TM1 Cube TPP files.",
    )
    parser.add_argument("skims_dir", type=Path,
                        help="Directory with TPP skim files (from a TM1 model run)")
    parser.add_argument("output_omx", type=Path,
                        help="Output OMX file path (e.g. .working/skims.omx)")
    args = parser.parse_args()

    if not args.skims_dir.is_dir():
        print(f"Error: {args.skims_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    SkimConverter(args.skims_dir, args.output_omx).run()


if __name__ == "__main__":
    # Convenience defaults — just run the file with no args
    REFERENCE_RUN = Path(r"\\MODEL3-C\Model3C-Share\Projects\2023_TM161_IPA_35_testrun")
    SKIMS_DIR = REFERENCE_RUN / "skims"
    OUTPUT_OMX = Path(__file__).resolve().parent.parent / ".working" / "skims.omx"

    SkimConverter(SKIMS_DIR, OUTPUT_OMX).run()
