r"""Validate native Cube ``.net`` node reads against Cube CS1 CSV oracles.

The comparison is exhaustive: row count and order, column count and order, and
every value must match. Cube CS1 rounds numeric output to five decimal places
with decimal half-up rounding, so native floats are rendered the same way
before comparison; this is not a raw float64 bit comparison. String cells are
normalized only for Cube CS1's presentation rules: the exact blank sentinel
``' '`` becomes an empty string and surrounding apostrophes are removed.

With no arguments, both documented cases are required and validated. This
script does not run Cube or generate either oracle. Use explicit ``--case``
pairs when intentionally validating a subset. Missing inputs exit 2;
mismatches exit 1.

Explicit cases can be repeated:

    python scripts/dev/validate_net_reader.py \
        --case E:/path/network.net E:/path/network_nodes.csv \
        --case E:/path/freeflow.net E:/path/freeflow_nodes.csv
"""

import argparse
import csv
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from net_validation import (
    Outcome,
    compare_headers,
    compare_missing_row,
    compare_present_row,
    declared_columns,
)

from cubeio import NetNodesResult, read_net_nodes

PRIMARY_NET = Path("E:/Tests/smoke_ctramp_cube/hwy/iter3/avgload5period.net")
FREEFLOW_NET = Path("E:/Tests/base_2023_ctramp/hwy/freeflow.net")


@dataclass(frozen=True)
class Case:
    """One network and its independently generated Cube CS1 node oracle."""

    name: str
    net_path: Path
    csv_path: Path


def _parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[2]
    primary_csv = (
        repo_root / "scratch" / "truck_counts" / "model_network" / "avgload5period_nodes.csv"
    )
    freeflow_csv = repo_root / "scratch" / "truck_counts" / "model_network" / "freeflow_nodes.csv"

    parser = argparse.ArgumentParser(
        description=(
            "Compare native cubeio .net node reads exhaustively with existing Cube CS1 CSV "
            "oracles. With no --case, use the documented primary and freeflow paths."
        ),
        epilog=(
            "Both default oracles must exist. Use explicit --case pairs to validate a subset. "
            f"The freeflow oracle path is {freeflow_csv}. This validator never generates it."
        ),
    )
    parser.add_argument(
        "--case",
        action="append",
        nargs=2,
        metavar=("NET", "CSV"),
        help="explicit .net/CS1 CSV pair; repeat for multiple cases",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        metavar="N",
        help="maximum mismatch samples per case (default: 10)",
    )
    parser.set_defaults(
        default_cases=(
            Case("primary", PRIMARY_NET, primary_csv),
            Case("freeflow", FREEFLOW_NET, freeflow_csv),
        )
    )
    return parser


def _cases_from_args(args: argparse.Namespace) -> list[Case]:
    if args.case is None:
        return list(cast("tuple[Case, ...]", args.default_cases))
    return [
        Case(Path(net).stem, Path(net), Path(csv_path))
        for net, csv_path in cast("list[list[str]]", args.case)
    ]


def _read_oracle(csv_path: Path) -> tuple[list[str], list[list[str]]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        try:
            header = next(reader)
        except StopIteration:
            return [], []
        return header, list(reader)


def _compare(
    parsed: NetNodesResult,
    csv_path: Path,
    sample_limit: int,
) -> Outcome:
    started = time.perf_counter()
    nodes = parsed["nodes"]
    variables = parsed["node_variables"]
    declared = declared_columns(variables)
    header, oracle_rows = _read_oracle(csv_path)
    samples: list[str] = []
    mismatches = compare_headers(declared, header, samples, sample_limit)
    cells_checked = 0

    for row_index in range(max(len(nodes), len(oracle_rows))):
        row_number = row_index + 1
        node = nodes[row_index] if row_index < len(nodes) else None
        oracle_row = oracle_rows[row_index] if row_index < len(oracle_rows) else None
        if node is None or oracle_row is None:
            mismatches += compare_missing_row(
                row_number,
                node,
                oracle_row,
                declared,
                samples,
                sample_limit,
            )
            continue
        row_cells, row_mismatches = compare_present_row(
            row_number,
            node,
            oracle_row,
            variables,
            declared,
            samples,
            sample_limit,
        )
        cells_checked += row_cells
        mismatches += row_mismatches

    return Outcome(
        native_rows=len(nodes),
        oracle_rows=len(oracle_rows),
        cells_checked=cells_checked,
        mismatches=mismatches,
        samples=samples,
        comparison_seconds=time.perf_counter() - started,
    )


def _metadata_text(value: object) -> str:
    if isinstance(value, Mapping):
        return ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value)


def _print_metadata(parsed: NetNodesResult, parse_seconds: float) -> None:
    print(f"  banner: {parsed['banner']}")
    print(f"  identifier: {parsed['identifier']}")
    print(f"  PAR: {_metadata_text(parsed['parameters'])}")
    print(
        f"  dictionary: {len(parsed['node_variables']):,} node variables, "
        f"{len(parsed['link_variables']):,} link variables"
    )
    print(f"  sections: {_metadata_text(parsed['sections'])}")
    print(f"  parse time: {parse_seconds:.3f}s")


def _missing_paths(case: Case) -> list[Path]:
    return [path for path in (case.net_path, case.csv_path) if not path.is_file()]


def main() -> int:
    """Run every requested NET/CSV comparison and return a process exit code."""
    args = _parser().parse_args()
    if args.samples < 0:
        print("ERROR: --samples must be nonnegative")
        return 2

    cases = _cases_from_args(args)
    failures = 0
    missing_inputs = 0
    ran = 0
    total_cells = 0
    total_mismatches = 0
    total_started = time.perf_counter()

    for case in cases:
        print(f"\nCASE {case.name}")
        print(f"  NET: {case.net_path}")
        print(f"  CSV: {case.csv_path}")
        missing = _missing_paths(case)
        if missing:
            missing_text = ", ".join(str(path) for path in missing)
            print(f"  FAIL: input/oracle not found: {missing_text}")
            missing_inputs += 1
            continue

        ran += 1
        parse_started = time.perf_counter()
        try:
            parsed = read_net_nodes(case.net_path)
            parse_seconds = time.perf_counter() - parse_started
            _print_metadata(parsed, parse_seconds)
            outcome = _compare(parsed, case.csv_path, args.samples)
        except Exception as error:  # noqa: BLE001 - one bad case must not hide later cases
            print(f"  FAIL: {type(error).__name__}: {error}")
            failures += 1
            continue

        total_cells += outcome.cells_checked
        total_mismatches += outcome.mismatches
        status = "PASS" if outcome.mismatches == 0 else "FAIL"
        print(
            f"  {status}: native rows={outcome.native_rows:,}, "
            f"Cube rows={outcome.oracle_rows:,}, cells checked={outcome.cells_checked:,}, "
            f"mismatches={outcome.mismatches:,}, compare time={outcome.comparison_seconds:.3f}s"
        )
        for sample in outcome.samples:
            print(f"    {sample}")
        if outcome.mismatches:
            failures += 1

    elapsed = time.perf_counter() - total_started
    print("\n" + "=" * 72)
    print(
        f"Ran {ran:,} case(s); checked {total_cells:,} cells in {elapsed:.3f}s; "
        f"mismatches={total_mismatches:,}; failed cases={failures:,}; "
        f"missing inputs={missing_inputs:,}"
    )
    if missing_inputs:
        return 2
    if ran == 0:
        print("No runnable cases. Supply an existing pair with --case NET CSV.")
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
