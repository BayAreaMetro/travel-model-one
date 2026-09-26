"""Source-neutral data used to write PT factor files."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ModeFactor:
    """A contiguous range of modes with one perceived run-time factor."""

    first_mode: int
    last_mode: int
    factor: Decimal

    @property
    def count(self) -> int:
        return self.last_mode - self.first_mode + 1


@dataclass(frozen=True, slots=True)
class FactorClass:
    """The factor settings for one PT assignment user class."""

    number: int
    access: str
    path: str
    egress: str
    run_factors: tuple[ModeFactor, ...]
    deleted_modes: tuple[tuple[int, int], ...]
    deleted_access_modes: tuple[int, ...]
    deleted_egress_modes: tuple[int, ...]

    @property
    def name(self) -> str:
        return f"{self.access}_{self.path}_{self.egress}"


@dataclass(frozen=True, slots=True)
class FactorSource:
    """All reusable TM1 user classes and common wait assumptions."""

    classes: tuple[FactorClass, ...]
    wait_factor: Decimal
    wait_curve: int
