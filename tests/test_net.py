"""Portable, end-to-end tests for the native Cube Voyager NET reader.

The fixtures in this module are deliberately assembled from bytes instead of
depending on a Cube installation or on model-run files outside the repository.
"""

# ruff: noqa: PLR2004

import struct
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

from cubeio import iter_net_links, read_net, read_net_links, read_net_nodes


def _outer_record(payload: bytes) -> bytes:
    """Wrap one NET section; its u32 length includes the prefix itself."""
    return struct.pack("<I", len(payload) + 4) + payload


def _container(payloads: Iterable[tuple[str, bytes]]) -> tuple[bytes, list[dict]]:
    """Assemble sections and return their dynamically calculated metadata."""
    data = bytearray()
    sections = []
    for name, payload in payloads:
        record = _outer_record(payload)
        sections.append({"name": name, "offset": len(data), "length": len(record)})
        data.extend(record)
    return bytes(data), sections


def _packed_integer(value: int) -> bytes:
    """Encode a non-negative integer in Cube NET's canonical compact form."""
    if not 0 <= value <= 0x7FFFF:
        msg = f"integer is outside the NET packed range: {value}"
        raise ValueError(msg)
    if value <= 0x3F:
        return bytes((value,))
    if value <= 0x7FF:
        return bytes((0x48 | (value >> 8), value & 0xFF))
    return bytes((0x50 | (value >> 16),)) + struct.pack("<H", value & 0xFFFF)


def _float64(value: float) -> bytes:
    return b"\x88" + struct.pack("<d", value)


def _float32(value: float) -> bytes:
    return b"\xa4" + struct.pack("<f", value)


def _fixed_decimal(stored: int, *, width: int, decimals: int) -> bytes:
    """Encode an unsigned fixed decimal using tags 0x90 through 0xa3."""
    if not 1 <= width <= 4 or not 1 <= decimals <= 4:
        msg = "fixed decimals support widths 1..4 and precisions 1..4"
        raise ValueError(msg)
    tag = 0x90 + (decimals - 1) * 4 + (width - 1)
    return bytes((tag,)) + stored.to_bytes(width, "little")


def _string(value: str) -> bytes:
    encoded = value.encode("ascii")
    if len(encoded) <= 0x3E:
        return bytes((0xC0 + len(encoded),)) + encoded
    if len(encoded) <= 0xFF:
        return b"\xff" + bytes((len(encoded),)) + encoded
    msg = "synthetic NET strings cannot exceed 255 bytes"
    raise ValueError(msg)


def _node_record(payload: bytes) -> bytes:
    """Wrap a NOD payload in its one- or two-byte record envelope."""
    length = len(payload)
    if length < 0x80:
        return bytes((length,)) + payload
    if length <= 0x7FFF:
        return bytes((0x80 | (length >> 8), length & 0xFF)) + payload
    msg = "synthetic node record is too large"
    raise ValueError(msg)


def _link_record(payload: bytes) -> bytes:
    """Wrap an LNK payload using the same envelope grammar as NOD."""
    return _node_record(payload)


_NODE_VARIABLE_NAMES = [
    "N",
    "X",
    "Y",
    "HIGH",
    "FLOAT32",
    "FIXED1",
    "FIXED4",
    "EMPTY",
    "SHORT",
    "LONG",
]

_NODE_VARIABLES = [
    {"name": name, "kind": "numeric", "width": None} for name in _NODE_VARIABLE_NAMES[:7]
] + [
    {"name": "EMPTY", "kind": "string", "width": 5},
    {"name": "SHORT", "kind": "string", "width": 10},
    {"name": "LONG", "kind": "string", "width": 200},
]

_LINK_VARIABLES = [
    {"name": "A", "kind": "numeric", "width": None},
    {"name": "B", "kind": "numeric", "width": None},
    {"name": "DISTANCE", "kind": "numeric", "width": None},
    {"name": "LABEL", "kind": "string", "width": 200},
]

# Literal record envelopes copied from Cube Voyager 6.5.1's
# avgload5period.net (nodes 1, 73, 20505, and 39030). These are deliberately
# not produced by the synthetic encoders above.
_CUBE_NODE_RECORDS = [
    bytes.fromhex("1601880000008012e0204188596e69a5fbe94f4100c0c0"),
    bytes.fromhex("174849880000000038ca20418800000000d6e84f4100c0c0"),
    bytes.fromhex(
        "2b501950882575023a56f8204188d7a370cd4dee4f4100d353465f3037303032375f436f6d706c65746564c0"
    ),
    bytes.fromhex("18507698886e861bc03e3023418803780ba0ec384f4100c0c0"),
]


