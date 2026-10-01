"""Write PT fare-system definitions and OD-matrix preparation tables."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
import csv
import json
import os
from pathlib import Path
import tempfile

from ..errors import OutputWriteError, ValidationError
from ..line_conversion.models import TransitMode
from .models import FareSource, ODFareTable


@dataclass(frozen=True, slots=True)
class FareWriteResult:
    """Fare outputs and the mode-to-fare-system mapping."""

    fare_path: Path
    report_path: Path
    fare_system_by_mode: dict[int, int]
    matrix_table_count: int


@dataclass(frozen=True, slots=True)
class FareMatrixSpec:
    """Prepared metadata for one source OD-fare table."""

    source_file: str


class FareWriter:
    """Create one operator-independent fare system per used transit mode."""

    def write(
        self,
        source: FareSource,
        modes: tuple[TransitMode, ...],
        used_transit_modes: set[int],
        output_directory: Path,
    ) -> FareWriteResult:
        self._validate(source, modes, used_transit_modes)
        output_directory.mkdir(parents=True, exist_ok=True)
        fare_system_by_mode = {
            mode: number
            for number, mode in enumerate(sorted(used_transit_modes), start=1)
        }
        mode_names = {mode.number: mode for mode in modes}
        matrix_specs = self._matrix_specs(source)
        zone_by_node = self._global_zone_by_node(source)
        fare_path = output_directory / "transitFares.far"
        self._write_text(
            fare_path,
            self._render_fares(
                source, mode_names, fare_system_by_mode, matrix_specs
            ),
        )

        prepared_directory = output_directory / "prepared"
        matrix_directory = output_directory / "matrices"
        prepared_directory.mkdir(parents=True, exist_ok=True)
        matrix_directory.mkdir(parents=True, exist_ok=True)
        self._write_rows(
            output_directory / "fareZoneCrosswalk.csv",
            (
                "NETWORK_NODE",
                "PT_FARE_ZONE",
                "SOURCE_FILES",
            ),
            (
                (
                    node,
                    fare_zone,
                    "|".join(
                        table.source_file
                        for table in source.od_tables
                        if any(
                            node in (record.from_node, record.to_node)
                            for record in table.records
                        )
                    ),
                )
                for node, fare_zone in sorted(zone_by_node.items())
            ),
        )
        matrix_manifest: list[dict[str, object]] = []
        combined_rows: list[tuple[object, ...]] = []
        for mode, system in fare_system_by_mode.items():
            source_file = source.od_file_by_mode.get(mode)
            if source_file is None:
                continue
            table = source.od_table(source_file)
            rows = self._matrix_rows(table, zone_by_node)
            combined_rows.extend(
                (row[0], row[1], system, row[2], mode, *row[3:]) for row in rows
            )
            matrix_manifest.append(
                {
                    "fare_system_id": system,
                    "mode": mode,
                    "source_file": source_file,
                    "prepared_csv": "prepared/fare_matrices.csv",
                    "cube_matrix_file": "matrices/fare_matrices.mat",
                    "fare_matrix_input_index": 1,
                    "matrix_table": system,
                    "pt_reference": f"FMI.1.{system}",
                    "fare_zone_variable": "NI.PTFAREZONE",
                    "matrix_dimension": len(zone_by_node),
                    "record_count": len(rows),
                }
            )
        self._write_rows(
            prepared_directory / "fare_matrices.csv",
            (
                "FROM_FARE_ZONE",
                "TO_FARE_ZONE",
                "FARE_SYSTEM_ID",
                "FARE",
                "MODE",
                "FROM_NETWORK_NODE",
                "TO_NETWORK_NODE",
                "SOURCE_FILE",
                "SOURCE_LINE",
                "COMMENT",
            ),
            combined_rows,
        )
        manifest_path = output_directory / "fare_matrix_manifest.json"
        self._write_text(manifest_path, json.dumps(matrix_manifest, indent=2) + "\n")
        self._write_text(
            output_directory / "fare_matrices.block",
            self._render_matrix_block(matrix_specs),
        )

        report_path = output_directory / "fare_conversion_report.json"
        self._write_text(
            report_path,
            json.dumps(
                self._report(
                    source, fare_system_by_mode, matrix_specs, zone_by_node
                ),
                indent=2,
            )
            + "\n",
        )
        return FareWriteResult(
            fare_path,
            report_path,
            fare_system_by_mode,
            len(source.od_tables),
        )

    @staticmethod
    def _validate(
        source: FareSource,
        modes: tuple[TransitMode, ...],
        used_modes: set[int],
    ) -> None:
        defined_modes = {mode.number for mode in modes}
        missing = sorted(used_modes - defined_modes)
        if missing:
            raise ValidationError(f"Fare modes are missing from transit_modes.csv: {missing}")
        if any(mode < 10 for mode in used_modes):
            raise ValidationError("NT modes 1-9 cannot receive PT fare systems.")
        referenced = {table.source_file for table in source.od_tables}
        missing_tables = sorted(
            {
                filename
                for mode, filename in source.od_file_by_mode.items()
                if mode in used_modes and filename not in referenced
            }
        )
        if missing_tables:
            raise ValidationError(f"Missing parsed OD fare table(s): {missing_tables}")

    @staticmethod
    def _matrix_specs(source: FareSource) -> dict[str, FareMatrixSpec]:
        return {
            table.source_file: FareMatrixSpec(source_file=table.source_file)
            for table in source.od_tables
        }

    @staticmethod
    def _global_zone_by_node(source: FareSource) -> dict[int, int]:
        nodes = sorted(
            {
                node
                for table in source.od_tables
                for record in table.records
                for node in (record.from_node, record.to_node)
            }
        )
        return {node: zone for zone, node in enumerate(nodes, 1)}

    @staticmethod
    def _render_fares(
        source: FareSource,
        mode_names: dict[int, TransitMode],
        systems: dict[int, int],
        matrix_specs: dict[str, FareMatrixSpec],
    ) -> str:
        rendered = [";;<<PT>><<FARESYSTEM>>;;"]
        source_modes_by_system = tuple(
            mode for mode, _ in sorted(systems.items(), key=lambda item: item[1])
        )
        for mode, system in systems.items():
            definition = mode_names[mode]
            attributes = [
                f"FARESYSTEM NUMBER={system}",
                f'NAME="M{mode}"',
                f'LONGNAME="{_quoted(definition.name[:40])}"',
            ]
            od_filename = source.od_file_by_mode.get(mode)
            is_free = (
                od_filename is None and source.xfare[0][mode - 1] == Decimal(1)
            )
            if is_free:
                attributes.append("STRUCTURE=FREE")
                rendered.append(",\n  ".join(attributes))
                continue
            if od_filename is None:
                attributes.append("STRUCTURE=FLAT")
            else:
                if od_filename not in matrix_specs:
                    raise ValidationError(f"Missing OD fare source: {od_filename}")
                attributes.extend(
                    (
                        "STRUCTURE=FROMTO",
                        f"FAREMATRIX=FMI.1.{system}",
                        "FAREZONES=NI.PTFAREZONE",
                    )
                )
            attributes.extend(
                (
                    "SAME=CUMULATIVE",
                    f"IBOARDFARE={_decimal(source.xfare[0][mode - 1])}",
                    "FAREFROMFS="
                    + _compressed(
                        tuple(
                            source.xfare[source_mode - 1][mode - 1]
                            for source_mode in source_modes_by_system
                        )
                    ),
                )
            )
            rendered.append(",\n  ".join(attributes))
        return "\n".join(rendered) + "\n"

    @staticmethod
    def _matrix_rows(
        table: ODFareTable, zone_by_node: dict[int, int]
    ) -> list[tuple[object, ...]]:
        fares: dict[tuple[int, int], tuple[Decimal, int, str]] = {}
        for record in table.records:
            directions = (
                (record.from_node, record.to_node),
                (record.to_node, record.from_node),
            )
            for pair in directions:
                prior = fares.get(pair)
                if prior is not None and prior[0] != record.fare:
                    raise ValidationError(
                        f"Conflicting OD fares for {pair[0]}-{pair[1]} in "
                        f"{table.source_file}."
                    )
                fares[pair] = (record.fare, record.source_line, record.comment)
        return [
            (
                zone_by_node[from_node],
                zone_by_node[to_node],
                _decimal(fare),
                from_node,
                to_node,
                table.source_file,
                source_line,
                comment,
            )
            for (from_node, to_node), (fare, source_line, comment) in sorted(fares.items())
        ]

    @staticmethod
    def _report(
        source: FareSource,
        systems: dict[int, int],
        matrix_specs: dict[str, FareMatrixSpec],
        zone_by_node: dict[int, int],
    ) -> dict[str, object]:
        structures = Counter(
            "FROMTO"
            if mode in source.od_file_by_mode
            else "FREE"
            if source.xfare[0][mode - 1] == Decimal(1)
            else "FLAT"
            for mode in systems
        )
        return {
            "fare_system_count": len(systems),
            "fare_system_assignment": "MODE only",
            "nontransit_modes_assigned": [],
            "fare_system_by_mode": {str(mode): system for mode, system in systems.items()},
            "global_fare_zone_count": len(zone_by_node),
            "structures": dict(sorted(structures.items())),
            "od_matrices": [
                {
                    "fare_system_id": system,
                    "mode": mode,
                    "source_file": source.od_file_by_mode[mode],
                    "fare_matrix_input_index": 1,
                    "matrix_table": system,
                    "pt_reference": f"FMI.1.{system}",
                    "fare_zone_variable": "NI.PTFAREZONE",
                    "matrix_dimension": len(zone_by_node),
                }
                for mode, system in systems.items()
                if mode in source.od_file_by_mode
            ],
            "translation_rules": {
                "IBOARDFARE": "XFARE from NT access mode 1 to the transit mode; validated equal for NT modes 1, 2, 4, 5, 6, and 7.",
                "FAREFROMFS": "Transit-mode-to-transit-mode XFARE, reordered into the compact fare-system numbering shown in fare_system_by_mode.",
                "flat_fares": "A transit mode without FAREMATI uses STRUCTURE=FLAT.",
                "od_fares": "All OD fare systems share one compact, one-based NI.PTFAREZONE crosswalk and one future CUBE fare_matrices.mat file. The matrix table number equals the fare-system ID, and every OD fare is written in both directions with the same value.",
                "free_fares": "A legacy initial XFARE value of 1 without an OD fare table is the TM1 free-service sentinel and becomes STRUCTURE=FREE, not IBOARDFARE=1.",
            },
            "farelinks": {
                "source_record_count": source.farelink_record_count,
                "affected_modes": list(source.farelink_modes),
                "status": "Preserved in this report but not translated. Link-dependent fares cannot be represented as FLAT or directly copied into a FROMTO matrix without path-level expansion and conflict testing.",
            },
            "task_2_matrix_build": "Build one CUBE fare_matrices.mat from prepared/fare_matrices.csv using PATTERN=IJM:V. Matrix M is the fare-system ID and every table uses the shared global fare-zone dimension.",
            "task_3_handoff": "Consume fare_matrices.mat through fare_matrices.block, add the generated PTFAREZONE attribute to the PT network nodes, and use the prepared fare systems during PT network building and assignment.",
            "value_of_time": "Not selected here. VALUEOFTIME and whether fare affects route evaluation remain assignment-specification decisions.",
        }

    @staticmethod
    def _render_matrix_block(matrix_specs: dict[str, FareMatrixSpec]) -> str:
        lines = ["; PT OD-fare matrix inputs"]
        if matrix_specs:
            lines.append(
                'FILEI FAREMATI[1]='
                '"@token_model_dir@\\trn\\pt\\fares\\matrices\\fare_matrices.mat"'
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _write_rows(path: Path, header: tuple[str, ...], rows: object) -> None:
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
            raise OutputWriteError(f"Could not write fare output {path}: {error}") from error
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
            raise OutputWriteError(f"Could not write fare output {path}: {error}") from error


def _compressed(values: tuple[Decimal, ...]) -> str:
    if not values:
        return ""
    rendered: list[str] = []
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        count = end - start
        value = _decimal(values[start])
        rendered.append(f"{count}*{value}" if count > 1 else value)
        start = end
    return ",".join(rendered)


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _quoted(value: str) -> str:
    return value.replace('"', '""')
