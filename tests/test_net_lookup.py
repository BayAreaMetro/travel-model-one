"""Portable tests for Cube Voyager SPD/CAP lookup-table decoding."""

# ruff: noqa: PLR2004

import struct
from collections.abc import Iterable
from pathlib import Path

import pytest

from cubeio import read_net

_LANES = 9
_CLASSES = 99
_LOOKUP_SIZE = _LANES * _CLASSES
_LOOKUP_PREFIX = bytes.fromhex("06 20 80 c0")


def _outer_record(payload: bytes) -> bytes:
    """Wrap one top-level section; its u32 length includes the prefix."""
    return struct.pack("<I", len(payload) + 4) + payload


def _dictionary(marker: str, entries: Iterable[str]) -> bytes:
    entries = list(entries)
    return (
        f"{marker} {len(entries)}".encode("ascii")
        + b"\x00"
        + b"\x00".join(entry.encode("ascii") for entry in entries)
        + b"\x00"
    )


def _sparse_high_stream(high_bytes: bytes) -> bytes:
    """Exercise two-byte RLE plus both sparse literal instruction forms."""
    assert len(high_bytes) == _LOOKUP_SIZE
    assert len(set(high_bytes[:300])) == 1

    # count=300: c=0x2c, m=0x81, then the repeated fill byte.
    run = bytes((0x2C, 0x81, high_bytes[0]))
    # m=0 encodes a short c-byte literal block.
    short_literal = bytes((200, 0)) + high_bytes[300:500]
    # count=391 (0x0187) encodes a long literal block when 0 < m < 0x80.
    long_literal = bytes((0x87, 0x01)) + high_bytes[500:]
    return run + short_literal + long_literal


def _lookup_body(
    section_name: str,
    stored_values: list[int],
    *,
    count: int = _LOOKUP_SIZE,
    prefix: bytes = _LOOKUP_PREFIX,
    high_stream: bytes | None = None,
) -> bytes:
    """Encode the bytes following an SPD/CAP marker."""
    if section_name == "SPD":
        seed = 1
    elif section_name == "CAP":
        seed = 20
    else:
        msg = f"unsupported synthetic lookup section {section_name!r}"
        raise ValueError(msg)

    low_bytes = bytes(value & 0xFF for value in stored_values)
    high_bytes = bytes(value >> 8 for value in stored_values)
    if high_stream is None:
        high_stream = _sparse_high_stream(high_bytes)
    return bytes((seed,)) + prefix + struct.pack("<H", count) + low_bytes + high_stream


def _stored_values(*, initial_high: int, maximum: int) -> list[int]:
    """Return lane-major values with an RLE-friendly prefix and distinct rows."""
    values = [
        (initial_high << 8) | ((index * 17 + index // _CLASSES) & 0xFF) for index in range(300)
    ]
    values.extend(
        (((index * 13) % initial_high) << 8) | ((index * 19 + 7) & 0xFF)
        for index in range(300, _LOOKUP_SIZE)
    )
    values[-1] = maximum
    return values


_SPEED_STORED = _stored_values(initial_high=0x7F, maximum=32_767)
_CAPACITY_STORED = _stored_values(initial_high=0x20, maximum=9_999)


def _rows(values: list[int], *, divisor: int) -> list[list[int | float]]:
    """Reshape a flat lane-major table into nine rows of 99 classes."""
    converted = [value if divisor == 1 else value / divisor for value in values]
    return [
        converted[row_start : row_start + _CLASSES]
        for row_start in range(0, _LOOKUP_SIZE, _CLASSES)
    ]


def _build_net(
    *,
    speed_body: bytes | None = None,
    capacity_body: bytes | None = None,
) -> bytes:
    """Build a complete one-node, one-link network containing lookup tables."""
    if speed_body is None:
        speed_body = _lookup_body("SPD", _SPEED_STORED)
    if capacity_body is None:
        capacity_body = _lookup_body("CAP", _CAPACITY_STORED)

    payloads = [
        b"NET PGM=HWYNET (vTEST) DATE=2026-08-05\r\n\x00",
        b"ID=lookup-test\x00",
        b"PAR Zones=1 Nodes=1 Links=1 NodeRecs=1\x00",
        b"SPD\x00" + speed_body,
        b"CAP\x00" + capacity_body,
        _dictionary("NVR", ["N"]),
        _dictionary("LVR", ["A", "B"]),
        b"NOD\x00\x01\x01",
        b"LNK\x00\x02\x01\x01",
        b"END\x00",
    ]
    return b"".join(_outer_record(payload) for payload in payloads)


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_read_net_decodes_speed_and_capacity_tables(tmp_path: Path) -> None:
    """Decode sparse streams and reshape all values in lane-major order."""
    result = read_net(_write(tmp_path / "lookups.net", _build_net()))

    assert list(result) == [
        "banner",
        "identifier",
        "parameters",
        "node_variables",
        "link_variables",
        "sections",
        "speed_table",
        "capacity_table",
        "nodes",
        "links",
    ]
    assert result["speed_table"] == _rows(_SPEED_STORED, divisor=10)
    assert result["capacity_table"] == _rows(_CAPACITY_STORED, divisor=1)
    assert [len(row) for row in result["speed_table"]] == [_CLASSES] * _LANES
    assert [len(row) for row in result["capacity_table"]] == [_CLASSES] * _LANES
    assert all(isinstance(value, float) for row in result["speed_table"] for value in row)
    assert all(isinstance(value, int) for row in result["capacity_table"] for value in row)
    assert result["speed_table"][8][98] == 3276.7
    assert result["capacity_table"][8][98] == 9999
    assert result["speed_table"][0] != result["speed_table"][1]
    assert result["capacity_table"][0] != result["capacity_table"][1]


@pytest.mark.parametrize(
    ("section_name", "body", "error"),
    [
        (
            "SPD",
            _lookup_body("SPD", _SPEED_STORED, prefix=bytes.fromhex("07 20 80 c0")),
            r"SPD.*(?:encoding )?header",
        ),
        (
            "CAP",
            _lookup_body("CAP", _CAPACITY_STORED, count=_LOOKUP_SIZE - 1),
            rf"CAP.*(?:declares )?{_LOOKUP_SIZE - 1}.*(?:expected )?{_LOOKUP_SIZE}",
        ),
        (
            "SPD",
            bytes((1,)) + _LOOKUP_PREFIX + struct.pack("<H", _LOOKUP_SIZE) + b"\x00" * 890,
            r"Truncated SPD.*low-byte",
        ),
        (
            "CAP",
            bytes((20,))
            + _LOOKUP_PREFIX
            + struct.pack("<H", _LOOKUP_SIZE)
            + bytes(value & 0xFF for value in _CAPACITY_STORED)
            + b"\x03\x00\x01",
            r"Truncated CAP.*high-byte.*literal",
        ),
        (
            "SPD",
            _lookup_body("SPD", _SPEED_STORED) + b"\x00",
            r"SPD.*1 trailing byte",
        ),
    ],
    ids=["bad-header", "wrong-count", "truncated-low", "truncated-literal", "trailing"],
)
def test_read_net_rejects_malformed_lookup_tables(
    tmp_path: Path,
    section_name: str,
    body: bytes,
    error: str,
) -> None:
    """Reject malformed lookup framing rather than silently dropping values."""
    overrides = {"speed_body": None, "capacity_body": None}
    overrides["speed_body" if section_name == "SPD" else "capacity_body"] = body
    path = _write(tmp_path / f"bad-{section_name.lower()}.net", _build_net(**overrides))

    with pytest.raises(ValueError, match=error):
        read_net(path)
