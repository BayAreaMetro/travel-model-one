"""Read Cube Voyager ``.net`` highway networks without Cube.

The reader is deliberately read-only and depends only on the Python standard
library. It parses the NET/PAR/NVR/LVR metadata and every record in the NOD and
LNK sections. Node-only and link-only entry points avoid decoding data the
caller did not request.

See ``NET_ENCODING.md`` beside this module for the byte-level format and
validation evidence.
"""

# ruff: noqa: PLR2004

import re
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, Literal, TypedDict

_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_F32 = struct.Struct("<f")
_F64 = struct.Struct("<d")

_CAPTURED_SECTIONS = frozenset({"NET", "ID", "PAR", "NVR", "LVR", "NOD"})
_REQUIRED_SECTIONS = frozenset({"NET", "ID", "PAR", "NVR", "LVR", "NOD", "LNK", "END"})
_UNIQUE_SECTIONS = _REQUIRED_SECTIONS | {"SPD", "CAP"}

_PAR_ITEM_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s\x00]+)")
_INTEGER_RE = re.compile(r"[+-]?\d+")
_STRING_VARIABLE_RE = re.compile(r"(.+)=(\d+)$")

_LOOKUP_LANE_ROWS = 9
_LOOKUP_CLASS_COLUMNS = 99
_LOOKUP_VALUE_COUNT = _LOOKUP_LANE_ROWS * _LOOKUP_CLASS_COLUMNS
_LOOKUP_HEADER_MIDDLE = b"\x06\x20\x80\xc0"

NodeValue = int | float | str
Node = dict[str, NodeValue]
Link = dict[str, NodeValue]
Parameters = dict[str, int | str]


class VariableDefinition(TypedDict):
    """One ordered NVR/LVR field descriptor."""

    name: str
    kind: Literal["numeric", "string"]
    width: int | None


class SectionInfo(TypedDict):
    """Location and total length of one outer section."""

    name: str
    offset: int
    length: int


class NetMetadata(TypedDict):
    """Metadata shared by node-only, link-only, and full reads."""

    banner: str
    identifier: str
    parameters: Parameters
    node_variables: list[VariableDefinition]
    link_variables: list[VariableDefinition]
    sections: list[SectionInfo]


class NetNodesResult(NetMetadata):
    """Structured result returned by :func:`read_net_nodes`."""

    nodes: list[Node]


class NetLinksResult(NetMetadata):
    """Structured result returned by :func:`read_net_links`."""

    links: list[Link]


class NetResult(NetNodesResult):
    """Structured full-network result returned by :func:`read_net`."""

    speed_table: list[list[float]]
    capacity_table: list[list[int]]
    links: list[Link]


def _read_exact(fh: BinaryIO, size: int, *, context: str) -> bytes:
    """Read exactly *size* bytes or raise an offset-rich format error."""
    offset = fh.tell()
    value = fh.read(size)
    if len(value) != size:
        msg = (
            f"Unexpected end of file at byte {offset} while reading {context}: "
            f"needed {size} bytes, found {len(value)}"
        )
        raise ValueError(msg)
    return value


def _section_name(marker: bytes) -> str:
    """Return the canonical name for a four-byte top-level marker."""
    if marker.startswith(b"ID="):
        return "ID"
    for prefix, name in (
        (b"NET ", "NET"),
        (b"PAR ", "PAR"),
        (b"SPD\x00", "SPD"),
        (b"CAP\x00", "CAP"),
        (b"NVR ", "NVR"),
        (b"LVR ", "LVR"),
        (b"NOD\x00", "NOD"),
        (b"LNK\x00", "LNK"),
        (b"END\x00", "END"),
    ):
        if marker == prefix:
            return name
    return marker.decode("ascii", errors="backslashreplace").rstrip(" \x00") or "UNKNOWN"


