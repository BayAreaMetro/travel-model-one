"""Write a validated physical-link handoff for the future PT network builder."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
import csv
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile

from ..errors import OutputWriteError
from ..line_conversion.models import TransitLine
from .models import DirectedTransitLink, TransitLink, TransitLinkSource


@dataclass(frozen=True, slots=True)
class TopologyWriteResult:
    """Files and counts produced for the physical-link handoff."""

    links_path: Path
    directed_links_path: Path
    factors_path: Path
    report_path: Path
    source_link_count: int
    directed_link_count: int


class TopologyWriter:
    """Normalize LINK records without creating or changing a network."""

    def write(
        self,
        source: TransitLinkSource,
        lines: tuple[TransitLine, ...],
        output_directory: Path,
    ) -> TopologyWriteResult:
        output_directory.mkdir(parents=True, exist_ok=True)
        directed = source.directed_links()
        links_path = output_directory / "transitNetworkLinks.csv"
        directed_path = output_directory / "transitNetworkDirectedLinks.csv"
        factors_path = output_directory / "transitLinkFactors.csv"
        report_path = output_directory / "link_conversion_report.json"

        self._write_source_links(links_path, source.links)
        self._write_directed_links(directed_path, directed)
        self._write_factors(factors_path, source)

        pair_records: dict[tuple[int, int], list[DirectedTransitLink]] = defaultdict(list)
        for link in directed:
            pair_records[(link.from_node, link.to_node)].append(link)
        used_modes = {line.mode for line in lines}
        unused_modes = sorted(
            {mode for link in source.links for mode in link.modes} - used_modes
        )
        report = {
            "source_link_count": len(source.links),
            "directed_link_count": len(directed),
            "unique_directed_node_pair_count": len(pair_records),
            "duplicate_directed_pair_count": sum(
                len(records) > 1 for records in pair_records.values()
            ),
            "conflicting_directed_pair_count": sum(
                self._has_conflicting_values(records)
                for records in pair_records.values()
                if len(records) > 1
            ),
            "time_rule_count": sum(link.time_minutes is not None for link in source.links),
            "speed_rule_count": sum(link.speed_mph is not None for link in source.links),
            "factor_record_count": len(source.factors),
            "link_modes_not_used_by_transit_lines": unused_modes,
            "distance_units": "miles",
            "source_distance_units": "hundredths of a mile",
            "handoff_contract": {
                "transitNetworkLinks.csv": (
                    "Canonical source-order records. ONEWAY retains the original direction rule."
                ),
                "transitNetworkDirectedLinks.csv": (
                    "Expanded directional records for Task 3. Every ONEWAY=N record appears "
                    "once in each direction. No duplicates or conflicts are discarded."
                ),
                "transitLinkFactors.csv": (
                    "Non-LINK FACTOR records retained separately for later PT rule mapping."
                ),
                "task_3_responsibility": (
                    "Use these prepared records when constructing NETI and decide how overlapping "
                    "mode-specific time and speed rules are represented in the PT network."
                ),
            },
            "duplicate_pairs": [
                {
                    "a": pair[0],
                    "b": pair[1],
                    "source_lines": [record.source_line for record in records],
                    "conflicting_values": self._has_conflicting_values(records),
                }
                for pair, records in sorted(pair_records.items())
                if len(records) > 1
            ],
        }
        self._write_text(report_path, json.dumps(report, indent=2) + "\n")
        return TopologyWriteResult(
            links_path,
            directed_path,
            factors_path,
            report_path,
            len(source.links),
            len(directed),
        )

    def _write_source_links(self, path: Path, links: tuple[TransitLink, ...]) -> None:
        self._write_rows(
            path,
            (
                "A",
                "B",
                "DISTANCE",
                "MODES",
                "ONEWAY",
                "TIME",
                "SPEED",
                "SOURCE_LINE",
                "COMMENT",
            ),
            (
                (
                    link.from_node,
                    link.to_node,
                    _distance(link.distance_miles),
                    _compress_modes(link.modes),
                    "Y" if link.one_way else "N",
                    str(link.time_minutes) if link.time_minutes is not None else "",
                    str(link.speed_mph) if link.speed_mph is not None else "",
                    link.source_line,
                    link.comment,
                )
                for link in links
            ),
        )

    def _write_directed_links(
        self, path: Path, links: tuple[DirectedTransitLink, ...]
    ) -> None:
        self._write_rows(
            path,
            (
                "A",
                "B",
                "DISTANCE",
                "MODES",
                "TIME",
                "SPEED",
                "SOURCE_LINE",
                "GENERATED_REVERSE",
            ),
            (
                (
                    link.from_node,
                    link.to_node,
                    _distance(link.distance_miles),
                    _compress_modes(link.modes),
                    str(link.time_minutes) if link.time_minutes is not None else "",
                    str(link.speed_mph) if link.speed_mph is not None else "",
                    link.source_line,
                    "Y" if link.generated_reverse else "N",
                )
                for link in links
            ),
        )

    def _write_factors(self, path: Path, source: TransitLinkSource) -> None:
        self._write_rows(
            path,
            ("MAXWAITTIME", "NODES", "SOURCE_LINE"),
            (
                (
                    str(factor.max_wait_time),
                    ",".join(str(node) for node in factor.nodes),
                    factor.source_line,
                )
                for factor in source.factors
            ),
        )

    @staticmethod
    def _has_conflicting_values(records: list[DirectedTransitLink]) -> bool:
        return len(
            {
                (
                    record.distance_hundredths_mile,
                    record.modes,
                    record.time_minutes,
                    record.speed_mph,
                )
                for record in records
            }
        ) > 1

    @staticmethod
    def _write_rows(
        path: Path,
        header: tuple[str, ...],
        rows: Iterable[Iterable[object]],
    ) -> None:
        temporary_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(header)
                writer.writerows(rows)
            temporary_path.replace(path)
        except OSError as error:
            raise OutputWriteError(f"Could not write link handoff {path}: {error}") from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        try:
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(content, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            raise OutputWriteError(f"Could not write link handoff {path}: {error}") from error


def _distance(value: Decimal) -> str:
    return format(value, "f")


def _compress_modes(modes: tuple[int, ...]) -> str:
    groups: list[str] = []
    start = previous = modes[0]
    for mode in modes[1:]:
        if mode == previous + 1:
            previous = mode
            continue
        groups.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = mode
    groups.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(groups)
