"""``tm1 status`` -- where the last run got to, and how to pick it up.

Read-only.  It opens the newest run log under ``{proj_dir}/logs`` and the scenario
config, and writes nothing: it can be run against a live run from a second shell
without touching it.

The log is the record and the config is the plan.  Nothing is stored between runs,
so there is no state file to go stale, and a deleted log costs the history rather
than corrupting it.

Its main use is after a run stops without saying so.  The runner prints a
``--resume-at`` hint when a *step* fails, but not when the harness itself dies --
a killed session, a reboot, a machine going to sleep -- and that is exactly when
nobody is watching the console.  This reconstructs the hint from the log.

Whether to resume turns on one question -- is the harness still alive -- and that
is answered exactly, from the PID in the log's filename (:func:`harness_alive`).
File mtimes are the fallback when the process cannot be identified, and they are
wrong in both directions often enough to be a poor primary: see
:data:`_STALLED_AFTER`.

Deliberately plain ASCII: it is read over ssh, in whatever terminal happens to be
in front of you.
"""

import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import psutil

from tm1.config import load_config, resolve_templates
from tm1.runner import (
    _fmt_elapsed,
    _iterate_block,
    _normalize_steps,
    _warmstart_block,
    resume_token,
)
from tm1.steps.simulate_ctramp import DEFAULT_SAMPLE_RATES

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

#: A step open this long with nothing written anywhere in proj_dir reads as a
#: dead run rather than a slow one.  Only consulted when the harness process
#: cannot be identified: it is wrong in both directions.  ``HwyAssign`` runs for
#: 35 minutes and writes its ``.net`` files at the end, so a healthy job looks
#: stalled at minute 31; and a killed harness leaves Cube workers writing for
#: another 25 minutes, so a dead run looks alive.
_STALLED_AFTER = 30 * 60

#: How far a process's start time may sit from its log's first line and still be
#: the process that wrote it.  A run logs within seconds of starting, so this is
#: slack, not tolerance -- it exists so that a *reused* PID, which will be hours
#: or days out, is rejected.
_PID_REUSE_WINDOW = 60 * 60

#: Cell markers.  Words, not symbols -- box-drawing and check marks render as
#: mojibake in half the terminals this gets read in.
_PENDING = "-"
_SKIPPED = "skip"
_FAILED_CELL = "FAIL"

_NAME_WIDTH = 32
_CELL_WIDTH = 9
_SECTION_INDENT = "  "
_STEP_INDENT = "    "


# --- what the config says will run ------------------------------------------


@dataclass
class Sections:
    """The four parts of a run, in the order the config writes them."""

    setup: list[str] = field(default_factory=list)
    warm: list[str] = field(default_factory=list)
    loop: list[str] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    rounds: int = 1

    def entries(self) -> list[tuple[str, int]]:
        """Every ``(step, round)`` the config plans, in execution order."""
        entries = [(n, 1) for n in self.setup]
        entries += [(n, 0) for n in self.warm]
        for rnd in range(1, self.rounds + 1):
            entries += [(n, rnd) for n in self.loop]
        return entries + [(n, self.rounds) for n in self.summaries]


def sections(steps_cfg: object) -> Sections:
    """Split the config into setup / warm start / loop / summaries.

    The same walk :func:`tm1.runner._iteration_plan` does, kept separate because
    the plan is a flat list and the display is not: the loop is a grid, and which
    section a step belongs to is what decides where it is drawn.
    """
    found = Sections()
    seen_loop = False
    for name, step_cfg in _normalize_steps(steps_cfg):
        if name == "warmstart":
            found.warm = [n for n, _ in _warmstart_block(step_cfg)]
        elif name == "iterate":
            found.rounds, body = _iterate_block(step_cfg, None)
            found.loop = [n for n, _ in body]
            seen_loop = True
        elif seen_loop:
            found.summaries.append(name)
        else:
            found.setup.append(name)
    return found


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


def newest_log(proj_dir: Path) -> Path | None:
    """The most recent run log, by the timestamp in its name.

    Names sort chronologically (``tm1_YYYYmmdd_HHMMSS_pid.log``), so this needs no
    stat call and is not confused by a file copied later than it was written.
    """
    logs = sorted((proj_dir / "logs").glob("tm1_*.log"))
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


def read_logs(proj_dir: Path) -> RunLog | None:
    """Replay every run log for this project directory, oldest first.

    A project directory accumulates: a resumed run continues where an earlier one
    stopped, and ``skip_if_exists`` already treats the directory as the record of
    what exists.  Reading only the newest log would report a one-step patch run as
    though nothing else had ever happened -- and then offer to resume from step
    one, which is the one answer this command must never give.
    """
    logs = sorted((proj_dir / "logs").glob("tm1_*.log"))
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