def _read_container(  # noqa: C901
    path: Path,
    *,
    include_lookup_tables: bool = False,
) -> tuple[dict[str, bytes], list[SectionInfo]]:
    """Read relevant top-level sections and validate the container framing."""
    payloads: dict[str, bytes] = {}
    sections: list[SectionInfo] = []
    seen: set[str] = set()
    file_size = path.stat().st_size
    found_end = False
    captured_sections = _CAPTURED_SECTIONS
    if include_lookup_tables:
        captured_sections |= {"SPD", "CAP"}

    with path.open("rb") as fh:
        while fh.tell() < file_size:
            section_offset = fh.tell()
            total_length = _U32.unpack(
                _read_exact(fh, _U32.size, context="top-level section length")
            )[0]
            if total_length < 8:
                msg = (
                    f"Invalid top-level section length {total_length} at byte "
                    f"{section_offset}; a four-byte marker is required"
                )
                raise ValueError(msg)
            section_end = section_offset + total_length
            if section_end > file_size:
                msg = (
                    f"Top-level section at byte {section_offset} ends at {section_end}, "
                    f"past file size {file_size}"
                )
                raise ValueError(msg)

            marker = _read_exact(fh, 4, context="top-level section marker")
            name = _section_name(marker)
            sections.append({"name": name, "offset": section_offset, "length": total_length})

            if name in _UNIQUE_SECTIONS and name in seen:
                msg = f"Duplicate {name} section at byte {section_offset}"
                raise ValueError(msg)
            seen.add(name)

            remaining = total_length - 8
            if name in captured_sections:
                payloads[name] = marker + _read_exact(
                    fh, remaining, context=f"{name} section payload"
                )
            else:
                fh.seek(remaining, 1)

            if name == "END":
                if total_length != 8 or marker != b"END\x00":
                    msg = f"Invalid END section at byte {section_offset}"
                    raise ValueError(msg)
                if section_end != file_size:
                    msg = f"END section at byte {section_offset} is not at end of file"
                    raise ValueError(msg)
                found_end = True
                break

        if not found_end:
            msg = "Missing final END section"
            raise ValueError(msg)

    missing = sorted(_REQUIRED_SECTIONS - seen)
    if missing:
        msg = f"Missing required top-level section(s): {', '.join(missing)}"
        raise ValueError(msg)
    return payloads, sections


def _decode_ascii(value: bytes, *, offset: int, context: str) -> str:
    """Decode an ASCII format field with a useful error on invalid bytes."""
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:
        msg = f"Non-ASCII bytes at byte {offset + exc.start} while decoding {context}"
        raise ValueError(msg) from exc


def _parse_parameters(payload: bytes, *, payload_offset: int) -> Parameters:
    """Parse the whitespace-separated ``PAR key=value`` record."""
    text = _decode_ascii(
        payload.rstrip(b"\x00"),
        offset=payload_offset,
        context="PAR metadata",
    )
    if not text.startswith("PAR "):
        msg = "PAR section does not start with 'PAR '"
        raise ValueError(msg)

    parameters: Parameters = {}
    for match in _PAR_ITEM_RE.finditer(text):
        key, raw_value = match.groups()
        if key in parameters:
            msg = f"PAR section contains duplicate parameter {key!r}"
            raise ValueError(msg)
        parameters[key] = int(raw_value) if _INTEGER_RE.fullmatch(raw_value) else raw_value
    if not parameters:
        msg = "PAR section contains no key=value parameters"
        raise ValueError(msg)
    return parameters


def _parse_variable_dictionary(
    payload: bytes,
    *,
    payload_offset: int,
    section_name: str,
) -> list[VariableDefinition]:
    """Parse an NVR/LVR dictionary, retaining ordered string-width metadata."""
    parts = payload.rstrip(b"\x00").split(b"\x00")
    part_offsets: list[int] = []
    position = 0
    for part in parts:
        part_offsets.append(position)
        position += len(part) + 1
    header = _decode_ascii(
        parts[0],
        offset=payload_offset,
        context=f"{section_name} header",
    )
    match = re.fullmatch(rf"{section_name}\s+(\d+)", header)
    if match is None:
        msg = f"Invalid {section_name} dictionary header: {header!r}"
        raise ValueError(msg)
    declared_count = int(match.group(1))

    raw_variables = [
        (part, part_offsets[index]) for index, part in enumerate(parts[1:], start=1) if part
    ]
    if len(raw_variables) != declared_count:
        msg = (
            f"{section_name} declares {declared_count} variables but contains {len(raw_variables)}"
        )
        raise ValueError(msg)

    variables: list[VariableDefinition] = []
    names: set[str] = set()
    for raw_variable, variable_offset in raw_variables:
        token = _decode_ascii(
            raw_variable,
            offset=payload_offset + variable_offset,
            context=f"{section_name} variable",
        )
        string_match = _STRING_VARIABLE_RE.fullmatch(token)
        if string_match is None:
            name = token
            kind: Literal["numeric", "string"] = "numeric"
            width = None
        else:
            name = string_match.group(1)
            kind = "string"
            width = int(string_match.group(2))
            if width < 1:
                msg = f"{section_name} string variable {name!r} has invalid width {width}"
                raise ValueError(msg)
        if not name:
            msg = f"{section_name} contains an empty variable name"
            raise ValueError(msg)
        if name in names:
            msg = f"{section_name} contains duplicate variable {name!r}"
            raise ValueError(msg)
        names.add(name)
        variables.append({"name": name, "kind": kind, "width": width})
    return variables