def _synthetic_nodes() -> tuple[list[bytes], list[dict]]:
    """Build records covering every Phase-1 value representation."""
    numbers = [0x3F, 0x40, 0x7FF, 0x800]
    long_strings = ["x" * 130, "y" * 63, "z" * 70, "w" * 63]
    encoded_records = []
    expected_nodes = []

    for index, (number, long_string) in enumerate(zip(numbers, long_strings, strict=True)):
        x = 552_969.25 + index
        y = 4_183_031.29228 + index
        float32 = 1.5 + index
        fixed1 = 12.3
        fixed4 = 1_234.5678
        short = f"s{index}"

        payload = b"".join(
            (
                _packed_integer(number),
                _float64(x),
                _float64(y),
                _packed_integer(0x12345),  # non-zero bits in the 0x50 tag
                _float32(float32),
                _fixed_decimal(123, width=1, decimals=1),
                _fixed_decimal(12_345_678, width=4, decimals=4),
                _string(""),
                _string(short),
                _string(long_string),
            )
        )
        encoded_records.append(_node_record(payload))
        expected_nodes.append(
            {
                "N": number,
                "X": x,
                "Y": y,
                "HIGH": 0x12345,
                "FLOAT32": float32,
                "FIXED1": fixed1,
                "FIXED4": fixed4,
                "EMPTY": "",
                "SHORT": short,
                "LONG": long_string,
            }
        )

    # The first payload is intentionally long enough to select the two-byte
    # envelope, while the 63-byte-string payload selects the one-byte form.
    assert encoded_records[0][0] & 0x80
    assert encoded_records[1][0] < 0x80
    return encoded_records, expected_nodes


def _synthetic_links() -> tuple[list[bytes], list[dict]]:
    """Build links covering both envelopes, extended strings, and parallels."""
    long_label = "express connector " + "x" * 114
    encoded_records = [
        _link_record(
            b"".join(
                (
                    _packed_integer(63),
                    _packed_integer(64),
                    _float32(1.5),
                    _string("short"),
                )
            )
        ),
        _link_record(
            b"".join(
                (
                    _packed_integer(64),
                    _packed_integer(2047),
                    _fixed_decimal(123, width=1, decimals=1),
                    _string(long_label),
                )
            )
        ),
        _link_record(
            b"".join(
                (
                    _packed_integer(63),
                    _packed_integer(64),
                    _float64(2.25),
                    _string(""),
                )
            )
        ),
    ]
    expected_links = [
        {"A": 63, "B": 64, "DISTANCE": 1.5, "LABEL": "short"},
        {"A": 64, "B": 2047, "DISTANCE": 12.3, "LABEL": long_label},
        {"A": 63, "B": 64, "DISTANCE": 2.25, "LABEL": ""},
    ]

    assert encoded_records[0][0] < 0x80
    assert encoded_records[1][0] & 0x80
    assert b"\xff" in encoded_records[1]
    return encoded_records, expected_links


def _minimal_node_payload(
    node_number: int,
    *,
    empty: bytes | None = None,
    short: bytes | None = None,
) -> bytes:
    """Encode one ten-field node payload with overridable string fields."""
    return b"".join(
        (
            _packed_integer(node_number),
            _float64(1.0),
            _float64(2.0),
            _packed_integer(0x40),
            _float32(1.5),
            _fixed_decimal(123, width=1, decimals=1),
            _fixed_decimal(1234, width=2, decimals=4),
            _string("") if empty is None else empty,
            _string("ok") if short is None else short,
            _string("tail"),
        )
    )


def _dictionary(marker: str, entries: Iterable[str]) -> bytes:
    entries = list(entries)
    return (
        f"{marker} {len(entries)}".encode("ascii")
        + b"\x00"
        + b"\x00".join(entry.encode("ascii") for entry in entries)
        + b"\x00"
    )


def _lookup_section(marker: str) -> bytes:
    """Build a valid all-zero 9-by-99 SPD/CAP lookup section."""
    seed = 1 if marker == "SPD" else 20
    value_count = 9 * 99
    header = bytes((seed, 0x06, 0x20, 0x80, 0xC0)) + struct.pack("<H", value_count)
    high_bytes_rle = bytes((value_count & 0xFF, 0x80 | (value_count >> 8), 0))
    return marker.encode("ascii") + b"\x00" + header + bytes(value_count) + high_bytes_rle


