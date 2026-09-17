"""Tests for the file shuffling ``RunIteration.bat`` does between Cube jobs.

These steps move and copy real files, so the tests do too -- there is nothing to
mock, and the failure mode being guarded against is a network landing in the wrong
directory, which only a real filesystem shows.

Each function is registered under whatever name the project gives it, so every
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


def _cfg(run_dir: Path, name: str, **step_cfg: object) -> dict:
    return {"run_dir": str(run_dir), "steps": {name: step_cfg}}


def _call(fn: Callable, run_dir: Path, name: str, **kwargs: object) -> object:
    """Invoke a staging step the way the runner does."""
    step_cfg = {k: v for k, v in kwargs.items() if k == "iteration"}
    return fn(run_dir, _cfg(run_dir, name, **step_cfg), step_name=name, **kwargs)


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


def test_transit_skims_copy_up_unchanged(proj: Path) -> None:
    """skims/ gets the same plain trnskm names TransitSkims.job writes -- a
    straight copy, no rename, since simplify_transit_master dropped the
    sub-iteration suffix TransitSkims.job used to write.
    """
    ta = proj / "trn" / "TransitAssignment.iter0"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.tpp").write_text("am")
    (ta / "trnskmev_drv_com_wlk.tpp").write_text("ev")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=0)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "am"
    assert (proj / "skims" / "trnskmev_drv_com_wlk.tpp").read_text() == "ev"


def test_the_pre_fare_backup_is_not_copied(proj: Path) -> None:
    """apply_regional_transit_fares_to_skims.job renames the original aside
    under `_woRegionalFare` before writing the fare-adjusted version back to
    the plain name -- only the plain name is this round's real product.
    """
    ta = proj / "trn" / "TransitAssignment.iter0"
    ta.mkdir()
    (ta / "trnskmam_wlk_trn_wlk.tpp").write_text("with fare")
    (ta / "trnskmam_wlk_trn_wlk_woRegionalFare.tpp").write_text("without fare")

    _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=0)

    assert (proj / "skims" / "trnskmam_wlk_trn_wlk.tpp").read_text() == "with fare"
    assert not (proj / "skims" / "trnskmam_wlk_trn_wlk_woRegionalFare.tpp").exists()


def test_missing_transit_skims_name_the_job_that_writes_them(proj: Path) -> None:
    """An empty iteration directory means TransitSkims.job never ran."""
    (proj / "trn" / "TransitAssignment.iter1").mkdir()

    with pytest.raises(FileNotFoundError, match=r"TransitSkims\.job"):
        _call(staging.copy_transit_skims, proj, "copy_transit_skims", iteration=1)


# --- copy_transit_links -----------------------------------------------------


def test_transit_links_copy_up_to_trn(proj: Path) -> None:
    """trnlink{PERIOD}.dbf moves from the iteration directory to trn/ itself.

    ConsolidateLoadedTransit.R reads it from there, not the iteration
    directory aggregateTransitLinks.py wrote it into.
    """
    ta = proj / "trn" / "TransitAssignment.iter3"
    ta.mkdir()
    for period in PERIODS:
        (ta / f"trnlink{period}.dbf").write_text(period)

    _call(staging.copy_transit_links, proj, "copy_transit_links", iteration=3)

    for period in PERIODS:
        assert (proj / "trn" / f"trnlink{period}.dbf").read_text() == period


def test_missing_transit_link_names_the_script_that_writes_it(proj: Path) -> None:
    """An empty iteration directory means aggregateTransitLinks.py never ran."""
    (proj / "trn" / "TransitAssignment.iter3").mkdir()

    with pytest.raises(FileNotFoundError, match=r"aggregateTransitLinks\.py"):
        _call(staging.copy_transit_links, proj, "copy_transit_links", iteration=3)


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


# --- normalize_popsyn_names --------------------------------------------------


def test_a_versioned_popsyn_file_is_aliased_to_the_plain_name(proj: Path) -> None:
    """CoreSummaries.R/MTCCreateLogsums hard-code the plain name, not the version."""
    popsyn = proj / "popsyn"
    popsyn.mkdir()
    (popsyn / "hhFile.2023_v12.csv").write_text("households")
    (popsyn / "personFile.2023_v12.csv").write_text("persons")

    result = staging.normalize_popsyn_names(
        proj, _cfg(proj, "normalize_popsyn_names"), step_name="normalize_popsyn_names",
    )

    assert result is None
    assert (popsyn / "hhFile.csv").read_text() == "households"
    assert (popsyn / "personFile.csv").read_text() == "persons"
    assert (popsyn / "hhFile.2023_v12.csv").exists()  # copied, not moved/renamed


def test_an_existing_plain_name_is_left_alone(proj: Path) -> None:
    """A re-run must not overwrite whatever a prior aliasing pass already wrote."""
    popsyn = proj / "popsyn"
    popsyn.mkdir()
    (popsyn / "hhFile.2023_v12.csv").write_text("new")
    (popsyn / "hhFile.csv").write_text("already aliased")
    (popsyn / "personFile.2023_v12.csv").write_text("persons")

    result = staging.normalize_popsyn_names(
        proj, _cfg(proj, "normalize_popsyn_names"), step_name="normalize_popsyn_names",
    )

    assert result is None  # personFile.csv still had to be written
    assert (popsyn / "hhFile.csv").read_text() == "already aliased"


def test_nothing_to_alias_reports_skipped(proj: Path) -> None:
    """Both plain names already present -- the whole step did no work."""
    popsyn = proj / "popsyn"
    popsyn.mkdir()
    (popsyn / "hhFile.csv").write_text("households")
    (popsyn / "personFile.csv").write_text("persons")

    result = staging.normalize_popsyn_names(
        proj, _cfg(proj, "normalize_popsyn_names"), step_name="normalize_popsyn_names",
    )

    assert result == "skipped"


def test_an_ambiguous_version_names_the_candidates(proj: Path) -> None:
    """Two versioned files for one stem is not a version this can guess between."""
    popsyn = proj / "popsyn"
    popsyn.mkdir()
    (popsyn / "hhFile.2023_v12.csv").write_text("v12")
    (popsyn / "hhFile.2023_v13.csv").write_text("v13")

    with pytest.raises(FileNotFoundError, match="hhFile.2023_v12.csv, hhFile.2023_v13.csv"):
        staging.normalize_popsyn_names(
            proj, _cfg(proj, "normalize_popsyn_names"), step_name="normalize_popsyn_names",
        )
