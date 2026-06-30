"""Tests for tm1.assignment — ActivitySim trip OMX -> Cube assignment demand TPP."""

from pathlib import Path

import numpy as np
import openmatrix as omx
import pytest

from cubeio import read_tpp
from tm1.assignment import _ASIM_TO_CUBE, _TABLE_ORDER, _ZERO_CLASSES, build_trip_matrices


def _make_trip_omx(path: Path, period: str, zones: int, fill: dict[str, float]) -> None:
    """Write a minimal ActivitySim-style trip OMX for one period."""
    with omx.open_file(str(path), "w") as f:
        for asim_name in _ASIM_TO_CUBE:
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
    assert np.allclose(d["sr2toll"], 3.0)
    assert np.allclose(d["wlk_hvy_drv"], 1.0)  # WALK_DRIVE_HVY -> wlk_hvy_drv
    # Unmapped real classes are zero; the 6 TNC/AV classes are zero-filled.
    assert np.allclose(d["sr3"], 0.0)
    for cls in _ZERO_CLASSES:
        assert np.allclose(d[cls], 0.0)


def test_build_trip_matrices_missing_omx_raises(tmp_path: Path) -> None:
    """A missing trip OMX raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        build_trip_matrices(tmp_path, tmp_path / "main", periods=("AM",))
