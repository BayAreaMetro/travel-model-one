"""Parse Network Wrangler's TRNBUILD-compatible transit line file."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import cast

from ..errors import SourceReadError, TranslationError
from .models import TransitLine


_LINE_START = re.compile(r"(?im)^[ \t]*LINE[ \t]+NAME[ \t]*=")
_STATEMENT_END = re.compile(r"\r?\n[ \t]*\r?\n")


class TransitLineReader:
    """Turn explicit Network Wrangler LINE statements into transit objects."""

    def read(self, path: Path) -> tuple[TransitLine, ...]:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as error:
            raise SourceReadError(f"Could not read transit line file {path}: {error}") from error

        starts = list(_LINE_START.finditer(text))
        lines: list[TransitLine] = []
        for start in starts:
            remainder = text[start.start() :]
            end = _STATEMENT_END.search(remainder)
            statement = remainder[: end.start()] if end else remainder
            source_line = text.count("\n", 0, start.start()) + 1
            lines.append(self._parse_statement(statement, source_line))
        return tuple(lines)

    def _parse_statement(self, statement: str, source_line: int) -> TransitLine:
        name = self._required_string(statement, "NAME", source_line)
        mode = self._required_integer(statement, "MODE", source_line)
        owner = self._optional_integer(statement, "OWNER", source_line)
        color = self._optional_integer(statement, "COLOR", source_line)
        long_name = self._optional_string(statement, "LONGNAME")
        runtime = self._optional_decimal(statement, "RUNTIME", source_line)
        one_way_value = self._optional_string(statement, "ONEWAY") or "T"
        one_way = one_way_value.strip().upper() in {"T", "Y", "TRUE", "YES", "1"}

        headways = cast(tuple[Decimal, Decimal, Decimal, Decimal, Decimal], tuple(
            self._required_decimal(statement, f"FREQ[{period}]", source_line)
            for period in range(1, 6)
        ))
        node_match = re.search(r"(?im)^[ \t]*N(?:ODES)?[ \t]*=", statement)
        if node_match is None:
            raise TranslationError(f"Line {name!r} at source line {source_line} has no nodes.")
        node_text = statement[node_match.start() :].strip()
        nodes = self._read_nodes(node_text)
        if len([node for node in nodes if node > 0]) < 2:
            raise TranslationError(
                f"Line {name!r} at source line {source_line} must have at least two stop nodes."
            )

        return TransitLine(
            name=name,
            mode=mode,
            operator=owner,
            headways=headways,
            one_way=one_way,
            nodes=nodes,
            node_text=node_text,
            color=color,
            long_name=long_name,
            runtime=runtime,
            source_line=source_line,
        )

    @staticmethod
    def _read_nodes(node_text: str) -> tuple[int, ...]:
        token_pattern = re.compile(r"(?i)\b(N(?:ODES)?|ACCESS_C|ACCESS)\s*=|(?<![A-Z0-9_])-?\d+")
        reading_nodes = False
        nodes: list[int] = []
        for match in token_pattern.finditer(node_text):
            keyword = match.group(1)
            if keyword:
                reading_nodes = keyword.upper() in {"N", "NODES"}
            elif reading_nodes:
                nodes.append(int(match.group(0)))
        return tuple(nodes)

    @staticmethod
    def _match_value(statement: str, keyword: str) -> re.Match[str] | None:
        escaped = re.escape(keyword)
        return re.search(
            rf'(?i)(?<![A-Z0-9_]){escaped}\s*=\s*(?:"([^"]*)"|([^,\s]+))',
            statement,
        )

    def _required_string(self, statement: str, keyword: str, source_line: int) -> str:
        value = self._optional_string(statement, keyword)
        if value is None or not value:
            raise TranslationError(
                f"LINE statement at source line {source_line} is missing {keyword}."
            )
        return value

    def _optional_string(self, statement: str, keyword: str) -> str | None:
        match = self._match_value(statement, keyword)
        return (match.group(1) if match.group(1) is not None else match.group(2)) if match else None

    def _required_integer(self, statement: str, keyword: str, source_line: int) -> int:
        value = self._optional_integer(statement, keyword, source_line)
        if value is None:
            raise TranslationError(
                f"LINE statement at source line {source_line} is missing {keyword}."
            )
        return value

    def _optional_integer(
        self, statement: str, keyword: str, source_line: int
    ) -> int | None:
        value = self._optional_string(statement, keyword)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at source line {source_line}."
            ) from error

    def _required_decimal(self, statement: str, keyword: str, source_line: int) -> Decimal:
        value = self._optional_decimal(statement, keyword, source_line)
        if value is None:
            raise TranslationError(
                f"LINE statement at source line {source_line} is missing {keyword}."
            )
        return value

    def _optional_decimal(
        self, statement: str, keyword: str, source_line: int
    ) -> Decimal | None:
        value = self._optional_string(statement, keyword)
        if value is None:
            return None
        try:
            return Decimal(value)
        except InvalidOperation as error:
            raise TranslationError(
                f"Invalid {keyword}={value!r} at source line {source_line}."
            ) from error
