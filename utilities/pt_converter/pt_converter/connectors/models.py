"""Source-neutral records for transit access and transfer inputs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True, slots=True)
class ZoneAccessRule:
    """A zone-access funnel leg read from a Network Wrangler ZAC record."""

    from_node: int
    to_node: int
    mode: int
    source_line: int
    comment: str = ""
    leading_comments: tuple[str, ...] = ()

    @property
    def cost_minutes(self) -> Decimal:
        return Decimal("1.00")

    @property
    def distance_miles(self) -> Decimal:
        return self.cost_minutes * Decimal(3) / Decimal(60)


@dataclass(frozen=True, slots=True)
class WalkAccessLeg:
    """An explicit walk leg that has enough information for a PT NT record."""

    from_node: int
    to_node: int
    distance_hundredths_mile: int
    mode: int
    one_way: bool
    speed_mph: Decimal
    source_line: int
    comment: str = ""
    leading_comments: tuple[str, ...] = ()

    @property
    def distance_miles(self) -> Decimal:
        return Decimal(self.distance_hundredths_mile) / Decimal(100)

    @property
    def cost_minutes(self) -> Decimal:
        minutes = self.distance_miles / self.speed_mph * Decimal(60)
        return minutes.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PNRFacility:
    """A park-and-ride funnel leg read from a Network Wrangler PNR record."""

    category: str
    facility_node: int
    transit_node: int
    zones: str
    time_minutes: Decimal
    cost: Decimal | None
    source_file: str
    source_line: int
    comment: str = ""
    leading_comments: tuple[str, ...] = ()

    @property
    def distance_miles(self) -> Decimal:
        """Infer distance using TM1's three-mile-per-hour walk speed."""

        inferred = self.time_minutes * Decimal(3) / Decimal(60)
        return max(inferred, Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class ConnectorSource:
    """Ancillary records that must be prepared for PT."""

    zone_access_rules: tuple[ZoneAccessRule, ...]
    walk_access_legs: tuple[WalkAccessLeg, ...]
    pnr_facilities: tuple[PNRFacility, ...]
