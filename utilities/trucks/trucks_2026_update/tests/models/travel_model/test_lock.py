"""Tests for lock.py (RunLock acquisition/release). Phase 2."""
from __future__ import annotations

import json
import os

import pytest

from models.travel_model.lock import RunLock


def test_acquiring_twice_without_releasing_fails(tmp_path):
    lock = RunLock(tmp_path)
    lock.acquire()
    with pytest.raises(RuntimeError, match="already held"):
        RunLock(tmp_path).acquire()


def test_release_then_reacquire_succeeds(tmp_path):
    lock = RunLock(tmp_path)
    lock.acquire()
    lock.release()
    # Should not raise now that the lock is free.
    RunLock(tmp_path).acquire()
    assert (tmp_path / ".runner.lock").exists()


def test_lock_content_includes_pid_and_timestamp(tmp_path):
    lock = RunLock(tmp_path)
    lock.acquire()

    content = json.loads(lock.lock_path.read_text())
    assert content["pid"] == os.getpid()
    assert "started_at" in content and content["started_at"]


def test_release_is_idempotent(tmp_path):
    lock = RunLock(tmp_path)
    lock.acquire()
    lock.release()
    lock.release()  # no error on second release
    assert not lock.lock_path.exists()


def test_context_manager_releases_on_exception(tmp_path):
    with pytest.raises(ValueError):
        with RunLock(tmp_path):
            assert (tmp_path / ".runner.lock").exists()
            raise ValueError("boom")
    # Lock was released despite the exception.
    assert not (tmp_path / ".runner.lock").exists()


def test_acquire_creates_missing_output_root(tmp_path):
    nested = tmp_path / "does" / "not" / "exist"
    RunLock(nested).acquire()
    assert (nested / ".runner.lock").exists()
