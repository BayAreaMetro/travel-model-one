"""
Provenance manifest writer. See §6.

Written into the scenario directory after replacement but before the .bat run,
so a record exists even if the run later fails.
"""
from __future__ import annotations

from pathlib import Path

from .config import Scenario


MANIFEST_FILENAME = "runner_manifest.json"


def write_manifest(
    scenario: Scenario,
    scenario_root: Path,
    base_zip_path: str,
    replacement_records: list[dict],
) -> Path:
    """
    Write the provenance manifest for a scenario. See §6.

    `replacement_records` is a list of dicts produced by ScenarioWorkspace.apply_replacements,
    each containing destination path, source type, and (for GitHub sources) resolved commit SHA.

    Returns the path of the written manifest file.
    """
    raise NotImplementedError("write_manifest not yet implemented")
