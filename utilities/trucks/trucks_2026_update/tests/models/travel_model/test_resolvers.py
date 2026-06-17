"""Tests for resolvers.py (LocalSource / GitHubSource resolution). Phase 3.

GitHub tests mock ``requests.get`` so they stay offline and fast (per §12.0 /
Phase 3 exit check: real network behavior is confirmed once, manually).
"""
from __future__ import annotations

import pytest

from models.travel_model import resolvers
from models.travel_model.config import GitHubSource, LocalSource

PERMALINK_SHA = "a1b2c3d4e5f6"  # all-hex ref → treated as a pinned permalink
BRANCH_HEAD_SHA = "f" * 40


class _FakeResponse:
    """Minimal stand-in for a ``requests`` response."""

    def __init__(self, status_code: int = 200, content: bytes = b"", json_data=None):
        self.status_code = status_code
        self.content = content
        self._json = json_data

    def json(self):
        return self._json


def _github(ref: str) -> GitHubSource:
    return GitHubSource(
        url="https://github.com/BayAreaMetro/travel-model-one/blob/x/y.job",
        owner="BayAreaMetro",
        repo="travel-model-one",
        ref=ref,
        file_path="model-files/scripts/nonres/TruckTimeOfDay.job",
    )


def test_resolve_local_copies_content(tmp_path):
    src = tmp_path / "edit.job"
    src.write_text("edited body\n")
    dest = tmp_path / "scenario" / "CTRAMP" / "x.job"

    result = resolvers.resolve_source(LocalSource(path=str(src)), dest)

    assert result is None  # local sources have no commit SHA
    assert dest.read_text() == "edited body\n"


def test_resolve_local_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolvers.resolve_local(LocalSource(path=str(tmp_path / "nope")), tmp_path / "d")


def test_resolve_github_permalink_returns_url_sha(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return _FakeResponse(200, content=b"real repo content")

    monkeypatch.setattr(resolvers.requests, "get", fake_get)
    dest = tmp_path / "out.job"

    sha = resolvers.resolve_github(_github(PERMALINK_SHA), dest)

    assert sha == PERMALINK_SHA
    assert dest.read_bytes() == b"real repo content"
    # Permalink: no API lookup, just the pinned raw fetch.
    assert len(calls) == 1
    assert f"/{PERMALINK_SHA}/" in calls[0]
    assert calls[0].startswith("https://raw.githubusercontent.com/")


def test_resolve_github_branch_queries_api_for_sha(tmp_path, monkeypatch):
    seen = []

    def fake_get(url, **_kwargs):
        seen.append(url)
        if url.startswith(resolvers.GITHUB_API_BASE):
            return _FakeResponse(200, json_data={"sha": BRANCH_HEAD_SHA})
        return _FakeResponse(200, content=b"branch content")

    monkeypatch.setattr(resolvers.requests, "get", fake_get)
    dest = tmp_path / "out.job"

    sha = resolvers.resolve_github(_github("tm1.7_truck_updates"), dest)

    assert sha == BRANCH_HEAD_SHA
    assert dest.read_bytes() == b"branch content"
    # Branch: one API call to resolve the SHA, then a fetch pinned to that SHA.
    assert seen[0].startswith(resolvers.GITHUB_API_BASE)
    assert f"/{BRANCH_HEAD_SHA}/" in seen[1]


def test_resolve_github_404_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        resolvers.requests, "get", lambda url, **_k: _FakeResponse(404)
    )
    with pytest.raises(RuntimeError, match="failed to fetch GitHub source"):
        resolvers.resolve_github(_github(PERMALINK_SHA), tmp_path / "out.job")


def test_resolve_github_branch_lookup_failure_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        resolvers.requests, "get", lambda url, **_k: _FakeResponse(404)
    )
    with pytest.raises(RuntimeError, match="failed to resolve GitHub ref"):
        resolvers.resolve_github(_github("no-such-branch"), tmp_path / "out.job")


def test_resolve_source_dispatches_github(tmp_path, monkeypatch):
    monkeypatch.setattr(
        resolvers.requests,
        "get",
        lambda url, **_k: _FakeResponse(200, content=b"body"),
    )
    sha = resolvers.resolve_source(_github(PERMALINK_SHA), tmp_path / "out.job")
    assert sha == PERMALINK_SHA


def test_raw_url_transform():
    src = _github("main")
    assert src.raw_url == (
        "https://raw.githubusercontent.com/BayAreaMetro/travel-model-one/"
        "main/model-files/scripts/nonres/TruckTimeOfDay.job"
    )
