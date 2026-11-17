"""
compare_outputs.py
==================

Compare the 24 DBF files produced by the Python pipeline against a reference
set produced by the R pipeline.

Expected layout::

    mtc-air-passenger/
        output/            <- Python run  (24 DBFs: 12 non-transit + 12 transit)
        reference_output/  <- R run       (24 DBFs in the same naming scheme)

Usage
-----
::

    uv run python compare_outputs.py
    uv run python compare_outputs.py --tol 0.01
    uv run python compare_outputs.py --py output --r reference_output

For every pair of matching file names the script reports:

* row count, column count, any column-name mismatches
* maximum absolute and relative difference across all numeric columns
* pass / fail verdict given the tolerance (default 0.01, matching the
  2-decimal rounding applied when writing the DBFs)

Exit status is 0 if every file matches within tolerance, 1 otherwise.
"""

# %% imports ------------------------------------------------------------------
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from make_air_passenger_demand import read_dbf


# %% defaults -----------------------------------------------------------------
HERE = Path(__file__).resolve().parent

DEFAULT_PY  = HERE / "output"
DEFAULT_REF = HERE / "reference_output"

DEFAULT_TOL     = 0.01   # absolute trips  – matches 2-decimal DBF rounding
DEFAULT_REL_TOL = 1e-4   # 0.01 % relative – only meaningful where |value| > 1


# %% single-file comparison ---------------------------------------------------
def _load(path: Path) -> pd.DataFrame:
    df = read_dbf(path)
    df.columns = [c.upper() for c in df.columns]
    return df


def compare_file(py_path: Path, ref_path: Path,
                 tol: float = DEFAULT_TOL,
                 rel_tol: float = DEFAULT_REL_TOL) -> dict:
    """Compare one Python DBF against one reference DBF.

    Returns a summary dict with ``passes`` (bool), ``max_abs_diff``,
    ``max_rel_diff``, and a list of ``fail_reasons``.
    """
    py_df  = _load(py_path)
    ref_df = _load(ref_path)

    only_py  = sorted(set(py_df.columns)  - set(ref_df.columns))
    only_ref = sorted(set(ref_df.columns) - set(py_df.columns))

    summary: dict = {
        "file":          py_path.name,
        "py_rows":       len(py_df),
        "ref_rows":      len(ref_df),
        "py_cols":       len(py_df.columns),
        "ref_cols":      len(ref_df.columns),
        "only_in_py":    only_py,
        "only_in_ref":   only_ref,
        "max_abs_diff":  0.0,
        "max_rel_diff":  0.0,
        "passes":        True,
        "fail_reasons":  [],
    }

    if summary["py_rows"] != summary["ref_rows"]:
        summary["passes"] = False
        summary["fail_reasons"].append(
            f"row count: py={summary['py_rows']}  ref={summary['ref_rows']}")
        return summary

    if only_py or only_ref:
        summary["passes"] = False
        summary["fail_reasons"].append(
            f"column mismatch – only in py: {only_py}  only in ref: {only_ref}")

    # align on (ORIG, DEST) so row order doesn't matter
    common = [c for c in py_df.columns if c in ref_df.columns]
    py_df  = py_df[common].sort_values(["ORIG", "DEST"]).reset_index(drop=True)
    ref_df = ref_df[common].sort_values(["ORIG", "DEST"]).reset_index(drop=True)

    if not py_df["ORIG"].equals(ref_df["ORIG"]) or not py_df["DEST"].equals(ref_df["DEST"]):
        summary["passes"] = False
        summary["fail_reasons"].append("ORIG/DEST values differ after sort")
        return summary

    for col in common:
        if col in ("ORIG", "DEST"):
            continue
        py_v  = pd.to_numeric(py_df[col],  errors="coerce").fillna(0.0).to_numpy()
        ref_v = pd.to_numeric(ref_df[col], errors="coerce").fillna(0.0).to_numpy()

        diff    = np.abs(py_v - ref_v)
        max_abs = float(diff.max()) if diff.size else 0.0
        max_rel = float((diff / np.maximum(np.abs(ref_v), 1.0)).max()) if diff.size else 0.0

        summary["max_abs_diff"] = max(summary["max_abs_diff"], max_abs)
        summary["max_rel_diff"] = max(summary["max_rel_diff"], max_rel)

        if max_abs > tol and max_rel > rel_tol:
            summary["passes"] = False
            summary["fail_reasons"].append(
                f"{col}: max|Δ|={max_abs:.4f}  max_rel={max_rel:.2e}")

    return summary


