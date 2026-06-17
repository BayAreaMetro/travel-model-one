"""Per-scenario filesystem staging: extraction and replacement application.

``ScenarioWorkspace`` owns one scenario directory: it applies the existing-
directory policy (§5.3), extracts the base zip, and applies replacements with
the all-or-nothing destination check (§5.4). Everything here is cross-platform;
no Windows dependency (§2).
"""
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

from .config import GitHubSource, LocalSource, RunConfig, Scenario
from .resolvers import resolve_source


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 of a file's contents.

    Parameters
    ----------
    path : Path
        File to hash.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class ScenarioWorkspace:
    """Owns extraction and replacement for a single scenario directory. See §7, §5.

    Parameters
    ----------
    scenario : Scenario
        The scenario being staged.
    config : RunConfig
        The top-level config, used for ``output_root`` and the shared
        ``base_zip`` (unless the scenario overrides it).
    """

    def __init__(self, scenario: Scenario, config: RunConfig) -> None:
        """Bind the scenario and config.

        Parameters
        ----------
        scenario : Scenario
            The scenario being staged.
        config : RunConfig
            The top-level run configuration.
        """
        self._scenario = scenario
        self._config = config

    @property
    def scenario_root(self) -> Path:
        """Return the scenario's target directory ``<output_root>/<name>/``. See §3.

        Returns
        -------
        Path
            Path to this scenario's directory.
        """
        return Path(self._config.output_root) / self._scenario.name

    @property
    def base_zip_path(self) -> Path:
        """Return the base zip used for this scenario (scenario override or shared). See §5.1.

        Returns
        -------
        Path
            The per-scenario ``base_zip`` if set, otherwise the shared
            ``RunConfig.base_zip``.
        """
        return Path(self._scenario.base_zip or self._config.base_zip)

    def prepare(self) -> bool:
        """Apply the existing-directory policy, then extract the base zip. See §5.3, §3.

        - ``skip_if_exists`` and the directory already exists → leave it untouched
          and return ``False`` (no extraction; the caller skips replacement and,
          per §3a, also the model run, running only conversion).
        - otherwise → delete any existing directory, then extract the base zip
          fresh, and return ``True``.

        Returns
        -------
        bool
            ``True`` if the scenario was (re)extracted, ``False`` if it was left
            untouched per ``skip_if_exists``.

        Raises
        ------
        FileNotFoundError
            If the base zip does not exist.
        """
        root = self.scenario_root
        if root.exists() and self._scenario.skip_if_exists:
            return False
        if root.exists():
            shutil.rmtree(root)
        self._extract_base_zip(root)
        return True

    def _extract_base_zip(self, root: Path) -> None:
        """Extract the base zip into ``root`` (created fresh).

        Parameters
        ----------
        root : Path
            Destination directory; created if missing.

        Raises
        ------
        FileNotFoundError
            If the base zip does not exist.
        """
        base_zip = self.base_zip_path
        if not base_zip.is_file():
            raise FileNotFoundError(f"base zip not found: {base_zip}")
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(base_zip) as archive:
            archive.extractall(root)

    def apply_replacements(self) -> list[dict]:
        """Validate every destination, then overwrite each with its source. See §5.4.

        All destinations are checked for existence in the extracted tree *before*
        any copy occurs; if any are missing the whole scenario aborts with every
        missing destination listed, and nothing is copied (§5.2, §5.4).

        Returns
        -------
        list[dict]
            One record per applied replacement, shaped for the provenance
            manifest (§6): destination, source type, and either a content hash
            (local) or the original URL plus resolved commit SHA (GitHub).

        Raises
        ------
        FileNotFoundError
            If one or more destinations do not already exist in the extracted
            tree (the message lists all of them); no files are copied.
        """
        root = self.scenario_root
        missing = [
            repl.destination
            for repl in self._scenario.replacements
            if not (root / repl.destination).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                f"scenario {self._scenario.name!r}: "
                f"{len(missing)} replacement destination(s) do not exist in the "
                f"extracted base model (nothing copied): " + ", ".join(missing)
            )

        records: list[dict] = []
        for repl in self._scenario.replacements:
            destination = root / repl.destination
            resolved_sha = resolve_source(repl.file_source, destination)
            records.append(self._manifest_record(repl, destination, resolved_sha))
        return records

    def _manifest_record(self, replacement, destination: Path, resolved_sha) -> dict:
        """Build the provenance record for one applied replacement. See §6.

        Parameters
        ----------
        replacement : Replacement
            The replacement that was applied.
        destination : Path
            The file that was overwritten.
        resolved_sha : str | None
            The commit SHA returned by the resolver (GitHub), or ``None`` (local).

        Returns
        -------
        dict
            The manifest record for this replacement.
        """
        source = replacement.file_source
        record = {"destination": replacement.destination}
        if isinstance(source, GitHubSource):
            record.update(
                source_type="github",
                url=source.url,
                ref=source.ref,
                resolved_sha=resolved_sha,
            )
        elif isinstance(source, LocalSource):
            record.update(
                source_type="local",
                source_path=str(Path(source.path).resolve()),
                content_sha256=_sha256(destination),
            )
        return record
