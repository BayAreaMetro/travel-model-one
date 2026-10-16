"""What a run's log says happened, and whether it is still happening.

Parsing only -- this module opens files and returns facts. It decides nothing and
draws nothing, so it can be pointed at a run that finished last month as readily
as one running now.

Liveness is deliberately answered two ways. The harness process is identified from
the log and checked directly, which is exact; when that is not possible (another
machine, a reused PID) the fallback is the age of the newest file the run wrote,
which is a guess and says so.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import psutil

#: One record in a run log, per ``tm1.FILE_FORMAT``: timestamp, level, logger,
#: message.  Anything else (a Cube traceback, a wrapped line) is not an event.
_LOG_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+\w+\s+\S+\s+(.*)$")
_TIMESTAMP = "%Y-%m-%d %H:%M:%S"

#: The step boundaries the runner logs.  ``Step`` carries the round, so an entry
#: places itself in the plan without counting from the top -- a resumed run starts
#: in the middle, where position alone would be ambiguous.
#:
#: The round is optional because logs written before it was added must still read
#: correctly: mistaking an old log for an empty one would answer "nothing ran", and
#: send someone back to the start of a fifteen-hour run.  Those logs are placed by
#: the iteration banner instead, which the runner has always emitted.
_STEP = re.compile(
    r"--- Step: (\S+)(?: \(iteration (-?\d+)\))?(?: -- skipped, (.+) exists)? ---"
)
_ITERATION = re.compile(r"=== Iteration (-?\d+) of \d+ ===")
_DONE = re.compile(r"--- Done: (\S+) \(")
_SELF_SKIPPED = re.compile(r"--- Skipped: (\S+) ---")
_FAILED = re.compile(r"^Step (\S+) failed: ")
_FINISHED = re.compile(r"^=== Finished .* in (\S+) ===")
#: How far a process's start time may sit from its log's first line and still be
#: the process that wrote it.  A run logs within seconds of starting, so this is
#: slack, not tolerance -- it exists so that a *reused* PID, which will be hours
#: or days out, is rejected.
_PID_REUSE_WINDOW = 60 * 60

# --- what the log says happened ---------------------------------------------


@dataclass
class RunLog:
    """Everything one run log records about step boundaries."""

    path: Path
    start: datetime | None = None
    last: datetime | None = None
    #: (step, round) -> seconds, measured between the Step and Done lines
    done: dict[tuple[str, int], float] = field(default_factory=dict)
    skipped: set[tuple[str, int]] = field(default_factory=set)
    failed: tuple[str, int] | None = None
    #: A step that started and never reported: running now, or killed mid-flight.
    open_step: tuple[str, int] | None = None
    open_since: datetime | None = None
    finished: bool = False
    #: Wall clock actually spent working, summed over attempts.  Not now-minus-first-
    #: log: a run resumed the next morning would count the night as work.
    elapsed: float = 0.0
    #: First timestamp in the oldest log, and the number of logs folded in.  Unlike
    #: `start`, these are never reset per attempt -- they describe the history.
    first_seen: datetime | None = None
    attempts: int = 0
    #: Round most recently announced by an iteration banner, for logs whose step
    #: lines do not carry one.
    round_now: int = 1

    def settled(self, key: tuple[str, int]) -> bool:
        """True once a step has run, skipped or failed -- it will not run again."""
        return key in self.done or key in self.skipped or key == self.failed

    def event(self, text: str, when: datetime) -> None:
        """Fold one log message into the state, if it is a step boundary."""
        if hit := _ITERATION.search(text):
            self.round_now = int(hit.group(1))
        elif hit := _STEP.search(text):
            key = (hit.group(1), int(hit.group(2) or self.round_now))
            if hit.group(3):                      # skipped on its declared product
                self.skipped.add(key)
                self.open_step = None
            else:
                self.open_step, self.open_since = key, when
        elif _FINISHED.search(text):
            self.finished = True
        elif self.open_step is not None and self.open_since is not None:
            self._close(self.open_step, self.open_since, text, when)

    def _close(
        self, step: tuple[str, int], since: datetime, text: str, when: datetime
    ) -> None:
        """Resolve the open step, if this message ends it."""
        if _DONE.search(text):
            self.done[step] = (when - since).total_seconds()
        elif _SELF_SKIPPED.search(text):
            self.skipped.add(step)
        elif _FAILED.search(text):
            self.failed = step
        else:
            return
        self.open_step = None


def newest_log(run_dir: Path) -> Path | None:
    """The most recent run log, by the timestamp in its name.

    Names sort chronologically (``tm1_YYYYmmdd_HHMMSS_pid.log``), so this needs no
    stat call and is not confused by a file copied later than it was written.
    """
    logs = sorted((run_dir / "logs").glob("tm1_*.log"))
    return logs[-1] if logs else None


def _fold(path: Path, state: RunLog) -> RunLog:
    """Replay one log into *state*, as a fresh attempt.

    What *ran* accumulates; what is *currently* true -- failed, open, finished,
    elapsed -- belongs to this attempt alone and is cleared first.
    """
    state.start = state.last = None
    state.failed = state.open_step = state.open_since = None
    state.finished = False
    state.round_now = 1
    state.attempts += 1

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = _LOG_LINE.match(raw)
        if not line:
            continue
        when = datetime.strptime(line.group(1), _TIMESTAMP)  # noqa: DTZ007
        if state.start is None:
            state.start = when
        if state.first_seen is None:
            state.first_seen = when
        state.last = when
        state.event(line.group(2), when)

    if state.start is not None and state.last is not None:
        state.elapsed += (state.last - state.start).total_seconds()
    return state


def read_log(path: Path) -> RunLog:
    """Replay a single run log into the state it describes."""
    return _fold(path, RunLog(path=path))


def read_logs(run_dir: Path) -> RunLog | None:
    """Replay every run log for this project directory, oldest first.

    A project directory accumulates: a resumed run continues where an earlier one
    stopped, and ``skip_if_exists`` already treats the directory as the record of
    what exists.  Reading only the newest log would report a one-step patch run as
    though nothing else had ever happened -- and then offer to resume from step
    one, which is the one answer this command must never give.
    """
    logs = sorted((run_dir / "logs").glob("tm1_*.log"))
    if not logs:
        return None
    state = RunLog(path=logs[-1])
    for path in logs:
        _fold(path, state)
    return state


def harness_pid(log_path: Path) -> int | None:
    """The PID a run log's name carries: ``tm1_<stamp>_<pid>[_<n>].log``."""
    parts = log_path.stem.split("_")
    if len(parts) < 4 or not parts[3].isdigit():  # noqa: PLR2004
        return None
    return int(parts[3])


