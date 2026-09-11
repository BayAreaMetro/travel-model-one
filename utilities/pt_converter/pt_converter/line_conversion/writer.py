"""Write deterministic OpenPaths PT line and system input files."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import tempfile
from collections.abc import Iterable

from ..errors import OutputWriteError, ValidationError
from .models import TransitLine, VehicleCatalog


@dataclass(frozen=True, slots=True)
class PTWriteResult:
    """Paths and counts produced by a successful write."""

    line_path: Path
    system_path: Path
    report_path: Path
    line_count: int
    vehicle_type_count: int


class PTInputWriter:
    """Serialize parsed transit information using PT-native keywords."""

    LINE_FILENAME = "transitLines.lin"
    SYSTEM_FILENAME = "transitSystem.pts"
    REPORT_FILENAME = "line_conversion_report.json"

    def write(
        self,
        lines: tuple[TransitLine, ...],
        vehicles: VehicleCatalog,
        output_directory: Path,
    ) -> PTWriteResult:
        self._validate(lines, vehicles)
        output_directory.mkdir(parents=True, exist_ok=True)

        line_path = output_directory / self.LINE_FILENAME
        system_path = output_directory / self.SYSTEM_FILENAME
        report_path = output_directory / self.REPORT_FILENAME

        vehicle_numbers = {
            vehicle.name.casefold(): number
            for number, vehicle in enumerate(vehicles.vehicle_types, start=1)
        }
        assignments = []
        unresolved_lines: list[str] = []
        period_specific_lines: list[str] = []
        for line in lines:
            period_names = vehicles.vehicle_names_by_period(line.name)
            names = vehicles.vehicle_names_for_line(line.name)
            if not names:
                unresolved_lines.append(line.name)
            elif len(names) > 1:
                period_specific_lines.append(line.name)
            assignments.append(
                {
                    "line_name": line.name,
                    "am_vehicle": period_names[0] or None,
                    "pm_vehicle": period_names[1] or None,
                    "off_peak_vehicle": period_names[2] or None,
                    "distinct_vehicle_names": list(names),
                    "vehicle_type_numbers": [
                        vehicle_numbers[name.casefold()] for name in names
                    ],
                    "encoded_on_pt_line": False,
                }
            )

        self._write_text(line_path, self._render_lines(lines))
        self._write_text(system_path, self._render_system(lines, vehicles))
        report = {
            "line_count": len(lines),
            "mode_count": len({line.mode for line in lines}),
            "operator_count": len(
                {line.operator for line in lines if line.operator is not None}
            ),
            "vehicle_type_count": len(vehicles.vehicle_types),
            "lines_missing_operator": [
                line.name for line in lines if line.operator is None
            ],
            "lines_without_vehicle_mapping": unresolved_lines,
            "lines_with_period_specific_vehicles": period_specific_lines,
            "vehicle_assignment_note": (
                "TM1 can assign AM, PM, and off-peak vehicles to one line, but PT LINE "
                "accepts one VEHICLETYPE. The mappings are retained here and are not yet "
                "written onto the PT line definitions."
            ),
            "line_vehicle_assignments": assignments,
        }
        self._write_text(report_path, json.dumps(report, indent=2) + "\n")

        return PTWriteResult(
            line_path=line_path,
            system_path=system_path,
            report_path=report_path,
            line_count=len(lines),
            vehicle_type_count=len(vehicles.vehicle_types),
        )

    @staticmethod
    def _validate(lines: tuple[TransitLine, ...], vehicles: VehicleCatalog) -> None:
        if not lines:
            raise ValidationError("No transit LINE statements were found.")

        duplicate_names = _duplicates(line.name.casefold() for line in lines)
        if duplicate_names:
            raise ValidationError(
                "Transit line names must be unique; duplicate(s): "
                + ", ".join(sorted(duplicate_names))
            )

        invalid_modes = sorted({line.mode for line in lines if not 1 <= line.mode <= 999})
        invalid_operators = sorted(
            {
                line.operator
                for line in lines
                if line.operator is not None and not 1 <= line.operator <= 999
            }
        )
        if invalid_modes:
            raise ValidationError(f"PT mode numbers must be 1-999: {invalid_modes}")
        if invalid_operators:
            raise ValidationError(
                f"PT operator numbers must be 1-999: {invalid_operators}"
            )
        if len(vehicles.vehicle_types) > 255:
            raise ValidationError("PT supports at most 255 vehicle types.")

        duplicate_vehicles = _duplicates(
            vehicle.name.casefold() for vehicle in vehicles.vehicle_types
        )
        if duplicate_vehicles:
            raise ValidationError(
                "Vehicle type names must be unique; duplicate(s): "
                + ", ".join(sorted(duplicate_vehicles))
            )

        defined = {vehicle.name.casefold() for vehicle in vehicles.vehicle_types}
        referenced = {
            name.casefold()
            for line in lines
            for name in vehicles.vehicle_names_for_line(line.name)
        }
        missing = sorted(referenced - defined)
        if missing:
            raise ValidationError(
                "Vehicle mappings reference undefined vehicle type(s): "
                + ", ".join(missing)
            )

    def _render_lines(self, lines: tuple[TransitLine, ...]) -> str:
        rendered = [";;<<PT>><<LINE>>;;"]
        for line in lines:
            rendered.extend(line.comments_before)
            rendered.extend(line.comments_within)
            attributes = [f'LINE NAME="{_quoted(line.name)}"']
            if line.color is not None:
                attributes.append(f"COLOR={line.color}")
            attributes.extend(
                f"HEADWAY[{period}]={_decimal(value)}"
                for period, value in enumerate(line.headways, start=1)
            )
            if line.long_name is not None:
                attributes.append(f'LONGNAME="{_quoted(line.long_name)}"')
            attributes.append(f"MODE={line.mode}")
            attributes.append(f"ONEWAY={'T' if line.one_way else 'F'}")
            if line.operator is not None:
                attributes.append(f"OPERATOR={line.operator}")
            if line.runtime is not None:
                attributes.append(f"RUNTIME={_decimal(line.runtime)}")

            rendered.append(",\n    ".join(attributes) + ",")
            rendered.append(" " + line.node_text)
            rendered.append("")
            rendered.extend(line.comments_after)
        return "\n".join(rendered).rstrip() + "\n"

    def _render_system(
        self, lines: tuple[TransitLine, ...], vehicles: VehicleCatalog
    ) -> str:
        rendered = [";;<<PT>>;;", "; Generated from finalized Network Wrangler inputs."]
        for mode in sorted({line.mode for line in lines}):
            rendered.append(f'MODE NUMBER={mode}, NAME="MODE_{mode}"')
        rendered.append("")
        for operator in sorted(
            {line.operator for line in lines if line.operator is not None}
        ):
            rendered.append(
                f'OPERATOR NUMBER={operator}, NAME="OPERATOR_{operator}"'
            )
        rendered.append("")
        for number, vehicle in enumerate(vehicles.vehicle_types, start=1):
            rendered.append(
                f'VEHICLETYPE NUMBER={number}, NAME="{_quoted(vehicle.name)}", '
                f"CRUSHCAP={vehicle.capacity_100_percent}"
            )
        return "\n".join(rendered).rstrip() + "\n"

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        temporary_path: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(content)
            temporary_path.replace(path)
        except OSError as error:
            raise OutputWriteError(f"Could not write PT output {path}: {error}") from error
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _decimal(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _quoted(value: str) -> str:
    return value.replace('"', '""')
