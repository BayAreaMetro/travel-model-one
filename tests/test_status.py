"""Tests for `tm1 status` -- what the last run did, read back out of its log.

The thing worth pinning is the resume token.  A run that ends by *failing* prints
its own hint; a run whose harness is killed prints nothing at all, and that is the
case this command exists for.  Getting the token wrong there is expensive in a way
a wrong duration is not: it re-runs hours of Cube, or skips a step that never ran.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psutil
import pytest

from tm1.runner import _iteration_plan
from tm1.status import (
    RunLog,
    Sections,
    _fmt_age,
    _grid_rows,
    _next_key,
    harness_alive,
    harness_pid,
    newest_log,
    read_log,
    read_logs,
    render,
    sections,
    status,
)

#: Rounds the fixture config declares, asserted rather than written twice.
ROUNDS = 3

STEPS = [
    {"copy_inputs": {}},
    {"warmstart": [
        {"hwy_assign": {"job": "warm.job", "skip_if_exists": "hwy/iter0/LOADEA.net"}},
        {"hwy_skims": {"job": "skims.job"}},
    ]},
    {"iterate": {"count": ROUNDS, "steps": [
        {"simulate_ctramp": {}},
        {"hwy_assign": {"job": "loop.job"}},
    ]}},
    {"net2csv": {}},
]


def _log(tmp_path: Path, events: list[tuple[int, str]]) -> Path:
    """Write a run log, *events* being (minutes from start, message)."""
    t0 = datetime(2026, 8, 11, 6, 0, 0, tzinfo=UTC)
    lines = [
        f"{(t0 + timedelta(minutes=m)).strftime('%Y-%m-%d %H:%M:%S')}"
        f"  INFO     tm1.runner                    {text}"
        for m, text in events
    ]
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "tm1_20260811_060000_100.log"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _plan() -> Sections:
    return sections(STEPS)


# --- the plan the config describes ------------------------------------------


def test_sections_split_the_config_into_its_four_parts() -> None:
    """Which section a step is in decides where it is drawn -- the loop is a grid."""
    plan = _plan()

    assert plan.setup == ["copy_inputs"]
    assert plan.warm == ["hwy_assign", "hwy_skims"]
    assert plan.loop == ["simulate_ctramp", "hwy_assign"]
    assert plan.summaries == ["net2csv"]
    assert plan.rounds == ROUNDS


def test_entries_reproduce_the_runners_execution_order() -> None:
    """Same entries, same order as `_iteration_plan` -- the display cannot drift."""
    plan, _ = _iteration_plan(STEPS)

    assert _plan().entries() == plan


# --- reading the log ---------------------------------------------------------


def test_a_finished_step_records_its_wall_clock(tmp_path: Path) -> None:
    """Measured between the Step and Done lines, not parsed back out of the text."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (5, "--- Done: copy_inputs (5.0m) ---"),
    ]))

    assert state.done[("copy_inputs", 1)] == pytest.approx(300)


def test_a_step_skipped_on_its_product_is_not_counted_as_work(tmp_path: Path) -> None:
    """`skip_if_exists` fired: the step is settled, but it cost nothing."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: hwy_assign (iteration 0) -- skipped, "
            "E:/t/hwy/iter0/LOADEA.net exists ---"),
    ]))

    assert ("hwy_assign", 0) in state.skipped
    assert state.done == {}


def test_the_round_comes_off_the_step_line_not_from_counting(tmp_path: Path) -> None:
    """A resumed run starts mid-plan, so position cannot say which round it is in."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 3) ---"),
        (60, "--- Done: simulate_ctramp (1h00m) ---"),
    ]))

    assert list(state.done) == [("simulate_ctramp", 3)]


def test_a_failure_is_attributed_to_the_open_step(tmp_path: Path) -> None:
    """The log names the step in the failure line, but the open step is the truth."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: hwy_assign (iteration 2) ---"),
        (9, "Step hwy_assign failed: Cube job HwyAssign.job exited 2"),
    ]))

    assert state.failed == ("hwy_assign", 2)
    assert state.open_step is None


def test_a_killed_run_leaves_the_step_open(tmp_path: Path) -> None:
    """No Done, no failure, no Finished -- the case the command exists for."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 2) ---"),
    ]))

    assert state.open_step == ("simulate_ctramp", 2)
    assert not state.finished


