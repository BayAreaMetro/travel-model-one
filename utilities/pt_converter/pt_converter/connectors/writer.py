"""Write PT non-transit legs and their source crosswalks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import csv
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile

from ..errors import OutputWriteError, ValidationError
from .models import ConnectorSource


@dataclass(frozen=True, slots=True)
class ConnectorWriteResult:
    """Paths and counts produced for connector preparation."""

    ntleg_path: Path
    report_path: Path
    ntleg_count: int
    crosswalk_record_count: int


class ConnectorWriter:
    """Serialize complete walk legs and preserve incomplete generation rules."""

    def write(self, source: ConnectorSource, output_directory: Path) -> ConnectorWriteResult:
        self._validate(source)
        output_directory.mkdir(parents=True, exist_ok=True)
        ntleg_path = output_directory / "transitAccess.NTL"
        report_path = output_directory / "connector_conversion_report.json"

        self._write_text(ntleg_path, self._render_ntlegs(source))
        self._write_rows(
            output_directory / "walkAccessCrosswalk.csv",
            ("A", "B", "MODE", "DISTANCE", "COST", "ONEWAY", "SPEED", "SOURCE_LINE", "COMMENT"),
            ((leg.from_node, leg.to_node, leg.mode, _decimal(leg.distance_miles), _decimal(leg.cost_minutes), "T" if leg.one_way else "F", _decimal(leg.speed_mph), leg.source_line, leg.comment) for leg in source.walk_access_legs),
        )
        self._write_rows(
            output_directory / "zoneAccessRules.csv",
            ("A", "B", "MODE", "SOURCE_LINE", "COMMENT"),
            ((rule.from_node, rule.to_node, rule.mode, rule.source_line, rule.comment) for rule in source.zone_access_rules),
        )
        self._write_rows(
            output_directory / "pnrFacilities.csv",
            ("CATEGORY", "FACILITY_NODE", "TRANSIT_NODE", "ZONES", "TIME", "COST", "SOURCE_FILE", "SOURCE_LINE", "COMMENT"),
            ((facility.category, facility.facility_node, facility.transit_node, facility.zones, _optional(facility.time_minutes), _optional(facility.cost), facility.source_file, facility.source_line, facility.comment) for facility in source.pnr_facilities),
        )

        report = self._report(source)
        self._write_text(report_path, json.dumps(report, indent=2) + "\n")
        crosswalk_count = len(source.zone_access_rules) + len(source.pnr_facilities)
        ntleg_count = crosswalk_count + len(source.walk_access_legs)
        return ConnectorWriteResult(ntleg_path, report_path, ntleg_count, crosswalk_count)

    @staticmethod
    def _validate(source: ConnectorSource) -> None:
        if not source.walk_access_legs:
            raise ValidationError("No explicit walk access legs were found.")
        duplicate_walk = _duplicates((leg.from_node, leg.to_node, leg.mode) for leg in source.walk_access_legs)
        if duplicate_walk:
            formatted = ", ".join(f"{a}-{b} mode {mode}" for a, b, mode in sorted(duplicate_walk))
            raise ValidationError(f"PT permits only one walk NT leg for each node pair and mode; duplicates: {formatted}")

    @staticmethod
    def _render_ntlegs(source: ConnectorSource) -> str:
        rendered = [";;<<PT>><<NT>>;;"]
        for leg in source.walk_access_legs:
            rendered.extend(leg.leading_comments)
            record = (
                f"NT LEG={leg.from_node}-{leg.to_node}, MODE={leg.mode}, "
                f"COST={_decimal(leg.cost_minutes)}, DIST={_decimal(leg.distance_miles)}, "
                f"ONEWAY={'T' if leg.one_way else 'F'}, SPEED={_decimal(leg.speed_mph)}"
            )
            rendered.append(_with_comment(record, leg.comment))
        for rule in source.zone_access_rules:
            rendered.extend(rule.leading_comments)
            record = (
                f"NT LEG={rule.from_node}-{rule.to_node}, MODE={rule.mode}, "
                f"COST={_decimal(rule.cost_minutes)}, "
                f"DIST={_decimal(rule.distance_miles)}, ONEWAY=F, SPEED=3.00"
            )
            rendered.append(_with_comment(record, rule.comment))
        for facility in source.pnr_facilities:
            rendered.extend(facility.leading_comments)
            record = (
                f"NT LEG={facility.facility_node}-{facility.transit_node}, MODE=4, "
                f"COST={_decimal(facility.time_minutes)}, "
                f"DIST={_decimal(facility.distance_miles)}, ONEWAY=T, SPEED=3.00"
            )
            rendered.append(_with_comment(record, facility.comment))
        return "\n".join(rendered) + "\n"

    @staticmethod
    def _report(source: ConnectorSource) -> dict[str, object]:
        categories = Counter(facility.category for facility in source.pnr_facilities)
        return {
            "pt_ntleg_count": len(source.walk_access_legs) + len(source.zone_access_rules) + len(source.pnr_facilities),
            "walk_ntleg_count": len(source.walk_access_legs),
            "zone_access_ntleg_count": len(source.zone_access_rules),
            "pnr_ntleg_count": len(source.pnr_facilities),
            "zone_access_rule_count": len(source.zone_access_rules),
            "pnr_facility_count": len(source.pnr_facilities),
            "pnr_facilities_by_category": dict(sorted(categories.items())),
            "pnr_facilities_without_cost": sum(f.cost is None for f in source.pnr_facilities),
            "units": {
                "source_walk_distance": "hundredths of a mile",
                "output_distance": "miles",
                "speed": "miles per hour",
                "nt_cost": "minutes",
            },
            "translation_rules": {
                "transitAccess.NTL": "Direct PT NTLEGI records. Walk COST is DIST / SPEED * 60. PNR COST is TIME, DIST is inferred at 3 mph, MODE is 4, and ONEWAY is true.",
                "zoneAccessRules.csv": "Crosswalk preserving each source zone-access record.",
                "pnrFacilities.csv": "Crosswalk preserving each source PNR record and its eligible-zone metadata.",
            },
            "task_3_responsibility": "Construct the PT network and pass transitAccess.NTL through FILEI NTLEGI. No network was constructed or modified here.",
            "duplicate_source_keys": {
                "zone_access_node_pairs_and_modes": _duplicate_count((x.from_node, x.to_node, x.mode) for x in source.zone_access_rules),
                "pnr_facility_pairs": _duplicate_count((x.facility_node, x.transit_node) for x in source.pnr_facilities),
            },
        }

    @staticmethod
    def _write_rows(path: Path, header: tuple[str, ...], rows: Iterable[Iterable[object]]) -> None:
        temporary_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            temporary_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(header)
                writer.writerows(rows)
            temporary_path.replace(path)
        except OSError as error:
            raise OutputWriteError(f"Could not write connector output {path}: {error}") from error
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
            raise OutputWriteError(f"Could not write connector output {path}: {error}") from error


def _duplicates(values: Iterable[tuple[int, ...]]) -> set[tuple[int, ...]]:
    seen: set[tuple[int, ...]] = set()
    duplicates: set[tuple[int, ...]] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _duplicate_count(values: Iterable[tuple[int, ...]]) -> int:
    return len(_duplicates(values))


def _decimal(value: Decimal) -> str:
    return format(value, ".2f")


def _optional(value: Decimal | None) -> str:
    return "" if value is None else _decimal(value)


def _with_comment(record: str, comment: str) -> str:
    return f"{record} ; {comment}" if comment else record
