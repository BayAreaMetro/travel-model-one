"""Data structures used to describe Network Wrangler transit inputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    """Importance of a problem found while inspecting source files."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A source problem that can be written to the inventory report."""

    severity: IssueSeverity
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
        }
        if self.path is not None:
            result["path"] = self.path
        return result


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One file found in the Network Wrangler transit directory."""

    path: str
    file_type: str
    size_bytes: int
    sha256: str
    record_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": self.path,
            "type": self.file_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }
        if self.record_count is not None:
            result["record_count"] = self.record_count
        return result


@dataclass(frozen=True, slots=True)
class TransitLineRecord:
    """Source-level transit-line facts retained for later translation."""

    name: str
    mode: int | None
    operator: int | None
    headway_periods: tuple[int, ...]
    source_path: str
    source_line: int


@dataclass(frozen=True, slots=True)
class TransitLineSummary:
    """Basic facts read from transitLines.lin without translating it."""

    count: int
    names: tuple[str, ...]
    modes: tuple[int, ...]
    operators: tuple[int, ...]
    headway_periods: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "names": list(self.names),
            "modes": list(self.modes),
            "operators": list(self.operators),
            "headway_periods": list(self.headway_periods),
        }


@dataclass(frozen=True, slots=True)
class SourceInventory:
    """Deterministic description of the converter's source files."""

    source_directory: str
    files: tuple[SourceFile, ...]
    transit_lines: TransitLineSummary
    issues: tuple[ValidationIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source": "network_wrangler",
            "source_directory": self.source_directory,
            "files": [source_file.to_dict() for source_file in self.files],
            "transit_lines": self.transit_lines.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }
