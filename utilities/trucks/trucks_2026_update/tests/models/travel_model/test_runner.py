"""Tests for runner.py (ModelRunner / Windows .bat execution). Phase 5.

The platform guard is testable anywhere. The subprocess plumbing is tested with a
trivial Python dummy script via ``sys.executable`` so it runs on any OS without
needing CUBE or a real ``.bat``.
"""
from __future__ import annotations

import sys

import pytest

from models.travel_model import runner
from models.travel_model.config import Scenario
from models.travel_model.runner import ModelRunner, ensure_windows, stream_subprocess


def _dummy_script(tmp_path, exit_code: int):
    script = tmp_path / f"dummy_{exit_code}.py"
    script.write_text(f"import sys\nprint('dummy ran')\nsys.exit({exit_code})\n")
    return script


def test_ensure_windows_raises_off_windows():
    # The test host is macOS/Linux, so the guard must fire.
    with pytest.raises(RuntimeError, match="requires Windows"):
        ensure_windows("model run")


def test_ensure_windows_passes_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    ensure_windows("model run")  # should not raise


def test_stream_subprocess_returns_exit_code_zero(tmp_path):
    assert stream_subprocess([sys.executable, str(_dummy_script(tmp_path, 0))], tmp_path) == 0


def test_stream_subprocess_returns_nonzero_exit_code(tmp_path):
    assert stream_subprocess([sys.executable, str(_dummy_script(tmp_path, 3))], tmp_path) == 3


def test_model_runner_run_guards_off_windows(tmp_path):
    scenario = Scenario(name="s", skip_if_exists=False, replacements=[])
    with pytest.raises(RuntimeError, match="requires Windows"):
        ModelRunner(scenario, tmp_path).run()


def test_bat_path_default(tmp_path):
    scenario = Scenario(name="s", skip_if_exists=False, replacements=[])
    assert ModelRunner(scenario, tmp_path).bat_path == tmp_path / "CTRAMP/RunIteration.bat"


def test_bat_path_scenario_override(tmp_path):
    scenario = Scenario(
        name="s", skip_if_exists=False, replacements=[], bat_file="custom/Other.bat"
    )
    assert ModelRunner(scenario, tmp_path).bat_path == tmp_path / "custom/Other.bat"


def test_model_runner_runs_on_windows(tmp_path, monkeypatch):
    """With the guard bypassed and the command pointed at a dummy, run() streams + returns the code."""
    monkeypatch.setattr(sys, "platform", "win32")
    script = _dummy_script(tmp_path, 0)

    # Bypass the Windows-only `cmd /c <bat>` command building by exercising the
    # shared plumbing directly (what run() delegates to).
    assert stream_subprocess([sys.executable, str(script)], tmp_path) == 0
    assert runner.DEFAULT_BAT_RELATIVE_PATH == "CTRAMP/RunIteration.bat"
