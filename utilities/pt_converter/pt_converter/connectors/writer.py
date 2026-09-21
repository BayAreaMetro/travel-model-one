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
    walk_funnel_path: Path
    drive_funnel_path: Path
    report_path: Path
    ntleg_count: int
    crosswalk_record_count: int


class ConnectorWriter:
    """Serialize complete walk legs and preserve incomplete generation rules."""

    def write(self, source: ConnectorSource, output_directory: Path) -> ConnectorWriteResult:
        self._validate(source)
        output_directory.mkdir(parents=True, exist_ok=True)
        ntleg_path = output_directory / "transitAccess.NTL"
        walk_funnel_path = output_directory / "generate_walk_funnels.block"
        drive_funnel_path = output_directory / "generate_drive_funnel.block"
        report_path = output_directory / "connector_conversion_report.json"

        self._write_text(ntleg_path, self._render_ntlegs(source))
        self._write_text(
            walk_funnel_path,
            self._render_walk_funnels(source),
        )
        self._write_text(
            drive_funnel_path,
            self._render_drive_funnels(source),
        )
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
        ntleg_count = len(source.walk_access_legs)
        return ConnectorWriteResult(
            ntleg_path,
            walk_funnel_path,
            drive_funnel_path,
            report_path,
            ntleg_count,
            crosswalk_count,
        )

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
        return "\n".join(rendered) + "\n"

    @classmethod
    def _render_walk_funnels(cls, source: ConnectorSource) -> str:
        groups = _groups_by_source_marker(
            source.zone_access_rules,
            default_source="transitLines.zac",
        )
        sections = [
            "; PT walk-access and walk-egress generation through station funnels",
            "; ACCESSLINK values use A-S,COST,DISTANCE.",
        ]
        for direction, mode, title in (
            (1, 1, "WALK ACCESS"),
            (2, 6, "WALK EGRESS"),
        ):
            for source_comments, records in groups:
                sections.extend(("", f"; {title}"))
                sections.extend(source_comments)
                access_links = [
                    (
                        rule.from_node,
                        rule.to_node,
                        rule.cost_minutes,
                        rule.distance_miles,
                        rule.comment,
                        _non_source_comments(rule.leading_comments),
                    )
                    for rule in records
                ]
                sections.extend(
                    cls._render_generate(
                        direction=direction,
                        mode=mode,
                        cost="LW.DISTANCE",
                        extract_cost="LW.WALKTIME",
                        max_cost="9*0.75, 70*0.75, 20*1.1, 20*1.1, 10*1.1, 10*1.1",
                        max_cost_comment=(
                            "Maximum walk distance is 0.75 miles, or 1.1 miles "
                            "for express bus and higher modes."
                        ),
                        access_links=access_links,
                    )
                )
        return "\n".join(sections).rstrip() + "\n"

    @classmethod
    def _render_drive_funnels(cls, source: ConnectorSource) -> str:
        groups = _groups_by_source_marker(
            source.pnr_facilities,
            default_source="transitLines_*.pnr",
        )
        sections = [
            "; PT drive-access and drive-egress generation through PNR funnels",
            "; ACCESSLINK values use A-S,COST,DISTANCE.",
        ]
        for direction, mode, title in (
            (1, 2, "DRIVE ACCESS"),
            (2, 7, "DRIVE EGRESS"),
        ):
            for source_comments, records in groups:
                sections.extend(("", f"; {title}"))
                sections.extend(source_comments)
                access_links = [
                    (
                        facility.facility_node,
                        facility.transit_node,
                        facility.time_minutes,
                        facility.distance_miles,
                        facility.comment,
                        _non_source_comments(facility.leading_comments),
                    )
                    for facility in records
                ]
                sections.extend(
                    cls._render_generate(
                        direction=direction,
                        mode=mode,
                        cost="LW.PNR_TIME",
                        extract_cost="LW.PNR_TIME",
                        max_cost="999*40",
                        max_cost_comment=(
                            "Maximum drive time is 40 minutes for all modes."
                        ),
                        access_links=access_links,
                    )
                )
        return "\n".join(sections).rstrip() + "\n"

    @staticmethod
    def _render_generate(
        *,
        direction: int,
        mode: int,
        cost: str,
        extract_cost: str,
        max_cost: str,
        max_cost_comment: str,
        access_links: list[
            tuple[int, int, Decimal, Decimal, str, tuple[str, ...]]
        ],
    ) -> list[str]:
        rendered = [
            "GENERATE,",
            "    FROMNODE=1-1454,",
            f"    DIRECTION={direction},",
            f"    COST={cost},",
            f"    EXTRACTCOST={extract_cost},",
            f"    MAXCOST={max_cost}, ; {max_cost_comment}",
            f"    NTLEGMODE={mode},",
            "    ACCESSLINK=",
        ]
        for index, (
            a_node,
            station,
            link_cost,
            distance,
            comment,
            leading_comments,
        ) in enumerate(access_links):
            rendered.extend(leading_comments)
            continuation = "," if index + 1 < len(access_links) else ""
            record = (
                f"        {a_node}-{station},{_decimal(link_cost)},"
                f"{_decimal(distance)}{continuation}"
            )
            rendered.append(_with_comment(record, comment))
        return rendered

    @staticmethod
    def _report(source: ConnectorSource) -> dict[str, object]:
        categories = Counter(facility.category for facility in source.pnr_facilities)
        return {
            "pt_ntleg_count": len(source.walk_access_legs),
            "walk_ntleg_count": len(source.walk_access_legs),
            "zone_access_ntleg_count": 0,
            "pnr_ntleg_count": 0,
            "walk_funnel_accesslink_count": len(source.zone_access_rules),
            "drive_funnel_accesslink_count": len(source.pnr_facilities),
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
                "transitAccess.NTL": "Direct PT NTLEGI records translated only from WALK_access.sup. The source records and modes are preserved.",
                "generate_walk_funnels.block": "Generates walk access mode 1 and walk egress mode 6. ZAC mode-5 funnels become ACCESSLINK A-S,COST,DISTANCE values.",
                "generate_drive_funnel.block": "Generates drive access mode 2 and drive egress mode 7. PNR mode-4 funnels become ACCESSLINK A-S,COST,DISTANCE values.",
                "zoneAccessRules.csv": "Crosswalk preserving each source zone-access record.",
                "pnrFacilities.csv": "Crosswalk preserving each source PNR record and its eligible-zone metadata.",
            },
            "task_3_responsibility": "Read transitAccess.NTL through FILEI NTLEGI and include both generated funnel blocks in PT DATAPREP. No network was constructed or modified here.",
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


def _groups_by_source_marker(
    records: tuple[object, ...], *, default_source: str
) -> list[tuple[tuple[str, ...], list[object]]]:
    groups: list[tuple[tuple[str, ...], list[object]]] = []
    current_comments = (f"; From: {default_source}",)
    current_records: list[object] = []
    current_file: str | None = None
    for record in records:
        source_file = getattr(record, "source_file", default_source)
        leading_comments = getattr(record, "leading_comments", ())
        source_markers = tuple(
            comment
            for comment in leading_comments
            if "from:" in comment.casefold()
        )
        starts_group = source_file != current_file or bool(source_markers)
        if starts_group and current_records:
            groups.append((current_comments, current_records))
            current_records = []
        if starts_group:
            current_file = source_file
            current_comments = source_markers or (f"; From: {source_file}",)
        current_records.append(record)
    if current_records:
        groups.append((current_comments, current_records))
    return groups


def _non_source_comments(comments: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        comment for comment in comments if "from:" not in comment.casefold()
    )
