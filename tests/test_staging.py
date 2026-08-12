"""Tests for the file shuffling ``RunIteration.bat`` does between Cube jobs.

These steps move and copy real files, so the tests do too -- there is nothing to
mock, and the failure mode being guarded against is a network landing in the wrong
directory, which only a real filesystem shows.

Each function is registered under whatever name the scenario gives it, so every
call passes ``step_name`` the way the runner does.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from tm1.steps import staging

PERIODS = staging.PERIODS


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    """A project directory with the hwy/ and trn/ trees a run has."""
    (tmp_path / "hwy").mkdir()
    (tmp_path / "trn").mkdir()
    return tmp_path


def _cfg(proj_dir: Path, name: str, **step_cfg: object) -> dict:
    return {"proj_dir": str(proj_dir), "steps": {name: step_cfg}}


def _call(fn: Callable, proj_dir: Path, name: str, **kwargs: object) -> object:
    """Invoke a staging step the way the runner does."""
    step_cfg = {k: v for k, v in kwargs.items() if k == "iteration"}
    return fn(proj_dir, _cfg(proj_dir, name, **step_cfg), step_name=name, **kwargs)


# --- stage_loaded_networks -------------------------------------------------


def test_loaded_networks_move_into_the_iteration_directory(proj: Path) -> None:
    """RunIteration.bat 159-164: HwyAssign writes hwy/, feedback reads hwy/iter{N}/."""
    for period in PERIODS:
        (proj / "hwy" / f"LOAD{period}.net").write_text(period)

    _call(staging.stage_loaded_networks, proj, "stage_loaded_networks", iteration=2)

    for period in PERIODS:
        assert (proj / "hwy" / "iter2" / f"LOAD{period}.net").read_text() == period
        assert not (proj / "hwy" / f"LOAD{period}.net").exists()  # moved, not copied


def test_missing_loaded_network_names_the_job_that_writes_it(proj: Path) -> None:
    """A silent skip here would surface much later as an obscure feedback failure."""
    with pytest.raises(FileNotFoundError, match=r"HwyAssign\.job"):
        _call(staging.stage_loaded_networks, proj, "stage_loaded_networks", iteration=1)


# --- copy_transit_skims ----------------------------------------------------


def test_transit_skims_copy_up_strips_the_iteration_suffix(proj: Path) -> None:
    """skims/ gets plain trnskm names -- the ones CT-RAMP and Accessibility read.

    trnAssign.bat:231-235 renames on copy; keeping the suffix crashes
    Accessibility.job at startup on the missing input.
    """
    ta = proj / "trn" / "TransitAssignment.iter0"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.avg.iter0.tpp").write_text("am")
    (ta / "trnskmev_drv_com_wlk.avg.iter0.tpp").write_text("ev")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=0)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "am"
    assert (proj / "skims" / "trnskmev_drv_com_wlk.tpp").read_text() == "ev"
    assert not (proj / "skims" / "trnskmam_wlk_trn_wlk.avg.iter0.tpp").exists()


def test_the_suffix_is_the_transit_subiteration_not_the_round(proj: Path) -> None:
    """Under TRNCONFIG=FAST the counter stays 0 in every global round.

    Round 2's directory therefore holds `.avg.iter0.tpp`, not `.avg.iter2.tpp`.
    Deriving the suffix from the round instead finds nothing and fails the step.
    """
    ta = proj / "trn" / "TransitAssignment.iter2"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.avg.iter0.tpp").write_text("round 2 output")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=2)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "round 2 output"


def test_the_highest_subiteration_wins(proj: Path) -> None:
    """trnAssign.bat copies %LASTITER_{period}% -- where STANDARD iterated to."""
    ta = proj / "trn" / "TransitAssignment.iter1"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.avg.iter0.tpp").write_text("first pass")
    (ta / "trnskmam_wlk_trn_wlk.avg.iter2.tpp").write_text("converged")
    (ta / "trnskmam_wlk_trn_wlk.avg.iter1.tpp").write_text("middle")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=1)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "converged"


def test_the_negative_seed_copy_is_ignored(proj: Path) -> None:
    """TransitSkims.job:424 seeds `.avg.iterNEG1.tpp`; it is not a sub-iteration."""
    ta = proj / "trn" / "TransitAssignment.iter0"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.avg.iterNEG1.tpp").write_text("seed")
    (ta / "trnskmam_wlk_trn_wlk.avg.iter0.tpp").write_text("real")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=0)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "real"


def test_missing_transit_skims_name_the_job_that_writes_them(proj: Path) -> None:
    """An empty iteration directory means TransitSkims.job never ran."""
    (proj / "trn" / "TransitAssignment.iter1").mkdir()

    with pytest.raises(FileNotFoundError, match=r"TransitSkims\.job"):
        _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=1)


# --- seed_average_networks -------------------------------------------------


def test_seeding_copies_the_renamed_networks(proj: Path) -> None:
    """The warm start has nothing to average against, so its result is the average."""
    iter_dir = proj / "hwy" / "iter0"
    iter_dir.mkdir()
    for period in PERIODS:
        (iter_dir / f"LOAD{period}_renamed.net").write_text(period)

    _call(staging.seed_average_networks, proj, "warmstart_seed", iteration=0)

    for period in PERIODS:
        assert (iter_dir / f"avgLOAD{period}.net").read_text() == period
        # copied, not moved -- MergeNetworks still reads the renamed originals
        assert (iter_dir / f"LOAD{period}_renamed.net").exists()


# --- publish_networks ------------------------------------------------------


def test_publishing_puts_averages_where_the_next_round_reads_them(proj: Path) -> None:
    """RunIteration.bat 193-200: HwySkims reads hwy/, not an iteration directory."""
    iter_dir = proj / "hwy" / "iter1"
    iter_dir.mkdir()
    for period in PERIODS:
        (iter_dir / f"avgLOAD{period}.net").write_text(period)

    _call(staging.publish_networks, proj, "publish_networks", iteration=1)

    for period in PERIODS:
        assert (proj / "hwy" / f"avgLOAD{period}.net").read_text() == period


def test_publishing_drops_the_scratch_networks(proj: Path) -> None:
    """x*.net are AverageNetworkVolumes' and CalculateSpeeds' intermediates."""
    iter_dir = proj / "hwy" / "iter1"
    iter_dir.mkdir()
    for period in PERIODS:
        (iter_dir / f"avgLOAD{period}.net").write_text(period)
        (iter_dir / f"xavgload{period}.net").write_text("scratch")
        (iter_dir / f"x2avgload{period}.net").write_text("scratch")

    _call(staging.publish_networks, proj, "publish_networks", iteration=1)

    assert not list(iter_dir.glob("x*.net"))
    assert len(list(iter_dir.glob("avgLOAD*.net"))) == len(PERIODS)


# --- stage_transit_lines ---------------------------------------------------


def test_transit_lines_are_staged_under_both_names(proj: Path) -> None:
    """trnAssign.bat 43-63: the _0 copy is the round's start, the bare one is read."""
    for period in PERIODS:
        (proj / "trn" / f"transitOriginal{period}.lin").write_text(period)

    _call(staging.stage_transit_lines, proj, "stage_transit_lines", iteration=3)

    ta_dir = proj / "trn" / "TransitAssignment.iter3"
    for period in PERIODS:
        assert (ta_dir / f"transit{period}_0.lin").read_text() == period
        assert (ta_dir / f"transit{period}.lin").read_text() == period


