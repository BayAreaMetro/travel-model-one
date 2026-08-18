"""Tests for how a round's CT-RAMP sample rate is resolved.

The rate decides how much of the synthetic population the demand model actually
simulates, and every downstream number scales with it.  A wrong rate does not
fail: the run completes and reports plausible totals, so the only protection is
that the config has to state the rate and the step has to refuse to guess one.
These tests pin that refusal.
"""

from pathlib import Path

import pytest
import yaml

from tm1.steps.simulate_ctramp import _sample_rate_for

#: RunModel.bat's ramp, lines 280, 304 and 328.
LEGACY_RAMP = {1: 0.15, 2: 0.30, 3: 0.50}

SCENARIO = (
    Path(__file__).parents[1] / "scenarios" / "base_2023_ctramp" / "scenario_config.yaml"
)


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


def test_the_shipped_scenario_states_the_legacy_ramp() -> None:
    """Parity depends on these three values; assert them rather than trust them."""
    cfg = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    loop = next(
        s["iterate"] for s in cfg["steps"] if isinstance(s, dict) and "iterate" in s
    )
    sim = next(s["simulate_ctramp"] for s in loop["steps"] if "simulate_ctramp" in s)
    assert {int(k): v for k, v in sim["sample_rate"].items()} == LEGACY_RAMP
