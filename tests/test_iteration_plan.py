"""Tests for the feedback loop's execution plan.

The plan decides what runs and in which iteration, which is also what
``--resume-at`` resolves against and what the "planned:" line reports.  The
shape the conventions lock: ``steps:`` is a list of ``name: {config}`` entries
run in the order written (a mapping also works, but cannot repeat a name);
``iterate: {count, steps}`` is the only nesting, and a step's iteration comes
from where it sits relative to ``iteration_zero_begins`` inside it, and from
``only_iteration:``/``skip_iteration:`` for the few steps that need pinning.

There is no other mechanism.  ``RunModel.bat``'s ``set ITER=0`` pass is
iteration 0, everything at or after ``iteration_zero_begins``; its
``if %ITER%==1`` block is iteration-0-only steps that skip on their products
via ``skip_if_exists:``, which the loop otherwise refuses.
"""

from pathlib import Path

import pytest

from tm1.run.iterations import (
    apply_resume,
    apply_until,
    iteration_plan,
    select_steps,
    skip_target,
)


def _plan(steps_cfg: object, override: int | None = None) -> list[tuple[str, int]]:
    plan, _ = iteration_plan(steps_cfg, override)
    return plan


def _iterations(plan: list[tuple[str, int]], step: str) -> list[int]:
    """Which iterations *step* runs in."""
    return [i for s, i in plan if s == step]


def test_loop_body_repeats_once_per_iteration() -> None:
    """`count:` is a number of iterations -- RunIteration.bat called N times."""
    plan = _plan({"iterate": {"count": 3, "steps": {"assignment": {}}}})

    assert _iterations(plan, "assignment") == [1, 2, 3]


def test_loop_body_keeps_its_written_order_within_an_iteration() -> None:
    """Steps run in the order written, which is what makes the config readable."""
    plan = _plan({
        "iterate": {"count": 2, "steps": {"simulate_ctramp": {}, "assignment": {}}}
    })

    assert plan == [
        ("simulate_ctramp", 1), ("assignment", 1),
        ("simulate_ctramp", 2), ("assignment", 2),
    ]


def test_steps_around_the_loop_take_the_first_and_last_iterations() -> None:
    """Before the loop runs at the first iteration; after it, at the last."""
    plan = _plan({
        "copy_inputs": {},
        "iterate": {"count": 3, "steps": {"assignment": {}}},
        "calibration": {},
    })

    assert _iterations(plan, "copy_inputs") == [1]
    assert _iterations(plan, "calibration") == [3]


def test_iterations_override_replaces_the_count() -> None:
    """`--iterations N` shortens a run without editing the project config."""
    cfg = {"iterate": {"count": 3, "steps": {"assignment": {}}}}

    assert _iterations(_plan(cfg, override=1), "assignment") == [1]


def test_a_run_without_a_loop_is_a_flat_sequence() -> None:
    """`iterate:` is optional; a preprocess-only run has no iterations at all."""
    plan = _plan({"copy_inputs": {}, "assignment": {}})

    assert plan == [("copy_inputs", 1), ("assignment", 1)]


# --- iteration_zero_begins: where iteration 0 joins the loop -----------------


def _listform() -> list:
    """Setup, a demand-only prefix, the shared body, a summary -- the real shape."""
    return [
        {"copy_inputs": {}},
        {"iterate": {"count": 3, "steps": [
            {"simulate_ctramp": {}},
            {"iteration_zero_begins": {}},
            {"hwy_assign": {"job": "hwy.job",
                            "only_iteration": 0,
                            "skip_if_exists": "hwy/iter0/LOADEA.net"}},
            {"hwy_skims": {"job": "skims.job"}},
        ]}},
        {"summarize": {}},
    ]


def test_list_form_runs_in_the_order_written() -> None:
    """The list is the pipeline; nothing reorders it."""
    plan = _plan(_listform())

    assert plan[:3] == [("copy_inputs", 1), ("hwy_assign", 0), ("hwy_skims", 0)]
    assert plan[-1] == ("summarize", 3)


def test_steps_before_the_marker_skip_iteration_zero() -> None:
    """Iteration 0's demand is already staged -- it does not run simulate_ctramp."""
    plan = _plan(_listform())

    assert _iterations(plan, "simulate_ctramp") == [1, 2, 3]


def test_steps_at_or_after_the_marker_run_at_every_iteration() -> None:
    """The shared assignment/skims body -- iteration 0 included."""
    plan = _plan(_listform())

    assert _iterations(plan, "hwy_skims") == [0, 1, 2, 3]


def test_only_iteration_pins_a_step_to_one_iteration() -> None:
    """The point of the key: hwy_assign here only ever runs once, at iteration 0."""
    plan = _plan(_listform())

    assert _iterations(plan, "hwy_assign") == [0]


def test_a_pinned_step_may_declare_skip_if_exists() -> None:
    """Pinned to one iteration, its product is unambiguous."""
    _, configs = iteration_plan(_listform())

    assert configs[("hwy_assign", 0)]["skip_if_exists"] == "hwy/iter0/LOADEA.net"


def test_skip_iteration_excludes_a_single_iteration() -> None:
    """The mirror of only_iteration: everywhere except one iteration."""
    plan = _plan({"iterate": {"count": 2, "steps": [
        {"iteration_zero_begins": {}},
        {"average_network_volumes": {"skip_iteration": 0}},
    ]}})

    assert _iterations(plan, "average_network_volumes") == [1, 2]


def test_a_loop_with_no_marker_never_runs_at_iteration_zero() -> None:
    """`iteration_zero_begins` is optional; without it, the loop is iterations 1..count."""
    plan = _plan({"iterate": {"count": 2, "steps": [{"assignment": {}}]}})

    assert _iterations(plan, "assignment") == [1, 2]


def test_two_markers_are_refused() -> None:
    """A second marker would leave the boundary ambiguous."""
    cfg = {"iterate": {"count": 2, "steps": [
        {"iteration_zero_begins": {}}, {"a": {}}, {"iteration_zero_begins": {}},
    ]}}

    with pytest.raises(ValueError, match="declared twice"):
        _plan(cfg)


def test_two_iterate_blocks_are_refused() -> None:
    """A second block would silently redefine the run's shape."""
    cfg = [
        {"iterate": {"count": 2, "steps": [{"a": {}}]}},
        {"iterate": {"count": 2, "steps": [{"b": {}}]}},
    ]

    with pytest.raises(ValueError, match="declared twice"):
        _plan(cfg)


def test_the_same_name_twice_in_one_iteration_is_refused() -> None:
    """Two definitions for one (step, iteration) would make --resume-at ambiguous."""
    with pytest.raises(ValueError, match="defined twice"):
        _plan([{"a": {}}, {"a": {}}])


def test_a_list_entry_must_be_a_single_named_mapping() -> None:
    """A bare string has no step kind to run; two keys is two steps."""
    with pytest.raises(TypeError, match="one `name"):
        _plan(["hwy_assign"])


def test_the_old_iteration_key_is_refused_with_a_pointer() -> None:
    """A config written before this mechanism fails loudly, not as a silent iteration 1.

    Silently, it would run an iteration-0 step as iteration 1 -- writing
    hwy/iter1/ from iteration-0 demand, succeeding while producing nonsense.
    """
    with pytest.raises(ValueError, match="iterate"):
        _plan([{"hwy_assign": {"iteration": 0}}])


# --- what the loop refuses ---------------------------------------------------


def test_skip_if_exists_without_only_iteration_is_refused_inside_the_loop() -> None:
    """Unpinned, the step runs at more than one iteration -- the check cannot work."""
    cfg = {"iterate": {"count": 3, "steps": [
        {"prep_assign": {"skip_if_exists": "main/tripsAM.tpp"}},
    ]}}

    with pytest.raises(ValueError, match="without .only_iteration"):
        _plan(cfg)


