"""Tests for workspace.py (ScenarioWorkspace: extraction + replacement). Phase 4.

All offline — uses a small in-test fake base zip and local replacement sources,
never the real multi-GB MTC zip or the network.
"""
from __future__ import annotations

import zipfile

import pytest

from models.travel_model.config import RunConfig
from models.travel_model.workspace import ScenarioWorkspace

BASE_FILES = {
    "CTRAMP/RunIteration.bat": "original bat\n",
    "CTRAMP/scripts/tollCalcs.s": "original tollCalcs\n",
    "model-files/params.properties": "original params\n",
}


def _make_base_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in BASE_FILES.items():
            zf.writestr(name, body)
    return path


def _config(tmp_path, replacements, *, name="demo", skip_if_exists=False) -> RunConfig:
    base_zip = _make_base_zip(tmp_path / "base.zip")
    return RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(tmp_path / "out"),
            "scenarios": [
                {"name": name, "skip_if_exists": skip_if_exists, "replacements": replacements}
            ],
        }
    )


def _local_edit(tmp_path) -> str:
    edit = tmp_path / "edited_tollCalcs.s"
    edit.write_text("EDITED tollCalcs\n")
    return str(edit)


def test_extraction_produces_expected_files(tmp_path):
    config = _config(tmp_path, replacements=[])
    ws = ScenarioWorkspace(config.scenarios[0], config)

    rebuilt = ws.prepare()

    assert rebuilt is True
    for name in BASE_FILES:
        assert (ws.scenario_root / name).is_file()


def test_replacement_overwrites_destination_and_records(tmp_path):
    config = _config(
        tmp_path,
        replacements=[
            {"source": _local_edit(tmp_path), "destination": "CTRAMP/scripts/tollCalcs.s"}
        ],
    )
    ws = ScenarioWorkspace(config.scenarios[0], config)
    ws.prepare()

    records = ws.apply_replacements()

    assert (ws.scenario_root / "CTRAMP/scripts/tollCalcs.s").read_text() == "EDITED tollCalcs\n"
    assert records[0]["destination"] == "CTRAMP/scripts/tollCalcs.s"
    assert records[0]["source_type"] == "local"
    assert "content_sha256" in records[0]


def test_skip_if_exists_true_leaves_directory_untouched(tmp_path):
    config = _config(tmp_path, replacements=[], skip_if_exists=True)
    ws = ScenarioWorkspace(config.scenarios[0], config)
    ws.prepare()  # first run extracts
    # Drop a marker so we can detect any re-extraction.
    marker = ws.scenario_root / "MARKER.txt"
    marker.write_text("kept")

    rebuilt = ws.prepare()  # second run: dir exists + skip_if_exists → untouched

    assert rebuilt is False
    assert marker.read_text() == "kept"


def test_skip_if_exists_false_wipes_and_rebuilds(tmp_path):
    config = _config(tmp_path, replacements=[], skip_if_exists=False)
    ws = ScenarioWorkspace(config.scenarios[0], config)
    ws.prepare()
    stale = ws.scenario_root / "STALE.txt"
    stale.write_text("should be wiped")

    rebuilt = ws.prepare()  # dir exists + skip_if_exists False → wipe + re-extract

    assert rebuilt is True
    assert not stale.exists()
    assert (ws.scenario_root / "CTRAMP/RunIteration.bat").is_file()


def test_missing_destination_aborts_and_copies_nothing(tmp_path):
    edit = _local_edit(tmp_path)
    config = _config(
        tmp_path,
        replacements=[
            {"source": edit, "destination": "CTRAMP/scripts/tollCalcs.s"},  # exists
            {"source": edit, "destination": "CTRAMP/scripts/DOES_NOT_EXIST.s"},  # missing
            {"source": edit, "destination": "model-files/ALSO_MISSING.properties"},  # missing
        ],
    )
    ws = ScenarioWorkspace(config.scenarios[0], config)
    ws.prepare()

    with pytest.raises(FileNotFoundError) as exc_info:
        ws.apply_replacements()

    # Both missing destinations are listed (not just the first).
    msg = str(exc_info.value)
    assert "DOES_NOT_EXIST.s" in msg and "ALSO_MISSING.properties" in msg
    # The valid destination was NOT overwritten — all-or-nothing (§5.4).
    assert (ws.scenario_root / "CTRAMP/scripts/tollCalcs.s").read_text() == "original tollCalcs\n"


def test_base_zip_missing_raises(tmp_path):
    config = RunConfig.model_validate(
        {
            "base_zip": str(tmp_path / "nope.zip"),
            "output_root": str(tmp_path / "out"),
            "scenarios": [{"name": "demo", "skip_if_exists": False, "replacements": []}],
        }
    )
    ws = ScenarioWorkspace(config.scenarios[0], config)
    with pytest.raises(FileNotFoundError, match="base zip not found"):
        ws.prepare()
