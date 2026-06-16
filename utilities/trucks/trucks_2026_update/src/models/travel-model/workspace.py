"""
ScenarioWorkspace: owns extraction of the base zip and application of replacements
for a single scenario directory. See §7 and §5.

Extraction and replacement are strictly cross-platform; no Windows dependency here.
"""
from __future__ import annotations

from pathlib import Path

from .config import RunConfig, Scenario


class ScenarioWorkspace:
    """
    Manages the filesystem state of one scenario directory. See §7.

    Responsibilities:
    - Apply the skip_if_exists / delete-and-re-extract logic (§5.3).
    - Extract the base zip into the scenario directory.
    - Validate all destination paths exist before copying anything (§5.4).
    - Apply replacements using the resolvers (§4.1, Phase 4).
    """

    def __init__(self, scenario: Scenario, config: RunConfig) -> None:
        """Bind scenario and top-level config; derive the scenario root path."""
        raise NotImplementedError("ScenarioWorkspace.__init__ not yet implemented")

    @property
    def scenario_root(self) -> Path:
        """Return <output_root>/<scenario.name>/. See §3 step 1."""
        raise NotImplementedError("ScenarioWorkspace.scenario_root not yet implemented")

    def prepare(self) -> bool:
        """
        Apply skip_if_exists logic, then extract the base zip. See §5.3 and §3 steps 2–3.

        Returns True if preparation ran (extract + replace will follow),
        False if the directory was skipped (skip_if_exists=True and dir exists).
        """
        raise NotImplementedError("ScenarioWorkspace.prepare not yet implemented")

    def apply_replacements(self) -> list[dict]:
        """
        Validate all destinations exist, then overwrite each with the resolved source. See §5.4.

        Returns a list of replacement records suitable for the manifest (§6).
        All destinations are checked before any copy occurs; missing ones abort with a combined error.
        """
        raise NotImplementedError("ScenarioWorkspace.apply_replacements not yet implemented")
