"""Tests for manifest.py (provenance manifest writer). Phase 2."""
from __future__ import annotations

import json

from models.travel_model.config import Scenario
from models.travel_model.manifest import MANIFEST_FILENAME, write_manifest

LOCAL_RECORD = {
    "destination": "CTRAMP/scripts/tollCalcs.s",
    "source_type": "local",
    "source_path": "/abs/path/to/tollCalcs.s",
    "content_sha256": "deadbeef" * 8,
}
GITHUB_RECORD = {
    "destination": "model-files/scripts/truckFFmodel.py",
    "source_type": "github",
    "url": "https://github.com/BayAreaMetro/travel-model-one/blob/main/x.py",
    "resolved_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
}


def _scenario() -> Scenario:
    return Scenario(name="scenario_low_toll", skip_if_exists=False, replacements=[])


def test_write_manifest_local_record(tmp_path):
    base_zip = tmp_path / "base.zip"
    base_zip.write_bytes(b"PK\x03\x04 fake zip bytes")

    out = write_manifest(_scenario(), tmp_path, base_zip, [LOCAL_RECORD])

    assert out == tmp_path / MANIFEST_FILENAME
    data = json.loads(out.read_text())
    assert data["scenario_name"] == "scenario_low_toll"
    assert data["timestamp"]
    assert data["base_zip"]["path"] == str(base_zip)
    assert data["base_zip"]["size_bytes"] == base_zip.stat().st_size
    assert data["base_zip"]["mtime"]
    assert data["replacements"] == [LOCAL_RECORD]


def test_write_manifest_github_record_includes_resolved_sha(tmp_path):
    base_zip = tmp_path / "base.zip"
    base_zip.write_bytes(b"zip")

    out = write_manifest(_scenario(), tmp_path, base_zip, [GITHUB_RECORD])

    record = json.loads(out.read_text())["replacements"][0]
    assert record["url"].startswith("https://github.com/")
    assert record["resolved_sha"] == GITHUB_RECORD["resolved_sha"]


def test_write_manifest_records_both_records(tmp_path):
    base_zip = tmp_path / "base.zip"
    base_zip.write_bytes(b"zip")

    out = write_manifest(_scenario(), tmp_path, base_zip, [LOCAL_RECORD, GITHUB_RECORD])

    replacements = json.loads(out.read_text())["replacements"]
    assert replacements == [LOCAL_RECORD, GITHUB_RECORD]


def test_write_manifest_tolerates_missing_base_zip(tmp_path):
    missing = tmp_path / "not_there.zip"

    out = write_manifest(_scenario(), tmp_path, missing, [])

    base = json.loads(out.read_text())["base_zip"]
    assert base["path"] == str(missing)
    assert base["size_bytes"] is None
    assert base["mtime"] is None