def _build_valid_net(
    *,
    declared_node_recs: int = 4,
    nod_body: bytes | None = None,
    declared_links: int = 0,
    lnk_body: bytes = b"",
    include_lookup_tables: bool = True,
) -> tuple[bytes, list[dict], dict[str, int | str], list[dict]]:
    """Return a complete synthetic NET, expected sections, and expected nodes."""
    node_records, expected_nodes = _synthetic_nodes()
    if nod_body is None:
        nod_body = b"".join(node_records)

    parameters = {
        "Zones": 1,
        "Nodes": 2048,
        "Links": declared_links,
        "NodeRecs": declared_node_recs,
        "Delta": -7,
        "Scenario": "synthetic",
    }
    parameter_text = "PAR " + " ".join(f"{key}={value}" for key, value in parameters.items())
    lookup_payloads = [("SPD", _lookup_section("SPD")), ("CAP", _lookup_section("CAP"))]
    payloads = [
        ("NET", b"NET PGM=HWYNET (vTEST) DATE=2026-08-05\r\n\x00"),
        ("ID", b"ID=synthetic-net\x00"),
        ("PAR", parameter_text.encode("ascii") + b"\x00"),
        *(lookup_payloads if include_lookup_tables else []),
        (
            "NVR",
            _dictionary("NVR", [*_NODE_VARIABLE_NAMES[:7], "EMPTY=005", "SHORT=010", "LONG=200"]),
        ),
        ("LVR", _dictionary("LVR", ["A", "B", "DISTANCE", "LABEL=200"])),
        ("NOD", b"NOD\x00" + nod_body),
        ("LNK", b"LNK\x00" + lnk_body),
        ("END", b"END\x00"),
    ]
    data, sections = _container(payloads)
    return data, sections, parameters, expected_nodes


def _build_link_net(
    *,
    declared_links: int = 3,
    lnk_body: bytes | None = None,
) -> tuple[bytes, list[dict], dict[str, int | str], list[dict], list[dict]]:
    """Return a synthetic NET containing representative link records."""
    link_records, expected_links = _synthetic_links()
    if lnk_body is None:
        lnk_body = b"".join(link_records)
    data, sections, parameters, expected_nodes = _build_valid_net(
        declared_links=declared_links,
        lnk_body=lnk_body,
    )
    return data, sections, parameters, expected_nodes, expected_links


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_read_net_nodes_decodes_portable_synthetic_container(tmp_path: Path) -> None:
    """Decode metadata and nodes end-to-end without any external fixtures."""
    data, sections, parameters, expected_nodes = _build_valid_net()
    result = read_net_nodes(_write(tmp_path / "synthetic.net", data))

    assert list(result) == [
        "banner",
        "identifier",
        "parameters",
        "node_variables",
        "link_variables",
        "sections",
        "nodes",
    ]
    assert result["banner"] == "NET PGM=HWYNET (vTEST) DATE=2026-08-05"
    assert result["identifier"] == "synthetic-net"
    assert result["parameters"] == parameters
    assert result["node_variables"] == _NODE_VARIABLES
    assert result["link_variables"] == _LINK_VARIABLES
    assert result["sections"] == sections
    assert result["nodes"] == expected_nodes
    assert [node["N"] for node in result["nodes"]] == [63, 64, 2047, 2048]
    assert all(list(node) == _NODE_VARIABLE_NAMES for node in result["nodes"])


def test_read_net_links_decodes_records_and_preserves_order(tmp_path: Path) -> None:
    """Decode representative links in LVR order, including extended strings."""
    data, sections, parameters, _, expected_links = _build_link_net()
    result = read_net_links(_write(tmp_path / "synthetic-links.net", data))

    assert list(result) == [
        "banner",
        "identifier",
        "parameters",
        "node_variables",
        "link_variables",
        "sections",
        "links",
    ]
    assert result["banner"] == "NET PGM=HWYNET (vTEST) DATE=2026-08-05"
    assert result["identifier"] == "synthetic-net"
    assert result["parameters"] == parameters
    assert result["node_variables"] == _NODE_VARIABLES
    assert result["link_variables"] == _LINK_VARIABLES
    assert result["sections"] == sections
    assert result["links"] == expected_links
    assert all(list(link) == ["A", "B", "DISTANCE", "LABEL"] for link in result["links"])
    assert len(result["links"][1]["LABEL"]) > 0x3E