# %% directory-level comparison -----------------------------------------------
def compare_dirs(py_dir: Path, ref_dir: Path,
                 tol: float, rel_tol: float,
                 verbose: bool = False) -> tuple[int, int]:
    """Compare every ``.dbf`` present in both *py_dir* and *ref_dir*.

    Returns ``(n_pass, n_fail)``.
    """
    if not py_dir.is_dir():
        print(f"Python output directory not found: {py_dir}")
        return 0, 0
    if not ref_dir.is_dir():
        print(f"Reference directory not found: {ref_dir}  (nothing to compare)")
        return 0, 0

    py_files  = {p.name: p for p in sorted(py_dir.glob("*.dbf"))}
    ref_files = {p.name: p for p in sorted(ref_dir.glob("*.dbf"))}
    shared    = sorted(py_files.keys() & ref_files.keys())
    only_py   = sorted(py_files.keys() - ref_files.keys())
    only_ref  = sorted(ref_files.keys() - py_files.keys())

    print(f"\nComparing  {py_dir}  vs  {ref_dir}")
    if only_py:
        print(f"  Only in Python output: {only_py}")
    if only_ref:
        print(f"  Only in reference:     {only_ref}")
    if not shared:
        print("  No files to compare.")
        return 0, 0

    print(f"  {'FILE':<26} {'rows':>5} {'cols':>5} {'max|Δ|':>9} {'max_rel':>9}  result")
    print(f"  {'-'*26} {'-'*5} {'-'*5} {'-'*9} {'-'*9}  ------")

    n_pass = n_fail = 0
    for name in shared:
        s = compare_file(py_files[name], ref_files[name], tol=tol, rel_tol=rel_tol)
        tag = "OK" if s["passes"] else "FAIL"
        print(f"  {name:<26} {s['py_rows']:>5} {s['py_cols']:>5} "
              f"{s['max_abs_diff']:>9.4f} {s['max_rel_diff']:>9.2e}  {tag}")
        if s["passes"]:
            n_pass += 1
        else:
            n_fail += 1
            for reason in s["fail_reasons"]:
                print(f"      ✗ {reason}")

    return n_pass, n_fail


# %% CLI ----------------------------------------------------------------------
def _cli() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--py",      type=Path, default=DEFAULT_PY,
                    help=f"Python output directory  (default: {DEFAULT_PY.name})")
    ap.add_argument("--r",       type=Path, default=DEFAULT_REF,
                    help=f"R reference directory    (default: {DEFAULT_REF.name})")
    ap.add_argument("--tol",     type=float, default=DEFAULT_TOL,
                    help="Max absolute difference per cell (default: 0.01)")
    ap.add_argument("--rel-tol", type=float, default=DEFAULT_REL_TOL,
                    help="Max relative difference (default: 1e-4)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Print per-column detail for failing files")
    args = ap.parse_args()

    n_pass, n_fail = compare_dirs(
        args.py, args.r,
        tol=args.tol, rel_tol=args.rel_tol, verbose=args.verbose,
    )
    print(f"\n{n_pass} passed, {n_fail} failed  "
          f"(abs tol={args.tol}, rel tol={args.rel_tol})")
    return 0 if n_fail == 0 else 1


# %% run ----------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(_cli())
