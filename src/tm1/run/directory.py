"""Where does this run go?

A run directory is ``{runs_root}/{scenario}_{NNN}``. ``NNN`` -- the run number
-- is given with ``--run-number``, not guessed by this tool.

Nothing is ever deleted or moved aside to make room: a land use update is
``--run-number 2`` beside an intact ``_001``, never a rewrite of it.

No project segment: every run on a machine sits flat under one ``runs_root``,
visible with one directory listing instead of one per project -- both to see
what has run recently and to find what is safe to archive off and delete when
disk space runs short. The cost is that every scenario ID is unique across
every project sharing a ``runs_root``, not just within its own project, so two
projects must not declare the same ID.
"""

import re
from pathlib import Path

#: ``{scenario}_{NNN}``.
_RUN_DIR = re.compile(r"^(?P<scenario>.+)_(?P<run>\d{3})$")

#: Cube and the Java stack are not long-path aware, and a full run nests roughly
#: 160 characters below its own root.  Erroring at the start beats a Cube job
#: failing on a path it cannot open in hour nine.
MAX_RUN_DIR_LEN = 70


def existing_runs(project_root: Path, scenario: str) -> list[tuple[int, Path]]:
    """Every ``{scenario}_{NNN}`` directory for *scenario*, oldest first."""
    root = Path(project_root)
    if not root.is_dir():
        return []
    out = []
    for child in root.iterdir():
        match = _RUN_DIR.match(child.name)
        if child.is_dir() and match and match.group("scenario") == scenario:
            out.append((int(match.group("run")), child))
    return sorted(out)


#: What :func:`resolve` found, and what the caller should do about it.
NEW = "new"          #: nothing there yet -- a fresh directory was made
RESUME = "resume"    #: already there -- *resume* said to continue it


def resolve(
    project_root: Path, scenario: str, run_number: int, *, resume: bool
) -> tuple[Path, str]:
    """``{scenario}_{run_number:03d}``, and whether it already existed.

    Existence is the only question asked here -- not what is inside, not
    whether the config that made it matches this one:

    - already there, and *resume* -> :data:`RESUME`, used as is.
    - already there, and not *resume* -> an error. Running the full pipeline
      into a directory something has already written to would not fail --
      it would just silently mix two attempts together.
    - nothing there, and *resume* -> an error. There is nothing to resume.
    - nothing there, and not *resume* -> a fresh directory, created here.
    """
    path = Path(project_root) / f"{scenario}_{run_number:03d}"
    exists = path.is_dir() and any(path.iterdir())
    if exists and not resume:
        msg = (
            f"{path} already has a run in it. Pass --resume-at to continue it, "
            f"or a different --run-number to start somewhere new."
        )
        raise ValueError(msg)
    if not exists and resume:
        state = "missing" if not path.is_dir() else "empty"
        msg = (
            f"--resume-at needs a run already under way; {path} is {state}. "
            f"Drop --resume-at to start run {run_number:03d} fresh."
        )
        raise ValueError(msg)
    path.mkdir(parents=True, exist_ok=True)
    return path, (RESUME if exists else NEW)


def check_length(run_dir: Path) -> None:
    """Refuse a run directory long enough to push Cube past MAX_PATH."""
    text = str(run_dir)
    if len(text) > MAX_RUN_DIR_LEN:
        msg = (
            f"Run directory is {len(text)} characters, over the {MAX_RUN_DIR_LEN} "
            f"this model can carry:\n  {text}\nA full run nests about 160 more "
            f"below it, and Cube and the Java stack are not long-path aware. "
            f"Shorten TM1_RUNS_ROOT, or the scenario ID."
        )
        raise ValueError(msg)