def test_a_completed_run_is_recognised(tmp_path: Path) -> None:
    """`Finished` distinguishes a real end from stopping on the last step reached."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: net2csv (iteration 3) ---"),
        (1, "--- Done: net2csv (1.0m) ---"),
        (1, "=== Finished projects/base in 15h43m ==="),
    ]))

    assert state.finished


def test_cube_tracebacks_are_not_events(tmp_path: Path) -> None:
    """Unstructured lines land in the log too; they must not shift the state."""
    path = _log(tmp_path, [(0, "--- Step: hwy_assign (iteration 1) ---")])
    with path.open("a", encoding="utf-8") as f:
        f.write("\nTraceback (most recent call last):\n  --- Done: nonsense (1s) ---\n")

    state = read_log(path)

    assert state.open_step == ("hwy_assign", 1)
    assert state.done == {}


def test_logs_accumulate_across_runs(tmp_path: Path) -> None:
    """A resumed run continues an earlier one; run_dir is the shared record.

    Reading only the newest log would report a one-step patch run as though
    nothing else had ever happened, then offer to resume from step one.
    """
    _log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
        (2, "--- Step: hwy_assign (iteration 0) ---"),
        (9, "Step hwy_assign failed: Cube job HwyAssign.job exited 2"),
    ])
    (tmp_path / "logs" / "tm1_20260812_090000_200.log").write_text(
        "2026-08-12 09:00:00  INFO     tm1.runner"
        "                    --- Step: hwy_assign (iteration 0) ---\n"
        "2026-08-12 09:40:00  INFO     tm1.runner"
        "                    --- Done: hwy_assign (40.0m) ---\n",
        encoding="utf-8",
    )

    state = read_logs(tmp_path)

    assert ("copy_inputs", 1) in state.done       # from the first log
    assert ("hwy_assign", 0) in state.done        # the retry succeeded
    assert state.failed is None                   # the older failure is not current
    assert _next_key(_plan(), state) == ("hwy_skims", 0)


def test_newest_log_picks_the_latest_by_name(tmp_path: Path) -> None:
    """Names sort chronologically, so a file copied later is not mistaken for newer."""
    (tmp_path / "logs").mkdir()
    for stamp in ("20260810_120000_1", "20260811_060000_2", "20260809_235959_3"):
        (tmp_path / "logs" / f"tm1_{stamp}.log").write_text("")

    assert newest_log(tmp_path).name == "tm1_20260811_060000_2.log"


# --- the resume token, which is the point ------------------------------------


def test_resume_points_at_the_failed_step(tmp_path: Path) -> None:
    """The failed step re-runs from the start; it is never continued part-way."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: hwy_assign (iteration 2) ---"),
        (9, "Step hwy_assign failed: Cube job HwyAssign.job exited 2"),
    ]))

    assert _next_key(_plan(), state) == ("hwy_assign", 2)


def test_resume_points_at_the_step_that_was_killed_mid_flight(tmp_path: Path) -> None:
    """Nothing printed a hint here -- the harness died before it could."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
        (2, "--- Step: hwy_assign (iteration 0) ---"),
    ]))

    assert _next_key(_plan(), state) == ("hwy_assign", 0)


def test_resume_after_a_clean_stop_names_the_next_unrun_step(tmp_path: Path) -> None:
    """`--until` ends a run with nothing open and nothing failed."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
    ]))

    assert _next_key(_plan(), state) == ("hwy_assign", 0)


def test_a_finished_run_offers_no_resume(tmp_path: Path) -> None:
    """Every entry settled: there is nothing to continue."""
    events = [(0, "--- Step: copy_inputs (iteration 1) ---")]
    state = read_log(_log(tmp_path, events))
    state.done = dict.fromkeys(_plan().entries(), 1.0)
    state.open_step = None

    assert _next_key(_plan(), state) is None


