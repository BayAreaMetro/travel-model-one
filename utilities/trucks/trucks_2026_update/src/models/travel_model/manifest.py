"""Provenance manifest writer.

Writes a manifest into the scenario directory after replacements are applied but
before the ``.bat`` run, so a record exists even if the run later fails. The
manifest is the source of truth for exactly what went into a scenario run: base
zip identity plus, per replacement, the source and (for GitHub) the resolved
commit SHA. See §6.

This module only *serialises* the record. The per-replacement details (content
hashes for local sources, resolved commit SHAs for GitHub sources) are computed
upstream by the workspace/resolvers at copy time (§6) and passed in as
``replacement_records``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import Scenario


MANIFEST_FILENAME = "runner_manifest.json"
"""Name of the manifest file written into each scenario directory. See §6."""


def _base_zip_identity(base_zip_path: Path) -> dict:
    """Describe the base zip for traceability: path plus size and mtime. See §6.

    Parameters
    ----------
    base_zip_path : Path
        Path to the base zip that was extracted for this scenario.

    Returns
    -------
    dict
        ``{"path": str, "size_bytes": int, "mtime": str}`` when the file exists;
        otherwise ``{"path": str, "size_bytes": None, "mtime": None}`` so the
        manifest still records which path was requested.
    """
    identity: dict = {"path": str(base_zip_path), "size_bytes": None, "mtime": None}
    try:
        stat = base_zip_path.stat()
    except OSError:
        return identity
    identity["size_bytes"] = stat.st_size
    identity["mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    return identity


def write_manifest(
    scenario: Scenario,
    scenario_root: Path,
    base_zip_path: Path,
    replacement_records: list[dict],
) -> Path:
    """Write the provenance manifest for a scenario. See §6.

    Parameters
    ----------
    scenario : Scenario
        The scenario being recorded (its ``name`` goes into the manifest).
    scenario_root : Path
        The scenario directory the manifest file is written into.
    base_zip_path : Path
        Path to the base zip used; its size and mtime are recorded for traceability.
    replacement_records : list[dict]
        One record per applied replacement, as produced by
        ``ScenarioWorkspace.apply_replacements``: each carries the ``destination``
        path, the source type, and either a content hash (local) or the original
        URL plus resolved commit SHA (GitHub). Embedded verbatim.

    Returns
    -------
    Path
        The path of the written manifest file
        (``<scenario_root>/runner_manifest.json``).
    """
    manifest = {
        "scenario_name": scenario.name,
        "timestamp": datetime.now().isoformat(),
        "base_zip": _base_zip_identity(base_zip_path),
        "replacements": list(replacement_records),
    }
    out_path = Path(scenario_root) / MANIFEST_FILENAME
    out_path.write_text(json.dumps(manifest, indent=2))
    return out_path
