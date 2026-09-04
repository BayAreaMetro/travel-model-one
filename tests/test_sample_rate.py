"""Tests for how a round's CT-RAMP sample rate is resolved.

The rate decides how much of the synthetic population the demand model actually
simulates, and every downstream number scales with it.  A wrong rate does not
fail: the run completes and reports plausible totals, so the only protection is
that the config has to state the rate and the step has to refuse to guess one.
These tests pin that refusal.
"""

from pathlib import Path

import pytest

from tm1.project.config import load_config
from tm1.run.model import _sample_str
from tm1.steps.simulate_ctramp import _sample_rate_for

#: RunModel.bat's ramp, lines 280, 304 and 328.
LEGACY_RAMP = {1: 0.15, 2: 0.30, 3: 0.50}

#: Every project the repo ships, discovered rather than named -- see test_scenarios.py.
PROJECTS = sorted((Path(__file__).parents[1] / "projects").glob("*/scenarios.yaml"))


def test_flat_rate_applies_to_every_round() -> None:
    """One number is the other legal form: every round runs at that rate."""
    assert [_sample_rate_for(i, 0.5) for i in (1, 2, 3)] == [0.5, 0.5, 0.5]


def test_ramp_selects_the_rate_for_this_round() -> None:
    """The runner supplies the round; the ramp answers for that round only."""
    assert [_sample_rate_for(i, LEGACY_RAMP) for i in (1, 2, 3)] == [0.15, 0.30, 0.50]


def test_string_keys_are_accepted() -> None:
    """PyYAML gives str keys for a quoted `"1":`, which means the same thing."""
    assert _sample_rate_for(2, {"1": 0.15, "2": 0.30}) == LEGACY_RAMP[2]


def test_a_whole_population_is_allowed() -> None:
    """1.0 is the upper bound, not an error: it simulates everyone."""
    assert _sample_rate_for(1, 1.0) == 1.0
    assert _sample_rate_for(1, 1) == 1.0


def test_omitting_it_is_an_error() -> None:
    """No default: the old code silently used 0.50 past the end of its table."""
    with pytest.raises(ValueError, match="is required"):
        _sample_rate_for(1, None)


def test_a_round_the_ramp_does_not_cover_is_an_error() -> None:
    """`count: 4` or `--iterations 5` used to fall through to 0.50 unannounced."""
    with pytest.raises(ValueError, match="no rate for round 4"):
        _sample_rate_for(4, LEGACY_RAMP)


def test_the_error_names_the_rounds_that_were_stated() -> None:
    """So the fix is visible from the message, without opening the YAML."""
    with pytest.raises(ValueError, match="rounds stated: 1, 2, 3"):
        _sample_rate_for(4, LEGACY_RAMP)


@pytest.mark.parametrize("bad", [0, 0.0, -0.1, 1.5, 15])
def test_rates_outside_zero_to_one_are_refused(bad: object) -> None:
    """0 is refused too -- it is falsy, and used to read as 'not stated'."""
    with pytest.raises(ValueError, match="greater than 0 and at most 1"):
        _sample_rate_for(1, bad)


@pytest.mark.parametrize("bad", ["0.5", None, True, [0.5]])
def test_non_numeric_rates_are_refused(bad: object) -> None:
    """A quoted rate is the likely one, and it must not be coerced silently."""
    with pytest.raises(ValueError, match="must be a number"):
        _sample_rate_for(1, {1: bad})


def test_a_ramp_key_that_is_not_a_round_number_is_an_error() -> None:
    """A ramp is keyed by round, so a word key is a misunderstanding, not a rate."""
    with pytest.raises(ValueError, match="keyed by round number"):
        _sample_rate_for(1, {"first": 0.15})


@pytest.mark.parametrize("config_path", PROJECTS, ids=lambda p: p.parent.name)
def test_every_shipped_project_states_a_rate_for_every_round(config_path: Path) -> None:
    """A project's ramp has to cover the rounds that project will actually run.

    Not *which* rate -- that is the project's business, and asserting today's values
    would make a config edit look like a regression.  What must hold for any project
    is that `count` and `sample_rate` agree: a ramp one round short used to fall
    through to 0.50 unannounced, which is the failure this file exists to prevent.
    """
    cfg = load_config(config_path.parent)
    loop = next(
        (s["iterate"] for s in cfg["steps"] if isinstance(s, dict) and "iterate" in s),
        None,
    )
    if loop is None:
        pytest.skip("no feedback loop, so no per-round rate to state")

    sim = next(
        (s["simulate_ctramp"] for s in loop["steps"] if "simulate_ctramp" in s), None
    )
    if sim is None:
        pytest.skip("this project's demand model is not CT-RAMP")

    rate = sim.get("sample_rate")
    for round_number in range(1, loop["count"] + 1):
        assert _sample_rate_for(round_number, rate) > 0


def test_start_notification_renders_the_ramp() -> None:
    """The ramp reaches the start notification as a mapping, not a number.

    Formatting it as one raised before the run log opened, so every run of the
    shipped config died with a bare TypeError instead of starting.
    """
    assert _sample_str(LEGACY_RAMP) == "15% -> 30% -> 50%"
    assert _sample_str(0.5) == "50%"
    assert _sample_str(None) == "per-iteration ramp"
