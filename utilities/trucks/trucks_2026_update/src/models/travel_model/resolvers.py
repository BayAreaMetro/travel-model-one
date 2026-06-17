"""Source resolution: copy a ``LocalSource`` or fetch a ``GitHubSource``.

Each resolver writes the source content to a destination path. The GitHub
resolver resolves the source's ref to a concrete commit SHA, fetches the file at
that SHA (so branch-based "latest" sources stay reproducible — the manifest can
record the exact SHA, §6), and returns it. See §7 (Resolution).

All of this is cross-platform (§2). The GitHub resolver is the single place a
rate-limit-aware delay/backoff or token would be added if needed (§7).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import requests

from .config import FileSource, GitHubSource, LocalSource

GITHUB_API_BASE = "https://api.github.com"
RAW_CONTENT_BASE = "https://raw.githubusercontent.com"
_HTTP_TIMEOUT_SECONDS = 30
_COMMIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
"""A ref that is all hex (7–40 chars) is treated as a pinned commit SHA, not a branch."""


def resolve_source(source: FileSource, destination: Path) -> str | None:
    """Copy or fetch ``source`` to ``destination``.

    Dispatches to :func:`resolve_local` or :func:`resolve_github` based on the
    concrete source type.

    Parameters
    ----------
    source : FileSource
        The resolved source (``LocalSource`` or ``GitHubSource``) to materialise.
    destination : Path
        Path the source content is written to (overwriting any existing file).

    Returns
    -------
    str | None
        The resolved commit SHA for a ``GitHubSource``, or ``None`` for a
        ``LocalSource``.

    Raises
    ------
    TypeError
        If ``source`` is neither a ``LocalSource`` nor a ``GitHubSource``.
    """
    if isinstance(source, LocalSource):
        resolve_local(source, destination)
        return None
    if isinstance(source, GitHubSource):
        return resolve_github(source, destination)
    raise TypeError(f"unsupported source type: {type(source).__name__}")


def resolve_local(source: LocalSource, destination: Path) -> None:
    """Copy a local file to ``destination``. See §4.1.

    Parameters
    ----------
    source : LocalSource
        The local source whose ``path`` is copied.
    destination : Path
        Path the file is copied to (overwriting any existing file). Parent
        directories are created if missing.

    Raises
    ------
    FileNotFoundError
        If the source path no longer exists or is not a file (it is validated at
        config time, but may have been removed since).
    """
    src = Path(source.path)
    if not src.is_file():
        raise FileNotFoundError(f"local source no longer exists or is not a file: {src}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, destination)


def resolve_github(source: GitHubSource, destination: Path) -> str:
    """Fetch a GitHub file to ``destination`` and return its commit SHA. See §4.1, §6.

    The ref is first resolved to a concrete commit SHA (see
    :func:`_resolve_commit_sha`); the file is then fetched pinned to that SHA, so
    the bytes written and the SHA returned always correspond to the same commit
    even if the branch moves.

    Parameters
    ----------
    source : GitHubSource
        The GitHub source to fetch.
    destination : Path
        Path the fetched content is written to. Parent directories are created
        if missing.

    Returns
    -------
    str
        The resolved commit SHA actually fetched.

    Raises
    ------
    RuntimeError
        If the file fetch returns a non-200 status (e.g. 404 for a wrong path,
        or a network/HTTP error surfaced as a non-200).
    """
    sha = _resolve_commit_sha(source)
    raw_url = f"{RAW_CONTENT_BASE}/{source.owner}/{source.repo}/{sha}/{source.file_path}"
    response = requests.get(raw_url, timeout=_HTTP_TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError(
            f"failed to fetch GitHub source (HTTP {response.status_code}): {raw_url}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return sha


def _resolve_commit_sha(source: GitHubSource) -> str:
    """Resolve a source's ref to a concrete commit SHA. See §6.

    A ref that is all hex (a permalink) is already pinned and returned as-is. A
    branch name is resolved by asking the GitHub API for the commit it currently
    points at, so a "latest on this branch" source records the exact SHA used.

    Parameters
    ----------
    source : GitHubSource
        The source whose ``ref`` is resolved.

    Returns
    -------
    str
        The commit SHA: the ref itself for a permalink, or the branch's current
        head commit for a branch ref.

    Raises
    ------
    RuntimeError
        If the GitHub API lookup for a branch ref returns a non-200 status.
    """
    if _COMMIT_SHA_RE.match(source.ref):
        return source.ref
    api_url = f"{GITHUB_API_BASE}/repos/{source.owner}/{source.repo}/commits/{source.ref}"
    response = requests.get(
        api_url,
        timeout=_HTTP_TIMEOUT_SECONDS,
        headers={"Accept": "application/vnd.github+json"},
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"failed to resolve GitHub ref {source.ref!r} "
            f"(HTTP {response.status_code}): {api_url}"
        )
    return response.json()["sha"]