#: The two Cube images a running job owns: the master interpreter and its
#: cluster nodes.  Matched case-insensitively -- Windows reports both spellings
#: (``RUNTPP.EXE``, ``Voyager.exe``) depending on how the process was started.
_CUBE_IMAGES = frozenset({"runtpp.exe", "voyager.exe"})

#: Seconds between the two CPU samples.  Long enough that a working job is
#: unambiguous (a 48-node assignment accrues tens of CPU-seconds), short enough
#: that ``tm1 status`` still feels immediate.
_CPU_SAMPLE = 2.0


@dataclass
class CubeProbe:
    """What the Cube processes of one run are doing, right now.

    CPU time is the only signal that separates *working* from *wedged*: Cube
    buffers its ``.PRN`` output and can leave every file untouched for minutes
    while computing, so file mtimes answer a different question (see
    :func:`newest_write`).  A job hung waiting on a licence holds its processes
    open and burns nothing.

    This reports; it does not judge.  A reader who sees 48 nodes and no CPU
    knows what that means, and nothing here acts on the answer -- which is what
    keeps the probe free of the false-positive risk that a killing watchdog has.
    """

    master: int
    nodes: int
    #: CPU-seconds accrued across every matched process during the sample.
    cpu_delta: float
    window: float
    #: Files in the cluster's commpath, or ``None`` when the job has no cluster.
    commpath_files: int | None


def _cube_cmdline(proc: psutil.Process) -> list[str] | None:
    """A live process's argv, or ``None`` if it cannot be read as Cube's.

    Both lookups race the process exiting, and ``cmdline()`` is denied outright
    for another user's processes.  Every failure means *cannot tell*, which is
    not the same as *not running* -- so they all drop the process rather than
    letting it count as evidence either way.
    """
    try:
        if proc.name().lower() not in _CUBE_IMAGES:
            return None
        return proc.cmdline()
    except (psutil.Error, OSError):
        return None


def _owns(cmdline: Iterable[str], proj_dir: Path) -> bool:
    r"""True if this Cube process is working for ``proj_dir``.

    Every Cube process a run starts names the project directory in its argv --
    the master through the ``.job`` path, each node through its
    ``commpath\\CTRAMP<n>.script``.  That is what separates this run's processes
    from a second scenario's on the same machine, so the harness never reports
    on, and a caller never acts on, someone else's run.

    Compared with separators folded and case ignored: the config writes forward
    slashes, Windows hands back backslashes, and drive letters vary in case.
    The match must end on a path boundary -- a plain prefix test claims
    ``base_2023_ctramp_v2``'s processes as ``base_2023_ctramp``'s.
    """
    want = str(proj_dir).replace("\\", "/").casefold().rstrip("/")
    for arg in cmdline:
        folded = arg.replace("\\", "/").casefold()
        if folded == want or folded.startswith(want + "/"):
            return True
    return False


def _commpath_of(cmdline: Iterable[str]) -> Path | None:
    """The cluster directory a node argv points at, if this is a node.

    Taken from the argv rather than assumed to be ``proj_dir/commpath``: a step
    may set ``commpath:`` itself, and the transit jobs run from a subdirectory
    while still pointing their cluster at the project root.
    """
    for arg in cmdline:
        if arg.replace("\\", "/").casefold().endswith(".script"):
            return Path(arg).parent
    return None


def probe_cube(
    proj_dir: Path,
    procs: Iterable[psutil.Process] | None = None,
    sample: float = _CPU_SAMPLE,
) -> CubeProbe | None:
    """Sample the Cube processes running for ``proj_dir``, or ``None`` if none are.

    ``None`` covers both "this step is not a Cube job" -- CT-RAMP is Java, the
    ``command:`` steps are Python -- and "the Cube processes are gone".  The
    caller prints nothing in either case rather than guessing which it is; a
    line reading *no Cube processes* under a running Java step would be true and
    still read as an alarm.
    """
    found: list[tuple[psutil.Process, list[str]]] = []
    for proc in procs if procs is not None else psutil.process_iter():
        cmdline = _cube_cmdline(proc)
        if cmdline and _owns(cmdline, proj_dir):
            found.append((proc, cmdline))
    if not found:
        return None

    before = _cpu_total(p for p, _ in found)
    time.sleep(sample)
    after = _cpu_total(p for p, _ in found)

    commpath = next(
        (c for _, cmdline in found if (c := _commpath_of(cmdline)) is not None), None
    )
    return CubeProbe(
        master=sum(1 for _, cmdline in found if _commpath_of(cmdline) is None),
        nodes=sum(1 for _, cmdline in found if _commpath_of(cmdline) is not None),
        cpu_delta=max(0.0, after - before),
        window=sample,
        commpath_files=_count_files(commpath) if commpath else None,
    )


