"""Read TM1's line-to-vehicle and vehicle-capacity CSV files."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from ..errors import SourceReadError, TranslationError
from .models import (
    LineVehicleAssignment,
    PrefixVehicleAssignment,
    VehicleCatalog,
    VehicleType,
)


class VehicleCatalogReader:
    """Load the three vehicle tables written by Network Wrangler."""

    def read(self, source_directory: Path) -> VehicleCatalog:
        line_rows = self._dict_rows(source_directory / "transitLineToVehicle.csv")
        prefix_rows = self._dict_rows(source_directory / "transitPrefixToVehicle.csv")
        capacity_rows = self._dict_rows(source_directory / "transitVehicleToCapacity.csv")
        name_rows = self._dict_rows(source_directory / "transit_vehicle_types.csv")
        names = self._vehicle_names(name_rows, source_directory)

        line_assignments = tuple(
            LineVehicleAssignment(
                line_name=row["Name"].strip(),
                system=row["System"].strip(),
                am_vehicle=row["AM VehicleType"].strip(),
                pm_vehicle=row["PM VehicleType"].strip(),
                off_peak_vehicle=row["OP Vehicle Type"].strip(),
            )
            for row in line_rows
            if row.get("Name") and row["Name"].strip().casefold() != "name"
        )
        prefix_assignments = tuple(
            PrefixVehicleAssignment(
                prefix=row["Prefix"].strip(),
                system=row["System"].strip(),
                vehicle=row["VehicleType"].strip(),
            )
            for row in prefix_rows
            if row.get("Prefix") and row["Prefix"].strip().casefold() != "prefix"
        )

        vehicles: list[VehicleType] = []
        for row in capacity_rows:
            name = row.get("VehicleType", "").strip()
            if not name or name.casefold() == "vehicletype":
                continue
            try:
                capacity_100 = int(float(row["100%Capacity"]))
                capacity_85 = int(float(row["85%Capacity"]))
            except (KeyError, ValueError) as error:
                raise TranslationError(f"Invalid capacity values for vehicle {name!r}.") from error
            lookup = names.get(name.casefold())
            if lookup is None:
                raise TranslationError(
                    f"Vehicle {name!r} is missing from transit_vehicle_types.csv."
                )
            vehicles.append(
                VehicleType(name, capacity_100, capacity_85, lookup[0], lookup[1])
            )

        capacity_names = {vehicle.name.casefold() for vehicle in vehicles}
        extra_names = sorted(set(names) - capacity_names)
        if extra_names:
            raise TranslationError(
                "transit_vehicle_types.csv references vehicle type(s) missing from "
                "transitVehicleToCapacity.csv: " + ", ".join(extra_names)
            )

        return VehicleCatalog(
            vehicle_types=tuple(sorted(vehicles, key=lambda item: item.name.casefold())),
            line_assignments=line_assignments,
            prefix_assignments=prefix_assignments,
        )

    @staticmethod
    def _vehicle_names(
        rows: list[dict[str, str]], source_directory: Path
    ) -> dict[str, tuple[str, str]]:
        expected = {"vehicle_type", "short_name", "vehicle_name"}
        if not rows or set(rows[0]) != expected:
            path = source_directory / "transit_vehicle_types.csv"
            raise TranslationError(
                f"Vehicle name table {path} must contain exactly: "
                + ", ".join(sorted(expected))
            )

        parsed: list[tuple[str, str, str]] = []
        for source_line, row in enumerate(rows, start=2):
            vehicle_type = row["vehicle_type"].strip()
            short_name = row["short_name"].strip()
            vehicle_name = row["vehicle_name"].strip()
            if not vehicle_type or not short_name or not vehicle_name:
                raise TranslationError(
                    f"Invalid vehicle name at transit_vehicle_types.csv:{source_line}."
                )
            if len(short_name) > 14:
                raise TranslationError(
                    f"short_name {short_name!r} exceeds 14 characters at "
                    f"transit_vehicle_types.csv:{source_line}."
                )
            parsed.append((vehicle_type, short_name, vehicle_name))

        type_counts = Counter(item[0].casefold() for item in parsed)
        short_counts = Counter(item[1].casefold() for item in parsed)
        duplicate_types = sorted(name for name, count in type_counts.items() if count > 1)
        duplicate_shorts = sorted(name for name, count in short_counts.items() if count > 1)
        if duplicate_types or duplicate_shorts:
            details: list[str] = []
            if duplicate_types:
                details.append("duplicate vehicle_type value(s): " + ", ".join(duplicate_types))
            if duplicate_shorts:
                details.append("duplicate short_name value(s): " + ", ".join(duplicate_shorts))
            raise TranslationError(
                "Invalid transit_vehicle_types.csv: " + "; ".join(details) + "."
            )
        return {
            vehicle_type.casefold(): (short_name, vehicle_name)
            for vehicle_type, short_name, vehicle_name in parsed
        }

    @staticmethod
    def _dict_rows(path: Path) -> list[dict[str, str]]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as source:
                return list(csv.DictReader(source))
        except OSError as error:
            raise SourceReadError(f"Could not read vehicle table {path}: {error}") from error
