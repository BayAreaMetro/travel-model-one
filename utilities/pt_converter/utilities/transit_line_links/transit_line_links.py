"""Create a directed-link inventory from a CUBE transit LINE file."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Sequence


LINE_START = re.compile(r"(?im)^[ \t]*LINE[ \t]+NAME[ \t]*=")
ATTRIBUTE = re.compile(
    r"(?i)(?<![A-Z0-9_])([A-Z][A-Z0-9_]*(?:\[\d+\])?)[ \t]*="
)
TRUE_VALUES = frozenset({"T", "Y", "TRUE", "YES", "1"})
FALSE_VALUES = frozenset({"F", "N", "FALSE", "NO", "0"})
OUTPUT_COLUMNS = ("A", "B", "NAME", "MODE", "OPERATOR", "DIRECTION")


class LineParseError(ValueError):
    """Raised when a LINE statement cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class TransitLine:
    """The route attributes needed to construct directed links."""

    name: str
    mode: int
    operator: int | None
    one_way: bool
    nodes: tuple[int, ...]
    source_line: int


@dataclass(frozen=True, slots=True)
class TransitRouteLink:
    """One directed link traversed by one transit line."""

    A: int
    B: int
    NAME: str
    MODE: int
    OPERATOR: int | None
    DIRECTION: int


def read_transit_lines(path: Path) -> tuple[TransitLine, ...]:
    """Read the route attributes and complete node sequence from a LIN file."""

    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as error:
        raise LineParseError(f"Could not read LINE file {path}: {error}") from error

    starts = list(LINE_START.finditer(text))
    if not starts:
        raise LineParseError(f"No LINE statements were found in {path}.")

    lines: list[TransitLine] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        statement = _remove_comments(text[start.start() : end])
        source_line = text.count("\n", 0, start.start()) + 1
        lines.append(_parse_line(statement, source_line))
    return tuple(lines)


def build_route_links(lines: Sequence[TransitLine]) -> tuple[TransitRouteLink, ...]:
    """Expand each route node sequence into forward and optional reverse links."""

    links: list[TransitRouteLink] = []
    for line in lines:
        nodes = tuple(abs(node) for node in line.nodes)
        links.extend(_links_for_direction(line, nodes, direction=0))
        if not line.one_way:
            links.extend(_links_for_direction(line, tuple(reversed(nodes)), direction=1))
    return tuple(links)


def build_dataframe(links: Sequence[TransitRouteLink]):
    """Return the route-link inventory as a pandas DataFrame."""

    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError(
            "pandas is required. Run 'uv sync' in "
            "utilities/pt_converter/utilities/transit_line_links "
            "or install the dependencies in requirements.txt."
        ) from error

    frame = pd.DataFrame((asdict(link) for link in links), columns=OUTPUT_COLUMNS)
    frame = frame.astype(
        {
            "A": "int64",
            "B": "int64",
            "NAME": "string",
            "MODE": "int64",
            "OPERATOR": "Int64",
            "DIRECTION": "int8",
        }
    )
    return frame


def write_parquet(lin_file: Path, output_directory: Path, output_name: str) -> Path:
    """Parse a LIN file and write its directed route links to Parquet."""

    if Path(output_name).name != output_name or not output_name.lower().endswith(
        ".parquet"
    ):
        raise ValueError("--output-name must be a filename ending in .parquet.")

    lines = read_transit_lines(lin_file)
    links = build_route_links(lines)
    frame = build_dataframe(links)
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / output_name
    try:
        frame.to_parquet(output_path, index=False, engine="pyarrow")
    except ImportError as error:
        raise RuntimeError(
            "pyarrow is required to write Parquet. Run 'uv sync' in "
            "utilities/pt_converter/utilities/transit_line_links or install the dependencies in "
            "requirements.txt."
        ) from error
    return output_path


def _parse_line(statement: str, source_line: int) -> TransitLine:
    name = _required_value(statement, "NAME", source_line)
    mode = _integer(_required_value(statement, "MODE", source_line), "MODE", source_line)

    owner = _optional_value(statement, "OWNER")
    operator = _optional_value(statement, "OPERATOR")
    if owner is not None and operator is not None and owner != operator:
        raise LineParseError(
            f"LINE {name!r} at source line {source_line} has conflicting "
            f"OWNER={owner} and OPERATOR={operator}."
        )
    operator_value = operator if operator is not None else owner
    operator_number = (
        _integer(operator_value, "OPERATOR", source_line)
        if operator_value is not None
        else None
    )

    one_way_value = _optional_value(statement, "ONEWAY") or "TRUE"
    normalized = one_way_value.upper()
    if normalized in TRUE_VALUES:
        one_way = True
    elif normalized in FALSE_VALUES:
        one_way = False
    else:
        raise LineParseError(
            f"Invalid ONEWAY={one_way_value!r} for LINE {name!r} at source "
            f"line {source_line}."
        )

    nodes = _node_sequence(statement)
    if len(nodes) < 2:
        raise LineParseError(
            f"LINE {name!r} at source line {source_line} must contain at least "
            "two nodes."
        )
    if any(node == 0 for node in nodes):
        raise LineParseError(
            f"LINE {name!r} at source line {source_line} contains node 0."
        )

    return TransitLine(name, mode, operator_number, one_way, nodes, source_line)


def _node_sequence(statement: str) -> tuple[int, ...]:
    matches = list(ATTRIBUTE.finditer(statement))
    nodes: list[int] = []
    for index, match in enumerate(matches):
        if match.group(1).upper() not in {"N", "NODES"}:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(statement)
        value = statement[match.end() : end]
        nodes.extend(int(token) for token in re.findall(r"(?<![A-Z0-9_])-?\d+", value))
    return tuple(nodes)


def _links_for_direction(
    line: TransitLine, nodes: tuple[int, ...], direction: int
) -> list[TransitRouteLink]:
    return [
        TransitRouteLink(a, b, line.name, line.mode, line.operator, direction)
        for a, b in zip(nodes, nodes[1:])
    ]


def _remove_comments(text: str) -> str:
    return "\n".join(raw.partition(";")[0] for raw in text.splitlines())


def _required_value(statement: str, keyword: str, source_line: int) -> str:
    value = _optional_value(statement, keyword)
    if value is None or value == "":
        raise LineParseError(
            f"LINE statement at source line {source_line} is missing {keyword}."
        )
    return value


def _optional_value(statement: str, keyword: str) -> str | None:
    match = re.search(
        rf'(?i)(?<![A-Z0-9_]){re.escape(keyword)}\s*=\s*'
        r'(?:(?:"([^"]*)")|(?:\'([^\']*)\')|([^,\s]+))',
        statement,
    )
    if match is None:
        return None
    return next(value for value in match.groups() if value is not None).strip()


def _integer(value: str, keyword: str, source_line: int) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise LineParseError(
            f"Invalid {keyword}={value!r} at source line {source_line}."
        ) from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a directed transit-route link inventory from a CUBE LIN file."
    )
    parser.add_argument("lin_file", type=Path, help="Input CUBE/TRNBUILD/PT .lin file")
    parser.add_argument("output_directory", type=Path, help="Directory for the Parquet output")
    parser.add_argument(
        "--output-name",
        default="transit_route_links.parquet",
        help="Parquet filename (default: transit_route_links.parquet)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = write_parquet(args.lin_file, args.output_directory, args.output_name)
    except (LineParseError, RuntimeError, ValueError) as error:
        print(f"Transit line link inventory error: {error}")
        return 2
    print(f"Wrote transit route links to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
