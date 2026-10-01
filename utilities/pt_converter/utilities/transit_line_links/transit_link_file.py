"""Convert a CUBE transitLines.link file into diagnostic Parquet tables."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence


ATTRIBUTE = re.compile(r"(?i)\b([A-Z_][A-Z0-9_]*)\s*=")
SOURCE_MARKER = re.compile(r"(?i)\bfrom\s*:\s*(.+?)\s*$")
TRUE_VALUES = frozenset({"T", "Y", "TRUE", "YES", "1"})
FALSE_VALUES = frozenset({"F", "N", "FALSE", "NO", "0"})
STANDARD_LINK_COLUMNS = (
    "A",
    "B",
    "DIRECTION",
    "GENERATED_REVERSE",
    "NODES",
    "DIST",
    "DISTANCE_MILES",
    "MODES",
    "MODES_EXPANDED",
    "ONEWAY",
    "TIME",
    "SPEED",
    "EFFECTIVE_SPEED_MPH",
    "SOURCE_FILE",
    "SOURCE_LINE",
    "COMMENT",
    "LEADING_COMMENTS",
)
PROVENANCE_COLUMNS = (
    "RECORD_TYPE",
    "SOURCE_FILE",
    "SOURCE_LINE",
    "COMMENT",
    "LEADING_COMMENTS",
)


class LinkFileParseError(ValueError):
    """Raised when a transit link input cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """One non-comment record and its source context."""

    record_type: str
    attributes: dict[str, str]
    source_file: str | None
    source_line: int
    comment: str
    leading_comments: tuple[str, ...]


def read_source_records(path: Path) -> tuple[SourceRecord, ...]:
    """Read every data record while preserving comments and arbitrary attributes."""

    try:
        raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError as error:
        raise LinkFileParseError(f"Could not read transit link file {path}: {error}") from error

    records: list[SourceRecord] = []
    pending_comments: list[str] = []
    current_source: str | None = None
    for source_line, raw in enumerate(raw_lines, 1):
        code, marker, inline_comment = raw.partition(";")
        code = code.strip()
        if not code:
            if marker:
                comment = ";" + inline_comment.strip()
                pending_comments.append(comment)
                source_match = SOURCE_MARKER.search(inline_comment)
                if source_match:
                    current_source = source_match.group(1).strip()
            continue

        record_type_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", code)
        if record_type_match is None:
            raise LinkFileParseError(
                f"Invalid record at {path.name}:{source_line}: {code}"
            )
        records.append(
            SourceRecord(
                record_type=record_type_match.group(1).upper(),
                attributes=_attributes(code, path.name, source_line),
                source_file=current_source,
                source_line=source_line,
                comment=inline_comment.strip() if marker else "",
                leading_comments=tuple(pending_comments),
            )
        )
        pending_comments.clear()

    if not records:
        raise LinkFileParseError(f"No records were found in {path}.")
    return tuple(records)


def build_link_rows(records: Iterable[SourceRecord]) -> list[dict[str, object]]:
    """Create one row per permitted directed LINK while retaining source attributes."""

    rows: list[dict[str, object]] = []
    for record in records:
        if record.record_type != "LINK":
            continue
        attributes = record.attributes
        required = {"NODES", "DIST", "MODES", "ONEWAY"}
        missing = sorted(required - attributes.keys())
        if missing:
            raise LinkFileParseError(
                f"LINK at source line {record.source_line} is missing: "
                + ", ".join(missing)
            )
        nodes = _integer_list(attributes["NODES"], "NODES", record.source_line)
        if len(nodes) != 2 or any(node <= 0 for node in nodes):
            raise LinkFileParseError(
                f"Invalid NODES={attributes['NODES']!r} at source line "
                f"{record.source_line}."
            )
        distance = _positive_float(attributes["DIST"], "DIST", record.source_line)
        one_way = _boolean(attributes["ONEWAY"], record.source_line)
        modes = _expand_modes(attributes["MODES"], record.source_line)
        time = _optional_positive_float(attributes.get("TIME"), "TIME", record.source_line)
        speed = _optional_positive_float(
            attributes.get("SPEED"), "SPEED", record.source_line
        )
        if time is not None and speed is not None:
            raise LinkFileParseError(
                f"LINK at source line {record.source_line} defines both TIME and SPEED."
            )

        directions = [(nodes[0], nodes[1], 0, False)]
        if not one_way:
            directions.append((nodes[1], nodes[0], 1, True))
        for a_node, b_node, direction, generated_reverse in directions:
            row: dict[str, object] = dict(attributes)
            row.update(
                {
                    "A": a_node,
                    "B": b_node,
                    "DIRECTION": direction,
                    "GENERATED_REVERSE": generated_reverse,
                    "NODES": attributes["NODES"],
                    "DIST": distance,
                    "DISTANCE_MILES": distance / 100.0,
                    "MODES": attributes["MODES"],
                    "MODES_EXPANDED": ",".join(str(mode) for mode in modes),
                    "ONEWAY": one_way,
                    "TIME": time,
                    "SPEED": speed,
                    "EFFECTIVE_SPEED_MPH": (
                        speed
                        if speed is not None
                        else (distance / 100.0) / (time / 60.0)
                        if time is not None
                        else None
                    ),
                    "SOURCE_FILE": record.source_file,
                    "SOURCE_LINE": record.source_line,
                    "COMMENT": record.comment,
                    "LEADING_COMMENTS": "\n".join(record.leading_comments),
                }
            )
            rows.append(row)
    if not rows:
        raise LinkFileParseError("No LINK records were found.")
    return rows


