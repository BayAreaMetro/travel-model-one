"""Tests for the filter_popsyn step.

The reference run has *zero* unconnected zones, so an end-to-end comparison
against it only ever exercises the copy branch.  The filter branch is covered
here instead, with a synthetic skim whose disconnected zones are known.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cubeio import write_tpp
from tm1.steps import filter_popsyn

ZONES = 5
#: Zones 1..4 internal, zone 5 external (mirrors the real 1454/1455 split).
MAX_INTERNAL = 4
#: One household per zone, numbered so household HHID_BASE+z lives in zone z.
HHID_BASE = 100
PERSONS_PER_HH = 2


def _write_skim(path: Path, unconnected: tuple[int, ...] = ()) -> None:
    """A TOLLDISTDA skim where each zone in *unconnected* has an all-500000 row."""
    dist = np.full((ZONES, ZONES), 12.34)
    for zone in unconnected:
        dist[zone - 1, :] = filter_popsyn.NO_PATH
    write_tpp(path, {"TOLLDISTDA": dist})


def _write_popsyn(src_dir: Path, person_id_col: str = "HHID") -> None:
    """Versioned popsyn files: one household per zone, two persons each."""
    src_dir.mkdir(parents=True, exist_ok=True)
    hh = pd.DataFrame(
        {"HHID": [HHID_BASE + z for z in range(1, ZONES + 1)],
         "TAZ": range(1, ZONES + 1)}
    )
    hh.to_csv(src_dir / "hhFile.2023_v12.csv", index=False)
    persons = pd.DataFrame(
        {
            person_id_col: np.repeat(hh["HHID"].to_numpy(), PERSONS_PER_HH),
            "PERID": range(1, PERSONS_PER_HH * ZONES + 1),
        }
    )
    persons.to_csv(src_dir / "personFile.2023_v12.csv", index=False)


def _cfg(src_dir: Path, out_dir: Path, skim: Path) -> dict:
    return {
        "steps": {
            "filter_popsyn": {
                "from": str(src_dir),
                "to": str(out_dir),
                "skim": str(skim),
                "max_internal_zone": MAX_INTERNAL,
            }
        }
    }


def test_find_unconnected_zones_excludes_externals(tmp_path: Path) -> None:
    """Zone 5 is also unconnected but external, so only zone 3 is reported."""
    skim = tmp_path / "HWYSKMAM.tpp"
    _write_skim(skim, unconnected=(3, 5))
    assert filter_popsyn.find_unconnected_zones(skim, MAX_INTERNAL) == [3]


def test_find_unconnected_zones_all_connected(tmp_path: Path) -> None:
    """A fully connected skim yields no unconnected zones."""
    skim = tmp_path / "HWYSKMAM.tpp"
    _write_skim(skim)
    assert filter_popsyn.find_unconnected_zones(skim, MAX_INTERNAL) == []


def test_copy_branch_is_byte_exact(tmp_path: Path) -> None:
    """With nothing to filter, outputs are byte copies -- not a pandas round-trip."""
    src, out, skim = tmp_path / "INPUT", tmp_path / "popsyn", tmp_path / "skim.tpp"
    src.mkdir()
    # Formatting pandas would not preserve: CRLF line endings, a quoted field.
    raw = b'HHID,TAZ,NAME\r\n101,1,"a,b"\r\n102,2,plain\r\n'
    (src / "hhFile.2023_v12.csv").write_bytes(raw)
    (src / "personFile.2023_v12.csv").write_bytes(b"HHID,PERID\r\n101,1\r\n")
    _write_skim(skim)

    assert filter_popsyn.run(tmp_path, _cfg(src, out, skim)) is None
    assert (out / "hhFile.csv").read_bytes() == raw
    assert (out / "personFile.csv").read_bytes() == b"HHID,PERID\r\n101,1\r\n"


def test_filter_branch_drops_unconnected_households(tmp_path: Path) -> None:
    """Households in internal-unconnected zones vanish from both files."""
    src, out, skim = tmp_path / "INPUT", tmp_path / "popsyn", tmp_path / "skim.tpp"
    _write_popsyn(src)
    # Zone 3 internal-unconnected -> filtered; zone 5 unconnected but external -> kept.
    _write_skim(skim, unconnected=(3, 5))

    assert filter_popsyn.run(tmp_path, _cfg(src, out, skim)) is None

    hh = pd.read_csv(out / "hhFile.csv")
    assert hh["TAZ"].tolist() == [1, 2, 4, 5]
    persons = pd.read_csv(out / "personFile.csv")
    assert HHID_BASE + 3 not in persons["HHID"].to_numpy()
    assert len(persons) == PERSONS_PER_HH * (ZONES - 1)


def test_filter_branch_hh_id_spelling(tmp_path: Path) -> None:
    """Person files spelling the ID column hh_id are filtered the same way."""
    src, out, skim = tmp_path / "INPUT", tmp_path / "popsyn", tmp_path / "skim.tpp"
    _write_popsyn(src, person_id_col="hh_id")
    _write_skim(skim, unconnected=(3,))

    filter_popsyn.run(tmp_path, _cfg(src, out, skim))
    persons = pd.read_csv(out / "personFile.csv")
    assert HHID_BASE + 3 not in persons["hh_id"].to_numpy()
    assert len(persons) == PERSONS_PER_HH * (ZONES - 1)


def test_skips_when_outputs_exist(tmp_path: Path) -> None:
    """Existing outputs are left alone unless force is passed."""
    src, out, skim = tmp_path / "INPUT", tmp_path / "popsyn", tmp_path / "skim.tpp"
    _write_popsyn(src)
    _write_skim(skim)
    out.mkdir()
    (out / "hhFile.csv").write_text("stale")
    (out / "personFile.csv").write_text("stale")

    assert filter_popsyn.run(tmp_path, _cfg(src, out, skim)) == "skipped"
    assert (out / "hhFile.csv").read_text() == "stale"

    filter_popsyn.run(tmp_path, _cfg(src, out, skim), force=True)
    assert (out / "hhFile.csv").read_text() != "stale"


def test_ambiguous_source_glob_errors(tmp_path: Path) -> None:
    """Two hhFile.* candidates is a loud error, never a silent pick."""
    src, out, skim = tmp_path / "INPUT", tmp_path / "popsyn", tmp_path / "skim.tpp"
    _write_popsyn(src)
    (src / "hhFile.older.csv").write_text("HHID,TAZ\n")
    _write_skim(skim)

    with pytest.raises(FileNotFoundError, match="exactly one hhFile"):
        filter_popsyn.run(tmp_path, _cfg(src, out, skim))


def test_missing_config_keys_error(tmp_path: Path) -> None:
    """Every absent required config key is named in one error."""
    with pytest.raises(KeyError, match="skim, max_internal_zone"):
        filter_popsyn.run(
            tmp_path, {"steps": {"filter_popsyn": {"from": "x", "to": "y"}}}
        )
