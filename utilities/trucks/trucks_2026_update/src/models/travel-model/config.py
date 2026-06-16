"""
Pydantic models for RunConfig YAML validation. See §4.

FileSource (LocalSource / GitHubSource) is auto-detected from the source string (§4.1).
Replacement, Scenario, and RunConfig mirror the YAML schema (§4.2–4.4).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from pydantic import BaseModel, field_validator, model_validator


@dataclass
class LocalSource:
    """A file on disk used as a replacement source. See §4.1."""

    path: str


@dataclass
class GitHubSource:
    """
    A GitHub URL (blob or raw) pointing to a single file. See §4.1.

    May be a permalink (pinned commit hash) or a branch-based URL.
    """

    url: str
    owner: str
    repo: str
    ref: str
    file_path: str

    @property
    def raw_url(self) -> str:
        """Return the raw.githubusercontent.com fetch URL."""
        raise NotImplementedError("GitHubSource.raw_url not yet implemented")


FileSource = Union[LocalSource, GitHubSource]


class Replacement(BaseModel):
    """
    A single file replacement entry. See §4.2.

    The `source` string is auto-detected as LocalSource or GitHubSource (§4.1).
    `destination` is relative to the scenario root; existence is checked post-extraction (§5.4),
    but path-traversal safety (no `..` escaping the root) is validated here.
    """

    model_config = {"arbitrary_types_allowed": True}

    source: str
    destination: str
    resolved_source: FileSource = None  # type: ignore[assignment]

    @model_validator(mode="after")
    def detect_and_set_source(self) -> "Replacement":
        """Infer LocalSource vs GitHubSource from the source string. See §4.1."""
        raise NotImplementedError("Source type auto-detection not yet implemented")

    @field_validator("destination")
    @classmethod
    def destination_no_traversal(cls, v: str) -> str:
        """Reject destinations that escape the scenario root via '..'. See §5.4."""
        raise NotImplementedError("Destination path-traversal check not yet implemented")


class Scenario(BaseModel):
    """A single scenario definition. See §4.3."""

    name: str
    skip_if_exists: bool  # Required — no default, every scenario must state this. See §4.3.
    replacements: list[Replacement] = []
    base_zip: str | None = None
    bat_file: str | None = None  # Escape hatch only; normally derived internally. See §4.3.1.


class RunConfig(BaseModel):
    """
    Top-level object that the entire travel_model_scenarios.yaml deserialises into. See §4.4.

    Usage: RunConfig.model_validate(yaml.safe_load(f))
    """

    base_zip: str
    output_root: str
    scenarios: list[Scenario]
