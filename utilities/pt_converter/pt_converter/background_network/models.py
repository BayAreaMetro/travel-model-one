"""Typed records for the background transit-network source files."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SourceContext:
    """Comments and location retained from one source record."""

    source_file: str
    source_line: int
    comment: str = ""
    leading_comments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AccessLink:
    """One bidirectional link from transitLines.access."""

    a: int
    b: int
    context: SourceContext


@dataclass(frozen=True, slots=True)
class TransferLink:
    """One bidirectional link from transitLines.xfer."""

    a: int
    b: int
    distance_miles: Decimal
    context: SourceContext


@dataclass(frozen=True, slots=True)
class TransitOnlyLink:
    """One LINK statement from transitLines.link before direction expansion."""

    a: int
    b: int
    distance_miles: Decimal
    modes: str
    one_way: bool
    time_minutes: Decimal | None
    speed_mph: Decimal | None
    attributes: tuple[tuple[str, str], ...]
    context: SourceContext


@dataclass(frozen=True, slots=True)
class TransitLinkControl:
    """A non-LINK control statement retained from transitLines.link."""

    record_type: str
    attributes: tuple[tuple[str, str], ...]
    context: SourceContext


@dataclass(frozen=True, slots=True)
class BackgroundNetworkSource:
    """All three finalized Network Wrangler background-network inputs."""

    access_links: tuple[AccessLink, ...]
    transfer_links: tuple[TransferLink, ...]
    transit_only_links: tuple[TransitOnlyLink, ...]
    transit_link_controls: tuple[TransitLinkControl, ...]