def _decode_lookup_high_bytes(
    encoded: bytes,
    *,
    count: int,
    encoded_offset: int,
    section_name: str,
) -> bytes:
    """Expand Cube's sparse literal/RLE stream for lookup-value high bytes."""
    decoded = bytearray()
    position = 0
    while len(decoded) < count:
        run_offset = position
        if position + 2 > len(encoded):
            msg = (
                f"Truncated {section_name} high-byte lookup run header at byte "
                f"{encoded_offset + position}"
            )
            raise ValueError(msg)
        low_count = encoded[position]
        mode = encoded[position + 1]
        position += 2
        run_length = low_count | ((mode & 0x7F) << 8)
        if run_length == 0:
            msg = f"Empty {section_name} high-byte lookup run at byte {encoded_offset + run_offset}"
            raise ValueError(msg)
        if len(decoded) + run_length > count:
            msg = (
                f"{section_name} high-byte lookup run at byte "
                f"{encoded_offset + run_offset} "
                f"expands past {count} values"
            )
            raise ValueError(msg)

        if mode & 0x80:
            if position >= len(encoded):
                msg = (
                    f"Truncated {section_name} high-byte repeated lookup run at byte "
                    f"{encoded_offset + run_offset}"
                )
                raise ValueError(msg)
            decoded.extend([encoded[position]] * run_length)
            position += 1
        else:
            run_end = position + run_length
            if run_end > len(encoded):
                msg = (
                    f"Truncated {section_name} high-byte literal lookup run at byte "
                    f"{encoded_offset + run_offset}"
                )
                raise ValueError(msg)
            decoded.extend(encoded[position:run_end])
            position = run_end

    if position != len(encoded):
        msg = (
            f"{section_name} lookup stream has {len(encoded) - position} "
            f"trailing byte(s) at byte {encoded_offset + position}"
        )
        raise ValueError(msg)
    return bytes(decoded)


def _parse_lookup_stored_values(
    payload: bytes,
    *,
    section_offset: int,
    section_name: Literal["SPD", "CAP"],
) -> list[int]:
    """Decode the 891 unsigned stored values in an SPD or CAP section."""
    marker = section_name.encode("ascii") + b"\x00"
    if not payload.startswith(marker):
        msg = f"{section_name} section does not start with the {section_name} marker"
        raise ValueError(msg)
    body = payload[4:]
    body_offset = section_offset + 8
    if len(body) < 7:
        msg = f"Truncated {section_name} lookup header at byte {body_offset}"
        raise ValueError(msg)

    expected_seed = 1 if section_name == "SPD" else 20
    if body[0] != expected_seed or body[1:5] != _LOOKUP_HEADER_MIDDLE:
        msg = f"Unsupported {section_name} lookup header at byte {body_offset}: {body[:5].hex(' ')}"
        raise ValueError(msg)

    declared_count = _U16.unpack_from(body, 5)[0]
    if declared_count != _LOOKUP_VALUE_COUNT:
        msg = (
            f"{section_name} lookup declares {declared_count} values; "
            f"expected {_LOOKUP_VALUE_COUNT}"
        )
        raise ValueError(msg)

    low_start = 7
    low_end = low_start + declared_count
    if low_end > len(body):
        msg = f"Truncated {section_name} lookup low-byte array at byte {body_offset + low_start}"
        raise ValueError(msg)
    low_bytes = body[low_start:low_end]
    high_bytes = _decode_lookup_high_bytes(
        body[low_end:],
        count=declared_count,
        encoded_offset=body_offset + low_end,
        section_name=section_name,
    )
    return [
        low_byte | (high_byte << 8)
        for low_byte, high_byte in zip(low_bytes, high_bytes, strict=True)
    ]