def test_missing_line_file_names_the_step_that_builds_it(proj: Path) -> None:
    """The line files come from a step, not from INPUT/ -- say which one."""
    with pytest.raises(FileNotFoundError, match="transit_dwell_access"):
        _call(staging.stage_transit_lines, proj, "stage_transit_lines", iteration=1)


# --- which round a step belongs to -----------------------------------------


def test_a_step_key_pins_the_round_against_the_loop(proj: Path) -> None:
    """The warm-start steps sit outside `iterate:`, where the runner would say 1."""
    iter_dir = proj / "hwy" / "iter0"
    iter_dir.mkdir()
    for period in PERIODS:
        (iter_dir / f"LOAD{period}_renamed.net").write_text(period)

    # runner supplies iteration=1 for a pre-loop step; the step's own key wins
    staging.seed_average_networks(
        proj,
        _cfg(proj, "warmstart_seed_average_networks", iteration=0),
        step_name="warmstart_seed_average_networks",
        iteration=1,
    )

    assert (iter_dir / f"avgLOAD{PERIODS[0]}.net").exists()


def test_a_step_with_no_round_at_all_is_refused(proj: Path) -> None:
    """These name files under hwy/iter{N}/, so a missing round is not guessable."""
    with pytest.raises(ValueError, match="needs an iteration"):
        staging.publish_networks(
            proj, _cfg(proj, "publish_networks"), step_name="publish_networks"
        )
