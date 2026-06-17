"""Tests for config.py (Pydantic config models + source auto-detection). Phase 2."""
from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from models.travel_model.config import (
    GitHubSource,
    LocalSource,
    RunConfig,
    parse_github_source,
)

PERMALINK = (
    "https://github.com/BayAreaMetro/travel-model-one/blob/"
    "a1b2c3d4e5f6/model-files/scripts/truckFFmodel.py"
)
BRANCH_URL = (
    "https://github.com/BayAreaMetro/travel-model-one/blob/main/model-files/params.properties"
)


def _config_dict(local_source: str, output_root: str = "out") -> dict:
    """Build a minimal valid RunConfig dict using a real local source path."""
    return {
        "base_zip": "//mtc-share/models/full_run_2026.zip",
        "output_root": output_root,
        "scenarios": [
            {"name": "baseline", "skip_if_exists": True, "replacements": []},
            {
                "name": "scenario_low_toll",
                "skip_if_exists": False,
                "replacements": [
                    {"source": local_source, "destination": "CTRAMP/scripts/tollCalcs.s"},
                    {"source": PERMALINK, "destination": "model-files/scripts/truckFFmodel.py"},
                ],
            },
        ],
    }


def test_valid_yaml_round_trips_into_runconfig(tmp_path):
    local = tmp_path / "tollCalcs.s"
    local.write_text("; edited\n")
    raw = yaml.safe_load(yaml.safe_dump(_config_dict(str(local))))

    config = RunConfig.model_validate(raw)

    assert config.base_zip.endswith("full_run_2026.zip")
    assert [s.name for s in config.scenarios] == ["baseline", "scenario_low_toll"]
    assert config.scenarios[0].replacements == []


def test_github_url_resolves_to_github_source(tmp_path):
    local = tmp_path / "tollCalcs.s"
    local.write_text("; edited\n")
    config = RunConfig.model_validate(_config_dict(str(local)))

    low_toll = config.scenarios[1]
    local_repl, github_repl = low_toll.replacements

    assert isinstance(local_repl.file_source, LocalSource)
    assert local_repl.file_source.path == str(local)
    assert isinstance(github_repl.file_source, GitHubSource)
    assert github_repl.file_source.owner == "BayAreaMetro"
    assert github_repl.file_source.repo == "travel-model-one"
    assert github_repl.file_source.ref == "a1b2c3d4e5f6"
    assert github_repl.file_source.file_path == "model-files/scripts/truckFFmodel.py"


def test_missing_skip_if_exists_is_a_validation_error():
    bad = {
        "base_zip": "z.zip",
        "output_root": "out",
        "scenarios": [{"name": "baseline", "replacements": []}],
    }
    with pytest.raises(ValidationError) as exc_info:
        RunConfig.model_validate(bad)
    assert any(err["loc"][-1] == "skip_if_exists" for err in exc_info.value.errors())


def test_destination_escaping_scenario_root_is_rejected(tmp_path):
    local = tmp_path / "edit.s"
    local.write_text("x\n")
    bad = {
        "base_zip": "z.zip",
        "output_root": "out",
        "scenarios": [
            {
                "name": "s",
                "skip_if_exists": False,
                "replacements": [
                    {"source": str(local), "destination": "../../etc/passwd"},
                ],
            }
        ],
    }
    with pytest.raises(ValidationError, match="escapes the scenario root"):
        RunConfig.model_validate(bad)


def test_absolute_destination_is_rejected(tmp_path):
    local = tmp_path / "edit.s"
    local.write_text("x\n")
    bad = {
        "base_zip": "z.zip",
        "output_root": "out",
        "scenarios": [
            {
                "name": "s",
                "skip_if_exists": False,
                "replacements": [
                    {"source": str(local), "destination": "/etc/passwd"},
                ],
            }
        ],
    }
    with pytest.raises(ValidationError, match="absolute path"):
        RunConfig.model_validate(bad)


def test_missing_local_source_is_rejected(tmp_path):
    bad = {
        "base_zip": "z.zip",
        "output_root": "out",
        "scenarios": [
            {
                "name": "s",
                "skip_if_exists": False,
                "replacements": [
                    {"source": str(tmp_path / "nope.s"), "destination": "a/b.s"},
                ],
            }
        ],
    }
    with pytest.raises(ValidationError, match="does not exist or is not a file"):
        RunConfig.model_validate(bad)


def test_multiple_errors_are_all_reported_together(tmp_path):
    # Two independent problems: missing skip_if_exists AND a bad destination.
    local = tmp_path / "edit.s"
    local.write_text("x\n")
    bad = {
        "base_zip": "z.zip",
        "output_root": "out",
        "scenarios": [
            {"name": "s1", "replacements": []},  # missing skip_if_exists
            {
                "name": "s2",
                "skip_if_exists": False,
                "replacements": [
                    {"source": str(local), "destination": "../escape.s"},
                ],
            },
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        RunConfig.model_validate(bad)
    assert len(exc_info.value.errors()) >= 2


@pytest.mark.parametrize(
    "url,ref",
    [
        (PERMALINK, "a1b2c3d4e5f6"),
        (BRANCH_URL, "main"),
        (
            "https://raw.githubusercontent.com/BayAreaMetro/travel-model-one/main/x/y.s",
            "main",
        ),
    ],
)
def test_parse_github_source_extracts_ref(url, ref):
    assert parse_github_source(url).ref == ref


def test_parse_github_source_rejects_non_file_url():
    with pytest.raises(ValueError):
        parse_github_source("https://github.com/BayAreaMetro/travel-model-one")
