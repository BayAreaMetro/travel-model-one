"""Where does this run go?

A run directory is ``{runs_root}/{project}/{case}-{NNN}``. ``NNN`` is the run
iteration -- the same case run again after an input is refreshed -- and it exists
so that nothing is ever deleted or moved aside to make room. A land use update
gives you ``-002`` beside an intact ``-001``.

Which one a run uses is decided by its fingerprint::

    the newest -NNN whose fingerprint matches and is not complete   -> resume it
    otherwise                                                       -> max + 1

So re-running an unchanged case continues where it stopped, and running a changed
one starts somewhere new rather than half-overwriting the old result.
"""

import re
from pathlib import Path

from tm1.run.receipt import read_receipt

#: ``{case}-{NNN}``.
_RUN_DIR = re.compile(r"^(?P<case>.+)-(?P<run>\d{3})$")

#: Cube and the Java stack are not long-path aware, and a full run nests roughly
#: 160 characters below its own root.  Erroring at the start beats a Cube job
#: failing on a path it cannot open in hour nine.
MAX_RUN_DIR_LEN = 70


def existing_runs(project_root: Path, case: str) -> list[tuple[int, Path]]:
    """Every ``{case}-{NNN}`` directory for *case*, oldest first."""
    root = Path(project_root)
    if not root.is_dir():
        return []
    out = []
    for child in root.iterdir():
        match = _RUN_DIR.match(child.name)
        if child.is_dir() and match and match.group("case") == case:
            out.append((int(match.group("run")), child))
    return sorted(out)


#: What :func:`allocate` decided, and what the caller should do about it.
NEW = "new"          #: nothing matching on disk -- a fresh directory was made
RESUME = "resume"    #: same fingerprint, unfinished -- continue where it stopped
COMPLETE = "complete"  #: same fingerprint, already finished -- there is nothing to do


def allocate(
    project_root: Path, case: str, fingerprint_: str, *, rerun: bool = False
) -> tuple[int, Path, str]:
    """The run directory for this case, as ``(run_no, path, state)``.

    Reuses the newest run whose fingerprint matches and which did not finish --
    that is a resume, and it is what makes ``--resume-at`` and the per-step
    ``skip_if_exists`` sentinels mean what they say.

    A matching run that *did* finish is reported as :data:`COMPLETE` rather than
    reopened or duplicated: re-running an unchanged case by accident would
    otherwise start a second hundred-gigabyte run and take fifteen hours to say
    what it could have said immediately.  *rerun* is how a caller asks for one
    anyway, and it lands on a fresh number so the finished result stays intact.

    Anything else allocates a fresh number, so a changed case never lands half on
    top of an old result.
    """
    runs = existing_runs(project_root, case)
    for run_no, path in reversed(runs):
        receipt = read_receipt(path)
        if receipt is None or receipt.get("fingerprint") != fingerprint_:
            continue
        if receipt.get("status") == "complete":
            if not rerun:
                return run_no, path, COMPLETE
            break
        return run_no, path, RESUME

    run_no = (runs[-1][0] + 1) if runs else 1
    path = Path(project_root) / f"{case}-{run_no:03d}"
    # Exclusive create: two machines forcing the same stale case at once must not
    # both believe they own the number.  Never check-then-create.
    while True:
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            run_no += 1
            path = Path(project_root) / f"{case}-{run_no:03d}"
            continue
        return run_no, path, NEW


def check_length(run_dir: Path) -> None:
    """Refuse a run directory long enough to push Cube past MAX_PATH."""
    text = str(run_dir)
    if len(text) > MAX_RUN_DIR_LEN:
        msg = (
            f"Run directory is {len(text)} characters, over the {MAX_RUN_DIR_LEN} "
            f"this model can carry:\n  {text}\nA full run nests about 160 more "
            f"below it, and Cube and the Java stack are not long-path aware. "
            f"Shorten TM1_RUNS_ROOT, or the case ID."
        )
        raise ValueError(msg)
