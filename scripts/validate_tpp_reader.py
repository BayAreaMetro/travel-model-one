"""Exhaustive validation: read every TPP in a skims directory, compare to Cube CSV dump.

For each TPP file with a matching CSV in csv_dump/, reads every cell via
read_tpp() and compares against Cube's own CSV output. Reports mismatches.

Usage:
    python scripts/validate_tpp_reader.py <skims_dir>

Example:
    python scripts/validate_tpp_reader.py \\\\MODEL3-C\\...\\skims
"""
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

from tm1.tpp import read_tpp


def validate_one(tpp_path: Path, csv_path: Path) -> tuple[int, int, list[str]]:
    """Compare one TPP against its CSV dump.

    Returns (cells_checked, mismatches, error_samples).
    """
    result = read_tpp(tpp_path)
    zones = result["zones"]
    tables = result["tables"]

    # Read Cube CSV — format: I, J, table1, table2, ...
    # Cube pads values with spaces, so strip before casting.
    df = pl.read_csv(csv_path, infer_schema_length=0)
    df = df.select([
        pl.col(c).str.strip_chars().cast(pl.Float64) for c in df.columns
    ])

    col_names = df.columns  # first two are I, J
    i_arr = df[col_names[0]].to_numpy().astype(int)
    j_arr = df[col_names[1]].to_numpy().astype(int)
    csv_tables = col_names[2:]

    cells = 0
    bad = 0
    errors = []

    for tbl_name in csv_tables:
        # CSV column names may have whitespace from Cube
        tbl_clean = tbl_name.strip()
        if tbl_clean not in result["data"]:
            errors.append(f"  table '{tbl_clean}' in CSV but not in TPP")
            continue

        mat = result["data"][tbl_clean]
        expected = df[tbl_name].to_numpy()
        actual = mat[i_arr - 1, j_arr - 1]

        # Tolerance: absolute 0.005 or relative 1e-4 (whichever is larger)
        threshold = np.maximum(0.005, np.abs(expected) * 1e-4)
        mismatch = np.abs(actual - expected) > threshold
        n_bad = int(mismatch.sum())
        cells += len(expected)
        bad += n_bad

        if n_bad > 0:
            idxs = np.nonzero(mismatch)[0][:5]
            for idx in idxs:
                errors.append(
                    f"  {tbl_clean}[{i_arr[idx]},{j_arr[idx]}]: "
                    f"tpp={actual[idx]:.6f} csv={expected[idx]:.6f}"
                )

    return cells, bad, errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <skims_dir>")
        sys.exit(1)

    skims_dir = Path(sys.argv[1])
    csv_dir = skims_dir / "csv_dump"

    if not csv_dir.is_dir():
        print(f"Error: {csv_dir} not found")
        sys.exit(1)

    # Find all TPP/CSV pairs
    pairs = []
    for csv_path in sorted(csv_dir.glob("*.csv")):
        stem = csv_path.stem
        tpp_path = skims_dir / f"{stem}.tpp"
        if tpp_path.exists():
            pairs.append((tpp_path, csv_path))

    print(f"Found {len(pairs)} TPP/CSV pairs in {skims_dir}\n")

    total_cells = 0
    total_bad = 0
    failures = []
    t0 = time.perf_counter()

    for tpp_path, csv_path in pairs:
        stem = tpp_path.stem
        t1 = time.perf_counter()
        try:
            cells, bad, errors = validate_one(tpp_path, csv_path)
        except Exception as e:
            print(f"  CRASH  {stem}: {e}")
            failures.append(stem)
            continue
        elapsed = time.perf_counter() - t1
        total_cells += cells
        total_bad += bad

        status = "OK" if bad == 0 else f"FAIL ({bad} mismatches)"
        print(f"  {status:>20s}  {stem:40s}  {cells:>10,} cells  {elapsed:.1f}s")
        if errors:
            for e in errors[:5]:
                print(f"    {e}")
            failures.append(stem)

    elapsed_total = time.perf_counter() - t0
    print(f"\n{'='*70}")
    print(f"Checked {total_cells:,} cells across {len(pairs)} files in {elapsed_total:.0f}s")
    print(f"Mismatches: {total_bad:,}")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    else:
        print("ALL FILES MATCH.")
    print(f"{'='*70}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
