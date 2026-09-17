"""Parse Network Wrangler ancillary connector files."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from ..errors import SourceReadError, TranslationError
from .models import (
    ConnectorSource,
    PNRFacility,
    WalkAccessLeg,
    ZoneAccessRule,
)


_ATTRIBUTE = re.compile(r"(?i)\b([A-Z_]+)\s*=")
_PAIR = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
_PNR_FILES = {
    "transitLines_commuter_rail.pnr": "commuter_rail",
    "transitLines_express_bus.pnr": "express_bus",
    "transitLines_ferry.pnr": "ferry",
    "transitLines_heavy_rail.pnr": "heavy_rail",
    "transitLines_light_rail.pnr": "light_rail",
}


class ConnectorInputReader:
    """Read PT-specific ancillary inputs without constructing a network."""

    def read(self, source_directory: Path) -> ConnectorSource:
        return ConnectorSource(
            zone_access_rules=self._read_zone_access(source_directory / "transitLines.zac"),
            walk_access_legs=self._read_walk(source_directory / "WALK_access.sup"),
            pnr_facilities=self._read_pnr_files(source_directory),
        )

    def _read_zone_access(self, path: Path) -> tuple[ZoneAccessRule, ...]:
        records: list[ZoneAccessRule] = []
        for source_line, code, comment, leading_comments in self._active_records(path):
            if not re.match(r"(?i)^ZONEACCESS\b", code):
                self._invalid(path, source_line, code)
            values = self._attributes(code, path, source_line)
            self._require_exact(values, {"LINK", "MODE"}, path, source_line)
            a, b = self._pair(values["LINK"], "LINK", path, source_line)
            mode = self._positive_integer(values["MODE"], "MODE", path, source_line)
            if mode > 999:
                raise TranslationError(f"MODE must be 1-999 at {path.name}:{source_line}.")
            records.append(ZoneAccessRule(a, b, mode, source_line, comment, leading_comments))
        return tuple(records)

    def _read_walk(self, path: Path) -> tuple[WalkAccessLeg, ...]:
        records: list[WalkAccessLeg] = []
        required = {"N", "DIST", "MODE", "ONEWAY", "SPEED"}
        for source_line, code, comment, leading_comments in self._active_records(path):
            if not re.match(r"(?i)^SUPPLINK\b", code):
                self._invalid(path, source_line, code)
            values = self._attributes(code, path, source_line)
            self._require_exact(values, required, path, source_line)
            a, b = self._pair(values["N"], "N", path, source_line)
            distance = self._positive_integer(values["DIST"], "DIST", path, source_line)
            mode = self._positive_integer(values["MODE"], "MODE", path, source_line)
            if mode > 999:
                raise TranslationError(f"MODE must be 1-999 at {path.name}:{source_line}.")
            speed = self._positive_decimal(values["SPEED"], "SPEED", path, source_line)
            one_way = self._boolean(values["ONEWAY"], path, source_line)
            records.append(WalkAccessLeg(a, b, distance, mode, one_way, speed, source_line, comment, leading_comments))
        return tuple(records)

    def _read_pnr_files(self, source_directory: Path) -> tuple[PNRFacility, ...]:
        records: list[PNRFacility] = []
        for filename, category in _PNR_FILES.items():
            path = source_directory / filename
            for source_line, code, comment, leading_comments in self._active_records(path):
                if not re.match(r"(?i)^PNR\b", code):
                    self._invalid(path, source_line, code)
                values = self._attributes(code, path, source_line)
                unknown = set(values) - {"NODE", "ZONES", "TIME", "COST"}
                missing = {"NODE", "ZONES"} - set(values)
                if missing or unknown:
                    self._attribute_error(missing, unknown, path, source_line)
                facility, transit = self._pair(values["NODE"], "NODE", path, source_line)
                zones = self._zones(values["ZONES"], path, source_line)
                time = self._optional_decimal(values.get("TIME"), "TIME", path, source_line)
                if time is None:
                    time = Decimal("0.01")
                cost = self._optional_decimal(values.get("COST"), "COST", path, source_line)
                records.append(PNRFacility(category, facility, transit, zones, time, cost, filename, source_line, comment, leading_comments))
        return tuple(records)

    @staticmethod
    def _active_records(path: Path) -> tuple[tuple[int, str, str, tuple[str, ...]], ...]:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read connector file {path}: {error}") from error
        records: list[tuple[int, str, str, tuple[str, ...]]] = []
        pending_comments: list[str] = []
        in_block = False
        for source_line, raw in enumerate(lines, start=1):
            code_parts: list[str] = []
            position = 0
            while position < len(raw):
                if in_block:
                    end = raw.find("*/", position)
                    if end < 0:
                        position = len(raw)
                    else:
                        in_block = False
                        position = end + 2
                else:
                    start = raw.find("/*", position)
                    if start < 0:
                        code_parts.append(raw[position:])
                        position = len(raw)
                    else:
                        code_parts.append(raw[position:start])
                        in_block = True
                        position = start + 2
            code, _, comment = "".join(code_parts).partition(";")
            if code.strip():
                records.append((source_line, code.strip(), comment.strip(), tuple(pending_comments)))
                pending_comments.clear()
            elif comment.strip():
                pending_comments.append(";" + comment.rstrip())
        if in_block:
            raise TranslationError(f"Unclosed block comment in {path}.")
        return tuple(records)

    @staticmethod
    def _attributes(code: str, path: Path, source_line: int) -> dict[str, str]:
        matches = list(_ATTRIBUTE.finditer(code))
        values: dict[str, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
            key = match.group(1).upper()
            value = code[match.end():end].strip().rstrip(",").strip()
            if key in values:
                raise TranslationError(f"Repeated {key} at {path.name}:{source_line}.")
            values[key] = value
        return values

    @staticmethod
    def _nodes(values: list[str], path: Path, source_line: int) -> tuple[int, int]:
        try:
            a, b = (int(value) for value in values)
        except ValueError as error:
            raise TranslationError(f"Invalid nodes at {path.name}:{source_line}.") from error
        if a <= 0 or b <= 0 or a == b:
            raise TranslationError(f"Invalid nodes at {path.name}:{source_line}.")
        return a, b

    def _pair(self, value: str, keyword: str, path: Path, source_line: int) -> tuple[int, int]:
        match = _PAIR.match(value)
        if not match:
            raise TranslationError(f"Invalid {keyword}={value!r} at {path.name}:{source_line}.")
        return self._nodes([match.group(1), match.group(2)], path, source_line)

    @staticmethod
    def _positive_integer(value: str, keyword: str, path: Path, source_line: int) -> int:
        try:
            parsed = int(value)
        except ValueError as error:
            raise TranslationError(f"Invalid {keyword}={value!r} at {path.name}:{source_line}.") from error
        if parsed <= 0:
            raise TranslationError(f"{keyword} must be positive at {path.name}:{source_line}.")
        return parsed

    @staticmethod
    def _positive_decimal(value: str, keyword: str, path: Path, source_line: int) -> Decimal:
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise TranslationError(f"Invalid {keyword}={value!r} at {path.name}:{source_line}.") from error
        if parsed <= 0:
            raise TranslationError(f"{keyword} must be positive at {path.name}:{source_line}.")
        return parsed

    def _optional_decimal(self, value: str | None, keyword: str, path: Path, source_line: int) -> Decimal | None:
        if value is None:
            return None
        return self._positive_decimal(value, keyword, path, source_line)

    @staticmethod
    def _boolean(value: str, path: Path, source_line: int) -> bool:
        normalized = value.upper()
        if normalized in {"Y", "YES", "T", "TRUE", "1"}:
            return True
        if normalized in {"N", "NO", "F", "FALSE", "0"}:
            return False
        raise TranslationError(f"Invalid ONEWAY={value!r} at {path.name}:{source_line}.")

    @staticmethod
    def _zones(value: str, path: Path, source_line: int) -> str:
        compact = re.sub(r"\s+", "", value)
        for item in compact.split(","):
            match = re.fullmatch(r"(\d+)(?:-(\d+))?", item)
            if not match or int(match.group(1)) <= 0 or (match.group(2) and int(match.group(1)) > int(match.group(2))):
                raise TranslationError(f"Invalid ZONES={value!r} at {path.name}:{source_line}.")
        return compact

    @staticmethod
    def _require_exact(values: dict[str, str], required: set[str], path: Path, source_line: int) -> None:
        missing = required - set(values)
        unknown = set(values) - required
        if missing or unknown:
            ConnectorInputReader._attribute_error(missing, unknown, path, source_line)

    @staticmethod
    def _attribute_error(missing: set[str], unknown: set[str], path: Path, source_line: int) -> None:
        details = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unsupported " + ", ".join(sorted(unknown)))
        raise TranslationError(f"Invalid attributes at {path.name}:{source_line}: {'; '.join(details)}.")

    @staticmethod
    def _invalid(path: Path, source_line: int, code: str) -> None:
        raise TranslationError(f"Unsupported record at {path.name}:{source_line}: {code}")
