"""Tests for :func:`tm1.assignment.cube.runner.run_cube_job`.

Cube is a licensed binary, so ``runtpp`` is replaced with a fake
``subprocess.run``.  What is verified is the bookkeeping *around* the engine
call -- that every launch path names its log file, and that the engine's
ReturnCode beats runtpp's process exit code.

The interactive/no-cluster path is the one short jobs like ``PrepHwyNet.job``
take.  It is the only one that reads Cube's output through a pipe rather than a
file redirect, and it used to leave ``logfile`` unbound -- so a *successful* job
crashed the runner, and a failing one lost its diagnosis.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tm1.assignment.cube import runner
from tm1.assignment.cube.runner import CubeJobError, run_cube_job


def _fake_runtpp(monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int = 0) -> None:
    """Stand in for ``runtpp.exe`` in an interactive session with no cluster."""
    monkeypatch.setattr(runner, "is_interactive_session", lambda: True)

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:  # noqa: ARG001
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)


def _job(tmp_path: Path) -> Path:
    job = tmp_path / "PrepHwyNet.job"
    job.write_text("; a Cube job\n", encoding="utf-8")
    return job


def test_no_cluster_success_writes_the_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job that succeeds returns cleanly and leaves its output on disk."""
    _fake_runtpp(monkeypatch, "VOYAGER ReturnCode = 0\n")
    cwd = tmp_path / "proj"

    assert run_cube_job(_job(tmp_path), cwd) == 0

    logfile = cwd / "_cube_PrepHwyNet.log"
    assert logfile.exists()
    assert "ReturnCode = 0" in logfile.read_text()


def test_no_cluster_failure_names_a_log_that_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fatal ReturnCode reports the Cube error, pointing at a real file."""
    _fake_runtpp(monkeypatch, "VOYAGER ReturnCode = 2\nF(1) fatal error\n")
    cwd = tmp_path / "proj"

    with pytest.raises(CubeJobError) as exc:
        run_cube_job(_job(tmp_path), cwd)

    logfile = cwd / "_cube_PrepHwyNet.log"
    assert str(logfile) in str(exc.value)
    assert "fatal error" in str(exc.value)
    assert logfile.exists()


def test_engine_returncode_beats_process_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A spurious .NET exit code does not fail an otherwise-successful job."""
    _fake_runtpp(monkeypatch, "VOYAGER ReturnCode = 1\n", returncode=-532462766)

    assert run_cube_job(_job(tmp_path), tmp_path / "proj") == 0
