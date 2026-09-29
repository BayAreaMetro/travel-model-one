"""Write standardized CSV files for the PT background transit network."""

from __future__ import annotations

from collections.abc import Iterable
import csv
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile

from ..errors import OutputWriteError
from .models import BackgroundNetworkSource, SourceContext, TransitOnlyLink


@dataclass(frozen=True, slots=True)
class BackgroundNetworkWriteResult:
    """Paths and counts produced by the background-network conversion."""

    access_path: Path
    transfer_path: Path
    transit_only_path: Path
    controls_path: Path
    report_path: Path
    access_count: int
    transfer_count: int
    transit_only_source_count: int
    transit_only_directed_count: int


class BackgroundNetworkWriter:
    """Write editable CSV inputs without creating a CUBE network."""

    def write(
        self, source: BackgroundNetworkSource, output_directory: Path
    ) -> BackgroundNetworkWriteResult:
        output_directory.mkdir(parents=True, exist_ok=True)
        access_path = output_directory / "transit_access_links.csv"
        transfer_path = output_directory / "transit_transfer_links.csv"
        transit_only_path = output_directory / "transit_only_links.csv"
        controls_path = output_directory / "transit_link_controls.csv"
        report_path = output_directory / "background_network_conversion_report.json"

        self._write_rows(
            access_path,
            ("A", "B", "COMMENT", "LEADING_COMMENTS", "SOURCE_FILE", "SOURCE_LINE"),
            (
                (link.a, link.b, *self._context(link.context))
                for link in source.access_links
            ),
        )
        self._write_rows(
            transfer_path,
            (
                "A",
                "B",
                "DISTANCE",
                "COMMENT",
                "LEADING_COMMENTS",
                "SOURCE_FILE",
                "SOURCE_LINE",
            ),
            (
                (link.a, link.b, self._number(link.distance_miles), *self._context(link.context))
                for link in source.transfer_links
            ),
        )

        extra_attributes = sorted(
            {
                key
                for link in source.transit_only_links
                for key, _ in link.attributes
                if key not in {"NODES", "DIST", "MODES", "ONEWAY", "TIME", "SPEED"}
            }
        )
        directed_rows: list[tuple[object, ...]] = []
        for link in source.transit_only_links:
            directions = ((link.a, link.b, "N"),)
            if not link.one_way:
                directions += ((link.b, link.a, "Y"),)
            attribute_map = dict(link.attributes)
            for a, b, generated_reverse in directions:
                directed_rows.append(
                    (
                        a,
                        b,
                        self._number(link.distance_miles),
                        link.modes,
                        self._optional(link.time_minutes),
                        self._optional(link.speed_mph),
                        generated_reverse,
                        *(attribute_map.get(key, "") for key in extra_attributes),
                        *self._context(link.context),
                    )
                )
        self._write_rows(
            transit_only_path,
            (
                "A",
                "B",
                "DISTANCE",
                "MODES",
                "TIME",
                "SPEED",
                "GENERATED_REVERSE",
                *extra_attributes,
                "COMMENT",
                "LEADING_COMMENTS",
                "SOURCE_FILE",
                "SOURCE_LINE",
            ),
            directed_rows,
        )

        control_attributes = sorted(
            {key for record in source.transit_link_controls for key, _ in record.attributes}
        )
        self._write_rows(
            controls_path,
            (
                "RECORD_TYPE",
                *control_attributes,
                "COMMENT",
                "LEADING_COMMENTS",
                "SOURCE_FILE",
                "SOURCE_LINE",
            ),
            (
                (
                    record.record_type,
                    *(dict(record.attributes).get(key, "") for key in control_attributes),
                    *self._context(record.context),
                )
                for record in source.transit_link_controls
            ),
        )

        report = {
            "access_link_count": len(source.access_links),
            "transfer_link_count": len(source.transfer_links),
            "transit_only_source_link_count": len(source.transit_only_links),
            "transit_only_directed_link_count": len(directed_rows),
            "transit_link_control_count": len(source.transit_link_controls),
            "distance_units": "miles",
            "cube_usage": {
                "transit_access_links.csv": "Read with REV=1.",
                "transit_transfer_links.csv": "Read with REV=1.",
                "transit_only_links.csv": (
                    "Directions are already expanded; do not use REV=1. "
                    "Mode-specific duplicate A-B records are retained."
                ),
            },
        }
        self._write_text(report_path, json.dumps(report, indent=2) + "\n")
        return BackgroundNetworkWriteResult(
            access_path,
            transfer_path,
            transit_only_path,
            controls_path,
            report_path,
            len(source.access_links),
            len(source.transfer_links),
            len(source.transit_only_links),
            len(directed_rows),
        )

    @staticmethod
    def _context(context: SourceContext) -> tuple[object, ...]:
        return (
            context.comment,
            " | ".join(context.leading_comments),
            context.source_file,
            context.source_line,
        )

    @staticmethod
    def _number(value: Decimal) -> str:
        return format(value, "f")

    def _optional(self, value: Decimal | None) -> str:
        return "" if value is None else self._number(value)

    @staticmethod
    def _write_rows(
        path: Path, header: tuple[str, ...], rows: Iterable[Iterable[object]]
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
            raise OutputWriteError(f"Could not write background network {path}: {error}") from error
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
            raise OutputWriteError(f"Could not write background network report {path}: {error}") from error
