"""Tests for tm1.tpp — pure-Python Cube Voyager TPP reader.

**Golden tests** (``tests/data/golden/*.tpp`` + ``*.csv``):
Small TPPs (sampled rows only) and Cube's own CSV dump of those TPPs.
Both are committed to git.  Cell-level validation: read TPP with our
reader, compare every non-zero cell against Cube's CSV output.

Golden files include rows that exercise all three decoder bugs fixed
in 2025-01: big-RLE (mode & 0x80), 0xC8 dense short-lo continuation,
and type 0x40 hi-byte-only blocks.

For exhaustive validation of all 81 TPP files, see
``scripts/validate_tpp_reader.py`` (1.1 B cells, 0 mismatches).

Ground truth generated from the reference model run
``2023_TM161_IPA_35_testrun`` on MODEL3-C.
"""

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from cubeio.tpp import read_tpp

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
_GOLDEN = _REPO / "tests" / "data" / "golden"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sparse_csv_gt(csv_path: Path) -> pl.DataFrame:
    """Load sparse I,J,table... CSV as a Polars DataFrame.

    Reads all columns as strings first (to handle mixed int/float columns),
    strips whitespace, and casts to Float64.
    """
    df = pl.read_csv(csv_path, infer_schema_length=0)
    return df.with_columns(pl.col(c).str.strip_chars().cast(pl.Float64) for c in df.columns)


def _check_sparse_cells(result: dict, gt: pl.DataFrame, tol: float = 5e-4):
    """Assert cell values match sparse ground truth (I,J format).

    Vectorised per-table: extracts I/J arrays once, then slices our
    matrix and compares against the CSV column in bulk.
    """
    data = result["data"]
    i_arr = gt["I"].to_numpy().astype(np.int32) - 1  # 0-based
    j_arr = gt["J"].to_numpy().astype(np.int32) - 1
    table_cols = [c for c in gt.columns if c not in ("I", "J")]

    errors = []
    for tbl in table_cols:
        mat = data.get(tbl.strip())
        if mat is None:
            continue
        expected = gt[tbl].to_numpy()
        actual = mat[i_arr, j_arr]
        threshold = np.maximum(tol, np.abs(expected) * 1e-4)
        bad = np.abs(actual - expected) > threshold
        if bad.any():
            idxs = np.nonzero(bad)[0]
            for idx in idxs[:5]:
                errors.append(
                    f"{tbl}[{i_arr[idx] + 1},{j_arr[idx] + 1}]: "
                    f"got {actual[idx]:.6f}, expected {expected[idx]:.6f}"
                )
            if len(errors) >= 20:
                break
    assert not errors, f"{len(errors)} cell mismatches:\n" + "\n".join(errors[:20])


# ---------------------------------------------------------------------------
# Golden tests — cell-level, committed to git, fully portable
# ---------------------------------------------------------------------------
# Each golden TPP in tests/data/golden/ has a matching CSV dumped by Cube.
# We read the TPP with our reader and compare every non-zero cell.


def _discover_golden_cases() -> list[tuple[str, Path, Path]]:
    """Find (test_id, golden_csv, golden_tpp) triples."""
    if not _GOLDEN.exists():
        return []

    cases = []
    for csv_file in sorted(_GOLDEN.glob("*.csv")):
        tpp_file = csv_file.with_suffix(".tpp")
        if tpp_file.exists():
            cases.append((csv_file.stem, csv_file, tpp_file))
    return cases


_golden_cases = _discover_golden_cases()


@pytest.mark.parametrize(
    "test_id, golden_csv, tpp_path",
    _golden_cases,
    ids=[c[0] for c in _golden_cases],
)
class TestGolden:
    """Cell-level validation against Cube's own CSV dump of golden TPPs."""

    def test_cell_values(self, golden_csv, test_id, tpp_path):
        result = read_tpp(tpp_path)
        gt = _load_sparse_csv_gt(golden_csv)
        assert len(gt) > 0, f"Golden CSV {golden_csv} has no rows"
        _check_sparse_cells(result, gt)
