"""Cherry-pick sampled rows from full CSV dumps to create golden CSVs.

This creates the CSV half of golden test data by filtering the full
Cube CSV dump to only the sampled rows. The TPP half must be created
by running extract_golden_tpps.job on MODEL3-C with runtpp.

Usage:
    python tests/generate/cherry_pick_csv.py <csv_dump_dir> <golden_dir>
"""
import hashlib
import random
import sys
from pathlib import Path

import polars as pl

FIXED_ROWS = [1, 2, 3, 100, 500, 1000, 1473, 1474, 1475]
N_RANDOM = 10
ZONES = 1475

EXTRA_ROWS: dict[str, list[int]] = {
    "HWYSKMMD": [749],
    "trnskmam_drv_com_wlk": [811, 1101],
}

FILES = [
    "HWYSKMEA",
    "HWYSKMAM",
    "HWYSKMMD",
    "HWYSKMPM",
    "trnskmam_drv_com_wlk",
    "trnskmam_wlk_com_wlk",
    "trnskmam_drv_hvy_wlk",
    "trnskmpm_wlk_loc_drv",
    "nonmotskm",
]


def seed_for_file(stem: str) -> int:
    return int(hashlib.md5(stem.encode()).hexdigest()[:8], 16)


def sample_rows(stem: str) -> list[int]:
    rng = random.Random(seed_for_file(stem))
    extras = set(EXTRA_ROWS.get(stem, []))
    base = set(FIXED_ROWS) | extras
    candidates = [r for r in range(1, ZONES + 1) if r not in base]
    randoms = rng.sample(candidates, min(N_RANDOM, len(candidates)))
    return sorted(base | set(randoms))


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <csv_dump_dir> <golden_dir>")
        sys.exit(1)

    csv_dump = Path(sys.argv[1])
    golden = Path(sys.argv[2])
    golden.mkdir(parents=True, exist_ok=True)

    for stem in FILES:
        src = csv_dump / f"{stem}.csv"
        if not src.exists():
            print(f"  SKIP  {stem} (no CSV)")
            continue

        rows = sample_rows(stem)
        df = pl.read_csv(src, infer_schema_length=0)
        i_col = df.columns[0]

        # Strip whitespace padding from Cube output and cast to numeric
        df = df.select([
            pl.col(c).str.strip_chars() for c in df.columns
        ])

        # Filter to sampled rows
        i_vals = df[i_col].cast(pl.Int64)
        mask = i_vals.is_in(rows)
        filtered = df.filter(mask)

        out = golden / f"{stem}.csv"
        filtered.write_csv(out)
        print(f"  {stem:40s} {len(filtered):>8,} rows  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
