"""Tests for the slice D build steps: transit line staging and HSR interpolation.

The reference run only exercises the trivial branch of each -- its complex
dwell modes are empty and its model year precedes the HSR opening -- so the
interesting behaviour is covered here with synthetic inputs.
"""

from pathlib import Path

import numpy as np
import pytest

from cubeio import read_tpp, write_tpp
from tm1.steps.build import hsr_trips, transit_lines

ZONES = 4
PERIODS = ("EA", "AM", "MD", "PM", "EV")


# --------------------------------------------------------------------------
# build_transit_lines
# --------------------------------------------------------------------------


def _cfg_lines(src: Path, out: Path, **extra: object) -> dict:
    return {"steps": {"build_transit_lines": {"from": str(src), "to": str(out), **extra}}}


def test_writes_one_identical_file_per_period(tmp_path: Path) -> None:
    """All five period files are copies of the master line file."""
    src = tmp_path / "transitLines.lin"
    src.write_text('LINE NAME="30_7AC",\n    FREQ[2]=32.0,\n N= 2412,\n')
    out = tmp_path / "trn"

    assert transit_lines.run(tmp_path, _cfg_lines(src, out)) is None
    written = sorted(out.glob("transitOriginal*.lin"))
    assert len(written) == len(PERIODS)
    for path in written:
        assert path.read_bytes() == src.read_bytes()


def test_complex_dwell_modes_refuse_to_run(tmp_path: Path) -> None:
    """Enabling complex dwell must fail loudly, not silently copy.

    With dwell modes set, the legacy applies mode-dependent delay and the five
    files stop being copies; a silent copy would change transit running times
    with no error.
    """
    src = tmp_path / "transitLines.lin"
    src.write_text("LINE NAME=x\n")
    out = tmp_path / "trn"

    with pytest.raises(NotImplementedError, match="dwell_modes"):
        transit_lines.run(tmp_path, _cfg_lines(src, out, dwell_modes=[21, 24]))
    with pytest.raises(NotImplementedError, match="access_modes"):
        transit_lines.run(tmp_path, _cfg_lines(src, out, access_modes=[110]))
    assert not out.exists() or not list(out.glob("*.lin"))


def test_transit_lines_skip_and_force(tmp_path: Path) -> None:
    """Existing outputs are left alone unless force is passed."""
    src = tmp_path / "transitLines.lin"
    src.write_text("LINE NAME=x\n")
    out = tmp_path / "trn"
    transit_lines.run(tmp_path, _cfg_lines(src, out))

    src.write_text("LINE NAME=changed\n")
    assert transit_lines.run(tmp_path, _cfg_lines(src, out)) == "skipped"
    assert "changed" not in (out / "transitOriginalAM.lin").read_text()

    transit_lines.run(tmp_path, _cfg_lines(src, out), force=True)
    assert "changed" in (out / "transitOriginalAM.lin").read_text()


def test_transit_lines_missing_source_errors(tmp_path: Path) -> None:
    """A missing master line file is a hard stop."""
    with pytest.raises(FileNotFoundError, match="input missing"):
        transit_lines.run(
            tmp_path, _cfg_lines(tmp_path / "absent.lin", tmp_path / "trn")
        )


# --------------------------------------------------------------------------
# build_hsr_trips
# --------------------------------------------------------------------------


def _write_hsr_inputs(src: Path, base: float, horizon: float) -> None:
    """Per-period 2040/2050 tables, every cell of every table a constant."""
    src.mkdir(parents=True, exist_ok=True)
    for period in PERIODS:
        for year, value in ((2040, base), (2050, horizon)):
            write_tpp(
                src / f"tripsHsr{period}_{year}.tpp",
                {n: np.full((ZONES, ZONES), value) for n in hsr_trips._TABLES},  # noqa: SLF001
            )


def _trn_param(tmp_path: Path, disable: int) -> Path:
    p = tmp_path / "trnParam.block"
    p.write_text(f"; block\nMeans_Based_Fare_Factor = 0.50\n"
                 f"HSR_Interregional_Disable  = {disable}\n")
    return p


