"""Pydantic configuration models for the scenario runner.

Defines the objects the scenarios YAML deserialises into: ``FileSource``
(``LocalSource`` / ``GitHubSource``), ``Replacement``, ``Scenario``, and the
top-level ``RunConfig``. See §4 of the spec for the schema and §4.1 for the
source-string auto-detection rules.

Validation is eager and platform-agnostic (§2): a local ``source`` must exist as
a file at validation time, a GitHub ``source`` must parse into owner/repo/ref/
path, and a ``destination`` must be a relative path that does not escape the
scenario root (§5.4). All of this runs on any platform — only the later ``.bat``
and ``.tpp`` → ``.omx`` steps need Windows.
"""
from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

GITHUB_HOSTS = frozenset({"github.com", "www.github.com", "raw.githubusercontent.com"})
"""Hosts whose URLs are treated as a ``GitHubSource`` rather than a local path. See §4.1."""


@dataclass
class LocalSource:
    """A replacement source that is a file on local disk. See §4.1.

    Parameters
    ----------
    path : str
        Filesystem path to the source file. Verified to exist and be a file by
        the ``Replacement`` validator at validation time.
    """

    path: str


@dataclass
class GitHubSource:
    """A replacement source that is a single file in a GitHub repo. See §4.1.

    May be a permalink (pinned commit SHA) or a branch URL (latest-on-branch).

    Parameters
    ----------
    url : str
        The original ``github.com`` (or ``raw.githubusercontent.com``) URL as
        written by the user.
    owner : str
        Repository owner / organisation (e.g. ``BayAreaMetro``).
    repo : str
        Repository name (e.g. ``travel-model-one``).
    ref : str
        Git ref from the URL: either a commit SHA (permalink) or a branch name.
    file_path : str
        Path to the file within the repository.
    """

    url: str
    owner: str
    repo: str
    ref: str
    file_path: str

    @property
    def raw_url(self) -> str:
        """Return the ``raw.githubusercontent.com`` fetch URL for this source. See §4.1.

        Transforms the parsed components into a raw-content URL pinned to this
        source's ``ref`` (a branch name or commit SHA).

        Returns
        -------
        str
            ``https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<file_path>``.
        """
        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/{self.ref}/{self.file_path}"
        )


FileSource = LocalSource | GitHubSource


def _looks_like_github_url(source: str) -> bool:
    """Return whether ``source`` should be treated as a GitHub URL. See §4.1.

    Parameters
    ----------
    source : str
        The raw ``source`` string from the YAML.

    Returns
    -------
    bool
        ``True`` if ``source`` parses as an http(s) URL whose host is a known
        GitHub host; ``False`` otherwise (i.e. treat as a local path).
    """
    parsed = urlparse(source)
    return parsed.scheme in ("http", "https") and parsed.netloc.lower() in GITHUB_HOSTS


