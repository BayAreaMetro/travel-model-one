"""Tests for the feedback loop's execution plan.

The plan decides what runs and in which round, which is also what ``--resume-at``
resolves against and what the "planned:" line reports.  It had no coverage; these
pin the shape the conventions lock -- ``iterate: {count, steps}``, the loop starting
at 1, and steps around it taking the first and last rounds.

``RunModel.bat``'s iteration 0 arrives through ``warm_start:`` -- a named slice of
the loop body, run once before the rounds, which is the one branch of
``RunIteration.bat`` that survives structurally (``if %ITER%==0 goto hwyAssign``).
"""

import pytest

from tm1.runner import _flatten_steps, _iteration_plan


def _plan(steps_cfg: dict, override: int | None = None) -> list[tuple[str, int]]:
    return _iteration_plan(steps_cfg, list(steps_cfg.keys()), override)


def _rounds(plan: list[tuple[str, int]], step: str) -> list[int]:
    """Which rounds *step* runs in."""
    return [i for s, i in plan if s == step]


def test_loop_body_repeats_once_per_round() -> None:
    """`count:` is a number of rounds -- RunIteration.bat called N times."""
    plan = _plan({"iterate": {"count": 3, "steps": {"assignment": {}}}})

    assert _rounds(plan, "assignment") == [1, 2, 3]


def test_loop_body_keeps_its_written_order_within_a_round() -> None:
    """Steps run in the order written, which is what makes the config readable."""
    plan = _plan({
        "iterate": {"count": 2, "steps": {"simulate_ctramp": {}, "assignment": {}}}
    })

    assert plan == [
        ("simulate_ctramp", 1), ("assignment", 1),
        ("simulate_ctramp", 2), ("assignment", 2),
    ]


def test_steps_around_the_loop_take_the_first_and_last_rounds() -> None:
    """Before the loop runs at the first round; after it, at the last."""
    plan = _plan({
        "copy_inputs": {},
        "iterate": {"count": 3, "steps": {"assignment": {}}},
        "calibration": {},
    })

    assert _rounds(plan, "copy_inputs") == [1]
    assert _rounds(plan, "calibration") == [3]


def test_iterations_override_replaces_the_count() -> None:
    """`--iterations N` shortens a run without editing the scenario."""
    cfg = {"iterate": {"count": 3, "steps": {"assignment": {}}}}

    assert _rounds(_plan(cfg, override=1), "assignment") == [1]


def test_a_run_without_a_loop_is_a_flat_sequence() -> None:
    """`iterate:` is optional; a preprocess-only run has no rounds at all."""
    plan = _plan({"copy_inputs": {}, "assignment": {}})

    assert plan == [("copy_inputs", 1), ("assignment", 1)]


# --- warm_start: the slice of the body that runs as iteration 0 ------------


def _warm_cfg(warm: list, body: dict | None = None) -> dict:
    body = body or {"hwy_assign": {}, "simulate_ctramp": {}}
    return {"iterate": {"count": 3, "warm_start": warm, "steps": body}}


def test_warm_start_runs_before_the_loop_as_iteration_zero() -> None:
    """RunModel.bat's `set ITER=0` block, calling the same body."""
    plan = _plan(_warm_cfg(["hwy_assign"]))

    assert plan[0] == ("hwy_assign", 0)
    assert _rounds(plan, "hwy_assign") == [0, 1, 2, 3]


def test_warm_start_keeps_its_written_order() -> None:
    """It is a sequence, not a set -- rename must precede seed must precede merge."""
    body = {"a": {}, "b": {}, "c": {}}
    plan = _plan(_warm_cfg(["c", "a"], body))

    assert [n for n, i in plan if i == 0] == ["c", "a"]


def test_a_bare_name_reuses_the_loop_definition() -> None:
    """The point of naming rather than duplicating: one definition, two rounds."""
    body = {"hwy_assign": {"job": "HwyAssign.job", "cluster_nodes": 48}}
    cfg = _warm_cfg(["hwy_assign"], body)

    flat = _flatten_steps(cfg)

    assert flat["hwy_assign"] == {"job": "HwyAssign.job", "cluster_nodes": 48}


def test_an_entry_with_a_body_defines_a_warm_start_only_step() -> None:
    """seed_average_networks exists only at iteration 0; the loop averages instead."""
    cfg = _warm_cfg([{"seed_average_networks": {"module": "tm1.steps.staging:seed"}}])

    flat = _flatten_steps(cfg)

    assert flat["seed_average_networks"] == {"module": "tm1.steps.staging:seed"}
    assert _rounds(_plan(cfg), "seed_average_networks") == [0]


def test_naming_a_step_the_body_does_not_define_is_refused() -> None:
    """A typo would otherwise be a step that silently never runs."""
    with pytest.raises(ValueError, match="does not define"):
        _plan(_warm_cfg(["typo_assign"]))


def test_warm_start_must_be_a_list() -> None:
    """It is an ordered slice of the body, so a mapping would lose the order."""
    with pytest.raises(TypeError, match="list of step names"):
        _plan({"iterate": {"count": 1, "warm_start": {"a": 1}, "steps": {"a": {}}}})


def test_a_loop_with_no_warm_start_is_unchanged() -> None:
    """`warm_start:` is opt-in; ActivitySim scenarios will declare their own."""
    plan = _plan({"iterate": {"count": 2, "steps": {"assignment": {}}}})

    assert _rounds(plan, "assignment") == [1, 2]


def test_empty_loop_body_is_refused() -> None:
    """An empty body is always a mistake, and silently does nothing."""
    with pytest.raises(ValueError, match="cannot be empty"):
        _plan({"iterate": {"count": 3, "steps": {}}})


def test_zero_count_is_refused() -> None:
    """A loop that runs nothing is a typo, not a configuration."""
    with pytest.raises(ValueError, match="must be >= 1"):
        _plan({"iterate": {"count": 0, "steps": {"assignment": {}}}})


def test_iterate_must_be_a_block() -> None:
    """The error shows the shape, since this is the one nesting the config allows."""
    with pytest.raises(TypeError, match="count"):
        _plan({"iterate": 3})
