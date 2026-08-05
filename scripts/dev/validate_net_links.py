r"""Validate native Cube ``.net`` link reads against a Cube CS1 CSV oracle.

The comparison is exhaustive but streaming: neither the decoded links nor CSV
rows are materialized. Header order, row order, field order, row widths, and
every scalar value must match. This script reads an existing oracle; it never
runs Cube or generates one. Missing inputs exit 2; mismatches exit 1.
"""

import argparse
import csv
import time
from collections.abc import Iterator
from itertools import zip_longest
from pathlib import Path
from typing import cast

from net_validation import (
    Outcome,
    compare_headers,
    compare_missing_row,
    compare_present_row,
    declared_columns,
    parameter_as_int,
    record_mismatch,
)

from cubeio import Link, VariableDefinition, iter_net_links, read_net_nodes

PRIMARY_NET = Path("E:/Tests/smoke_ctramp_cube/hwy/iter3/avgload5period.net")
_MISSING = object()


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser with the documented fixture defaults."""
    repo_root = Path(__file__).resolve().parents[2]
    primary_oracle = (
        repo_root / "scratch" / "truck_counts" / "model_network" / "avgload5period_links.csv"
    )
    parser = argparse.ArgumentParser(
        description=(
            "Compare iter_net_links() exhaustively with an existing Cube CS1 link CSV. "
            "Both inputs are streamed during comparison."
        ),
        epilog="This validator never invokes Cube or generates an oracle.",
    )
    parser.add_argument(
        "--net",
        type=Path,
        default=PRIMARY_NET,
        help=f"Cube .net file (default: {PRIMARY_NET})",
    )
    parser.add_argument(
        "--oracle",
        type=Path,
        default=primary_oracle,
        help=f"Cube CS1 link CSV (default: {primary_oracle})",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=10,
        metavar="N",
        help="maximum mismatch samples to print (default: 10)",
    )
    return parser


def _close_iterator(iterator: Iterator[Link]) -> None:
    """Close a generator-backed iterator when comparison exits early."""
    close = getattr(iterator, "close", None)
    if callable(close):
        close()


def _compare(
    net_path: Path,
    oracle_path: Path,
    variables: list[VariableDefinition],
    declared_rows: int,
    sample_limit: int,
) -> Outcome:
    """Stream both inputs through a complete row-, column-, and value comparison."""
    started = time.perf_counter()
    declared = declared_columns(variables)
    samples: list[str] = []
    mismatches = 0
    cells_checked = 0
    native_rows = 0
    oracle_rows = 0
    links = iter_net_links(net_path)

    try:
        with oracle_path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader, [])
            mismatches += compare_headers(declared, header, samples, sample_limit)

            for row_number, pair in enumerate(
                zip_longest(links, reader, fillvalue=_MISSING),
                start=1,
            ):
                native_item, oracle_item = pair
                if native_item is _MISSING:
                    oracle_rows += 1
                    mismatches += compare_missing_row(
                        row_number,
                        None,
                        cast("list[str]", oracle_item),
                        declared,
                        samples,
                        sample_limit,
                    )
                    continue
                if oracle_item is _MISSING:
                    native_rows += 1
                    mismatches += compare_missing_row(
                        row_number,
                        cast("Link", native_item),
                        None,
                        declared,
                        samples,
                        sample_limit,
                    )
                    continue

                native_rows += 1
                oracle_rows += 1
                row_cells, row_mismatches = compare_present_row(
                    row_number,
                    cast("Link", native_item),
                    cast("list[str]", oracle_item),
                    variables,
                    declared,
                    samples,
                    sample_limit,
                )
                cells_checked += row_cells
                mismatches += row_mismatches
    finally:
        _close_iterator(links)

    if native_rows != declared_rows:
        mismatches += record_mismatch(
            samples,
            sample_limit,
            f"native row count: decoded={native_rows:,}, PAR Links={declared_rows:,}",
        )
    if oracle_rows != declared_rows:
        mismatches += record_mismatch(
            samples,
            sample_limit,
            f"Cube row count: CSV={oracle_rows:,}, PAR Links={declared_rows:,}",
        )

    return Outcome(
        native_rows=native_rows,
        oracle_rows=oracle_rows,
        cells_checked=cells_checked,
        mismatches=mismatches,
        samples=samples,
        comparison_seconds=time.perf_counter() - started,
    )


def main() -> int:
    """Run the streaming link comparison and return a process exit code."""
    args = _parser().parse_args()
    net_path = cast("Path", args.net)
    oracle_path = cast("Path", args.oracle)
    sample_limit = cast("int", args.sample_limit)

    if sample_limit < 0:
        print("ERROR: --sample-limit must be nonnegative")
        return 2

    print("NET LINK VALIDATION")
    print(f"  NET: {net_path}")
    print(f"  CSV: {oracle_path}")
    missing = [path for path in (net_path, oracle_path) if not path.is_file()]
    if missing:
        print(f"  FAIL: input/oracle not found: {', '.join(str(path) for path in missing)}")
        return 2

    total_started = time.perf_counter()
    try:
        metadata_started = time.perf_counter()
        parsed = read_net_nodes(net_path)
        metadata_seconds = time.perf_counter() - metadata_started
        variables = parsed["link_variables"]
        declared_rows = parameter_as_int(parsed["parameters"], "Links")
        declared_cells = declared_rows * len(variables)
        print(f"  banner: {parsed['banner']}")
        print(f"  PAR Links: {declared_rows:,}")
        print(f"  LVR fields: {len(variables):,}")
        print(f"  declared cells: {declared_cells:,}")
        print(f"  metadata/node parse time: {metadata_seconds:.3f}s")

        outcome = _compare(
            net_path,
            oracle_path,
            variables,
            declared_rows,
            sample_limit,
        )
    except Exception as error:  # noqa: BLE001 - report format/CSV failures cleanly
        print(f"  FAIL: {type(error).__name__}: {error}")
        return 1

    status = "PASS" if outcome.mismatches == 0 else "FAIL"
    print(
        f"  {status}: native rows={outcome.native_rows:,}, "
        f"Cube rows={outcome.oracle_rows:,}, cells checked={outcome.cells_checked:,}, "
        f"mismatches={outcome.mismatches:,}, compare time={outcome.comparison_seconds:.3f}s"
    )
    for sample in outcome.samples:
        print(f"    {sample}")

    elapsed = time.perf_counter() - total_started
    print("=" * 72)
    print(
        f"Checked {outcome.cells_checked:,}/{declared_cells:,} declared cells in "
        f"{elapsed:.3f}s; mismatches={outcome.mismatches:,}"
    )
    return 1 if outcome.mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