def test_iteration_pin_is_refused_inside_the_loop() -> None:
    """The loop numbers its own iterations; a pinned step would lie about its files."""
    cfg = {"iterate": {"count": 3, "steps": [{"hwy_assign": {"iteration": 0}}]}}

    with pytest.raises(ValueError, match="numbered by the loop"):
        _plan(cfg)


def test_removed_mechanisms_are_refused_by_name() -> None:
    """A config written for warmstart:/warm_start:/first_round: fails loudly, not silently."""
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

    hit = skip_target({"skip_if_exists": "popsyn/hhFile.csv"}, cfg)

    assert hit == tmp_path / "popsyn" / "hhFile.csv"


def test_skip_target_is_none_when_the_product_is_absent(tmp_path: Path) -> None:
    """No file, no skip: the step runs and builds it."""
    cfg = {"run_dir": str(tmp_path)}

    assert skip_target({"skip_if_exists": "popsyn/hhFile.csv"}, cfg) is None


def test_a_step_without_the_key_never_skips(tmp_path: Path) -> None:
    """skip_if_exists is opt-in; an undeclared step always runs."""
    assert skip_target({}, {"run_dir": str(tmp_path)}) is None


# --- selecting a slice of the plan -----------------------------------------


def _pipeline() -> list:
    """A config with steps before, inside and after the loop."""
    return [
        {"copy_inputs": {}},
        {"iterate": {"count": 3, "steps": [
            {"simulate_ctramp": {}},
            {"iteration_zero_begins": {}},
            {"hwy_assign": {"job": "loop.job"}},
            {"publish": {}},
        ]}},
    ]


def test_until_stops_after_the_named_step() -> None:
    """The mirror of --resume-at: inclusive, so the named step itself runs."""
    plan = apply_until(_plan(_pipeline()), "0:hwy_assign")

    assert plan[-1] == ("hwy_assign", 0)


def test_until_composes_with_resume_at_to_name_a_slice() -> None:
    """Together they express any contiguous range without listing steps."""
    full = _plan(_pipeline())

    sliced = apply_until(apply_resume(full, "2:hwy_assign"), "2:publish")

    assert sliced == [("hwy_assign", 2), ("publish", 2)]


def test_until_refuses_an_ambiguous_bare_name() -> None:
    """Picking the wrong iteration costs hours of Cube, so it asks rather than guesses."""
    with pytest.raises(ValueError, match="ambiguous"):
        apply_until(_plan(_pipeline()), "hwy_assign")


def test_steps_filters_the_plan_and_keeps_real_iteration_numbers() -> None:
    """The bug this replaces: a fresh plan from bare names numbered everything 1.

    An iteration-0 step run as iteration 1 writes hwy/iter1/ from iteration-0
    demand -- succeeding, while producing nonsense.
    """
    plan = select_steps(_plan(_pipeline()), ["hwy_assign"])

    assert plan == [("hwy_assign", i) for i in (0, 1, 2, 3)]


def test_steps_may_name_one_iteration() -> None:
    """`0:hwy_assign` picks iteration 0's run and leaves the loop alone."""
    plan = select_steps(_plan(_pipeline()), ["0:hwy_assign"])

    assert plan == [("hwy_assign", 0)]


def test_steps_keeps_plan_order_not_argument_order() -> None:
    """Order is the pipeline's, so a mistyped argument order cannot reorder a run."""
    plan = select_steps(_plan(_pipeline()), ["1:publish", "1:simulate_ctramp"])

    assert plan == [("simulate_ctramp", 1), ("publish", 1)]


def test_steps_naming_nothing_is_refused() -> None:
    """A typo should not quietly run nothing and report success."""
    with pytest.raises(ValueError, match="matches nothing"):
        select_steps(_plan(_pipeline()), ["no_such_step"])

