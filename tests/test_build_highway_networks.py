"""Tests for build_highway_networks' native csv -> dBASE III conversion.

The Cube jobs themselves are *moved* code (same binary, same scripts) and are
covered by the run-and-produced checks plus the end-to-end parity run; only the
rewritten glue -- the DBF writer replacing csvToDbf.py -- needs unit coverage.
"""

import struct
from pathlib import Path

import pytest

from tm1.steps.build.highway_networks import _infer_fields, _write_dbf

HEADER_SIZE = 32
FIELD_SIZE = 32


def _read_dbf(path: Path) -> tuple[list[tuple[str, str, int, int]], list[list[str]]]:
    """Minimal dBASE III parser: ((name, type, length, decimals), records)."""
    raw = path.read_bytes()
    n_records, header_size, record_size = struct.unpack_from("<IHH", raw, 4)
    fields = []
    for off in range(HEADER_SIZE, header_size - 1, FIELD_SIZE):
        name, ftype, _, length, decimals = struct.unpack_from("<11scI2B", raw, off)
        fields.append(
            (name.rstrip(b"\0").decode(), ftype.decode(), length, decimals)
        )
    records = []
    for i in range(n_records):
        rec = raw[header_size + i * record_size : header_size + (i + 1) * record_size]
        assert rec[0:1] == b" "  # not deleted
        vals, pos = [], 1
        for _, _, length, _ in fields:
            vals.append(rec[pos : pos + length].decode())
            pos += length
        records.append(vals)
    return fields, records


def test_type_ladder_matches_legacy() -> None:
    """Ladder is int -> float -> string, with legacy widths and name truncation."""
    header = ["fac_index", "toll_rate", "facility_name_long", "mixed"]
    rows = [["2001", "3.5", "Carquinez Bridge", "7"], ["31", "0", "GG", "x2"]]
    fields = _infer_fields(header, rows)
    assert fields == [
        ("FAC_INDEX", "N", 10, 0),
        ("TOLL_RATE", "N", 10, 5),  # "3.5" fails int() -> float
        ("FACILITY_N", "C", 18, 0),  # truncated name; longest value + 2
        ("MIXED", "C", 4, 0),  # "x2" fails float() -> string
    ]


def test_roundtrip_values(tmp_path: Path) -> None:
    """Written records parse back to the csv's values."""
    src = tmp_path / "tolls.csv"
    src.write_text(
        "facility_name,fac_index,use,tollam_da\n"
        "Carquinez Bridge GP,2001,1,3.5\n"
        "SFOBB,2005,1,7\n"
    )
    n_rows, fac_index = 2, 2001
    out = tmp_path / "tolls.dbf"
    assert _write_dbf(src, out) == n_rows

    fields, records = _read_dbf(out)
    assert [f[0] for f in fields] == ["FACILITY_N", "FAC_INDEX", "USE", "TOLLAM_DA"]
    assert records[0][0].strip() == "Carquinez Bridge GP"
    assert int(records[0][1]) == fac_index
    assert float(records[0][3]) == pytest.approx(3.5)
    assert float(records[1][3]) == pytest.approx(7.0)


def test_value_too_wide_errors(tmp_path: Path) -> None:
    """A numeric that cannot fit its fixed width fails loudly, not truncated."""
    src = tmp_path / "bad.csv"
    src.write_text("v\n123456789012345\n")  # 15 digits > N(10)
    with pytest.raises(ValueError, match="does not fit"):
        _write_dbf(src, tmp_path / "bad.dbf")


def test_duplicate_truncated_names_error(tmp_path: Path) -> None:
    """Two columns that collide at 10 characters are an error, not silent loss."""
    src = tmp_path / "dup.csv"
    src.write_text("facility_name_a,facility_name_b\n1,2\n")
    with pytest.raises(ValueError, match="collides"):
        _write_dbf(src, tmp_path / "dup.dbf")