def _cpu_total(procs: Iterable[psutil.Process]) -> float:
    """CPU-seconds accrued across processes, skipping any that have exited."""
    total = 0.0
    for proc in procs:
        try:
            times = proc.cpu_times()
        except (psutil.Error, OSError):
            continue
        total += times.user + times.system
    return total


def _count_files(commpath: Path) -> int | None:
    """Files in the cluster directory, or ``None`` if it cannot be read."""
    try:
        return sum(1 for _ in commpath.iterdir())
    except OSError:
        return None


def newest_write(proj_dir: Path) -> tuple[Path, float] | None:
    """The most recently written model file, and its age in seconds.

    The only evidence available that a quiet run is still alive: a Cube job or
    CT-RAMP writes constantly while it works but logs nothing until it exits.
    Logs are excluded -- they are written by the harness, not by the work.
    """
    newest, newest_mtime = None, 0.0
    for path in proj_dir.rglob("*"):
        if "logs" in path.parts or not path.is_file():
            continue
        mtime = path.stat().st_mtime
        if mtime > newest_mtime:
            newest, newest_mtime = path, mtime
    if newest is None:
        return None
    return newest, datetime.now().timestamp() - newest_mtime  # noqa: DTZ005


# --- rendering ---------------------------------------------------------------


def _estimate_remaining(plan: Sections, state: RunLog) -> float | None:
    """Seconds of work left, priced from what the same step cost earlier.

    ``None`` when nothing still pending has ever run -- the whole of a first run.
    There is no history to price from, and reporting the sum of nothing as ``0s``
    reads as *nearly done* on a run that has barely started.

    Otherwise rough by construction, and a floor: a step never yet run contributes
    nothing rather than a guess.  ``simulate_ctramp`` is scaled by the sample-rate
    ramp, the one step whose cost changes between rounds by a known factor.
    """
    priced = {name: seconds for (name, _), seconds in state.done.items()}
    base_rate = DEFAULT_SAMPLE_RATES.get(1, 0.50)
    remaining = 0.0
    known = False

    for name, rnd in plan.entries():
        if state.settled((name, rnd)) or (name, rnd) == state.open_step:
            continue
        cost = priced.get(name)
        if cost is None:
            continue
        known = True
        if name == "simulate_ctramp":
            cost *= DEFAULT_SAMPLE_RATES.get(rnd, 0.50) / base_rate
        remaining += cost
    return remaining if known else None


def _cell(name: str, rnd: int, state: RunLog, planned: set[tuple[str, int]]) -> str:
    """One square of the grid.

    Blank where the config plans nothing -- the warm start runs no demand model,
    the loop has no ``seed_average_networks`` -- which must not read as pending.

    ``done`` outranks ``skipped`` because a step can be both across a project's
    history: skipped on one attempt, actually run on another.  It ran.
    """
    key = (name, rnd)
    if key not in planned:
        return ""
    if key == state.failed:
        return _FAILED_CELL
    if key == state.open_step:
        return ">" + _fmt_elapsed(_open_for(state))
    if key in state.done:
        return _fmt_elapsed(state.done[key])
    if key in state.skipped:
        return _SKIPPED
    return _PENDING


def _grid_rows(plan: Sections) -> list[str]:
    """Row order for the grid: loop order, with warm-start-only steps slotted in.

    The two lists share fourteen names.  Merging rather than concatenating keeps
    both orders, so ``seed_average_networks`` lands where the loop runs
    ``average_network_volumes`` -- which is the step it stands in for, round 0
    having no earlier round to average against.
    """
    in_loop = set(plan.loop)
    rows: list[str] = []
    at = 0
    for name in plan.loop:
        if name in plan.warm[at:]:
            while plan.warm[at] != name:
                if plan.warm[at] not in in_loop:
                    rows.append(plan.warm[at])
                at += 1
            at += 1
        rows.append(name)
    return rows + [n for n in plan.warm[at:] if n not in in_loop]


def _fmt_age(seconds: float) -> str:
    """Wall-clock staleness, which unlike a step duration can run to days.

    ``_fmt_elapsed`` would render a month-old run as ``744h00m``; the question
    being answered here is "is this last week's run or this morning's".
    """
    days, rest = divmod(int(max(seconds, 0)), 86400)
    return f"{days}d {rest // 3600}h" if days else _fmt_elapsed(seconds)