def test_iter_net_links_matches_materialized_reader(tmp_path: Path) -> None:
    """Expose the same ordered records without materializing the link list."""
    data, _, _, _, expected_links = _build_link_net()
    path = _write(tmp_path / "iter-links.net", data)

    link_iterator = iter_net_links(path)
    assert iter(link_iterator) is link_iterator
    assert list(link_iterator) == expected_links
    assert read_net_links(path)["links"] == expected_links


def test_read_net_returns_nodes_and_links(tmp_path: Path) -> None:
    """Return a complete network while retaining the node-only result shape."""
    data, sections, parameters, expected_nodes, expected_links = _build_link_net()
    path = _write(tmp_path / "full-network.net", data)
    result = read_net(path)

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
    assert result["parameters"] == parameters
    assert result["sections"] == sections
    assert result["speed_table"] == [[0.0] * 99 for _ in range(9)]
    assert result["capacity_table"] == [[0] * 99 for _ in range(9)]
    assert result["nodes"] == expected_nodes
    assert result["links"] == expected_links

    node_only = read_net_nodes(path)
    assert list(node_only)[-1] == "nodes"
    assert node_only["nodes"] == result["nodes"]
    assert "links" not in node_only


def test_read_net_links_allows_parallel_endpoint_pairs(tmp_path: Path) -> None:
    """Do not mistake multiple records with the same A/B pair for duplicates."""
    data, _, _, _, _ = _build_link_net()
    links = read_net_links(_write(tmp_path / "parallel-links.net", data))["links"]

    assert (links[0]["A"], links[0]["B"]) == (63, 64)
    assert (links[2]["A"], links[2]["B"]) == (63, 64)
    assert links[0] != links[2]


def test_read_net_nodes_decodes_literal_cube_records(tmp_path: Path) -> None:
    """Decode representative records copied byte-for-byte from Cube output."""
    payloads = [
        ("NET", b"NET PGM=HWYNET (v.07/10/2023 [6.5.1 x64])\n\x00"),
        ("ID", b"ID=\x00"),
        ("PAR", b"PAR Zones=1475 Nodes=39030 Links=0 NodeRecs=4 \x00"),
        (
            "NVR",
            _dictionary(
                "NVR",
                ["N", "X", "Y", "GGFARE", "PROJ=019", "PBA2050_RTP_ID=001"],
            ),
        ),
        ("LVR", _dictionary("LVR", ["A", "B"])),
        ("NOD", b"NOD\x00" + b"".join(_CUBE_NODE_RECORDS)),
        ("LNK", b"LNK\x00"),
        ("END", b"END\x00"),
    ]
    data, _ = _container(payloads)
    nodes = read_net_nodes(_write(tmp_path / "cube-records.net", data))["nodes"]

    assert [node["N"] for node in nodes] == [1, 73, 20505, 39030]
    assert [node["X"] for node in nodes] == pytest.approx(
        [552969.25, 550172, 556075.1133, 628767.37521],
        abs=5e-6,
    )
    assert [node["Y"] for node in nodes] == pytest.approx(
        [4183031.29228, 4182444, 4185243.605, 4092377.25035],
        abs=5e-6,
    )
    assert [node["GGFARE"] for node in nodes] == [0, 0, 0, 0]
    assert [node["PROJ"] for node in nodes] == ["", "", "SF_070027_Completed", ""]
    assert [node["PBA2050_RTP_ID"] for node in nodes] == ["", "", "", ""]


def test_read_net_nodes_accepts_string_path(tmp_path: Path) -> None:
    """Accept both Path objects and ordinary string paths."""
    data, _, _, _ = _build_valid_net()
    path = _write(tmp_path / "string-path.net", data)
    assert len(read_net_nodes(str(path))["nodes"]) == 4


def test_reader_module_needs_only_the_standard_library() -> None:
    """Load net_read.py with site packages such as NumPy disabled."""
    module_path = Path(__file__).resolve().parents[1] / "src" / "cubeio" / "net_read.py"
    code = (
        "import importlib.util; "
        f"spec = importlib.util.spec_from_file_location('net_read_stdlib', {str(module_path)!r}); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module); "
        "print(','.join(name for name in "
        "('iter_net_links', 'read_net', 'read_net_links', 'read_net_nodes') "
        "if callable(getattr(module, name))))"
    )
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-S", "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "iter_net_links,read_net,read_net_links,read_net_nodes"


