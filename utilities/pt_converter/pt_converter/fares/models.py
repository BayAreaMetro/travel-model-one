"""Source-neutral fare records used by the PT converter."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ODFare:
    """One legacy stop-to-stop fare."""

    from_node: int
    to_node: int
    fare: Decimal
    one_way: bool
    source_file: str
    source_line: int
    comment: str = ""


@dataclass(frozen=True, slots=True)
class ODFareTable:
    """All OD fares read from one legacy fare file."""

    source_file: str
    records: tuple[ODFare, ...]


@dataclass(frozen=True, slots=True)
class FareSource:
    """Legacy mode fares, OD tables, and fare-link inventory."""

    xfare: tuple[tuple[Decimal, ...], ...]
    od_file_by_mode: dict[int, str]
    od_tables: tuple[ODFareTable, ...]
    farelink_record_count: int
    farelink_modes: tuple[int, ...]

    def od_table(self, filename: str) -> ODFareTable:
        return next(table for table in self.od_tables if table.source_file == filename)
