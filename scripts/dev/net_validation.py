"""Shared comparison helpers for the Cube CS1 CSV oracle validators.

Both the node and link validators render native values with Cube CS1's
presentation rules -- five-decimal half-up numeric rounding and
apostrophe-wrapped strings -- and compare headers, rows, and cells
exhaustively. The row comparison is dictionary-driven: each cell is rendered
according to its declared NVR/LVR kind, never by guessing from the Python
type alone.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import zip_longest

from cubeio import NodeValue, Parameters, VariableDefinition

Row = dict[str, NodeValue]

_CS1_QUANTUM = Decimal("0.00001")
_SURROUNDING_QUOTES_LENGTH = 2


@dataclass(frozen=True)
class Outcome:
    """Counts and bounded diagnostic samples from one exhaustive comparison."""

    native_rows: int
    oracle_rows: int
    cells_checked: int
    mismatches: int
    samples: list[str]
    comparison_seconds: float


def record_mismatch(samples: list[str], sample_limit: int, message: str) -> int:
    """Append one diagnostic if space remains and return one mismatch."""
    if len(samples) < sample_limit:
        samples.append(message)
    return 1


def render_numeric(value: float) -> str:
    """Render a native number with Cube CS1's five-place half-up rules."""
    if isinstance(value, int):
        return str(value)
    rounded = Decimal.from_float(value).quantize(_CS1_QUANTUM, rounding=ROUND_HALF_UP)
    rendered = format(rounded, "f").rstrip("0").rstrip(".")
    return "0" if rendered == "-0" else rendered


def normalize_oracle_string(value: str) -> str:
    """Remove Cube CS1 string presentation without altering string content."""
    if value == "' '":
        return ""
    if len(value) >= _SURROUNDING_QUOTES_LENGTH and value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def declared_columns(variables: list[VariableDefinition]) -> list[str]:
    """Return NVR/LVR field names in their declared on-disk order."""
    return [variable["name"] for variable in variables]


def parameter_as_int(parameters: Parameters, name: str) -> int:
    """Return one required integer PAR parameter."""
    value = parameters.get(name)
    if not isinstance(value, int):
        msg = f"PAR parameter {name} is missing or is not an integer"
        raise ValueError(msg)  # noqa: TRY004
    return value


def compare_headers(
    declared: list[str],
    oracle: list[str],
    samples: list[str],
    sample_limit: int,
) -> int:
    """Compare every dictionary and CSV header position, including missing columns."""
    mismatches = 0
    for column_number, (native_name, oracle_name) in enumerate(
        zip_longest(declared, oracle, fillvalue=None),
        start=1,
    ):
        if native_name != oracle_name:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"header column {column_number}: native={native_name!r}, Cube={oracle_name!r}",
            )
    return mismatches


def compare_missing_row(
    row_number: int,
    native_row: Row | None,
    oracle_row: list[str] | None,
    declared: list[str],
    samples: list[str],
    sample_limit: int,
) -> int:
    """Record one mismatch per expected cell when either side lacks a row."""
    if native_row is None:
        width = max(len(declared), len(oracle_row or []), 1)
        side = "native row missing"
    else:
        width = max(len(declared), len(native_row), 1)
        side = "Cube row missing"

    mismatches = 0
    for column_index in range(width):
        name = declared[column_index] if column_index < len(declared) else None
        mismatches += record_mismatch(
            samples,
            sample_limit,
            f"row {row_number}, column {column_index + 1} ({name!r}): {side}",
        )
    return mismatches


def _render_cell(
    value: NodeValue,
    variable: VariableDefinition,
) -> tuple[str | None, str | None]:
    """Render one native cell or return an explanatory type error."""
    kind = variable["kind"]
    if kind == "string":
        if not isinstance(value, str):
            return None, f"expected string, found {type(value).__name__}"
        return value, None
    if kind == "numeric":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, f"expected number, found {type(value).__name__}"
        return render_numeric(value), None
    return None, f"unsupported dictionary kind {kind!r}"


def compare_present_row(
    row_number: int,
    native_row: Row,
    oracle_row: list[str],
    variables: list[VariableDefinition],
    declared: list[str],
    samples: list[str],
    sample_limit: int,
) -> tuple[int, int]:
    """Compare field order, width, kind, and value across one present row."""
    native_items = list(native_row.items())
    width = max(len(variables), len(native_items), len(oracle_row))
    cells_checked = 0
    mismatches = 0

    for column_index in range(width):
        column_number = column_index + 1
        variable = variables[column_index] if column_index < len(variables) else None
        declared_name = declared[column_index] if column_index < len(declared) else None
        native_item = native_items[column_index] if column_index < len(native_items) else None
        oracle_value = oracle_row[column_index] if column_index < len(oracle_row) else None

        if native_item is None:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number} ({declared_name!r}): "
                "native field missing",
            )
            continue

        native_name, native_value = native_item
        if native_name != declared_name:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number}: "
                f"native name={native_name!r}, dictionary name={declared_name!r}",
            )

        if variable is None:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number} ({native_name!r}): "
                "dictionary field missing",
            )
            continue
        if oracle_value is None:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number} ({native_name!r}): Cube field missing",
            )
            continue

        cells_checked += 1
        rendered, type_error = _render_cell(native_value, variable)
        if type_error is not None:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number} ({native_name!r}): {type_error}",
            )
            continue

        expected = (
            normalize_oracle_string(oracle_value) if variable["kind"] == "string" else oracle_value
        )
        if rendered != expected:
            mismatches += record_mismatch(
                samples,
                sample_limit,
                f"row {row_number}, column {column_number} ({native_name!r}): "
                f"native={rendered!r}, Cube={expected!r}",
            )

    return cells_checked, mismatches