def test_read_net_nodes_rejects_truncated_outer_record(tmp_path: Path) -> None:
    """Reject a top-level section whose declared end is beyond EOF."""
    data, _, _, _ = _build_valid_net()
    path = _write(tmp_path / "truncated.net", data[:-1])
    with pytest.raises(ValueError, match=r"past file size|Unexpected end"):
        read_net_nodes(path)


def test_read_net_nodes_rejects_bytes_after_end(tmp_path: Path) -> None:
    """Require END to be the final top-level record."""
    data, _, _, _ = _build_valid_net()
    path = _write(tmp_path / "after-end.net", data + b"unexpected")
    with pytest.raises(ValueError, match=r"Invalid END|not at end"):
        read_net_nodes(path)


def test_read_net_nodes_rejects_node_count_mismatch(tmp_path: Path) -> None:
    """Use PAR NodeRecs as the record count and reject a mismatch."""
    data, _, _, _ = _build_valid_net(declared_node_recs=5)
    path = _write(tmp_path / "wrong-count.net", data)
    with pytest.raises(ValueError, match=r"NOD section ends before node record|record count"):
        read_net_nodes(path)


def test_read_net_nodes_rejects_truncated_node_envelope(tmp_path: Path) -> None:
    """Bounds-check the payload declared by a two-byte node envelope."""
    # A two-byte envelope that claims a 256-byte payload but supplies one byte.
    data, _, _, _ = _build_valid_net(declared_node_recs=1, nod_body=b"\x81\x00\x01")
    path = _write(tmp_path / "truncated-node.net", data)
    with pytest.raises(ValueError, match=r"past the NOD section|Truncated|truncated"):
        read_net_nodes(path)


def test_read_net_nodes_rejects_unknown_numeric_tag(tmp_path: Path) -> None:
    """Fail loudly for numeric encodings that have not been established."""
    # 0x80 is not one of the numeric value tags used by NET node records.
    data, _, _, _ = _build_valid_net(declared_node_recs=1, nod_body=_node_record(b"\x80"))
    path = _write(tmp_path / "unknown-tag.net", data)
    with pytest.raises(ValueError, match="Unsupported numeric tag"):
        read_net_nodes(path)


def test_read_net_links_rejects_link_count_mismatch(tmp_path: Path) -> None:
    """Use PAR Links as the record count and reject a short LNK section."""
    data, _, _, _, _ = _build_link_net(declared_links=4)
    path = _write(tmp_path / "wrong-link-count.net", data)

    with pytest.raises(ValueError, match=r"LNK section ends before link record|record count"):
        read_net_links(path)


def test_read_net_links_rejects_truncated_link_envelope(tmp_path: Path) -> None:
    """Bounds-check a link payload declared by a two-byte envelope."""
    data, _, _, _, _ = _build_link_net(
        declared_links=1,
        lnk_body=b"\x81\x00\x01",
    )
    path = _write(tmp_path / "truncated-link.net", data)

    with pytest.raises(ValueError, match=r"past the LNK section|Truncated|truncated"):
        read_net_links(path)


def test_read_net_links_rejects_extra_lnk_bytes(tmp_path: Path) -> None:
    """Reject bytes left after the number of records declared by PAR Links."""
    records, _ = _synthetic_links()
    data, _, _, _, _ = _build_link_net(
        lnk_body=b"".join(records) + b"\x00",
    )
    path = _write(tmp_path / "extra-link-bytes.net", data)

    with pytest.raises(ValueError, match=r"LNK contains 1 extra byte"):
        read_net_links(path)


def test_read_net_links_rejects_unknown_numeric_tag(tmp_path: Path) -> None:
    """Fail loudly when a link field uses an unsupported scalar tag."""
    bad_payload = b"".join(
        (
            b"\x80",
            _packed_integer(64),
            _float32(1.5),
            _string("bad"),
        )
    )
    data, _, _, _, _ = _build_link_net(
        declared_links=1,
        lnk_body=_link_record(bad_payload),
    )
    path = _write(tmp_path / "unknown-link-tag.net", data)

    with pytest.raises(ValueError, match=r"Unsupported numeric tag.*field A"):
        read_net_links(path)