def parse_github_source(url: str) -> GitHubSource:
    """Parse a GitHub blob or raw URL into a ``GitHubSource``. See §4.1.

    Accepts ``github.com/<owner>/<repo>/blob/<ref>/<path>`` (and the ``/raw/``
    variant) and ``raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>``.

    Parameters
    ----------
    url : str
        The GitHub URL to parse.

    Returns
    -------
    GitHubSource
        The parsed source with owner / repo / ref / file_path populated.

    Raises
    ------
    ValueError
        If the URL host is not a known GitHub host, or the path does not contain
        enough segments to identify owner / repo / ref / file path.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]

    if host in ("github.com", "www.github.com"):
        # /<owner>/<repo>/(blob|raw)/<ref>/<path...>
        if len(parts) < 5 or parts[2] not in ("blob", "raw"):
            raise ValueError(
                f"not a valid GitHub file URL (expected "
                f".../<owner>/<repo>/blob/<ref>/<path>): {url!r}"
            )
        owner, repo, _kind, ref, *rest = parts
    elif host == "raw.githubusercontent.com":
        # /<owner>/<repo>/<ref>/<path...>
        if len(parts) < 4:
            raise ValueError(
                f"not a valid raw GitHub URL (expected "
                f".../<owner>/<repo>/<ref>/<path>): {url!r}"
            )
        owner, repo, ref, *rest = parts
    else:
        raise ValueError(f"not a GitHub host: {url!r}")

    file_path = "/".join(rest)
    if not file_path:
        raise ValueError(f"GitHub URL does not point at a file: {url!r}")

    return GitHubSource(url=url, owner=owner, repo=repo, ref=ref, file_path=file_path)


class Replacement(BaseModel):
    """A single file swap: a resolved source overwriting a destination. See §4.2.

    The user writes only ``source`` (a string) and ``destination``. Validators
    auto-detect the source kind (§4.1) and check the destination is a safe
    relative path (§5.4); after validation, ``file_source`` holds the typed
    ``FileSource`` so downstream code never re-derives the string-vs-URL
    distinction.

    Parameters
    ----------
    source : str
        A local filesystem path (must exist) or a GitHub URL (must parse).
    destination : str
        Path relative to the scenario root; must not escape it via ``..`` and
        must not be absolute. Existence is checked post-extraction (§5.4), not here.
    file_source : FileSource | None
        Populated by the validator; not supplied by the user.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str
    destination: str
    file_source: FileSource | None = None

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: str) -> str:
        """Validate the source string as a parseable GitHub URL or existing file. See §4.1.

        Parameters
        ----------
        value : str
            The raw ``source`` string.

        Returns
        -------
        str
            The unchanged ``source`` string.

        Raises
        ------
        ValueError
            If a GitHub URL fails to parse, or a local path does not exist / is
            not a file.
        """
        if _looks_like_github_url(value):
            parse_github_source(value)  # raises ValueError on a malformed URL
            return value
        path = Path(value)
        if not path.is_file():
            raise ValueError(
                f"local source does not exist or is not a file: {value!r}"
            )
        return value

    @field_validator("destination")
    @classmethod
    def _validate_destination(cls, value: str) -> str:
        """Reject absolute destinations and ones that escape the scenario root. See §5.4.

        Parameters
        ----------
        value : str
            The raw ``destination`` string (relative to the scenario root).

        Returns
        -------
        str
            The unchanged ``destination`` string.

        Raises
        ------
        ValueError
            If ``destination`` is absolute (posix or Windows) or normalises to a
            path that escapes the scenario root via ``..``.
        """
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError(
                f"destination must be relative to the scenario root, "
                f"got an absolute path: {value!r}"
            )
        normalized = posixpath.normpath(value.replace("\\", "/"))
        if normalized == ".." or normalized.startswith("../"):
            raise ValueError(
                f"destination escapes the scenario root via '..': {value!r}"
            )
        return value

    @model_validator(mode="after")
    def _attach_file_source(self) -> Replacement:
        """Attach the typed ``FileSource`` once both fields have validated. See §4.1.

        Returns
        -------
        Replacement
            This instance, with ``file_source`` populated.
        """
        if _looks_like_github_url(self.source):
            self.file_source = parse_github_source(self.source)
        else:
            self.file_source = LocalSource(path=str(Path(self.source)))
        return self


class Scenario(BaseModel):
    """One scenario: a named directory built from the base zip plus replacements. See §4.3.

    Parameters
    ----------
    name : str
        Scenario name; also the directory created under ``output_root``.
    skip_if_exists : bool
        Required, no default (§4.3). ``True`` leaves an existing scenario
        directory untouched and runs it; ``False`` deletes and rebuilds it (§5.3).
    replacements : list[Replacement]
        Files to swap in after extraction. May be empty (untouched base run).
    base_zip : str | None, optional
        Per-scenario override of the shared ``RunConfig.base_zip`` (§5.1).
    bat_file : str | None, optional
        Escape-hatch override of the fixed internal bat path (§4.3.1). Normally
        omitted.
    """

    name: str
    skip_if_exists: bool
    replacements: list[Replacement] = []
    base_zip: str | None = None
    bat_file: str | None = None


class RunConfig(BaseModel):
    """Top-level object the entire scenarios YAML deserialises into. See §4.4.

    Validate via ``RunConfig.model_validate(yaml.safe_load(f))``.

    Parameters
    ----------
    base_zip : str
        Shared full-model zip used by every scenario unless overridden (§5.1).
        Existence is not checked here (it is only needed at extraction time on
        Windows); only the string is validated.
    output_root : str
        Parent directory under which each scenario's folder is created.
    scenarios : list[Scenario]
        The scenarios to run, in order.
    """

    base_zip: str
    output_root: str
    scenarios: list[Scenario]
