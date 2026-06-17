"""Tests for converter.py (MatrixConverter / .tpp -> .omx conversion). Phase 6.

Mirrors test_runner.py: platform guard testable anywhere; the subprocess path is
exercised with a dummy script (guard bypassed, ``runtpp`` swapped for the Python
interpreter) so it runs on any OS without CUBE or the real ``.s`` script.
"""
from __future__ import annotations

import sys

import pytest

from models.travel_model import converter
from models.travel_model.converter import DEFAULT_CONVERSION_SCRIPT, MatrixConverter


def test_run_guards_off_windows(tmp_path):
    with pytest.raises(RuntimeError, match="requires Windows"):
        MatrixConverter(tmp_path).run()


def test_script_path_defaults_to_packaged_script(tmp_path):
    assert MatrixConverter(tmp_path).script_path == DEFAULT_CONVERSION_SCRIPT
    assert DEFAULT_CONVERSION_SCRIPT.is_file()


def test_script_path_override(tmp_path):
    custom = tmp_path / "my_convert.s"
    custom.write_text("; custom\n")
    assert MatrixConverter(tmp_path, custom).script_path == custom


def test_run_with_dummy_script_returns_exit_code(tmp_path, monkeypatch):
    # Bypass the guard, and run the "conversion script" via the Python interpreter
    # instead of `runtpp` so it works on any OS.
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(converter, "CUBE_SCRIPT_RUNNER", sys.executable)
    script = tmp_path / "convert.py"
    script.write_text("import sys\nprint('converted')\nsys.exit(0)\n")

    assert MatrixConverter(tmp_path, script).run() == 0


def test_run_with_dummy_script_propagates_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(converter, "CUBE_SCRIPT_RUNNER", sys.executable)
    script = tmp_path / "convert_fail.py"
    script.write_text("import sys\nsys.exit(2)\n")

    assert MatrixConverter(tmp_path, script).run() == 2


def test_run_missing_script_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")  # get past the guard
    with pytest.raises(FileNotFoundError, match="conversion script not found"):
        MatrixConverter(tmp_path, tmp_path / "nope.s").run()
