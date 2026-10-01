"""Read the transit files produced by Network Wrangler."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re

from ..errors import SourceReadError
from .models import (
    IssueSeverity,
    SourceFile,
    SourceInventory,
    TransitLineRecord,
    TransitLineSummary,
    ValidationIssue,
)


_KNOWN_FILE_TYPES = {
    "transitlines.lin": "transit_lines",
    "transitlines.link": "transit_links",
    "transitlines.access": "walk_access_connectors",
    "transitlines.xfer": "transfer_connectors",
    "transitlines.zac": "zone_access_connectors",
    "walk_access.sup": "walk_access_support",
    "transit_support_nodes.dat": "transit_support_nodes",
}

_LINE_START = re.compile(r"(?im)^[ \t]*LINE[ \t]+NAME[ \t]*=")
_NAME = re.compile(r'(?i)\bNAME\s*=\s*(?:"([^"]+)"|([^,\s]+))')
_MODE = re.compile(r"(?i)\bMODE\s*=\s*(-?\d+)")
_OPERATOR = re.compile(r"(?i)\b(?:OPERATOR|OWNER)\s*=\s*(-?\d+)")
_HEADWAY = re.compile(r"(?i)\bFREQ\[(\d+)\]\s*=")


class NetworkWranglerInputReader:
    """Inspect finalized Network Wrangler files under ``INPUT/trn``."""

    def inspect(self, model_directory: Path) -> SourceInventory:
        source_directory = model_directory / "INPUT" / "trn"
        if not source_directory.is_dir():
            raise SourceReadError(
                f"Network Wrangler transit directory does not exist: {source_directory}"
            )

        paths = sorted(
            (path for path in source_directory.iterdir() if path.is_file()),
            key=lambda path: path.name.casefold(),
        )
        issues: list[ValidationIssue] = []

        line_candidates = [path for path in paths if path.name.casefold() == "transitlines.lin"]
        if not line_candidates:
            issues.append(
                ValidationIssue(
                    IssueSeverity.ERROR,
                    "MISSING_TRANSIT_LINES",
                    "Required Network Wrangler output transitLines.lin was not found.",
                    "INPUT/trn/transitLines.lin",
                )
            )
            line_summary = TransitLineSummary(0, (), (), (), ())
        elif len(line_candidates) > 1:
            issues.append(
                ValidationIssue(
                    IssueSeverity.ERROR,
                    "AMBIGUOUS_TRANSIT_LINES",
                    "More than one case-insensitive match for transitLines.lin was found.",
                    "INPUT/trn",
                )
            )
            line_summary = self._summarize_lines(self.read_transit_lines(line_candidates[0]))
        else:
            line_summary = self._summarize_lines(self.read_transit_lines(line_candidates[0]))

        source_files = tuple(
            self._describe_file(path, source_directory, line_summary.count)
            for path in paths
        )
        return SourceInventory(
            source_directory="INPUT/trn",
            files=source_files,
            transit_lines=line_summary,
            issues=tuple(issues),
        )

    def _describe_file(
        self, path: Path, source_directory: Path, transit_line_count: int
    ) -> SourceFile:
        relative_path = path.relative_to(source_directory).as_posix()
        file_type = self._classify(path.name)
        record_count = transit_line_count if file_type == "transit_lines" else None
        return SourceFile(
            path=relative_path,
            file_type=file_type,
            size_bytes=path.stat().st_size,
            sha256=self._sha256(path),
            record_count=record_count,
        )

    @staticmethod
    def _classify(filename: str) -> str:
        lower_name = filename.casefold()
        if lower_name in _KNOWN_FILE_TYPES:
            return _KNOWN_FILE_TYPES[lower_name]
        if lower_name.startswith("transitlines_") and lower_name.endswith(".pnr"):
            return "park_and_ride_connectors"
        if lower_name.endswith(".far") or "fare" in lower_name:
            return "fare"
        if lower_name == "transitlinetovehicle.csv":
            return "line_to_vehicle"
        if lower_name == "transitprefixtovehicle.csv":
            return "prefix_to_vehicle"
        if "capacity" in lower_name and lower_name.endswith(".csv"):
            return "capacity"
        return "other"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise SourceReadError(f"Could not read source file {path}: {error}") from error
        return digest.hexdigest()

    @staticmethod
    def read_transit_lines(path: Path) -> tuple[TransitLineRecord, ...]:
        """Read basic line attributes while retaining their source locations."""

        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as error:
            raise SourceReadError(f"Could not read transit line file {path}: {error}") from error

        starts = list(_LINE_START.finditer(text))
        records = [
            text[start.start() : starts[index + 1].start() if index + 1 < len(starts) else len(text)]
            for index, start in enumerate(starts)
        ]

        parsed: list[TransitLineRecord] = []
        for start, record in zip(starts, records):
            name_match = _NAME.search(record)
            mode_match = _MODE.search(record)
            operator_match = _OPERATOR.search(record)
            parsed.append(
                TransitLineRecord(
                    name=(name_match.group(1) or name_match.group(2)) if name_match else "",
                    mode=int(mode_match.group(1)) if mode_match else None,
                    operator=int(operator_match.group(1)) if operator_match else None,
                    headway_periods=tuple(
                        sorted({int(value) for value in _HEADWAY.findall(record)})
                    ),
                    source_path=path.name,
                    source_line=text.count("\n", 0, start.start()) + 1,
                )
            )
        return tuple(parsed)

    @staticmethod
    def _summarize_lines(lines: tuple[TransitLineRecord, ...]) -> TransitLineSummary:
        names = {line.name for line in lines if line.name}
        modes = {line.mode for line in lines if line.mode is not None}
        operators = {line.operator for line in lines if line.operator is not None}
        headway_periods = {
            period for line in lines for period in line.headway_periods
        }

        return TransitLineSummary(
            count=len(lines),
            names=tuple(sorted(names, key=str.casefold)),
            modes=tuple(sorted(modes)),
            operators=tuple(sorted(operators)),
            headway_periods=tuple(sorted(headway_periods)),
        )
