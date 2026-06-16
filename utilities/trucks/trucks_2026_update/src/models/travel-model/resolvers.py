"""
Source resolution: copy a LocalSource or fetch a GitHubSource to a target path. See §7.

GitHub resolver transforms blob URLs to raw.githubusercontent.com fetch URLs and
returns the resolved commit SHA (even for branch-based refs). See §4.1 and §6.
"""
from __future__ import annotations

from pathlib import Path

from .config import FileSource, GitHubSource, LocalSource


def resolve_source(source: FileSource, destination: Path) -> str | None:
    """
    Copy or fetch `source` to `destination`.

    Returns the resolved commit SHA for a GitHubSource, or None for a LocalSource.
    See §4.1, §6.
    """
    raise NotImplementedError("resolve_source not yet implemented")


def resolve_local(source: LocalSource, destination: Path) -> None:
    """Copy a local file to `destination`. See §4.1."""
    raise NotImplementedError("resolve_local not yet implemented")


def resolve_github(source: GitHubSource, destination: Path) -> str:
    """
    Fetch a GitHub file to `destination`.

    For branch-based refs, queries GitHub for the current commit SHA so the run
    remains reproducible after the fact. Returns the resolved commit SHA. See §4.1, §6.
    """
    raise NotImplementedError("resolve_github not yet implemented")


def parse_github_url(url: str) -> GitHubSource:
    """
    Parse a github.com or raw.githubusercontent.com URL into a GitHubSource.

    Raises ValueError if the URL cannot be parsed. See §4.1.
    """
    raise NotImplementedError("parse_github_url not yet implemented")