def _parse_speed_table(payload: bytes, *, section_offset: int) -> list[list[float]]:
    """Decode SPD as nine lane rows by 99 speed classes."""
    stored = _parse_lookup_stored_values(
        payload,
        section_offset=section_offset,
        section_name="SPD",
    )
    values = [value / 10 for value in stored]
    return [
        values[start : start + _LOOKUP_CLASS_COLUMNS]
        for start in range(0, len(values), _LOOKUP_CLASS_COLUMNS)
    ]


def _parse_capacity_table(payload: bytes, *, section_offset: int) -> list[list[int]]:
    """Decode CAP as nine lane rows by 99 per-lane capacity classes."""
    values = _parse_lookup_stored_values(
        payload,
        section_offset=section_offset,
        section_name="CAP",
    )
    return [
        values[start : start + _LOOKUP_CLASS_COLUMNS]
        for start in range(0, len(values), _LOOKUP_CLASS_COLUMNS)
    ]


def _require_bytes(
    record: bytes,
    position: int,
    size: int,
    *,
    record_offset: int,
    context: str,
) -> None:
    """Require *size* record bytes from *position*."""
    if position + size > len(record):
        absolute = record_offset + position
        msg = (
            f"Truncated scalar at byte {absolute} ({context}): needed {size} bytes, "
            f"only {len(record) - position} remain"
        )
        raise ValueError(msg)


def _decode_numeric(
    record: bytes,
    position: int,
    *,
    record_offset: int,
    context: str,
) -> tuple[int | float, int]:
    """Decode one observed Cube positive-number scalar."""
    _require_bytes(record, position, 1, record_offset=record_offset, context=context)
    tag_position = position
    tag = record[position]
    position += 1

    if tag <= 0x3F:
        return tag, position

    if 0x48 <= tag <= 0x4F:
        _require_bytes(record, position, 1, record_offset=record_offset, context=context)
        value = ((tag & 0x07) << 8) | record[position]
        return value, position + 1

    if 0x50 <= tag <= 0x57:
        _require_bytes(record, position, _U16.size, record_offset=record_offset, context=context)
        value = ((tag & 0x07) << 16) | _U16.unpack_from(record, position)[0]
        return value, position + _U16.size

    if tag == 0x88:
        _require_bytes(record, position, _F64.size, record_offset=record_offset, context=context)
        return _F64.unpack_from(record, position)[0], position + _F64.size

    if 0x90 <= tag <= 0x9F:
        width = (tag & 0x03) + 1
        decimal_places = 1 + ((tag - 0x90) >> 2)
        _require_bytes(record, position, width, record_offset=record_offset, context=context)
        stored = int.from_bytes(record[position : position + width], "little", signed=False)
        return stored / (10**decimal_places), position + width

    if tag == 0xA4:
        _require_bytes(record, position, _F32.size, record_offset=record_offset, context=context)
        return _F32.unpack_from(record, position)[0], position + _F32.size

    absolute = record_offset + tag_position
    msg = f"Unsupported numeric tag 0x{tag:02X} at byte {absolute} ({context})"
    raise ValueError(msg)


