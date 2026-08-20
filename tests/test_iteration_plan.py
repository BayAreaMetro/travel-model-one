"""Tests for the feedback loop's execution plan.

The plan decides what runs and in which round, which is also what ``--resume-at``
resolves against and what the "planned:" line reports.  The shape the conventions
lock: ``steps:`` is a list of ``name: {config}`` entries run in the order written
(a mapping also works, but cannot repeat a name); ``warmstart:`` and
``iterate: {count, steps}`` are the only nesting, and a step's round comes from
which of them it sits in and from nothing else.

There is no other mechanism.  ``RunModel.bat``'s ``set ITER=0`` pass is
``warmstart:``; its ``if %ITER%==1`` block is warm-start steps that skip on their
products via ``skip_if_exists:``, which the loop refuses.
"""

from pathlib import Path

import pytest

from tm1.runner import (
    _apply_resume,
    _apply_until,
    _iteration_plan,
    _select_steps,
    _skip_target,
)


def _plan(steps_cfg: object, override: int | None = None) -> list[tuple[str, int]]:
    plan, _ = _iteration_plan(steps_cfg, override)
    return plan


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
    """`--iterations N` shortens a run without editing the project config."""
    cfg = {"iterate": {"count": 3, "steps": {"assignment": {}}}}

    assert _rounds(_plan(cfg, override=1), "assignment") == [1]


def test_a_run_without_a_loop_is_a_flat_sequence() -> None:
    """`iterate:` is optional; a preprocess-only run has no rounds at all."""
    plan = _plan({"copy_inputs": {}, "assignment": {}})

    assert plan == [("copy_inputs", 1), ("assignment", 1)]


# --- the list form: order, repetition, and each entry keeping its config ----


def _listform() -> list:
    """Setup, a two-step warm start, the loop, a summary -- the real shape."""
    return [
        {"copy_inputs": {}},
        {"warmstart": [
            {"hwy_assign": {"job": "warm.job",
                            "skip_if_exists": "hwy/iter0/LOADEA.net"}},
            {"hwy_skims": {"job": "skims.job"}},
        ]},
        {"iterate": {"count": 3, "steps": [
            {"simulate_ctramp": {}},
            {"hwy_assign": {"job": "loop.job"}},
            {"hwy_skims": {"job": "skims.job"}},
        ]}},
        {"summarize": {}},
    ]


def test_list_form_runs_in_the_order_written() -> None:
    """The list is the pipeline; nothing reorders it."""
    plan = _plan(_listform())

    assert plan[:3] == [("copy_inputs", 1), ("hwy_assign", 0), ("hwy_skims", 0)]
    assert plan[-1] == ("summarize", 3)


def test_a_name_may_appear_outside_and_inside_the_loop() -> None:
    """The point of the list form: the warm start and the loop each carry their own copy."""
    plan = _plan(_listform())

    assert _rounds(plan, "hwy_assign") == [0, 1, 2, 3]


def test_each_entry_keeps_its_own_config() -> None:
    """Two entries with one name are different steps -- the entry identifies it."""
    _, configs = _iteration_plan(_listform())

    assert configs[("hwy_assign", 0)]["job"] == "warm.job"
    assert configs[("hwy_assign", 2)]["job"] == "loop.job"


# --- warmstart: the round-0 block --------------------------------------------


def test_warmstart_steps_run_at_round_zero() -> None:
    """`warmstart:` is RunModel.bat's `set ITER=0`, stated once for the block."""
    plan = _plan([
        {"warmstart": [{"warm_assign": {}}]},
        {"iterate": {"count": 2, "steps": [{"assignment": {}}]}},
    ])

    assert plan[0] == ("warm_assign", 0)


def test_warmstart_keeps_its_written_order() -> None:
    """It is a pipeline, not a set: transit skims depend on the assignment before them."""
    plan = _plan([{"warmstart": [{"a": {}}, {"b": {}}, {"c": {}}]}])

    assert plan == [("a", 0), ("b", 0), ("c", 0)]