def test_read_net_links_rejects_non_integer_endpoint(tmp_path: Path) -> None:
    """Require A and B to use an integer representation."""
    bad_payload = b"".join(
        (
            _float64(63.0),
            _packed_integer(64),
            _float32(1.5),
            _string("bad"),
        )
    )
    data, _, _, _, _ = _build_link_net(
        declared_links=1,
        lnk_body=_link_record(bad_payload),
    )
    path = _write(tmp_path / "float-endpoint.net", data)

    with pytest.raises(ValueError, match=r"non-integer A=63\.0"):
        read_net_links(path)


def test_read_net_links_rejects_endpoint_outside_node_range(tmp_path: Path) -> None:
    """Require link endpoints to fall within 1..PAR Nodes."""
    bad_payload = b"".join(
        (
            _packed_integer(2049),
            _packed_integer(64),
            _float32(1.5),
            _string("bad"),
        )
    )
    data, _, _, _, _ = _build_link_net(
        declared_links=1,
        lnk_body=_link_record(bad_payload),
    )
    path = _write(tmp_path / "endpoint-out-of-range.net", data)

    with pytest.raises(ValueError, match=r"A=2049.*outside.*PAR Nodes"):
        read_net_links(path)


def test_read_net_nodes_skips_malformed_lnk_payload(tmp_path: Path) -> None:
    """Keep the lightweight node reader independent of link record validity."""
    data, _, _, expected_nodes = _build_valid_net(
        declared_links=1,
        lnk_body=b"\x81",
    )
    path = _write(tmp_path / "malformed-links.net", data)

    assert read_net_nodes(path)["nodes"] == expected_nodes
    with pytest.raises(ValueError, match=r"Truncated|truncated"):
        read_net_links(path)


def test_read_net_nodes_rejects_duplicate_node_number(tmp_path: Path) -> None:
    """Reject two NOD records that decode to the same node number."""
    record = _node_record(_minimal_node_payload(63))
    data, _, _, _ = _build_valid_net(declared_node_recs=2, nod_body=record * 2)
    path = _write(tmp_path / "duplicate-node.net", data)

    with pytest.raises(ValueError, match=r"Duplicate node number N=63 in record 2"):
        read_net_nodes(path)


def test_read_net_nodes_rejects_string_wider_than_declared(tmp_path: Path) -> None:
    """Reject a string value longer than its declared NVR width."""
    payload = _minimal_node_payload(63, short=_string("x" * 11))
    data, _, _, _ = _build_valid_net(declared_node_recs=1, nod_body=_node_record(payload))
    path = _write(tmp_path / "wide-string.net", data)

    with pytest.raises(
        ValueError,
        match=r"String length 11 exceeds declared width 10 .*field SHORT",
    ):
        read_net_nodes(path)


def test_read_net_nodes_rejects_unknown_string_tag(tmp_path: Path) -> None:
    """Fail loudly when a string field starts with a non-string tag byte."""
    # 0x3F is a numeric inline tag, never a string-length tag.
    payload = _minimal_node_payload(63, empty=b"\x3f")
    data, _, _, _ = _build_valid_net(declared_node_recs=1, nod_body=_node_record(payload))
    path = _write(tmp_path / "unknown-string-tag.net", data)

    with pytest.raises(ValueError, match=r"Unsupported string tag 0x3F .*field EMPTY"):
        read_net_nodes(path)


def test_read_net_rejects_endpoint_absent_from_nod(tmp_path: Path) -> None:
    """Enforce NOD membership only in the full read, not the range-only readers."""
    # Node 100 is within 1..PAR Nodes but is not one of the decoded NOD records.
    lnk_body = _link_record(
        b"".join(
            (
                _packed_integer(100),
                _packed_integer(64),
                _float32(1.5),
                _string("orphan"),
            )
        )
    )
    data, _, _, _ = _build_valid_net(declared_links=1, lnk_body=lnk_body)
    path = _write(tmp_path / "absent-endpoint.net", data)

    assert read_net_links(path)["links"][0]["A"] == 100
    with pytest.raises(ValueError, match=r"A=100.*absent from NOD"):
        read_net(path)


def test_read_net_requires_lookup_sections(tmp_path: Path) -> None:
    """Require SPD and CAP for a full read while node reads stay independent."""
    data, _, _, expected_nodes = _build_valid_net(include_lookup_tables=False)
    path = _write(tmp_path / "no-lookups.net", data)

    assert read_net_nodes(path)["nodes"] == expected_nodes
    with pytest.raises(ValueError, match=r"requires lookup section\(s\): SPD, CAP"):
        read_net(path)
