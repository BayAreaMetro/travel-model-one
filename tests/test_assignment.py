"""Tests for the Cube trip bridge — ActivitySim trip OMX -> Cube assignment demand TPP."""

from pathlib import Path

import numpy as np
import openmatrix as omx
import pytest

from cubeio import read_tpp
from tm1.assignment.params import load_aeq_params
from tm1.assignment.cube.asim_bridge import (
    _DIRECT_MAP,
    _TABLE_ORDER,
    _ZERO_CLASSES,
    build_trip_matrices,
)


_AUTO_TABLES = (
    "DRIVEALONEFREE", "DRIVEALONEPAY",
    "SHARED2FREE", "SHARED2PAY",
    "SHARED3FREE", "SHARED3PAY",
)


def _asim_tables() -> tuple[str, ...]:
    """Every ActivitySim table name build_trip_matrices reads."""
    ridehail = load_aeq_params().highway.ridehail.tables
    return (*_DIRECT_MAP, *_AUTO_TABLES, *ridehail.values())


def _make_trip_omx(path: Path, period: str, zones: int, fill: dict[str, float]) -> None:
    """Write a minimal ActivitySim-style trip OMX for one period."""
    with omx.open_file(str(path), "w") as f:
        for asim_name in _asim_tables():
            m = np.full((zones, zones), fill.get(asim_name, 0.0), dtype=np.float64)
            f[f"{asim_name}_{period}"] = m


def test_build_trip_matrices_maps_and_zero_fills(tmp_path: Path) -> None:
    """ActivitySim tables map to Cube class names; TNC/AV classes zero-fill."""
    zones = 5
    fill = {"DRIVEALONEFREE": 10.0, "SHARED2PAY": 3.0, "WALK_DRIVE_HVY": 1.0}
    asim_dir = tmp_path / "asim"
    asim_dir.mkdir()
    _make_trip_omx(asim_dir / "trips_am.omx", "AM", zones, fill)

    out = build_trip_matrices(asim_dir, tmp_path / "main", periods=("AM",))
    assert [p.name for p in out] == ["tripsAM.tpp"]

    t = read_tpp(out[0])
    assert t["zones"] == zones
    # All 29 canonical tables present, in order.
    assert t["tables"] == list(_TABLE_ORDER)

    d = t["data"]
    # Mapped ActivitySim values land under the Cube class names.
    assert np.allclose(d["da"], 10.0)
    # Shared-ride tables are vehicle trips in the OMX but person trips in the
    # tpp (HwyAssign divides by occupancy again), so they scale up by occupancy.
    occ2 = load_aeq_params().highway.occupancy["sr2"]
    assert np.allclose(d["sr2toll"], 3.0 * occ2)
    assert np.allclose(d["wlk_hvy_drv"], 1.0)  # WALK_DRIVE_HVY -> wlk_hvy_drv
    # Unmapped real classes are zero; the 6 TNC/AV classes are zero-filled.
    assert np.allclose(d["sr3"], 0.0)
    for cls in _ZERO_CLASSES:
        assert np.allclose(d[cls], 0.0)


def test_build_trip_matrices_missing_omx_raises(tmp_path: Path) -> None:
    """A missing trip OMX raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        build_trip_matrices(tmp_path, tmp_path / "main", periods=("AM",))