def _decode_string(
    record: bytes,
    position: int,
    *,
    maximum_width: int,
    record_offset: int,
    context: str,
) -> tuple[str, int]:
    """Decode one length-tagged ASCII string scalar."""
    _require_bytes(record, position, 1, record_offset=record_offset, context=context)
    tag_position = position
    tag = record[position]
    position += 1

    if 0xC0 <= tag <= 0xFE:
        length = tag - 0xC0
    elif tag == 0xFF:
        _require_bytes(record, position, 1, record_offset=record_offset, context=context)
        length = record[position]
        position += 1
    else:
        absolute = record_offset + tag_position
        msg = f"Unsupported string tag 0x{tag:02X} at byte {absolute} ({context})"
        raise ValueError(msg)

    if length > maximum_width:
        absolute = record_offset + tag_position
        msg = (
            f"String length {length} exceeds declared width {maximum_width} "
            f"at byte {absolute} ({context})"
        )
        raise ValueError(msg)
    _require_bytes(record, position, length, record_offset=record_offset, context=context)
    value = _decode_ascii(
        record[position : position + length],
        offset=record_offset + position,
        context=context,
    )
    return value, position + length


def _read_record_envelope(
    body: bytes,
    position: int,
    *,
    body_offset: int,
    record_kind: str,
    record_number: int,
    section_name: str,
) -> tuple[bytes, int, int]:
    """Read one one- or two-byte-length-prefixed NOD/LNK record."""
    if position >= len(body):
        msg = f"{section_name} section ends before {record_kind} record {record_number}"
        raise ValueError(msg)

    prefix_offset = position
    first = body[position]
    position += 1
    if first < 0x80:
        payload_length = first
    else:
        if position >= len(body):
            msg = f"Truncated record-length prefix at byte {body_offset + prefix_offset}"
            raise ValueError(msg)
        payload_length = ((first & 0x7F) << 8) | body[position]
        position += 1
    if payload_length == 0:
        msg = f"Empty {record_kind} record {record_number} at byte {body_offset + prefix_offset}"
        raise ValueError(msg)

    record_offset = body_offset + position
    record_end = position + payload_length
    if record_end > len(body):
        msg = (
            f"{record_kind.title()} record {record_number} at byte {record_offset} has "
            f"length {payload_length}, past the {section_name} section end"
        )
        raise ValueError(msg)
    return body[position:record_end], record_end, record_offset


def _read_file_record(
    fh: BinaryIO,
    *,
    section_end: int,
    record_kind: str,
    record_number: int,
    section_name: str,
) -> tuple[bytes, int]:
    """Read one record envelope and payload without buffering its whole section."""
    prefix_offset = fh.tell()
    if prefix_offset >= section_end:
        msg = f"{section_name} section ends before {record_kind} record {record_number}"
        raise ValueError(msg)

    first = _read_exact(fh, 1, context=f"{record_kind} record-length prefix")[0]
    if first < 0x80:
        payload_length = first
    else:
        if fh.tell() >= section_end:
            msg = f"Truncated record-length prefix at byte {prefix_offset}"
            raise ValueError(msg)
        second = _read_exact(fh, 1, context=f"{record_kind} record-length prefix")[0]
        payload_length = ((first & 0x7F) << 8) | second
    if payload_length == 0:
        msg = f"Empty {record_kind} record {record_number} at byte {prefix_offset}"
        raise ValueError(msg)

    record_offset = fh.tell()
    record_end = record_offset + payload_length
    if record_end > section_end:
        msg = (
            f"{record_kind.title()} record {record_number} at byte {record_offset} has "
            f"length {payload_length}, past the {section_name} section end"
        )
        raise ValueError(msg)
    record = _read_exact(fh, payload_length, context=f"{record_kind} record {record_number}")
    return record, record_offset


def _parameter_as_int(parameters: Parameters, name: str) -> int:
    """Return one required integer PAR parameter."""
    value = parameters.get(name)
    if not isinstance(value, int):
        msg = f"PAR parameter {name} is missing or is not an integer"
        raise ValueError(msg)  # noqa: TRY004
    return value


