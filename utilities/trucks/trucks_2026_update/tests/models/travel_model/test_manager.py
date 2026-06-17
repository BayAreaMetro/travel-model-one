"""Tests for manager.py (ScenarioManager orchestration). Phase 7.

The Windows-only ModelRunner / MatrixConverter are replaced with fakes so the
full orchestration — sequencing, the three-way conversion outcome, and
failure-isolation across scenarios (§8) — is exercised on any platform.
"""
from __future__ import annotations

import zipfile

from models.travel_model import manager as manager_module
from models.travel_model.config import RunConfig
from models.travel_model.manager import ScenarioManager, Status

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


def _install_fakes(monkeypatch, model_codes=None, conv_codes=None):
    """Swap ModelRunner / MatrixConverter for fakes; return a record of calls."""
    model_codes = model_codes or {}
    conv_codes = conv_codes or {}
    calls = {"model": [], "conversion": []}

    class FakeRunner:
        def __init__(self, scenario, root):
            self._scenario = scenario

        def run(self):
            calls["model"].append(self._scenario.name)
            return model_codes.get(self._scenario.name, 0)

    class FakeConverter:
        def __init__(self, root, script_path=None):
            self._root = root

        def run(self):
            calls["conversion"].append(self._root.name)
            return conv_codes.get(self._root.name, 0)

    monkeypatch.setattr(manager_module, "ModelRunner", FakeRunner)
    monkeypatch.setattr(manager_module, "MatrixConverter", FakeConverter)
    return calls


def _result(results, name):
    return next(r for r in results if r.name == name)


def test_mixed_outcomes_and_failure_isolation(tmp_path, monkeypatch):
    base_zip = _make_base_zip(tmp_path / "base.zip")
    edit = tmp_path / "edit.s"
    edit.write_text("edited\n")
    config = RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(tmp_path / "out"),
            "scenarios": [
                {"name": "good", "skip_if_exists": False, "replacements": []},
                {
                    "name": "broken",
                    "skip_if_exists": False,
                    "replacements": [{"source": str(edit), "destination": "NOPE.txt"}],
                },
                {"name": "model_fail", "skip_if_exists": False, "replacements": []},
            ],
        }
    )
    calls = _install_fakes(monkeypatch, model_codes={"model_fail": 1})

    results = ScenarioManager(config).run()

    good = _result(results, "good")
    assert good.model is Status.SUCCEEDED and good.conversion is Status.SUCCEEDED

    broken = _result(results, "broken")
    assert broken.model is Status.FAILED and broken.conversion is Status.SKIPPED
    assert "NOPE.txt" in broken.detail

    model_fail = _result(results, "model_fail")
    assert model_fail.model is Status.FAILED and model_fail.conversion is Status.SKIPPED

    # A failed model run never triggers conversion; a broken scenario never runs the model.
    assert calls["conversion"] == ["good"]
    assert "broken" not in calls["model"]


def test_skip_if_exists_skips_model_but_runs_conversion(tmp_path, monkeypatch):
    base_zip = _make_base_zip(tmp_path / "base.zip")
    output_root = tmp_path / "out"
    # Pre-create the scenario directory so skip_if_exists takes effect.
    (output_root / "done").mkdir(parents=True)
    config = RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(output_root),
            "scenarios": [{"name": "done", "skip_if_exists": True, "replacements": []}],
        }
    )
    calls = _install_fakes(monkeypatch)

    results = ScenarioManager(config).run()

    done = _result(results, "done")
    assert done.model is Status.SKIPPED  # model not re-run (§3a)
    assert done.conversion is Status.SUCCEEDED  # conversion still runs
    assert calls["model"] == []  # the model runner was never invoked
    assert calls["conversion"] == ["done"]


def test_manifest_written_before_run(tmp_path, monkeypatch):
    base_zip = _make_base_zip(tmp_path / "base.zip")
    config = RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(tmp_path / "out"),
            "scenarios": [{"name": "good", "skip_if_exists": False, "replacements": []}],
        }
    )
    _install_fakes(monkeypatch)

    ScenarioManager(config).run()

    assert (tmp_path / "out" / "good" / "runner_manifest.json").is_file()


def test_lock_released_after_run(tmp_path, monkeypatch):
    base_zip = _make_base_zip(tmp_path / "base.zip")
    config = RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(tmp_path / "out"),
            "scenarios": [{"name": "good", "skip_if_exists": False, "replacements": []}],
        }
    )
    _install_fakes(monkeypatch)

    ScenarioManager(config).run()

    assert not (tmp_path / "out" / ".runner.lock").exists()


def test_summary_reports_all_states(tmp_path, monkeypatch):
    base_zip = _make_base_zip(tmp_path / "base.zip")
    config = RunConfig.model_validate(
        {
            "base_zip": str(base_zip),
            "output_root": str(tmp_path / "out"),
            "scenarios": [
                {"name": "good", "skip_if_exists": False, "replacements": []},
                {"name": "model_fail", "skip_if_exists": False, "replacements": []},
            ],
        }
    )
    _install_fakes(monkeypatch, model_codes={"model_fail": 1})

    mgr = ScenarioManager(config)
    summary = mgr.summary(mgr.run())

    assert "good: model=succeeded, conversion=succeeded" in summary
    assert "model_fail: model=failed, conversion=skipped" in summary
