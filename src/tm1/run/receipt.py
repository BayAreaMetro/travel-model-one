"""What a run records about itself: what ran, where, and how it ended.

The receipt is a run's own account of itself, written into its ``.tm1/``. It is
what :mod:`tm1.run.directory` reads to decide whether a directory holds a
finished run, an interrupted one, or something it does not recognise -- and what
a shared index across machines will read for the same reason.

The git commit is **recorded, not fingerprinted**. Hashing it would mark every
case in the project stale on every commit, which trains people to ignore the
signal.
"""

import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: Where a run keeps its own record.
TM1_DIR = ".tm1"

#: The receipt: what ran, from what, where, and how it ended.
RECEIPT = "case.json"

#: The config as executed, fully resolved -- the answer to "what did this run use".
RESOLVED = "config.resolved.yaml"

#: The case applied but not yet templated -- a self-contained config.yaml for this
#: one case, portable to a fresh run_dir.  Copy it into a project directory (with a
#: one-entry cases.yaml) to re-run this exact case even after config.yaml/cases.yaml
#: have since moved on.
CASE_CONFIG = "config.case.yaml"


@dataclass
class Receipt:
    """What a run records about itself, locally and in the shared index."""

    project: str
    case: str
    run: int
    fingerprint: str
    machine: str
    pid: int
    status: str = "running"
    started: str = ""
    ended: str = ""
    git: dict[str, object] = field(default_factory=dict)

    def write(self, run_dir: Path) -> Path:
        """Write the receipt into the run's ``.tm1/``, replacing atomically."""
        path = Path(run_dir) / TM1_DIR / RECEIPT
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        # Replace rather than truncate-and-write: a crash mid-write would otherwise
        # leave a receipt nobody can parse, and an unparseable receipt is worse
        # than an absent one -- it cannot be told from a run still in progress.
        tmp.replace(path)
        return path


def read_receipt(run_dir: Path) -> dict | None:
    """A run's receipt, or None when it has none or it cannot be read.

    An unreadable receipt is treated as absent rather than fatal: it means one
    run's directory is unusable, not that the project cannot be worked on.
    """
    path = Path(run_dir) / TM1_DIR / RECEIPT
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def git_state(repo_root: Path) -> dict[str, object]:
    """The commit a run was launched from, and whether the tree was dirty.

    Recorded for traceability, never fingerprinted: hashing it would mark every
    case in the project stale on every commit.
    """
    def _git(*args: str) -> str | None:
        try:
            out = subprocess.run(  # noqa: S603
                ["git", *args],  # noqa: S607
                cwd=str(repo_root), capture_output=True, text=True, check=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip()

    head = _git("rev-parse", "HEAD")
    if head is None:
        return {}
    return {"head": head, "dirty": bool(_git("status", "--porcelain"))}


def machine_name() -> str:
    """This machine, as the receipt and the shared index name it."""
    return platform.node() or "unknown"