def _parse_nodes(  # noqa: C901, PLR0912, PLR0915
    nod_payload: bytes,
    *,
    nod_section_offset: int,
    parameters: Parameters,
    variables: list[VariableDefinition],
) -> list[Node]:
    """Decode all NOD records using the NVR field dictionary."""
    if not nod_payload.startswith(b"NOD\x00"):
        msg = "NOD section does not start with the NOD marker"
        raise ValueError(msg)
    body = nod_payload[4:]
    body_offset = nod_section_offset + 8
    record_count = _parameter_as_int(parameters, "NodeRecs")
    maximum_node = _parameter_as_int(parameters, "Nodes")
    if record_count < 0 or maximum_node < 1:
        msg = "PAR NodeRecs/Nodes values are outside their valid ranges"
        raise ValueError(msg)

    variable_names = [str(variable["name"]) for variable in variables]
    if "N" not in variable_names:
        msg = "NVR dictionary does not define node-number variable N"
        raise ValueError(msg)

    nodes: list[Node] = []
    node_numbers: set[int] = set()
    position = 0
    for record_index in range(record_count):
        record_number = record_index + 1
        record, position, record_offset = _read_record_envelope(
            body,
            position,
            body_offset=body_offset,
            record_kind="node",
            record_number=record_number,
            section_name="NOD",
        )
        node: Node = {}
        scalar_position = 0
        for variable in variables:
            name = str(variable["name"])
            node_label = node.get("N", "unknown")
            context = f"node record {record_number}, node {node_label}, field {name}"
            if variable["kind"] == "string":
                width = variable["width"]
                if not isinstance(width, int):
                    msg = f"NVR string variable {name!r} has no integer width"
                    raise ValueError(msg)
                value, scalar_position = _decode_string(
                    record,
                    scalar_position,
                    maximum_width=width,
                    record_offset=record_offset,
                    context=context,
                )
            else:
                value, scalar_position = _decode_numeric(
                    record,
                    scalar_position,
                    record_offset=record_offset,
                    context=context,
                )
            node[name] = value

        if scalar_position != len(record):
            msg = (
                f"Node record {record_number} has {len(record) - scalar_position} "
                f"trailing byte(s) at byte {record_offset + scalar_position}"
            )
            raise ValueError(msg)

        node_number = node["N"]
        if not isinstance(node_number, int):
            msg = f"Node record {record_number} has non-integer N={node_number!r}"
            raise ValueError(msg)  # noqa: TRY004
        if node_number < 1 or node_number > maximum_node:
            msg = (
                f"Node record {record_number} has N={node_number}, outside "
                f"1..PAR Nodes ({maximum_node})"
            )
            raise ValueError(msg)
        if node_number in node_numbers:
            msg = f"Duplicate node number N={node_number} in record {record_number}"
            raise ValueError(msg)
        node_numbers.add(node_number)
        nodes.append(node)

    if position != len(body):
        msg = (
            f"NOD contains {len(body) - position} extra byte(s) after "
            f"PAR NodeRecs={record_count} records"
        )
        raise ValueError(msg)
    return nodes


def _decode_link_record(
    record: bytes,
    *,
    record_number: int,
    record_offset: int,
    maximum_node: int,
    node_numbers: set[int] | None,
    variables: list[VariableDefinition],
) -> Link:
    """Decode and validate one link payload."""
    link: Link = {}
    scalar_position = 0
    for variable in variables:
        name = variable["name"]
        link_label = f"{link.get('A', 'unknown')}->{link.get('B', 'unknown')}"
        context = f"link record {record_number}, link {link_label}, field {name}"
        if variable["kind"] == "string":
            width = variable["width"]
            if not isinstance(width, int):
                msg = f"LVR string variable {name!r} has no integer width"
                raise ValueError(msg)
            value, scalar_position = _decode_string(
                record,
                scalar_position,
                maximum_width=width,
                record_offset=record_offset,
                context=context,
            )
        else:
            value, scalar_position = _decode_numeric(
                record,
                scalar_position,
                record_offset=record_offset,
                context=context,
            )
        link[name] = value

    if scalar_position != len(record):
        msg = (
            f"Link record {record_number} has {len(record) - scalar_position} "
            f"trailing byte(s) at byte {record_offset + scalar_position}"
        )
        raise ValueError(msg)

    for endpoint_name in ("A", "B"):
        endpoint = link[endpoint_name]
        if not isinstance(endpoint, int):
            msg = f"Link record {record_number} has non-integer {endpoint_name}={endpoint!r}"
            raise ValueError(msg)  # noqa: TRY004
        if endpoint < 1 or endpoint > maximum_node:
            msg = (
                f"Link record {record_number} has {endpoint_name}={endpoint}, outside "
                f"1..PAR Nodes ({maximum_node})"
            )
            raise ValueError(msg)
        if node_numbers is not None and endpoint not in node_numbers:
            msg = (
                f"Link record {record_number} has {endpoint_name}={endpoint}, "
                "which is absent from NOD"
            )
            raise ValueError(msg)
    return link


