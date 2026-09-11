"""Transit line and vehicle information independent of file syntax."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TransitLine:
    """One transit service read from a Network Wrangler line file."""

    name: str
    mode: int
    operator: int | None
    headways: tuple[Decimal, Decimal, Decimal, Decimal, Decimal]
    one_way: bool
    nodes: tuple[int, ...]
    node_text: str
    color: int | None = None
    long_name: str | None = None
    runtime: Decimal | None = None
    source_line: int = 0
    comments_before: tuple[str, ...] = ()
    comments_within: tuple[str, ...] = ()
    comments_after: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TransitMode:
    """A published TM1 transit mode name and category."""

    number: int
    short_name: str
    name: str
    category: str


@dataclass(frozen=True, slots=True)
class TransitOperator:
    """A PT operator number with short and descriptive names."""

    number: int
    short_name: str
    name: str


@dataclass(frozen=True, slots=True)
class VehicleType:
    """A PT vehicle type and the capacities available from TM1."""

    name: str
    capacity_100_percent: int
    capacity_85_percent: int
    short_name: str
    long_name: str


@dataclass(frozen=True, slots=True)
class LineVehicleAssignment:
    """Vehicle names assigned to a line for peak and off-peak service."""

    line_name: str
    system: str
    am_vehicle: str
    pm_vehicle: str
    off_peak_vehicle: str


@dataclass(frozen=True, slots=True)
class PrefixVehicleAssignment:
    """Fallback vehicle assignment selected from a line-name prefix."""

    prefix: str
    system: str
    vehicle: str


@dataclass(frozen=True, slots=True)
class VehicleCatalog:
    """All vehicle definitions and line-to-vehicle lookup rules."""

    vehicle_types: tuple[VehicleType, ...]
    line_assignments: tuple[LineVehicleAssignment, ...]
    prefix_assignments: tuple[PrefixVehicleAssignment, ...]

    def vehicle_names_by_period(self, line_name: str) -> tuple[str, str, str]:
        """Return AM, PM, and off-peak vehicle names, using prefix fallback."""

        key = line_name.casefold()
        exact = next(
            (item for item in self.line_assignments if item.line_name.casefold() == key),
            None,
        )
        if exact is not None:
            return (
                exact.am_vehicle,
                exact.pm_vehicle,
                exact.off_peak_vehicle,
            )

        candidates = sorted(
            self.prefix_assignments, key=lambda item: len(item.prefix), reverse=True
        )
        match = next(
            (item for item in candidates if key.startswith(item.prefix.casefold())),
            None,
        )
        vehicle = match.vehicle if match is not None else ""
        return (vehicle, vehicle, vehicle)

    def vehicle_names_for_line(self, line_name: str) -> tuple[str, ...]:
        """Return the distinct nonempty vehicle names used by a line."""

        return tuple(
            dict.fromkeys(
                name for name in self.vehicle_names_by_period(line_name) if name
            )
        )
