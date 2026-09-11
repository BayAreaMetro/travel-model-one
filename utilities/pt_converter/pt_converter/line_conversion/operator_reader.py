"""Read PT operator names supplied with the model transit inputs."""

from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path

from ..errors import SourceReadError, TranslationError
from .models import TransitOperator


class TransitOperatorReader:
    """Load unique operator numbers and PT-compatible short names."""

    def read(self, path: Path) -> tuple[TransitOperator, ...]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.DictReader(source))
        except OSError as error:
            raise SourceReadError(
                f"Could not read transit operator table {path}: {error}"
            ) from error

        expected = {"operator_number", "short_name", "operator_name"}
        if not rows or set(rows[0]) != expected:
            raise TranslationError(
                f"Transit operator table {path} must contain exactly: "
                + ", ".join(sorted(expected))
            )

        operators: list[TransitOperator] = []
        for source_line, row in enumerate(rows, start=2):
            try:
                number = int(row["operator_number"])
            except (TypeError, ValueError) as error:
                raise TranslationError(
                    f"Invalid operator_number at {path.name}:{source_line}."
                ) from error
            short_name = row["short_name"].strip()
            name = row["operator_name"].strip()
            if not 1 <= number <= 999 or not short_name or not name:
                raise TranslationError(
                    f"Invalid transit operator at {path.name}:{source_line}."
                )
            if len(short_name) > 14:
                raise TranslationError(
                    f"short_name {short_name!r} exceeds 14 characters at "
                    f"{path.name}:{source_line}."
                )
            operators.append(TransitOperator(number, short_name, name))

        number_counts = Counter(operator.number for operator in operators)
        short_name_counts = Counter(
            operator.short_name.casefold() for operator in operators
        )
        duplicate_numbers = sorted(
            number for number, count in number_counts.items() if count > 1
        )
        duplicate_short_names = sorted(
            name for name, count in short_name_counts.items() if count > 1
        )
        problems: list[str] = []
        if duplicate_numbers:
            problems.append(
                "duplicate operator_number value(s): "
                + ", ".join(str(number) for number in duplicate_numbers)
            )
        if duplicate_short_names:
            original_names = {
                operator.short_name.casefold(): operator.short_name
                for operator in operators
            }
            problems.append(
                "duplicate short_name value(s): "
                + ", ".join(
                    repr(original_names[name]) for name in duplicate_short_names
                )
            )
        if problems:
            raise TranslationError(
                f"Invalid transit operator table {path}: "
                + "; ".join(problems)
                + "."
            )
        return tuple(operators)