def _iter_links(
    network_path: Path,
    *,
    link_section_offset: int,
    link_section_length: int,
    node_numbers: set[int] | None,
    parameters: Parameters,
    variables: list[VariableDefinition],
) -> Iterator[Link]:
    """Yield every LNK record in LVR order while holding only one record."""
    record_count = _parameter_as_int(parameters, "Links")
    maximum_node = _parameter_as_int(parameters, "Nodes")
    if record_count < 0 or maximum_node < 1:
        msg = "PAR Links/Nodes values are outside their valid ranges"
        raise ValueError(msg)

    variable_names = [variable["name"] for variable in variables]
    missing_endpoints = [name for name in ("A", "B") if name not in variable_names]
    if missing_endpoints:
        msg = f"LVR dictionary does not define endpoint variable(s): {', '.join(missing_endpoints)}"
        raise ValueError(msg)

    section_end = link_section_offset + link_section_length
    with network_path.open("rb") as fh:
        fh.seek(link_section_offset + 4)
        marker = _read_exact(fh, 4, context="LNK section marker")
        if marker != b"LNK\x00":
            msg = "LNK section does not start with the LNK marker"
            raise ValueError(msg)

        for record_index in range(record_count):
            record_number = record_index + 1
            record, record_offset = _read_file_record(
                fh,
                section_end=section_end,
                record_kind="link",
                record_number=record_number,
                section_name="LNK",
            )
            yield _decode_link_record(
                record,
                record_number=record_number,
                record_offset=record_offset,
                maximum_node=maximum_node,
                node_numbers=node_numbers,
                variables=variables,
            )

        if fh.tell() != section_end:
            msg = (
                f"LNK contains {section_end - fh.tell()} extra byte(s) after "
                f"PAR Links={record_count} records"
            )
            raise ValueError(msg)


def _parse_links(
    network_path: Path,
    *,
    link_section_offset: int,
    link_section_length: int,
    node_numbers: set[int] | None,
    parameters: Parameters,
    variables: list[VariableDefinition],
) -> list[Link]:
    """Decode all LNK records into an in-memory list of dictionaries."""
    return list(
        _iter_links(
            network_path,
            link_section_offset=link_section_offset,
            link_section_length=link_section_length,
            node_numbers=node_numbers,
            parameters=parameters,
            variables=variables,
        )
    )


def _read_metadata(
    path: Path,
    *,
    include_lookup_tables: bool = False,
) -> tuple[NetMetadata, dict[str, bytes], dict[str, SectionInfo]]:
    """Read and decode metadata shared by all public NET entry points."""
    payloads, sections = _read_container(
        path,
        include_lookup_tables=include_lookup_tables,
    )
    section_by_name = {section["name"]: section for section in sections}

    banner = _decode_ascii(
        payloads["NET"].rstrip(b"\x00\r\n"),
        offset=section_by_name["NET"]["offset"] + 4,
        context="NET banner",
    )
    identifier_payload = payloads["ID"]
    identifier = _decode_ascii(
        identifier_payload[3:].split(b"\x00", 1)[0],
        offset=section_by_name["ID"]["offset"] + 7,
        context="NET identifier",
    )
    parameters = _parse_parameters(
        payloads["PAR"],
        payload_offset=section_by_name["PAR"]["offset"] + 4,
    )
    node_variables = _parse_variable_dictionary(
        payloads["NVR"],
        payload_offset=section_by_name["NVR"]["offset"] + 4,
        section_name="NVR",
    )
    link_variables = _parse_variable_dictionary(
        payloads["LVR"],
        payload_offset=section_by_name["LVR"]["offset"] + 4,
        section_name="LVR",
    )

    metadata: NetMetadata = {
        "banner": banner,
        "identifier": identifier,
        "parameters": parameters,
        "node_variables": node_variables,
        "link_variables": link_variables,
        "sections": sections,
    }
    return metadata, payloads, section_by_name


