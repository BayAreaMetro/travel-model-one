"""Has anything changed since last time?

A fingerprint is a stable hash of **what a run computes**, taken from the parsed
config after the scenario's overrides and *before* ``{env:}`` expansion and
``{key}`` resolution. That ordering is the whole trick: template strings stay
literal, so the same scenario fingerprints identically on every machine, and the
``{scenario}-{NNN}`` inside ``run_dir`` cannot make every run look new.

Removed before hashing:

* **location** -- ``runs_root``, ``run_dir`` and the identity keys. A run is the
  same run wherever it is written.
* **compute** -- ``cluster_nodes``, ``threads``, ``timeout`` and friends. Tuning a
  machine must never invalidate a result, which is also what keeps runs from
  different machines comparable.
* **``logging`` and ``slack``** -- how a run reports, not what it computes.
"""

import copy
import hashlib
import json
from pathlib import Path

#: Top-level keys removed before fingerprinting: where a run is written, and how it
#: talks about itself, are not part of what it computes.
_SKIP_TOP = frozenset({
    "runs_root", "run_dir", "project", "scenario", "run", "logging", "slack",
})

#: Step keys removed before fingerprinting.  Result-neutral by construction: this
#: is the same set a machine is allowed to tune without making its output
#: incomparable with another machine's.
_SKIP_STEP = frozenset({
    "cluster_nodes", "threads", "intrastep_processes", "acc_threads",
    "timeout", "commpath",
})


def _strip(value: object, *, top: bool) -> object:
    """*value* with the keys that must not affect a fingerprint removed."""
    if isinstance(value, dict):
        skip = _SKIP_TOP if top else _SKIP_STEP
        return {
            k: _strip(v, top=False) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
            if k not in skip
        }
    if isinstance(value, list):
        return [_strip(v, top=False) for v in value]
    return value


def fingerprint(cfg: dict, extra_files: dict[str, str] | None = None) -> str:
    """A stable hash of what this run computes.

    *cfg* must be the config with the scenario applied but **not** yet resolved --
    see the module docstring.  *extra_files* maps a label to a content hash, for
    the repo-local files the config points at; they are part of the run even
    though their contents are not in the config.
    """
    payload = {
        "config": _strip(copy.deepcopy(cfg), top=True),
        "files": dict(sorted((extra_files or {}).items())),
    }
    text = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    """The sha256 of one file, read in blocks so a large one is not held whole."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def referenced_files(cfg: dict, config_dir: Path) -> dict[str, str]:
    """Content hashes of the project-local files *cfg* points at.

    A variant job, an alternate properties file, a hook: editing one changes what
    the run does without changing a single value in the config, so the fingerprint
    has to see it.  Deliberately **not** included: ``module:`` targets, which are
    this repo's own code -- consistent with the git commit being recorded rather
    than hashed, and noted here so the omission is a decision rather than a gap.
    """
    config_dir = Path(config_dir)
    found: dict[str, str] = {}
    for value in _strings(cfg):
        # `script:` targets carry an entry point; the file is the part before it.
        candidate = value.split(":")[0] if value.endswith(".py") or ".py:" in value else value
        path = config_dir / candidate
        if candidate and not Path(candidate).is_absolute() and path.is_file():
            found[candidate.replace("\\", "/")] = hash_file(path)
    return found


def _strings(value: object) -> list[str]:
    """Every string in a nested structure, for spotting path-like values."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []
