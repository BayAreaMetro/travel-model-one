"""Drawing a run: the grid, the verdict, and the line telling you how to resume.

Everything here is presentation. It takes the plan (as :class:`Sections`) and what
happened (as :class:`~tm1.status.read.RunLog`) and returns text.

:class:`Sections` lives here rather than with the reading because it is a *layout*:
the config gives a flat list of ``(step, round)``, and which of the four sections a
step belongs to is what decides where on the grid it is drawn.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cube.process import CubeProbe, probe_cube
from tm1 import fmt_elapsed
from tm1.run.iterations import iterate_block, normalize_steps, resume_token
from tm1.status.read import RunLog, harness_pid, newest_write

#: A step open this long with nothing written anywhere in run_dir reads as a
#: dead run rather than a slow one.  Only consulted when the harness process
#: cannot be identified: it is wrong in both directions.  ``HwyAssign`` runs for
#: 35 minutes and writes its ``.net`` files at the end, so a healthy job looks
#: stalled at minute 31; and a killed harness leaves Cube workers writing for
#: another 25 minutes, so a dead run looks alive.
_STALLED_AFTER = 30 * 60
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
    #: ``simulate_ctramp``'s sample rate per round, as the project states it.
    #: Empty when the config does not say, which costs an estimate, not a crash.
    sample_rates: dict[int, float] = field(default_factory=dict)

    def entries(self) -> list[tuple[str, int]]:
        """Every ``(step, round)`` the config plans, in execution order."""
        entries = [(n, 1) for n in self.setup]
        entries += [(n, 0) for n in self.warm]
        for rnd in range(1, self.rounds + 1):
            entries += [(n, rnd) for n in self.loop]
        return entries + [(n, self.rounds) for n in self.summaries]


def sections(steps_cfg: object) -> Sections:
    """Split the config into setup / warm start / loop / summaries.

    The same walk :func:`tm1.run.iterations.iteration_plan` does, kept separate
    because the plan is a flat list and the display is not: the loop is a grid,
    and which section a step belongs to is what decides where it is drawn.
    """
    found = Sections()
    seen_loop = False
    for name, step_cfg in normalize_steps(steps_cfg):
        if name == "iterate":
            found.rounds, body, zero_idx = iterate_block(step_cfg, None)
            found.warm = [
                n for idx, (n, c) in enumerate(body)
                if idx >= zero_idx and c.get("skip_iteration") != 0
            ]
            found.loop = [
                n for idx, (n, c) in enumerate(body)
                if idx < zero_idx or c.get("only_iteration") != 0
            ]
            found.sample_rates = _sample_rates(body, found.rounds)
            seen_loop = True
        elif seen_loop:
            found.summaries.append(name)
        else:
            found.setup.append(name)
    return found


def _sample_rates(body: list[tuple[str, object]], rounds: int) -> dict[int, float]:
    """``simulate_ctramp``'s rate for each round, read off the project config.

    ``status`` is read-only and must survive a config the runner would reject,
    so anything it cannot read as a rate is left out rather than raised on.  The
    cost of leaving it out is a rougher estimate.
    """
    cfg = next(
        (c for n, c in body if n == "simulate_ctramp" and isinstance(c, dict)), None
    )
    spec = cfg.get("sample_rate") if cfg else None

    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        return dict.fromkeys(range(1, rounds + 1), float(spec))

    rates: dict[int, float] = {}
    if isinstance(spec, dict):
        for key, value in spec.items():
            try:
                rates[int(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return rates


# --- rendering ---------------------------------------------------------------


def _estimate_remaining(plan: Sections, state: RunLog) -> float | None:
    """Seconds of work left, priced from what the same step cost earlier.

    ``None`` when nothing still pending has ever run -- the whole of a first run.
    There is no history to price from, and reporting the sum of nothing as ``0s``
    reads as *nearly done* on a run that has barely started.

    Otherwise rough by construction, and a floor: a step never yet run contributes
    nothing rather than a guess.  ``simulate_ctramp`` is scaled by the project's
    sample-rate ramp, the one step whose cost changes between rounds by a known
    factor.  A round the ramp does not price is left unscaled.
    """
    priced: dict[str, tuple[float, int]] = {}
    for (name, rnd), seconds in state.done.items():
        priced.setdefault(name, (seconds, rnd))
    remaining = 0.0
    known = False

    for name, rnd in plan.entries():
        if state.settled((name, rnd)) or (name, rnd) == state.open_step:
            continue
        measured = priced.get(name)
        if measured is None:
            continue
        known = True
        cost, measured_round = measured
        if name == "simulate_ctramp":
            this = plan.sample_rates.get(rnd)
            base = plan.sample_rates.get(measured_round)
            if this and base:
                cost *= this / base
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
        return ">" + fmt_elapsed(_open_for(state))
    if key in state.done:
        return fmt_elapsed(state.done[key])
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
    return f"{days}d {rest // 3600}h" if days else fmt_elapsed(seconds)


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
    left = "no estimate yet" if estimate is None else f"~{fmt_elapsed(estimate)} left"
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
        f"{fmt_elapsed(state.elapsed)} elapsed",
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


def _last_write_line(run_dir: Path) -> list[str]:
    """The newest write under ``run_dir``, as one indented line, if there is one."""
    write = newest_write(run_dir)
    if write is None:
        return []
    path, age = write
    return [
        f"          newest write {path.relative_to(run_dir)}, {fmt_elapsed(age)} ago"
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
    project: str, plan: Sections, state: RunLog, run_dir: Path, alive: bool | None
) -> list[str]:
    """What stopped the run, and the command that continues it.

    A live harness gets no resume command.  Printing a copy-pasteable one beside
    a running model invites starting a second one on top of it, and two runs
    writing the same ``run_dir`` corrupt each other's networks.
    """
    resume = _next_key(plan, state)
    if resume is None:
        return []

    if alive is True and state.open_step:
        name, rnd = state.open_step
        return [
            f"  RUNNING  {name} (round {rnd}), started "
            f"{fmt_elapsed(_open_for(state))} ago, harness pid "
            f"{harness_pid(state.path)}",
            *_last_write_line(run_dir),
            # Only a live run is worth the two-second CPU sample, and only here
            # is the answer actionable.
            *_cube_lines(probe_cube(run_dir)),
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
            f"{fmt_elapsed(_open_for(state))} ago and never reported"
        )
        lines += _last_write_line(run_dir)
        lines.append(
            "          harness pid is gone -- resume:" if alive is False
            else "          if that is not moving, the run is gone -- resume:"
        )

    token = resume_token(plan.entries(), *resume)
    return [*lines, "", f"  tm1 run {project} --resume-at {token}"]


def render(
    project: str,
    plan: Sections,
    state: RunLog,
    run_dir: Path,
    alive: bool | None = None,
) -> str:
    """The whole view, as one block of text.

    *alive* is whether the harness process is still running -- ``None`` when that
    could not be established, which falls back to reading file mtimes.
    """
    planned = set(plan.entries())
    lines = ["", _header(project, plan, state, alive), _provenance(state), ""]

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

    footer = _footer(project, plan, state, run_dir, alive)
    body = [*lines, *(["", *footer] if footer else []), ""]
    # Rows whose trailing cells are blank would otherwise carry the padding.
    return "\n".join(line.rstrip() for line in body)