def read_net_nodes(path: str | Path) -> NetNodesResult:
    """Read node records and metadata from a Cube Voyager highway network.

    Args:
        path: Path to a Cube Voyager ``.net`` file.

    Returns:
        A dictionary with ``banner``, ``identifier``, parsed ``parameters``,
        ordered ``node_variables`` and ``link_variables`` definitions,
        top-level ``sections`` (offset and total length), and decoded ``nodes``.
        Each node is a dictionary whose insertion order follows NVR.

    Raises:
        ValueError: If the file framing, metadata, record encoding, or values are
            inconsistent. Signed numeric encodings have not been observed and
            are rejected instead of guessed.
    """
    network_path = Path(path)
    metadata, payloads, section_by_name = _read_metadata(network_path)
    nodes = _parse_nodes(
        payloads["NOD"],
        nod_section_offset=section_by_name["NOD"]["offset"],
        parameters=metadata["parameters"],
        variables=metadata["node_variables"],
    )
    return {**metadata, "nodes": nodes}


def iter_net_links(path: str | Path) -> Iterator[Link]:
    """Return an iterator over decoded links without materializing the link list.

    The iterator validates record boundaries and the declared link count when it
    is fully consumed. Endpoint values are range-checked against ``PAR Nodes``;
    use :func:`read_net` when membership in the decoded NOD records must also be
    verified. If iteration stops early, call the iterator's ``close()`` method
    promptly so its file handle is released.
    """
    network_path = Path(path)
    metadata, _, section_by_name = _read_metadata(network_path)
    link_section = section_by_name["LNK"]
    return _iter_links(
        network_path,
        link_section_offset=link_section["offset"],
        link_section_length=link_section["length"],
        node_numbers=None,
        parameters=metadata["parameters"],
        variables=metadata["link_variables"],
    )


def read_net_links(path: str | Path) -> NetLinksResult:
    """Read all link records and metadata from a Cube Voyager highway network.

    This materializes one ordered dictionary per link. For wide or large
    networks, prefer :func:`iter_net_links` to keep memory usage bounded.
    """
    network_path = Path(path)
    metadata, _, section_by_name = _read_metadata(network_path)
    link_section = section_by_name["LNK"]
    links = _parse_links(
        network_path,
        link_section_offset=link_section["offset"],
        link_section_length=link_section["length"],
        node_numbers=None,
        parameters=metadata["parameters"],
        variables=metadata["link_variables"],
    )
    return {**metadata, "links": links}


def read_net(path: str | Path) -> NetResult:
    """Read metadata, nodes, and links from a Cube Voyager highway network.

    The returned ``nodes`` and ``links`` lists preserve NVR/LVR field order and
    on-disk record order. This full read also verifies that every link endpoint
    is present in the decoded node records.
    """
    network_path = Path(path)
    metadata, payloads, section_by_name = _read_metadata(
        network_path,
        include_lookup_tables=True,
    )
    missing_lookups = [name for name in ("SPD", "CAP") if name not in payloads]
    if missing_lookups:
        msg = f"Full NET read requires lookup section(s): {', '.join(missing_lookups)}"
        raise ValueError(msg)
    speed_table = _parse_speed_table(
        payloads["SPD"],
        section_offset=section_by_name["SPD"]["offset"],
    )
    capacity_table = _parse_capacity_table(
        payloads["CAP"],
        section_offset=section_by_name["CAP"]["offset"],
    )
    nodes = _parse_nodes(
        payloads["NOD"],
        nod_section_offset=section_by_name["NOD"]["offset"],
        parameters=metadata["parameters"],
        variables=metadata["node_variables"],
    )
    node_numbers = {int(node["N"]) for node in nodes}
    link_section = section_by_name["LNK"]
    links = _parse_links(
        network_path,
        link_section_offset=link_section["offset"],
        link_section_length=link_section["length"],
        node_numbers=node_numbers,
        parameters=metadata["parameters"],
        variables=metadata["link_variables"],
    )
    return {
        **metadata,
        "speed_table": speed_table,
        "capacity_table": capacity_table,
        "nodes": nodes,
        "links": links,
    }
