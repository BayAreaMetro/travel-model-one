"""Parse the TRNBUILD fare inputs used by TM1."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path, PureWindowsPath
import re

from ..errors import SourceReadError, ValidationError
from .models import FareSource, ODFare, ODFareTable


_XFARE = re.compile(r"^\s*XFARE\[(\d+)\]\s*=\s*(.*?)\s*$", re.IGNORECASE)
_FAREMATI = re.compile(r"FAREMATI\[(\d+)\]\s*=\s*[\"']?([^\"']+)", re.IGNORECASE)
_FARELINK_MODES = re.compile(
    r"\bMODES\s*=\s*(.*?)(?=\s+ONEWAY\b|\s*$)", re.IGNORECASE
)


class FareInputReader:
    """Read mode-to-mode fares and referenced OD fare tables."""

    def read(self, source_directory: Path, used_transit_modes: set[int]) -> FareSource:
        xfare = self._read_xfare(source_directory / "xfare.far")
        if not used_transit_modes:
            raise ValidationError("No transit modes are available for fare conversion.")
        if min(used_transit_modes) < 10:
            raise ValidationError("Fare systems may only be assigned to transit modes 10 and above.")
        highest_mode = max(used_transit_modes)
        if len(xfare) < highest_mode or any(len(row) < highest_mode for row in xfare):
            raise ValidationError(
                f"xfare.far does not cover the highest used transit mode {highest_mode}."
            )
        self._validate_initial_fares(xfare, used_transit_modes)

        od_file_by_mode = self._read_faremat_block(
            source_directory / "transit_faremat.block"
        )
        referenced_files = sorted(
            {filename for mode, filename in od_file_by_mode.items() if mode in used_transit_modes}
        )
        od_tables = tuple(
            self._read_od_table(source_directory / filename) for filename in referenced_files
        )
        farelink_count, farelink_modes = self._read_farelinks(
            source_directory / "farelinks.far"
        )
        return FareSource(
            xfare=xfare,
            od_file_by_mode=od_file_by_mode,
            od_tables=od_tables,
            farelink_record_count=farelink_count,
            farelink_modes=tuple(sorted(farelink_modes)),
        )

    @staticmethod
    def _read_xfare(path: Path) -> tuple[tuple[Decimal, ...], ...]:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read transfer fares {path}: {error}") from error
        rows: dict[int, tuple[Decimal, ...]] = {}
        for source_line, line in enumerate(lines, 1):
            data = line.split(";", 1)[0].strip()
            if not data:
                continue
            match = _XFARE.match(data)
            if match is None:
                raise ValidationError(f"Invalid XFARE record at {path.name}:{source_line}.")
            row_number = int(match.group(1))
            if row_number in rows:
                raise ValidationError(f"Duplicate XFARE row {row_number} in {path.name}.")
            rows[row_number] = tuple(_expand_values(match.group(2), path, source_line))
        if not rows:
            raise ValidationError(f"No XFARE records found in {path}.")
        expected = list(range(1, max(rows) + 1))
        if sorted(rows) != expected:
            raise ValidationError(f"XFARE rows in {path.name} must be consecutive from 1.")
        return tuple(rows[number] for number in expected)

    @staticmethod
    def _validate_initial_fares(
        xfare: tuple[tuple[Decimal, ...], ...], used_modes: set[int]
    ) -> None:
        access_modes = (1, 2, 4, 5, 6, 7)
        for transit_mode in sorted(used_modes):
            values = {xfare[mode - 1][transit_mode - 1] for mode in access_modes}
            if len(values) != 1:
                rendered = ", ".join(
                    f"mode {mode}={xfare[mode - 1][transit_mode - 1]}"
                    for mode in access_modes
                )
                raise ValidationError(
                    f"Initial fare for transit mode {transit_mode} varies by NT access mode: "
                    f"{rendered}. PT IBOARDFARE cannot represent this."
                )

    @staticmethod
    def _read_faremat_block(path: Path) -> dict[int, str]:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read fare-matrix block {path}: {error}") from error
        result: dict[int, str] = {}
        for source_line, line in enumerate(lines, 1):
            data = line.split(";", 1)[0].strip()
            if not data:
                continue
            match = _FAREMATI.search(data)
            if match is None:
                raise ValidationError(f"Invalid FAREMATI record at {path.name}:{source_line}.")
            mode = int(match.group(1))
            filename = PureWindowsPath(match.group(2).strip()).name
            if mode in result:
                raise ValidationError(f"Duplicate FAREMATI mode {mode} in {path.name}.")
            result[mode] = filename
        return result

    @staticmethod
    def _read_od_table(path: Path) -> ODFareTable:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read OD fare table {path}: {error}") from error
        records: list[ODFare] = []
        for source_line, line in enumerate(lines, 1):
            data, _, comment = line.partition(";")
            data = data.strip()
            if not data:
                continue
            fields = [field for field in re.split(r"[\s,]+", data) if field]
            if len(fields) not in (3, 4):
                raise ValidationError(f"Invalid OD fare at {path.name}:{source_line}.")
            try:
                from_node = int(fields[0])
                to_node = int(fields[1])
                fare = Decimal(fields[2])
                direction = int(fields[3]) if len(fields) == 4 else 0
            except (ValueError, InvalidOperation) as error:
                raise ValidationError(
                    f"Invalid OD fare value at {path.name}:{source_line}."
                ) from error
            records.append(
                ODFare(
                    from_node,
                    to_node,
                    fare,
                    one_way=direction == 1,
                    source_file=path.name,
                    source_line=source_line,
                    comment=comment.strip(),
                )
            )
        if not records:
            raise ValidationError(f"No OD fare records found in {path}.")
        return ODFareTable(path.name, tuple(records))

    @staticmethod
    def _read_farelinks(path: Path) -> tuple[int, set[int]]:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read fare links {path}: {error}") from error
        count = 0
        modes: set[int] = set()
        for source_line, line in enumerate(lines, 1):
            data = line.split(";", 1)[0].strip()
            if not data:
                continue
            if not data.upper().startswith("FARELINKS"):
                raise ValidationError(f"Invalid FARELINKS record at {path.name}:{source_line}.")
            match = _FARELINK_MODES.search(data)
            if match is None:
                raise ValidationError(f"Missing MODES at {path.name}:{source_line}.")
            modes.update(int(value) for value in re.findall(r"\d+", match.group(1)))
            count += 1
        return count, modes


def _expand_values(value_text: str, path: Path, source_line: int) -> list[Decimal]:
    values: list[Decimal] = []
    try:
        for token in value_text.split(","):
            token = token.strip()
            if not token:
                continue
            if "*" in token:
                count_text, value = token.split("*", 1)
                values.extend([Decimal(value.strip())] * int(count_text.strip()))
            else:
                values.append(Decimal(token))
    except (ValueError, InvalidOperation) as error:
        raise ValidationError(f"Invalid fare value at {path.name}:{source_line}.") from error
    return values