def test_warmstart_steps_may_skip_on_their_products() -> None:
    """The point of the block: an expensive round-0 step is not redone on a rerun."""
    _, configs = _iteration_plan(_listform())

    assert configs[("hwy_assign", 0)]["skip_if_exists"] == "hwy/iter0/LOADEA.net"


def test_warmstart_accepts_the_compact_mapping_form() -> None:
    """Same two shapes as `steps:` -- a block is not a different kind of list."""
    plan = _plan([{"warmstart": {"a": {}, "b": {}}}])

    assert plan == [("a", 0), ("b", 0)]


def test_warmstart_written_as_a_block_is_refused() -> None:
    """`warmstart: {steps: [...]}` is `iterate:` by analogy; it has no count to hold."""
    with pytest.raises(TypeError, match="bare list"):
        _plan([{"warmstart": {"steps": [{"a": {}}]}}])


def test_empty_warmstart_is_refused() -> None:
    """An empty block silently does nothing, which reads as "the warm start ran"."""
    with pytest.raises(ValueError, match="declares no steps"):
        _plan([{"warmstart": []}])


def test_warmstart_after_the_loop_is_refused() -> None:
    """Round-0 steps at the end would overwrite the finished round's networks."""
    cfg = [
        {"iterate": {"count": 2, "steps": [{"assignment": {}}]}},
        {"warmstart": [{"hwy_assign": {}}]},
    ]

    with pytest.raises(ValueError, match="has to come before"):
        _plan(cfg)


def test_two_warmstart_blocks_are_refused() -> None:
    """A second block would silently redefine round 0 rather than extend it."""
    with pytest.raises(ValueError, match="declared twice"):
        _plan([{"warmstart": [{"a": {}}]}, {"warmstart": [{"b": {}}]}])


def test_iteration_pin_is_refused_inside_warmstart() -> None:
    """The block already says the round; a key repeating it can disagree with it."""
    with pytest.raises(ValueError, match="Drop the key"):
        _plan([{"warmstart": [{"hwy_assign": {"iteration": 1}}]}])


def test_the_old_iteration_key_is_refused_with_a_pointer() -> None:
    """A config written before `warmstart:` fails loudly, not as a silent round 1.

    Silently, it would run a warm-start step as round 1 -- writing hwy/iter1/ from
    iteration-0 demand, succeeding while producing nonsense.
    """
    with pytest.raises(ValueError, match="warmstart"):
        _plan([{"hwy_assign": {"iteration": 0}}])


def test_the_same_name_twice_in_one_round_is_refused() -> None:
    """Two definitions for one (step, round) would make --resume-at ambiguous."""
    with pytest.raises(ValueError, match="defined twice"):
        _plan([{"a": {}}, {"a": {}}])


def test_a_list_entry_must_be_a_single_named_mapping() -> None:
    """A bare string has no step kind to run; two keys is two steps."""
    with pytest.raises(TypeError, match="one `name"):
        _plan(["hwy_assign"])


# --- what the loop refuses ---------------------------------------------------


def test_skip_if_exists_is_refused_inside_the_loop() -> None:
    """Loop outputs land on the same paths every round, so the check cannot work."""
    cfg = {"iterate": {"count": 3, "steps": [
        {"prep_assign": {"skip_if_exists": "main/tripsAM.tpp"}},
    ]}}

    with pytest.raises(ValueError, match="always re-runs"):
        _plan(cfg)


def test_iteration_pin_is_refused_inside_the_loop() -> None:
    """The loop numbers its own rounds; a pinned step would lie about its files."""
    cfg = {"iterate": {"count": 3, "steps": [{"hwy_assign": {"iteration": 0}}]}}

    with pytest.raises(ValueError, match="numbered by the loop"):
        _plan(cfg)


def test_removed_mechanisms_are_refused_by_name() -> None:
    """A config written for warm_start:/first_round: fails loudly, not silently."""
    cfg = {"iterate": {"count": 3, "warm_start": ["a"], "steps": {"a": {}}}}

    with pytest.raises(ValueError, match="warm_start"):
        _plan(cfg)


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


# --- skip_if_exists: the declared product gate -------------------------------


def test_skip_target_resolves_against_run_dir(tmp_path: Path) -> None:
    """Relative paths mean run_dir, where every model artifact lives."""
    (tmp_path / "popsyn").mkdir()
    (tmp_path / "popsyn" / "hhFile.csv").write_text("done")
    cfg = {"run_dir": str(tmp_path)}

    hit = _skip_target({"skip_if_exists": "popsyn/hhFile.csv"}, cfg)

    assert hit == tmp_path / "popsyn" / "hhFile.csv"


def test_skip_target_is_none_when_the_product_is_absent(tmp_path: Path) -> None:
    """No file, no skip: the step runs and builds it."""
    cfg = {"run_dir": str(tmp_path)}

    assert _skip_target({"skip_if_exists": "popsyn/hhFile.csv"}, cfg) is None


def test_a_step_without_the_key_never_skips(tmp_path: Path) -> None:
    """skip_if_exists is opt-in; an undeclared step always runs."""
    assert _skip_target({}, {"run_dir": str(tmp_path)}) is None


# --- selecting a slice of the plan -----------------------------------------


def _pipeline() -> list:
    """A config with steps before, inside and after the loop."""
    return [
        {"copy_inputs": {}},
        {"warmstart": [{"hwy_assign": {"job": "warm.job"}}]},
        {"iterate": {"count": 3, "steps": [
            {"simulate_ctramp": {}},
            {"hwy_assign": {"job": "loop.job"}},
            {"publish": {}},
        ]}},
    ]


def test_until_stops_after_the_named_step() -> None:
    """The mirror of --resume-at: inclusive, so the named step itself runs."""
    plan = _apply_until(_plan(_pipeline()), "0:hwy_assign")

    assert plan[-1] == ("hwy_assign", 0)


def test_until_composes_with_resume_at_to_name_a_slice() -> None:
    """Together they express any contiguous range without listing steps."""
    full = _plan(_pipeline())

    sliced = _apply_until(_apply_resume(full, "2:simulate_ctramp"), "2:publish")

    assert sliced == [("simulate_ctramp", 2), ("hwy_assign", 2), ("publish", 2)]


def test_until_refuses_an_ambiguous_bare_name() -> None:
    """Picking the wrong round costs hours of Cube, so it asks rather than guesses."""
    with pytest.raises(ValueError, match="ambiguous"):
        _apply_until(_plan(_pipeline()), "hwy_assign")


def test_steps_filters_the_plan_and_keeps_real_round_numbers() -> None:
    """The bug this replaces: a fresh plan from bare names numbered everything 1.

    A warm-start step run as iteration 1 writes hwy/iter1/ from iteration-0
    demand -- succeeding, while producing nonsense.
    """
    plan = _select_steps(_plan(_pipeline()), ["hwy_assign"])

    assert plan == [("hwy_assign", i) for i in (0, 1, 2, 3)]


def test_steps_may_name_one_round() -> None:
    """`0:hwy_assign` picks the warm start's run and leaves the loop alone."""
    plan = _select_steps(_plan(_pipeline()), ["0:hwy_assign"])

    assert plan == [("hwy_assign", 0)]


def test_steps_keeps_plan_order_not_argument_order() -> None:
    """Order is the pipeline's, so a mistyped argument order cannot reorder a run."""
    plan = _select_steps(_plan(_pipeline()), ["1:publish", "1:simulate_ctramp"])

    assert plan == [("simulate_ctramp", 1), ("publish", 1)]


def test_steps_naming_nothing_is_refused() -> None:
    """A typo should not quietly run nothing and report success."""
    with pytest.raises(ValueError, match="matches nothing"):
        _select_steps(_plan(_pipeline()), ["no_such_step"])
