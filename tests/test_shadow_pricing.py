"""Tests for the shadow-pricing flags CT-RAMP is configured with.

These pin `RuntimeConfiguration.py`'s ladder, which is easy to misread and whose
consequence is quiet: too few iterations does not fail, it just leaves location
choice unconverged.  The total it produces -- seven -- is the number a convergence
run has to beat, so it is asserted rather than left to inference.
"""

from pathlib import Path

import pytest

from tm1.steps.simulate_ctramp import _popsyn_files, shadow_pricing_flags

PREFIX = "UsualWorkAndSchoolLocationChoice"
MAX_ITER = f"{PREFIX}.ShadowPricing.MaximumIterations"
INPUT_FILE = f"{PREFIX}.ShadowPrice.Input.File"

#: Shadow-price passes a stock three-round run performs: 4 + 2 + 2.
PASSES_PERFORMED = 8

#: Length of the chain that actually reaches the end: round 2 restarts from
#: ShadowPricing_3, so round 1's fourth pass is computed and then discarded.
CHAIN_LENGTH = 7


def test_first_iteration_starts_from_nothing() -> None:
    """An empty value comments the property out, so CT-RAMP seeds its own prices.

    This is why a ShadowPricing_*.csv staged into main/ beforehand goes unread.
    """
    flags = shadow_pricing_flags(1)

    assert flags[INPUT_FILE] == ""
    assert flags[MAX_ITER] == "4"


@pytest.mark.parametrize(("iteration", "expected"), [(2, "3"), (3, "5"), (4, "7")])
def test_later_iterations_chain_from_the_previous_output(
    iteration: int, expected: str
) -> None:
    """Input is ShadowPricing_{2n-1}.csv -- the file the last round left behind."""
    flags = shadow_pricing_flags(iteration)

    assert flags[INPUT_FILE] == f"main/ShadowPricing_{expected}.csv"
    assert flags[MAX_ITER] == "2"


def test_a_stock_run_performs_eight_passes_but_chains_only_seven() -> None:
    """Round 1 runs four passes; round 2 then restarts from the *third*.

    So the fourth pass of round 1 is computed and thrown away, and the chain that
    survives to the end is seven long -- the seven known not to converge.  The
    file numbering is what shows it: round 3 reads ShadowPricing_5, which only
    exists if round 2 continued the count from its input rather than restarting.
    """
    per_round = [int(shadow_pricing_flags(i)[MAX_ITER]) for i in (1, 2, 3)]

    assert per_round == [4, 2, 2]
    assert sum(per_round) == PASSES_PERFORMED
    # Round 2 reads _3, so one pass of round 1 is discarded.
    assert sum(per_round) - 1 == CHAIN_LENGTH


def test_disabling_shadow_pricing_stops_at_one_iteration() -> None:
    """Not zero: location choice still runs, it just never adjusts."""
    flags = shadow_pricing_flags(1, shadow_pricing=False)

    assert flags[MAX_ITER] == "1"
    assert flags[INPUT_FILE] == ""


def test_passes_override_the_ladder_for_a_convergence_run() -> None:
    """The knob a convergence scenario turns; the chain stays put."""
    passes = {"first": 30, "subsequent": 30}

    assert shadow_pricing_flags(1, passes=passes)[MAX_ITER] == "30"
    assert shadow_pricing_flags(3, passes=passes)[MAX_ITER] == "30"


def test_either_key_may_be_overridden_alone() -> None:
    """Partial overrides fall back on the legacy value, not on zero."""
    flags_first = shadow_pricing_flags(1, passes={"subsequent": 9})
    flags_later = shadow_pricing_flags(2, passes={"subsequent": 9})

    assert flags_first[MAX_ITER] == "4"        # untouched
    assert flags_later[MAX_ITER] == "9"


def test_overriding_passes_leaves_the_input_chain_alone() -> None:
    """It changes how long to iterate, not where to start."""
    flags = shadow_pricing_flags(3, passes={"subsequent": 30})

    assert flags[INPUT_FILE] == "main/ShadowPricing_5.csv"


def test_a_misspelled_key_is_refused() -> None:
    """`subsequant: 30` would otherwise silently run the default 2 passes."""
    with pytest.raises(ValueError, match="unknown key"):
        shadow_pricing_flags(1, passes={"subsequant": 30})


def test_disabling_beats_the_override() -> None:
    """`shadow_pricing: false` means off, whatever else the scenario says."""
    flags = shadow_pricing_flags(1, shadow_pricing=False, passes={"first": 30})

    assert flags[MAX_ITER] == "1"


# --- the synthetic-population filenames CT-RAMP is pointed at ---------------


def test_popsyn_files_use_the_versioned_names_that_exist(tmp_path: Path) -> None:
    """The versioned name is the real one, so the properties must state it.

    Hard-coding ``hhFile.csv`` is a FileNotFoundException three processes deep
    in the Java model.
    """
    popsyn = tmp_path / "INPUT" / "popsyn"
    popsyn.mkdir(parents=True)
    (popsyn / "hhFile.2023_v12.csv").write_text("hh")
    (popsyn / "personFile.2023_v12.csv").write_text("per")

    hh, person = _popsyn_files(tmp_path)

    assert hh == "popsyn/hhFile.2023_v12.csv"
    assert person == "popsyn/personFile.2023_v12.csv"


def test_popsyn_files_refuse_ambiguity(tmp_path: Path) -> None:
    """Two candidates would let the properties name one arbitrarily.

    The legacy RuntimeConfiguration asserts exactly one match, and so does this.
    """
    popsyn = tmp_path / "INPUT" / "popsyn"
    popsyn.mkdir(parents=True)
    (popsyn / "hhFile.a.csv").write_text("a")
    (popsyn / "hhFile.b.csv").write_text("b")
    (popsyn / "personFile.csv").write_text("p")

    with pytest.raises(FileNotFoundError, match="exactly one"):
        _popsyn_files(tmp_path)
