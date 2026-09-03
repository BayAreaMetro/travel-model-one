"""Read TM1's line-to-vehicle and vehicle-capacity CSV files."""

from __future__ import annotations

import csv
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
            vehicles.append(VehicleType(name, capacity_100, capacity_85))

        return VehicleCatalog(
            vehicle_types=tuple(sorted(vehicles, key=lambda item: item.name.casefold())),
            line_assignments=line_assignments,
            prefix_assignments=prefix_assignments,
        )

    @staticmethod
    def _dict_rows(path: Path) -> list[dict[str, str]]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as source:
                return list(csv.DictReader(source))
        except OSError as error:
            raise SourceReadError(f"Could not read vehicle table {path}: {error}") from error
