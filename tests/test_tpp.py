"""Tests for tm1.tpp — pure-Python Cube Voyager TPP reader.

Two test tiers:

1. **Golden tests** (``tests/data/golden/*.tpp`` + ``*.csv``):
   Small TPPs (sampled rows only) and Cube's own CSV dump of those TPPs.
   Both are committed to git.  Cell-level validation: read TPP with our
   reader, compare every non-zero cell against Cube's CSV output.

2. **Row-stat tests** (``.working/ground_truth/*_rowstats.csv``):
   Every row of every table checked for nonzero-count and sum against
   full-size TPPs in ``.working/test_skims/``.
   These were the original reverse-engineering validation data.

Both tiers skip gracefully when test data is absent.

Ground truth generated from the reference model run
``2023_TM161_IPA_35_testrun`` on MODEL3-C.
"""
import csv
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from tm1.tpp import read_tpp

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent
_SKIMS = _REPO / ".working" / "test_skims"
_GT = _REPO / ".working" / "ground_truth"
_GOLDEN = _REPO / "tests" / "data" / "golden"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_sparse_csv_gt(csv_path: Path) -> pl.DataFrame:
    """Load sparse I,J,table... CSV as a Polars DataFrame.

    Cube's PRINT format pads values with whitespace, so we strip and
    cast all columns to Float64.
    """
    df = pl.read_csv(csv_path)
    return df.with_columns(
        pl.col(c).str.strip_chars().cast(pl.Float64) for c in df.columns
    )


def _load_cell_gt(csv_path: Path) -> dict[tuple[str, int, int], float]:
    """Load legacy row,col,table... CSV into {(table, row, col): value}."""
    gt = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        col_names = [c.strip() for c in reader.fieldnames]
        skip = {"row", "col"}
        for rec in reader:
            r = int(rec["row"].strip())
            c = int(rec["col"].strip())
            for cn in col_names:
                if cn not in skip:
                    gt[(cn, r, c)] = float(rec[cn].strip())
    return gt


def _load_stat_gt(csv_path: Path) -> dict[tuple[str, int], tuple[int, float]]:
    """Load row-stat ground truth: {(table, row): (nonzero_count, sum)}."""
    gt = {}
    with open(csv_path) as f:
        for rec in csv.DictReader(f):
            r = int(rec["row"].strip())
            tbl = rec["table"].strip()
            gt[(tbl, r)] = (
                int(rec["nonzero_count"].strip()),
                float(rec["sum"].strip()),
            )
    return gt


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
                    f"{tbl}[{i_arr[idx]+1},{j_arr[idx]+1}]: "
                    f"got {actual[idx]:.6f}, expected {expected[idx]:.6f}"
                )
            if len(errors) >= 20:
                break
    assert not errors, f"{len(errors)} cell mismatches:\n" + "\n".join(errors[:20])


def _check_cells(result: dict, gt: dict[tuple[str, int, int], float],
                  tol: float = 0.005):
    """Assert cell values match legacy ground truth (row,col format)."""
    errors = []
    for (tbl, r, c), expected in gt.items():
        if tbl not in result["data"]:
            continue
        actual = float(result["data"][tbl][r - 1, c - 1])
        if abs(actual - expected) >= tol:
            errors.append(
                f"{tbl}[{r},{c}]: got {actual:.6f}, expected {expected:.6f}"
            )
    assert not errors, f"{len(errors)} cell mismatches:\n" + "\n".join(errors[:20])


def _check_stats(result: dict, gt: dict[tuple[str, int], tuple[int, float]]):
    """Assert all ground-truth row stats match."""
    errors = []
    for (tbl, r), (exp_nz, exp_sum) in gt.items():
        if tbl not in result["data"]:
            continue
        row = result["data"][tbl][r - 1]
        actual_nz = int(np.count_nonzero(row))
        actual_sum = float(np.sum(row))
        if actual_nz != exp_nz:
            errors.append(f"{tbl}[{r}]: nz={actual_nz}, expected {exp_nz}")
        if abs(actual_sum - exp_sum) >= max(0.5, abs(exp_sum) * 0.001):
            errors.append(f"{tbl}[{r}]: sum={actual_sum:.2f}, expected {exp_sum:.2f}")
    assert not errors, f"{len(errors)} stat mismatches:\n" + "\n".join(errors[:20])


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


# ---------------------------------------------------------------------------
# Heavy tests — full row-stat validation (local data only)
# ---------------------------------------------------------------------------

_heavy_skip = pytest.mark.skipif(
    not _SKIMS.exists() or not _GT.exists(),
    reason="Test skims or ground truth not available",
)


@_heavy_skip
class TestHwySkmEA:

    @pytest.fixture(scope="class")
    def result(self):
        p = _SKIMS / "HWYSKMEA.tpp"
        if not p.exists():
            pytest.skip(f"{p} not found")
        return read_tpp(p)

    def test_header(self, result):
        assert result["zones"] == 1475
        assert len(result["tables"]) == 21
        assert "TIMEDA" in result["tables"]
        assert "TOLLVTOLLS3" in result["tables"]

    def test_shapes(self, result):
        for name, arr in result["data"].items():
            assert arr.shape == (1475, 1475), f"{name} shape mismatch"

    def test_cell_values(self, result):
        gt = _load_cell_gt(_GT / "dump_tpp_rows.csv")
        _check_cells(result, gt)

    def test_row_stats(self, result):
        gt = _load_stat_gt(_GT / "dump_tpp_rowstats.csv")
        _check_stats(result, gt)


@_heavy_skip
class TestHwySkmAM:

    @pytest.fixture(scope="class")
    def result(self):
        p = _SKIMS / "HWYSKMAM.tpp"
        if not p.exists():
            pytest.skip(f"{p} not found")
        return read_tpp(p)

    def test_header(self, result):
        assert result["zones"] == 1475
        assert len(result["tables"]) == 21

    def test_cell_values(self, result):
        gt = _load_cell_gt(_GT / "dump_hwyskmam_rows.csv")
        _check_cells(result, gt)

    def test_row_stats(self, result):
        gt = _load_stat_gt(_GT / "dump_hwyskmam_rowstats.csv")
        _check_stats(result, gt)


@_heavy_skip
class TestTransit:

    @pytest.fixture(scope="class")
    def result(self):
        p = _SKIMS / "trnskmam_wlk_com_wlk.tpp"
        if not p.exists():
            pytest.skip(f"{p} not found")
        return read_tpp(p)

    def test_header(self, result):
        assert result["zones"] == 1475
        assert "ivt" in result["tables"]
        assert "fare" in result["tables"]

    def test_cell_values(self, result):
        gt = _load_cell_gt(_GT / "dump_transit_rows.csv")
        _check_cells(result, gt)

    def test_row_stats(self, result):
        gt = _load_stat_gt(_GT / "dump_transit_rowstats.csv")
        _check_stats(result, gt)


@_heavy_skip
class TestNonMotorized:

    @pytest.fixture(scope="class")
    def result(self):
        p = _SKIMS / "nonmotskm.tpp"
        if not p.exists():
            pytest.skip(f"{p} not found")
        return read_tpp(p)

    def test_header(self, result):
        assert result["zones"] == 1475
        assert sorted(result["tables"]) == ["DIST", "DISTBIKE", "DISTWALK"]

    def test_cell_values(self, result):
        gt = _load_cell_gt(_GT / "dump_nonmotskm_rows.csv")
        _check_cells(result, gt)

    def test_row_stats(self, result):
        gt = _load_stat_gt(_GT / "dump_nonmotskm_rowstats.csv")
        _check_stats(result, gt)