def _provenance(state: RunLog) -> str:
    """When this run last did anything, and out of which log.

    There is no *who*: the model server has one shared login, so nothing recorded
    by the OS distinguishes one person's run from another's.
    """
    if state.last is None:
        return ""
    age = (datetime.now() - state.last).total_seconds()  # noqa: DTZ005
    parts = [f"last activity {state.last:%Y-%m-%d %H:%M} ({_fmt_age(age)} ago)"]
    if state.attempts > 1 and state.first_seen is not None:
        # Worth saying, because it changes how the table reads: the durations
        # below are not one sitting, they are assembled from several.
        parts.append(
            f"assembled from {state.attempts} runs since {state.first_seen:%Y-%m-%d}"
        )
    parts.append(f"log {state.path.name}")
    return "  " + "  |  ".join(parts)


def _open_for(state: RunLog) -> float:
    """Seconds the currently-open step has been open."""
    if state.open_since is None:
        return 0.0
    return (datetime.now() - state.open_since).total_seconds()  # noqa: DTZ005


def _block(
    label: str,
    names: list[str],
    rounds: list[int],
    state: RunLog,
    planned: set[tuple[str, int]],
    columns: bool = False,
) -> list[str]:
    """A section header carrying its progress, then one line per step."""
    keys = [(n, r) for n in names for r in rounds if (n, r) in planned]
    settled = sum(1 for k in keys if state.settled(k))
    count = f"{settled}/{len(keys)}"

    lines = [f"{_SECTION_INDENT}{label:<{_NAME_WIDTH + 2}}{count:>{_CELL_WIDTH}}"]
    if columns:
        heads = "".join(
            ("iter 0" if r == 0 else f"round {r}").rjust(_CELL_WIDTH) for r in rounds
        )
        lines.append(f"{_STEP_INDENT}{'':<{_NAME_WIDTH}}{heads}")
    lines += [
        f"{_STEP_INDENT}{name:<{_NAME_WIDTH}}"
        + "".join(_cell(name, r, state, planned).rjust(_CELL_WIDTH) for r in rounds)
        for name in names
    ]
    return [*lines, ""]


def _verdict(plan: Sections, state: RunLog, alive: bool | None) -> list[str]:
    """The words at the end of the header: is this run going, stopped, or done?"""
    # Completeness is read off the plan, not off the `Finished` marker: a run
    # assembled from several resumed attempts never logs one, and logs written
    # before that line existed have none either.
    if _next_key(plan, state) is None:
        return ["complete"]
    if state.failed:
        return ["FAILED"]

    estimate = _estimate_remaining(plan, state)
    left = "no estimate yet" if estimate is None else f"~{_fmt_elapsed(estimate)} left"
    if alive is True:
        return [f"running (pid {harness_pid(state.path)})", left]
    if alive is False:
        # No estimate: there is nothing running for it to be an estimate of.
        return ["stopped, harness is gone"]
    if state.open_step and _open_for(state) > _STALLED_AFTER:
        return ["stalled or stopped"]
    return [left]


def _header(name: str, plan: Sections, state: RunLog, alive: bool | None) -> str:
    """The one line that answers "should I be worried"."""
    keys = plan.entries()
    settled = sum(1 for k in keys if state.settled(k))
    rnd = state.open_step[1] if state.open_step else _last_round(state)

    return "  |  ".join([
        name,
        f"round {rnd} of {plan.rounds}",
        f"{settled}/{len(keys)} steps",
        f"{_fmt_elapsed(state.elapsed)} elapsed",
        *_verdict(plan, state, alive),
    ])


def _last_round(state: RunLog) -> int:
    """The round the run reached, for a run with nothing currently open."""
    return max((r for _, r in (*state.done, *state.skipped) if r > 0), default=1)


def _next_key(plan: Sections, state: RunLog) -> tuple[str, int] | None:
    """The entry a resumed run should start at.

    The failed or open one if there is one -- both re-run from the start, since a
    killed Cube job leaves partial files -- otherwise the first entry that never
    settled.  ``None`` means there is nothing left to run.
    """
    if state.failed:
        return state.failed
    if state.open_step:
        return state.open_step
    return next((k for k in plan.entries() if not state.settled(k)), None)


def _last_write_line(proj_dir: Path) -> list[str]:
    """The newest write under ``proj_dir``, as one indented line, if there is one."""
    write = newest_write(proj_dir)
    if write is None:
        return []
    path, age = write
    return [
        f"          newest write {path.relative_to(proj_dir)}, {_fmt_elapsed(age)} ago"
    ]