def test_the_command_line_is_printed_verbatim(tmp_path: Path) -> None:
    """It is meant to be copy-pasted, so it has to be a whole command."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 2) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert (
        "tm1 run base_2023_ctramp --resume-at 2:simulate_ctramp" in out
    )


def test_a_step_that_runs_once_needs_no_round_prefix(tmp_path: Path) -> None:
    """The shortest unambiguous form: `net2csv`, not `3:net2csv`."""
    state = read_log(_log(tmp_path, [(0, "--- Step: net2csv (iteration 3) ---")]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert "--resume-at net2csv" in out


# --- is the harness alive: the question --resume-at actually turns on ---------


def test_the_pid_comes_out_of_the_log_name() -> None:
    """Already recorded, so liveness needs nothing new written during a run."""
    pid = 18244

    assert harness_pid(Path(f"tm1_20260811_064512_{pid}.log")) == pid
    # The counter suffix separates two runs started in the same second.
    assert harness_pid(Path(f"tm1_20260811_064512_{pid}_1.log")) == pid
    assert harness_pid(Path("something_else.log")) is None


def test_this_process_reads_as_alive(tmp_path: Path) -> None:
    """The live case, against a real PID -- our own."""
    started = datetime.fromtimestamp(  # noqa: DTZ006
        psutil.Process(os.getpid()).create_time()
    )
    state = RunLog(path=tmp_path / f"tm1_20260811_064512_{os.getpid()}.log")
    state.start = started

    assert harness_alive(state) is True


def test_a_vanished_process_reads_as_dead(tmp_path: Path) -> None:
    """The case the command exists for: the harness died without saying so."""
    state = RunLog(path=tmp_path / "tm1_20260811_064512_999999999.log")
    state.start = datetime(2026, 8, 11, 6, 45, 12, tzinfo=UTC).replace(tzinfo=None)

    assert harness_alive(state) is False


def test_a_recycled_pid_is_not_mistaken_for_the_run(tmp_path: Path) -> None:
    """PIDs are reused. Our own PID, against a log claiming to be from 2026, is not us.

    Without this guard the check is confidently wrong, which is worse than the
    mtime guess it replaces.
    """
    state = RunLog(path=tmp_path / f"tm1_20260811_064512_{os.getpid()}.log")
    state.start = datetime(2026, 8, 11, 6, 45, 12, tzinfo=UTC).replace(tzinfo=None)

    assert harness_alive(state) is False


def test_an_unreadable_log_name_gives_no_verdict(tmp_path: Path) -> None:
    """Unknown is a third answer, not a guess -- the caller falls back to mtimes."""
    state = RunLog(path=tmp_path / "handwritten.log")
    state.start = datetime(2026, 8, 11, 6, tzinfo=UTC).replace(tzinfo=None)

    assert harness_alive(state) is None


def test_a_live_run_is_never_offered_a_resume_command(tmp_path: Path) -> None:
    """Two runs writing one run_dir corrupt each other's networks.

    So a copy-pasteable resume line must not appear beside a running model.
    """
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 2) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path, alive=True)

    assert "--resume-at" not in out
    assert "RUNNING" in out
    assert "still going" in out


def test_a_dead_harness_is_stated_plainly(tmp_path: Path) -> None:
    """No ETA either: there is nothing running for it to be an estimate of."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 2) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path, alive=False)

    assert "harness is gone" in out
    assert "left" not in out
    assert "--resume-at 2:simulate_ctramp" in out


# --- how stale is this ------------------------------------------------------


