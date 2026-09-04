"""Source-neutral records for transit-only physical links."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TransitLink:
    """One LINK statement, before expanding its direction or mode list."""

    from_node: int
    to_node: int
    distance_hundredths_mile: int
    modes: tuple[int, ...]
    one_way: bool
    time_minutes: Decimal | None
    speed_mph: Decimal | None
    source_line: int
    comment: str = ""

    @property
    def distance_miles(self) -> Decimal:
        return Decimal(self.distance_hundredths_mile) / Decimal(100)


@dataclass(frozen=True, slots=True)
class DirectedTransitLink:
    """A transit link in one permitted travel direction."""

    from_node: int
    to_node: int
    distance_hundredths_mile: int
    modes: tuple[int, ...]
    time_minutes: Decimal | None
    speed_mph: Decimal | None
    source_line: int
    generated_reverse: bool

    @property
    def distance_miles(self) -> Decimal:
        return Decimal(self.distance_hundredths_mile) / Decimal(100)


@dataclass(frozen=True, slots=True)
class TransitLinkFactor:
    """A non-LINK control record found in the physical-link source file."""

    max_wait_time: Decimal
    nodes: tuple[int, ...]
    source_line: int


@dataclass(frozen=True, slots=True)
class TransitLinkSource:
    """Everything parsed from transitLines.link."""

    links: tuple[TransitLink, ...]
    factors: tuple[TransitLinkFactor, ...]

    def directed_links(self) -> tuple[DirectedTransitLink, ...]:
        directed: list[DirectedTransitLink] = []
        for link in self.links:
            directed.append(
                DirectedTransitLink(
                    link.from_node,
                    link.to_node,
                    link.distance_hundredths_mile,
                    link.modes,
                    link.time_minutes,
                    link.speed_mph,
                    link.source_line,
                    False,
                )
            )
            if not link.one_way:
                directed.append(
                    DirectedTransitLink(
                        link.to_node,
                        link.from_node,
                        link.distance_hundredths_mile,
                        link.modes,
                        link.time_minutes,
                        link.speed_mph,
                        link.source_line,
                        True,
                    )
                )
        return tuple(directed)