def build_control_rows(records: Iterable[SourceRecord]) -> list[dict[str, object]]:
    """Preserve FACTOR and any future non-LINK records in a companion table."""

    rows: list[dict[str, object]] = []
    for record in records:
        if record.record_type == "LINK":
            continue
        row: dict[str, object] = dict(record.attributes)
        row.update(
            {
                "RECORD_TYPE": record.record_type,
                "SOURCE_FILE": record.source_file,
                "SOURCE_LINE": record.source_line,
                "COMMENT": record.comment,
                "LEADING_COMMENTS": "\n".join(record.leading_comments),
            }
        )
        rows.append(row)
    return rows


def build_dataframes(records: tuple[SourceRecord, ...]):
    """Return directed LINK and non-LINK pandas DataFrames."""

    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError(
            "pandas is required. Run 'uv sync' in "
            "utilities/pt_converter/utilities/transit_line_links."
        ) from error

    link_rows = build_link_rows(records)
    control_rows = build_control_rows(records)
    link_columns = _ordered_columns(link_rows, STANDARD_LINK_COLUMNS)
    control_columns = _ordered_columns(control_rows, PROVENANCE_COLUMNS)
    links = pd.DataFrame(link_rows, columns=link_columns).convert_dtypes()
    controls = pd.DataFrame(control_rows, columns=control_columns).convert_dtypes()
    return links, controls


def write_parquet_tables(
    link_file: Path,
    output_directory: Path,
    links_output_name: str,
    controls_output_name: str,
) -> tuple[Path, Path]:
    """Write the directed physical links and companion control records."""

    for option, filename in (
        ("--links-output-name", links_output_name),
        ("--controls-output-name", controls_output_name),
    ):
        if Path(filename).name != filename or not filename.lower().endswith(".parquet"):
            raise ValueError(f"{option} must be a filename ending in .parquet.")

    records = read_source_records(link_file)
    links, controls = build_dataframes(records)
    output_directory.mkdir(parents=True, exist_ok=True)
    links_path = output_directory / links_output_name
    controls_path = output_directory / controls_output_name
    try:
        links.to_parquet(links_path, index=False, engine="pyarrow")
        controls.to_parquet(controls_path, index=False, engine="pyarrow")
    except ImportError as error:
        raise RuntimeError(
            "pyarrow is required. Run 'uv sync' in "
            "utilities/pt_converter/utilities/transit_line_links."
        ) from error
    return links_path, controls_path


def _attributes(code: str, filename: str, source_line: int) -> dict[str, str]:
    matches = list(ATTRIBUTE.finditer(code))
    values: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
        key = match.group(1).upper()
        value = code[match.end() : end].strip().rstrip(",").strip()
        if key in values:
            raise LinkFileParseError(
                f"Repeated {key} at {filename}:{source_line}."
            )
        values[key] = value
    return values


def _integer_list(value: str, keyword: str, source_line: int) -> tuple[int, ...]:
    try:
        return tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise LinkFileParseError(
            f"Invalid {keyword}={value!r} at source line {source_line}."
        ) from error


def _expand_modes(value: str, source_line: int) -> tuple[int, ...]:
    modes: list[int] = []
    try:
        for item in value.split(","):
            item = item.strip()
            if "-" in item:
                first_text, last_text = item.split("-", 1)
                first, last = int(first_text), int(last_text)
                if first > last:
                    raise ValueError
                modes.extend(range(first, last + 1))
            elif item:
                modes.append(int(item))
    except ValueError as error:
        raise LinkFileParseError(
            f"Invalid MODES={value!r} at source line {source_line}."
        ) from error
    if not modes:
        raise LinkFileParseError(f"Empty MODES at source line {source_line}.")
    return tuple(dict.fromkeys(modes))


def _positive_float(value: str, keyword: str, source_line: int) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise LinkFileParseError(
            f"Invalid {keyword}={value!r} at source line {source_line}."
        ) from error
    if result <= 0:
        raise LinkFileParseError(
            f"{keyword} must be positive at source line {source_line}."
        )
    return result


def _optional_positive_float(
    value: str | None, keyword: str, source_line: int
) -> float | None:
    return None if value is None else _positive_float(value, keyword, source_line)


def _boolean(value: str, source_line: int) -> bool:
    normalized = value.strip().upper()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise LinkFileParseError(
        f"Invalid ONEWAY={value!r} at source line {source_line}."
    )


def _ordered_columns(
    rows: list[dict[str, object]], preferred: tuple[str, ...]
) -> list[str]:
    available = {key for row in rows for key in row}
    return [key for key in preferred if key in available] + sorted(available - set(preferred))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert transitLines.link into directed-link Parquet tables."
    )
    parser.add_argument("link_file", type=Path, help="Input transitLines.link file")
    parser.add_argument("output_directory", type=Path, help="Directory for outputs")
    parser.add_argument(
        "--links-output-name",
        default="transit_physical_links.parquet",
    )
    parser.add_argument(
        "--controls-output-name",
        default="transit_link_controls.parquet",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        links_path, controls_path = write_parquet_tables(
            args.link_file,
            args.output_directory,
            args.links_output_name,
            args.controls_output_name,
        )
    except (LinkFileParseError, RuntimeError, ValueError) as error:
        print(f"Transit link inventory error: {error}")
        return 2
    print(f"Wrote directed transit links to {links_path}")
    print(f"Wrote non-link control records to {controls_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