def test_the_last_activity_and_its_age_are_shown(tmp_path: Path) -> None:
    """Without this, a grid full of durations gives no clue which week it is from."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert "last activity 2026-08-11 06:02" in out
    assert "ago)" in out
    assert "log tm1_20260811_060000_100.log" in out


def test_age_is_reported_in_days_once_it_passes_one() -> None:
    """`_fmt_elapsed` would render a month-old run as 744h00m."""
    assert _fmt_age(3 * 3600) == "3h00m"
    assert _fmt_age(50 * 3600) == "2d 2h"
    assert _fmt_age(30 * 86400) == "30d 0h"


def test_repeated_runs_are_counted_from_the_first(tmp_path: Path) -> None:
    """A run_dir worked on over several days should say so, not look like one run."""
    _log(tmp_path, [(0, "--- Step: copy_inputs (iteration 1) ---")])
    (tmp_path / "logs" / "tm1_20260812_090000_200.log").write_text(
        "2026-08-12 09:00:00  INFO     tm1.runner"
        "                    --- Step: hwy_assign (iteration 0) ---\n",
        encoding="utf-8",
    )

    state = read_logs(tmp_path)
    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert state.attempts == len(list((tmp_path / "logs").glob("*.log")))
    assert "2 runs since 2026-08-11" in out


# --- the grid: one table, round 0 as its own column --------------------------


def test_warm_start_only_steps_are_slotted_into_loop_order() -> None:
    """Merged, not concatenated, so a step lands beside the one it stands in for."""
    plan = sections([
        {"warmstart": [{"a": {}}, {"seed": {}}, {"c": {}}, {"only_warm": {}}]},
        {"iterate": {"count": 2, "steps": [
            {"a": {}}, {"average": {}}, {"c": {}},
        ]}},
    ])

    # `seed` sits between a and c in the warm start; `average` between them in the
    # loop.  Both survive, in an order consistent with each list.
    assert _grid_rows(plan) == ["a", "average", "seed", "c", "only_warm"]


def test_a_step_absent_from_a_round_is_blank_not_pending(tmp_path: Path) -> None:
    """`-` means "has not run yet". Nothing planned must not look like that."""
    state = read_log(_log(tmp_path, [(0, "--- Step: net2csv (iteration 3) ---")]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)
    row = next(ln for ln in out.splitlines() if "simulate_ctramp" in ln)

    # simulate_ctramp has no iteration-0 entry: three cells, not four.
    assert row.split() == ["simulate_ctramp", "-", "-", "-"]
    assert "iter 0" in out


def test_a_step_that_ran_outranks_the_same_step_skipped(tmp_path: Path) -> None:
    """A project's history holds both: skipped on one attempt, run on another.

    This is the bug that showed `hwy_assign` as skipped in round 1 when it had
    really run for 30.6 minutes -- the skip came from a different attempt.
    """
    state = read_log(_log(tmp_path, [
        (0, "--- Step: hwy_assign (iteration 1) -- skipped, LOADEA.net exists ---"),
        (1, "--- Step: hwy_assign (iteration 1) ---"),
        (31, "--- Done: hwy_assign (30.6m) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)
    row = next(ln for ln in out.splitlines() if "hwy_assign" in ln)

    assert "30.0m" in row
    assert "skip" not in row


def test_every_step_is_listed_by_name(tmp_path: Path) -> None:
    """Sections are not collapsed to counts: the point is per-step durations."""
    state = read_log(_log(tmp_path, [(0, "--- Step: copy_inputs (iteration 1) ---")]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    for name in ("copy_inputs", "hwy_skims", "simulate_ctramp", "net2csv"):
        assert any(ln.strip().startswith(name) for ln in out.splitlines()), name


def test_no_row_carries_trailing_whitespace(tmp_path: Path) -> None:
    """Blank trailing cells would otherwise pad the line, which breaks diffs."""
    state = read_log(_log(tmp_path, [(0, "--- Step: copy_inputs (iteration 1) ---")]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert all(ln == ln.rstrip() for ln in out.splitlines())


# --- rendering ---------------------------------------------------------------


def test_output_is_plain_ascii(tmp_path: Path) -> None:
    """It is read over ssh; box-drawing and check marks render as mojibake."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
        (2, "--- Step: simulate_ctramp (iteration 1) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert out.isascii()


def test_the_grid_shows_one_column_per_round(tmp_path: Path) -> None:
    """The loop is a grid because a step's cost per round is the thing you read."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: simulate_ctramp (iteration 1) ---"),
        (60, "--- Done: simulate_ctramp (1h00m) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert "round 1" in out
    assert f"round {ROUNDS}" in out
    # Round 1 ran, rounds 2 and 3 have not.
    row = next(ln for ln in out.splitlines() if "simulate_ctramp" in ln)
    assert row.split() == ["simulate_ctramp", "1h00m", "-", "-"]


def test_a_first_run_says_there_is_no_estimate_yet(tmp_path: Path) -> None:
    """Nothing pending has ever run, so there is no history to price from.

    Summing nothing gives 0, and `~0s left` on a four-minute-old run reads as
    "nearly done" — the opposite of the truth.
    """
    state = read_log(_log(tmp_path, [
        (0, "--- Step: copy_inputs (iteration 1) ---"),
        (2, "--- Done: copy_inputs (2.0m) ---"),
        (2, "--- Step: hwy_assign (iteration 0) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path, alive=True)

    assert "no estimate yet" in out
    assert "~0s left" not in out


def test_an_estimate_appears_once_a_step_has_a_precedent(tmp_path: Path) -> None:
    """Round 1's hwy_assign prices rounds 2 and 3."""
    state = read_log(_log(tmp_path, [
        (0, "--- Step: hwy_assign (iteration 1) ---"),
        (30, "--- Done: hwy_assign (30.0m) ---"),
    ]))

    out = render("base_2023_ctramp", _plan(), state, tmp_path, alive=True)

    assert "no estimate yet" not in out
    assert "left" in out


def test_a_complete_run_says_so_instead_of_estimating(tmp_path: Path) -> None:
    """An ETA on a finished run is noise, and reads as though it is still going.

    Completeness comes off the plan, not the `Finished` marker: a run assembled
    from several resumed attempts never logs one.
    """
    state = RunLog(path=tmp_path, elapsed=56580.0)
    state.done = dict.fromkeys(_plan().entries(), 1.0)

    out = render("base_2023_ctramp", _plan(), state, tmp_path)

    assert "15h43m elapsed" in out
    assert "complete" in out
    assert "left" not in out
    assert "--resume-at" not in out


def test_status_says_so_when_nothing_has_run(tmp_path: Path) -> None:
    """A missing run_dir is the normal state before the first run, not an error."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "config.yaml").write_text(
        f'run_dir: "{(tmp_path / "nope").as_posix()}"\nsteps:\n  - copy_inputs: {{}}\n',
        encoding="utf-8",
    )

    assert "nothing run yet" in status(project)
