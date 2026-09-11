"""Parse Network Wrangler's transitLines.link control statements."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from ..errors import SourceReadError, TranslationError
from .models import TransitLink, TransitLinkFactor, TransitLinkSource


_ATTRIBUTE = re.compile(r"(?i)\b([A-Z_]+)\s*=")
_LINK = re.compile(r"(?i)^LINK\b")
_FACTOR = re.compile(r"(?i)^FACTOR\b")


class TransitLinkReader:
    """Turn LINK and supported FACTOR records into typed objects."""

    def read(self, path: Path) -> TransitLinkSource:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read transit link file {path}: {error}") from error

        links: list[TransitLink] = []
        factors: list[TransitLinkFactor] = []
        for source_line, raw in enumerate(lines, start=1):
            code, _, comment = raw.partition(";")
            code = code.strip()
            if not code:
                continue
            attributes = self._attributes(code, source_line)
            if _LINK.match(code):
                links.append(self._link(attributes, source_line, comment.strip()))
            elif _FACTOR.match(code):
                factors.append(self._factor(attributes, source_line))
            else:
                raise TranslationError(
                    f"Unsupported record at {path.name}:{source_line}: {code}"
                )

        if not links:
            raise TranslationError(f"No LINK records were found in {path}.")
        return TransitLinkSource(tuple(links), tuple(factors))

    @staticmethod
    def _attributes(code: str, source_line: int) -> dict[str, str]:
        matches = list(_ATTRIBUTE.finditer(code))
        values: dict[str, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
            value = code[match.end() : end].strip().rstrip(",").strip()
            key = match.group(1).upper()
            if key in values:
                raise TranslationError(
                    f"Repeated {key} attribute at transitLines.link:{source_line}."
                )
            values[key] = value
        return values

    def _link(
        self, values: dict[str, str], source_line: int, comment: str
    ) -> TransitLink:
        required = {"NODES", "DIST", "MODES", "ONEWAY"}
        missing = sorted(required - values.keys())
        unknown = sorted(values.keys() - required - {"TIME", "SPEED"})
        if missing:
            raise TranslationError(
                f"LINK at transitLines.link:{source_line} is missing: {', '.join(missing)}"
            )
        if unknown:
            raise TranslationError(
                f"LINK at transitLines.link:{source_line} has unsupported attributes: "
                + ", ".join(unknown)
            )
        if ("TIME" in values) == ("SPEED" in values):
            raise TranslationError(
                f"LINK at transitLines.link:{source_line} must define exactly one of TIME or SPEED."
            )

        nodes = self._integer_list(values["NODES"], "NODES", source_line)
        if len(nodes) != 2 or any(node <= 0 for node in nodes) or nodes[0] == nodes[1]:
            raise TranslationError(
                f"Invalid NODES={values['NODES']!r} at transitLines.link:{source_line}."
            )
        distance = self._positive_integer(values["DIST"], "DIST", source_line)
        modes = self._modes(values["MODES"], source_line)
        one_way = self._boolean(values["ONEWAY"], source_line)
        time = self._positive_decimal(values.get("TIME"), "TIME", source_line)
        speed = self._positive_decimal(values.get("SPEED"), "SPEED", source_line)
        return TransitLink(
            from_node=nodes[0],
            to_node=nodes[1],
            distance_hundredths_mile=distance,
            modes=modes,
            one_way=one_way,
            time_minutes=time,
            speed_mph=speed,
            source_line=source_line,
            comment=comment,
        )

    def _factor(self, values: dict[str, str], source_line: int) -> TransitLinkFactor:
        if set(values) != {"MAXWAITTIME", "NODES"}:
            raise TranslationError(
                f"Unsupported FACTOR attributes at transitLines.link:{source_line}: "
                + ", ".join(sorted(values))
            )
        wait = self._positive_decimal(values["MAXWAITTIME"], "MAXWAITTIME", source_line)
        assert wait is not None
        nodes = self._integer_list(values["NODES"], "NODES", source_line)
        if not nodes or any(node <= 0 for node in nodes):
            raise TranslationError(
                f"Invalid FACTOR NODES at transitLines.link:{source_line}."
            )
        return TransitLinkFactor(wait, nodes, source_line)

    @staticmethod
    def _integer_list(value: str, keyword: str, source_line: int) -> tuple[int, ...]:
        try:
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        except ValueError as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at transitLines.link:{source_line}."
            ) from error

    def _modes(self, value: str, source_line: int) -> tuple[int, ...]:
        modes: list[int] = []
        for item in value.split(","):
            item = item.strip()
            try:
                if "-" in item:
                    first_text, last_text = item.split("-", 1)
                    first, last = int(first_text), int(last_text)
                    if first > last:
                        raise ValueError
                    modes.extend(range(first, last + 1))
                else:
                    modes.append(int(item))
            except ValueError as error:
                raise TranslationError(
                    f"Invalid MODES={value!r} at transitLines.link:{source_line}."
                ) from error
        unique = tuple(dict.fromkeys(modes))
        if not unique or any(not 1 <= mode <= 999 for mode in unique):
            raise TranslationError(
                f"Invalid MODES={value!r} at transitLines.link:{source_line}."
            )
        return unique

    @staticmethod
    def _positive_integer(value: str, keyword: str, source_line: int) -> int:
        try:
            parsed = int(value)
        except ValueError as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at transitLines.link:{source_line}."
            ) from error
        if parsed <= 0:
            raise TranslationError(
                f"{keyword} must be positive at transitLines.link:{source_line}."
            )
        return parsed

    @staticmethod
    def _positive_decimal(
        value: str | None, keyword: str, source_line: int
    ) -> Decimal | None:
        if value is None:
            return None
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at transitLines.link:{source_line}."
            ) from error
        if parsed <= 0:
            raise TranslationError(
                f"{keyword} must be positive at transitLines.link:{source_line}."
            )
        return parsed

    @staticmethod
    def _boolean(value: str, source_line: int) -> bool:
        normalized = value.strip().upper()
        if normalized in {"Y", "YES", "T", "TRUE", "1"}:
            return True
        if normalized in {"N", "NO", "F", "FALSE", "0"}:
            return False
        raise TranslationError(
            f"Invalid ONEWAY={value!r} at transitLines.link:{source_line}."
        )