def _cube_lines(probe: CubeProbe | None) -> list[str]:
    """The Cube probe as indented lines, if there was anything to probe.

    Facts only, and deliberately no verdict: ``+0.0 CPU-s`` beside 48 nodes says
    *wedged* to anyone reading it, without the harness having to be right about
    it.  Naming a healthy run stalled is the expensive mistake here -- it is what
    a mtime-based watchdog did once already, and recovering the licence
    afterwards cost more than the hang would have.
    """
    if probe is None:
        return []
    procs = f"{probe.master} master + {probe.nodes} nodes"
    lines = [f"          cube     {procs}, +{probe.cpu_delta:.1f} CPU-s over {probe.window:.0f}s"]
    if probe.commpath_files is not None:
        lines.append(f"          commpath {probe.commpath_files} files")
    return lines


def _footer(
    scenario: str, plan: Sections, state: RunLog, proj_dir: Path, alive: bool | None
) -> list[str]:
    """What stopped the run, and the command that continues it.

    A live harness gets no resume command.  Printing a copy-pasteable one beside
    a running model invites starting a second one on top of it, and two runs
    writing the same ``proj_dir`` corrupt each other's networks.
    """
    resume = _next_key(plan, state)
    if resume is None:
        return []

    if alive is True and state.open_step:
        name, rnd = state.open_step
        return [
            f"  RUNNING  {name} (round {rnd}), started "
            f"{_fmt_elapsed(_open_for(state))} ago, harness pid "
            f"{harness_pid(state.path)}",
            *_last_write_line(proj_dir),
            # Only a live run is worth the two-second CPU sample, and only here
            # is the answer actionable.
            *_cube_lines(probe_cube(proj_dir)),
            "          nothing to do -- it is still going.",
        ]

    lines: list[str] = []
    if state.failed:
        name, rnd = state.failed
        lines += [f"  FAILED  {name} in round {rnd}", f"          {state.path}"]
    elif state.open_step:
        name, rnd = state.open_step
        lines.append(
            f"  OPEN    {name} (round {rnd}) started "
            f"{_fmt_elapsed(_open_for(state))} ago and never reported"
        )
        lines += _last_write_line(proj_dir)
        lines.append(
            "          harness pid is gone -- resume:" if alive is False
            else "          if that is not moving, the run is gone -- resume:"
        )

    token = resume_token(plan.entries(), *resume)
    return [*lines, "", f"  tm1 run --scenario {scenario} --resume-at {token}"]


def render(
    scenario: str,
    plan: Sections,
    state: RunLog,
    proj_dir: Path,
    alive: bool | None = None,
) -> str:
    """The whole view, as one block of text.

    *alive* is whether the harness process is still running -- ``None`` when that
    could not be established, which falls back to reading file mtimes.
    """
    planned = set(plan.entries())
    lines = ["", _header(scenario, plan, state, alive), _provenance(state), ""]

    if plan.setup:
        lines += _block("setup (once)", plan.setup, [1], state, planned)

    grid = _grid_rows(plan)
    if grid:
        # Round 0 is a column rather than its own block: the warm start is a loop
        # round minus the demand model, and reading it beside rounds 1-3 is what
        # shows that -- including where it deliberately differs.
        rounds = ([0] if plan.warm else []) + list(range(1, plan.rounds + 1))
        lines += _block("loop", grid, rounds, state, planned, columns=True)

    if plan.summaries:
        lines += _block(
            "summaries (once)", plan.summaries, [plan.rounds], state, planned
        )

    footer = _footer(scenario, plan, state, proj_dir, alive)
    body = [*lines, *(["", *footer] if footer else []), ""]
    # Rows whose trailing cells are blank would otherwise carry the padding.
    return "\n".join(line.rstrip() for line in body)


def status(scenario_dir: Path) -> str:
    """Render the newest run's status, or say why there is nothing to show."""
    scenario_dir = Path(scenario_dir).resolve()
    resolved = resolve_templates(load_config(scenario_dir))
    cfg: dict = resolved if isinstance(resolved, dict) else {}
    proj_dir = Path(cfg["proj_dir"])

    if not proj_dir.is_dir():
        return f"\n  {scenario_dir.name}: nothing run yet -- {proj_dir} does not exist.\n"

    state = read_logs(proj_dir)
    if state is None:
        return f"\n  {scenario_dir.name}: no run logs in {proj_dir / 'logs'}.\n"

    return render(
        scenario_dir.name,
        sections(cfg.get("steps") or []),
        state,
        proj_dir,
        harness_alive(state),
    )
