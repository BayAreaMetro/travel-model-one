"""Read Network Wrangler background transit-network files."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from ..errors import SourceReadError, TranslationError
from .models import (
    AccessLink,
    BackgroundNetworkSource,
    SourceContext,
    TransferLink,
    TransitLinkControl,
    TransitOnlyLink,
)


_ATTRIBUTE = re.compile(r"(?i)\b([A-Z_][A-Z0-9_]*)\s*=")
_SOURCE_MARKER = re.compile(r"(?i)\bfrom\s*:\s*(.+?)\s*$")
_TRUE = frozenset({"Y", "YES", "T", "TRUE", "1"})
_FALSE = frozenset({"N", "NO", "F", "FALSE", "0"})


class BackgroundNetworkReader:
    """Read .access, .xfer, and .link as one conversion input."""

    def read(self, source_directory: Path) -> BackgroundNetworkSource:
        transit_only_links, transit_link_controls = self._read_transit_only(
            source_directory / "transitLines.link"
        )
        return BackgroundNetworkSource(
            access_links=self._read_access(source_directory / "transitLines.access"),
            transfer_links=self._read_transfer(source_directory / "transitLines.xfer"),
            transit_only_links=transit_only_links,
            transit_link_controls=transit_link_controls,
        )

    def _read_access(self, path: Path) -> tuple[AccessLink, ...]:
        records = self._plain_records(path)
        links: list[AccessLink] = []
        for fields, context in records:
            if len(fields) != 2:
                raise TranslationError(
                    f"Expected A B at {path.name}:{context.source_line}; "
                    f"found {len(fields)} values."
                )
            links.append(AccessLink(self._node(fields[0], path, context), self._node(fields[1], path, context), context))
        if not links:
            raise TranslationError(f"No access links were found in {path}.")
        return tuple(links)

    def _read_transfer(self, path: Path) -> tuple[TransferLink, ...]:
        records = self._plain_records(path)
        links: list[TransferLink] = []
        for fields, context in records:
            if len(fields) != 3:
                raise TranslationError(
                    f"Expected A B DISTANCE at {path.name}:{context.source_line}; "
                    f"found {len(fields)} values."
                )
            distance = self._decimal(fields[2], "DISTANCE", path, context, allow_zero=True)
            links.append(
                TransferLink(
                    self._node(fields[0], path, context),
                    self._node(fields[1], path, context),
                    distance,
                    context,
                )
            )
        if not links:
            raise TranslationError(f"No transfer links were found in {path}.")
        return tuple(links)

    def _read_transit_only(
        self, path: Path
    ) -> tuple[tuple[TransitOnlyLink, ...], tuple[TransitLinkControl, ...]]:
        lines = self._read_lines(path)
        pending: list[str] = []
        current_source = ""
        links: list[TransitOnlyLink] = []
        controls: list[TransitLinkControl] = []
        for number, raw in enumerate(lines, 1):
            code, separator, inline = raw.partition(";")
            code = code.strip()
            if not code:
                if separator:
                    comment = inline.strip()
                    pending.append(comment)
                    marker = _SOURCE_MARKER.search(comment)
                    if marker:
                        current_source = marker.group(1).strip()
                continue
            context = SourceContext(
                source_file=current_source,
                source_line=number,
                comment=inline.strip() if separator else "",
                leading_comments=tuple(pending),
            )
            pending.clear()
            record_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", code)
            if record_match is None:
                raise TranslationError(f"Invalid record at {path.name}:{number}: {code}")
            record_type = record_match.group(1).upper()
            attributes = self._attributes(code, path, number)
            if record_type != "LINK":
                controls.append(
                    TransitLinkControl(record_type, tuple(attributes.items()), context)
                )
                continue
            required = {"NODES", "DIST", "MODES", "ONEWAY"}
            missing = sorted(required - attributes.keys())
            if missing:
                raise TranslationError(
                    f"LINK at {path.name}:{number} is missing: {', '.join(missing)}"
                )
            nodes = self._nodes(attributes["NODES"], path, context)
            distance = self._decimal(
                attributes["DIST"], "DIST", path, context
            ) / Decimal(100)
            time = self._optional_decimal(attributes.get("TIME"), "TIME", path, context)
            speed = self._optional_decimal(attributes.get("SPEED"), "SPEED", path, context)
            if time is not None and speed is not None:
                raise TranslationError(
                    f"LINK at {path.name}:{number} defines both TIME and SPEED."
                )
            links.append(
                TransitOnlyLink(
                    a=nodes[0],
                    b=nodes[1],
                    distance_miles=distance,
                    modes=attributes["MODES"],
                    one_way=self._boolean(attributes["ONEWAY"], path, context),
                    time_minutes=time,
                    speed_mph=speed,
                    attributes=tuple(attributes.items()),
                    context=context,
                )
            )
        if not links:
            raise TranslationError(f"No LINK records were found in {path}.")
        return tuple(links), tuple(controls)

    def _plain_records(
        self, path: Path
    ) -> tuple[tuple[tuple[str, ...], SourceContext], ...]:
        lines = self._read_lines(path)
        records: list[tuple[tuple[str, ...], SourceContext]] = []
        pending: list[str] = []
        current_source = ""
        for number, raw in enumerate(lines, 1):
            code, separator, inline = raw.partition(";")
            code = code.strip()
            if not code:
                if separator:
                    comment = inline.strip()
                    pending.append(comment)
                    marker = _SOURCE_MARKER.search(comment)
                    if marker:
                        current_source = marker.group(1).strip()
                continue
            context = SourceContext(
                source_file=current_source,
                source_line=number,
                comment=inline.strip() if separator else "",
                leading_comments=tuple(pending),
            )
            pending.clear()
            records.append((tuple(code.split()), context))
        return tuple(records)

    @staticmethod
    def _read_lines(path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError as error:
            raise SourceReadError(f"Could not read background network file {path}: {error}") from error

    @staticmethod
    def _attributes(code: str, path: Path, number: int) -> dict[str, str]:
        matches = list(_ATTRIBUTE.finditer(code))
        values: dict[str, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(code)
            key = match.group(1).upper()
            value = code[match.end() : end].strip().rstrip(",").strip()
            if key in values:
                raise TranslationError(f"Repeated {key} at {path.name}:{number}.")
            values[key] = value
        return values

    def _nodes(
        self, value: str, path: Path, context: SourceContext
    ) -> tuple[int, int]:
        values = tuple(item.strip() for item in value.split(",") if item.strip())
        if len(values) != 2:
            raise TranslationError(
                f"Invalid NODES={value!r} at {path.name}:{context.source_line}."
            )
        return self._node(values[0], path, context), self._node(values[1], path, context)

    @staticmethod
    def _node(value: str, path: Path, context: SourceContext) -> int:
        try:
            node = int(value)
        except ValueError as error:
            raise TranslationError(
                f"Invalid node {value!r} at {path.name}:{context.source_line}."
            ) from error
        if node <= 0:
            raise TranslationError(
                f"Node must be positive at {path.name}:{context.source_line}."
            )
        return node

    @staticmethod
    def _decimal(
        value: str,
        keyword: str,
        path: Path,
        context: SourceContext,
        *,
        allow_zero: bool = False,
    ) -> Decimal:
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at {path.name}:{context.source_line}."
            ) from error
        if parsed < 0 or (parsed == 0 and not allow_zero):
            raise TranslationError(
                f"Invalid {keyword}={value!r} at {path.name}:{context.source_line}."
            )
        return parsed

    def _optional_decimal(
        self,
        value: str | None,
        keyword: str,
        path: Path,
        context: SourceContext,
    ) -> Decimal | None:
        if value is None:
            return None
        return self._decimal(value, keyword, path, context)

    @staticmethod
    def _boolean(value: str, path: Path, context: SourceContext) -> bool:
        normalized = value.strip().upper()
        if normalized in _TRUE:
            return True
        if normalized in _FALSE:
            return False
        raise TranslationError(
            f"Invalid ONEWAY={value!r} at {path.name}:{context.source_line}."
        )