def _cfg_hsr(src: Path, out: Path, trn: Path, year: int) -> dict:
    return {"steps": {"build_hsr_trips": {
        "from": str(src), "to": str(out), "trn_param": str(trn), "model_year": year,
    }}}


def test_hsr_interpolates_between_forecast_years(tmp_path: Path) -> None:
    """2045 sits halfway between the 2040 and 2050 tables."""
    src, out = tmp_path / "in", tmp_path / "nonres"
    _write_hsr_inputs(src, 100.0, 200.0)
    hsr_trips.run(tmp_path, _cfg_hsr(src, out, _trn_param(tmp_path, 0), 2045))

    data = read_tpp(out / "tripsHsrAM.tpp")
    assert data["tables"] == list(hsr_trips._TABLES)  # noqa: SLF001
    for name in hsr_trips._TABLES:  # noqa: SLF001
        assert np.allclose(data["data"][name], 150.0)


def test_hsr_extrapolates_beyond_horizon(tmp_path: Path) -> None:
    """The legacy formula is a line, not a clamp: 2060 continues the slope."""
    src, out = tmp_path / "in", tmp_path / "nonres"
    _write_hsr_inputs(src, 100.0, 200.0)
    hsr_trips.run(tmp_path, _cfg_hsr(src, out, _trn_param(tmp_path, 0), 2060))
    assert np.allclose(read_tpp(out / "tripsHsrAM.tpp")["data"]["da_veh"], 300.0)


def test_hsr_zero_before_opening_year(tmp_path: Path) -> None:
    """No HSR trips before 2040 -- the 2023 base case."""
    src, out = tmp_path / "in", tmp_path / "nonres"
    _write_hsr_inputs(src, 100.0, 200.0)
    hsr_trips.run(tmp_path, _cfg_hsr(src, out, _trn_param(tmp_path, 0), 2023))

    for period in PERIODS:
        data = read_tpp(out / f"tripsHsr{period}.tpp")
        for name in hsr_trips._TABLES:  # noqa: SLF001
            assert not data["data"][name].any()


def test_hsr_disable_switch_zeroes_output(tmp_path: Path) -> None:
    """HSR_Interregional_Disable=1 wins even in a year past the opening."""
    src, out = tmp_path / "in", tmp_path / "nonres"
    _write_hsr_inputs(src, 100.0, 200.0)
    hsr_trips.run(tmp_path, _cfg_hsr(src, out, _trn_param(tmp_path, 1), 2050))
    assert not read_tpp(out / "tripsHsrAM.tpp")["data"]["da_veh"].any()


def test_hsr_disabled_reads_trn_param(tmp_path: Path) -> None:
    """The switch is read from trnParam.block, which configure_ctramp writes."""
    assert hsr_trips.hsr_disabled(_trn_param(tmp_path, 1)) is True
    assert hsr_trips.hsr_disabled(_trn_param(tmp_path, 0)) is False


def test_hsr_missing_switch_errors(tmp_path: Path) -> None:
    """A trnParam.block without the switch is an error, not a default."""
    p = tmp_path / "trnParam.block"
    p.write_text("; block\nMeans_Based_Fare_Factor = 0.50\n")
    with pytest.raises(ValueError, match="HSR_Interregional_Disable"):
        hsr_trips.hsr_disabled(p)


def test_hsr_missing_trn_param_errors(tmp_path: Path) -> None:
    """A missing trnParam.block names configure_ctramp as the producer."""
    with pytest.raises(FileNotFoundError, match="configure_ctramp"):
        hsr_trips.hsr_disabled(tmp_path / "absent.block")


def test_hsr_zone_mismatch_errors(tmp_path: Path) -> None:
    """Forecast tables that disagree on zone count must not be interpolated."""
    src, out = tmp_path / "in", tmp_path / "nonres"
    _write_hsr_inputs(src, 100.0, 200.0)
    write_tpp(
        src / "tripsHsrEA_2050.tpp",
        {n: np.full((ZONES + 1, ZONES + 1), 200.0) for n in hsr_trips._TABLES},  # noqa: SLF001
    )
    with pytest.raises(ValueError, match="zones"):
        hsr_trips.run(tmp_path, _cfg_hsr(src, out, _trn_param(tmp_path, 0), 2045))