def harness_alive(state: RunLog) -> bool | None:
    """Is the process that wrote the newest log still running?

    This is the question ``--resume-at`` actually turns on, and the only one with
    an exact answer: resume iff the harness is gone.  ``None`` means it could not
    be told -- an unparseable log name, or a process owned by someone else -- and
    the caller falls back to guessing from file mtimes.

    A live harness is not proof that work is progressing, and a dead one is not
    proof that nothing is: killing the harness orphans the Cube cluster, which
    keeps writing for another twenty minutes.  But it is exactly the right signal
    for *should I restart this*, because the harness is what would be restarted.
    """
    pid = harness_pid(state.path)
    if pid is None or state.start is None:
        return None
    try:
        started = datetime.fromtimestamp(psutil.Process(pid).create_time())  # noqa: DTZ006
    except psutil.NoSuchProcess:
        return False
    except (psutil.Error, OSError, ValueError):
        return None
    # PID reuse: the process holding this number now need not be the one that
    # wrote the log.  A run logs its first line seconds after starting, so a
    # process that began hours from the log's start is a different process.
    return abs((started - state.start).total_seconds()) < _PID_REUSE_WINDOW




def newest_write(run_dir: Path) -> tuple[Path, float] | None:
    """The most recently written model file, and its age in seconds.

    The only evidence available that a quiet run is still alive: a Cube job or
    CT-RAMP writes constantly while it works but logs nothing until it exits.
    Logs are excluded -- they are written by the harness, not by the work.
    """
    newest, newest_mtime = None, 0.0
    for path in run_dir.rglob("*"):
        if "logs" in path.parts or not path.is_file():
            continue
        mtime = path.stat().st_mtime
        if mtime > newest_mtime:
            newest, newest_mtime = path, mtime
    if newest is None:
        return None
    return newest, datetime.now().timestamp() - newest_mtime  # noqa: DTZ005
