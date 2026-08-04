"""Tests for the warmstart step's seeding and its configuration guards.

The assignment half needs Cube, so it is not exercised here; these cover the
seeding, the destination derivation, and every way the config can be wrong.
"""

from pathlib import Path

import numpy as np
import pytest

from cubeio import read_tpp, write_tpp
from tm1.steps import warmstart

PERIODS = ("EA", "AM", "MD", "PM", "EV")
ZONES = 6


def _seed_dir(tmp_path: Path, *, nonres: bool = True) -> Path:
    """A previous run's INPUT/warmstart: main/ trip tables plus nonres/."""
    src = tmp_path / "warmstart"
    (src / "main").mkdir(parents=True)
    for i, period in enumerate(PERIODS):
        write_tpp(
            src / "main" / f"trips{period}.tpp",
            {n: np.full((ZONES, ZONES), float(i + 1)) for n in warmstart.TABLES},
        )
    if nonres:
        (src / "nonres").mkdir()
        for name in ("TripsTrkAMx.tpp", "tripsIXAM.tpp"):
            write_tpp(src / "nonres" / name, {"trk": np.ones((ZONES, ZONES))})
    return src


def _cfg(tmp_path: Path, **step: object) -> dict:
    """A scenario shaped like the real one: assignment lives inside `iterate`."""
    return {
        "proj_dir": str(tmp_path / "proj"),
        "steps": {
            "warmstart": step,
            "iterate": {
                "count": 1,
                "steps": {
                    "simulate_ctramp": {},
                    "assignment": {
                        "demand": str(tmp_path / "proj" / "main" / "trips{PERIOD}.tpp")
                    },
                },
            },
        },
    }


def test_finds_assignment_demand_inside_iterate(tmp_path: Path) -> None:
    """The assignment step normally sits in the loop body, not at the top level."""
    expected = str(tmp_path / "proj" / "main" / "trips{PERIOD}.tpp")
    assert warmstart._demand_pattern(_cfg(tmp_path)) == expected  # noqa: SLF001


def test_finds_assignment_demand_at_top_level(tmp_path: Path) -> None:
    """A scenario without a loop still resolves."""
    cfg = {
        "proj_dir": str(tmp_path / "proj"),
        "steps": {"warmstart": {}, "assignment": {"demand": "x/trips{PERIOD}.tpp"}},
    }
    assert warmstart._demand_pattern(cfg) == "x/trips{PERIOD}.tpp"  # noqa: SLF001


def test_seed_lands_where_demand_points(tmp_path: Path) -> None:
    """Trip tables go to the assignment step's declared demand artifact."""
    src = _seed_dir(tmp_path)
    demand = warmstart._demand_pattern(_cfg(tmp_path, **{"from": str(src)}))  # noqa: SLF001

    warmstart.seed_from_previous_run(src, demand, tmp_path / "proj" / "nonres")

    for i, period in enumerate(PERIODS):
        out = tmp_path / "proj" / "main" / f"trips{period}.tpp"
        assert out.is_file()
        assert np.allclose(read_tpp(out)["data"]["da"], float(i + 1))


def test_seed_copies_nonres(tmp_path: Path) -> None:
    """Iteration 0 does not run the nonres models, so their tables come along."""
    src = _seed_dir(tmp_path)
    nonres = tmp_path / "proj" / "nonres"
    warmstart.seed_from_previous_run(
        src, str(tmp_path / "proj" / "main" / "trips{PERIOD}.tpp"), nonres
    )
    assert {p.name for p in nonres.glob("*.tpp")} == {"TripsTrkAMx.tpp", "tripsIXAM.tpp"}


def test_seed_missing_period_errors(tmp_path: Path) -> None:
    """A seed directory missing a period is a hard stop, not a partial run."""
    src = _seed_dir(tmp_path)
    (src / "main" / "tripsMD.tpp").unlink()
    with pytest.raises(FileNotFoundError, match="tripsMD"):
        warmstart.seed_from_previous_run(
            src, str(tmp_path / "proj" / "main" / "trips{PERIOD}.tpp"),
            tmp_path / "proj" / "nonres",
        )


def test_seed_without_main_dir_errors(tmp_path: Path) -> None:
    """Pointing `from` at the wrong level names what it expected to find."""
    bare = tmp_path / "not_a_warmstart"
    bare.mkdir()
    with pytest.raises(FileNotFoundError, match="no main/ directory"):
        warmstart.seed_from_previous_run(
            bare, str(tmp_path / "m" / "trips{PERIOD}.tpp"), tmp_path / "n"
        )


def test_cold_start_writes_zero_demand(tmp_path: Path) -> None:
    """Cold start writes the full 29-table schema, all zero."""
    demand = str(tmp_path / "proj" / "main" / "trips{PERIOD}.tpp")
    warmstart.seed_cold_start(demand, zones=ZONES)

    for period in PERIODS:
        data = read_tpp(tmp_path / "proj" / "main" / f"trips{period}.tpp")
        assert data["tables"] == list(warmstart.TABLES)
        assert data["zones"] == ZONES
        assert not any(data["data"][n].any() for n in warmstart.TABLES)


def test_table_schema_matches_legacy_warmstart() -> None:
    """29 tables in the order CreateWarmStart.job writes them."""
    expected = 29
    assert len(warmstart.TABLES) == expected
    assert warmstart.TABLES[:2] == ("da", "datoll")
    assert warmstart.TABLES[-3:] == ("da_av", "s2_av", "s3_av")


def test_missing_from_is_an_error(tmp_path: Path) -> None:
    """Leaving the seed unstated is an error, not a silent default."""
    with pytest.raises(ValueError, match="needs `from`"):
        warmstart.run(tmp_path, _cfg(tmp_path))


def test_missing_from_path_does_not_become_a_cold_start(tmp_path: Path) -> None:
    """A typo'd path must fail, never quietly fall through to zero demand."""
    cfg = _cfg(tmp_path, **{"from": str(tmp_path / "nope")})
    with pytest.raises(FileNotFoundError, match=warmstart.COLD_START):
        warmstart.run(tmp_path, cfg)
    assert not (tmp_path / "proj" / "main").exists()


@pytest.mark.parametrize("spelling", ["coldstart", "COLDSTART", "  ColdStart "])
def test_coldstart_sentinel_is_forgiving(tmp_path: Path, spelling: str) -> None:
    """The sentinel is matched case- and whitespace-insensitively."""
    cfg = _cfg(tmp_path, **{"from": spelling, "zones": ZONES})
    # Runs past seeding and fails only when it reaches the Cube assignment.
    with pytest.raises(Exception, match=r"(?i)cube|scripts|backend"):
        warmstart.run(tmp_path, cfg)
    data = read_tpp(tmp_path / "proj" / "main" / "tripsAM.tpp")
    assert not data["data"]["da"].any()


def test_requires_assignment_demand_key(tmp_path: Path) -> None:
    """Without the demand seam there is nowhere to put the seed."""
    cfg = {
        "proj_dir": str(tmp_path / "proj"),
        "steps": {
            "warmstart": {"from": warmstart.COLD_START},
            "iterate": {"steps": {"assignment": {}}},
        },
    }
    with pytest.raises(ValueError, match="demand"):
        warmstart.run(tmp_path, cfg)
