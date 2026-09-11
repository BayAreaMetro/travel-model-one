"""Read the published TM1 transit-mode lookup table."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from ..errors import SourceReadError, TranslationError
from .models import TransitMode


class TransitModeReader:
    """Load unique mode numbers and their human-readable names."""

    def read(self, path: Path) -> tuple[TransitMode, ...]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
        except OSError as error:
            raise SourceReadError(f"Could not read transit mode table {path}: {error}") from error

        expected = {"mode_number", "short_name", "mode_name", "mode_category"}
        if not rows or set(rows[0]) != expected:
            raise TranslationError(
                f"Transit mode table {path} must contain exactly: "
                + ", ".join(sorted(expected))
            )

        modes: list[TransitMode] = []
        for source_line, row in enumerate(rows, start=2):
            try:
                number = int(row["mode_number"])
            except (TypeError, ValueError) as error:
                raise TranslationError(
                    f"Invalid mode_number at {path.name}:{source_line}."
                ) from error
            short_name = row["short_name"].strip()
            name = row["mode_name"].strip()
            category = row["mode_category"].strip()
            if not 1 <= number <= 999 or not short_name or not name or not category:
                raise TranslationError(f"Invalid transit mode at {path.name}:{source_line}.")
            if len(short_name) > 14:
                raise TranslationError(
                    f"short_name {short_name!r} exceeds 14 characters at "
                    f"{path.name}:{source_line}."
                )
            modes.append(TransitMode(number, short_name, name, category))

        number_counts = Counter(mode.number for mode in modes)
        short_name_counts = Counter(mode.short_name.casefold() for mode in modes)
        duplicate_numbers = sorted(
            number for number, count in number_counts.items() if count > 1
        )
        duplicate_short_names = sorted(
            name for name, count in short_name_counts.items() if count > 1
        )
        problems: list[str] = []
        if duplicate_numbers:
            problems.append(
                "duplicate mode_number value(s): "
                + ", ".join(str(number) for number in duplicate_numbers)
            )
        if duplicate_short_names:
            original_names = {
                mode.short_name.casefold(): mode.short_name for mode in modes
            }
            problems.append(
                "duplicate short_name value(s): "
                + ", ".join(
                    repr(original_names[name]) for name in duplicate_short_names
                )
            )
        if problems:
            raise TranslationError(
                f"Invalid transit mode table {path}: " + "; ".join(problems) + "."
            )
        return tuple(modes)
