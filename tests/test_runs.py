"""Tests for run identity: which directory a run uses, and why that one.

Two properties are load-bearing and neither is visible from the config.  A
fingerprint has to be the *same* on every machine, or nothing is ever recognised
as already done; and it has to be *different* when the model changes, or a re-run
lands on top of a result it does not match.  Getting either wrong is expensive in
a way a wrong message is not -- one re-runs fifteen hours, the other reports the
wrong run as finished.
"""

import json
from pathlib import Path

import pytest

from tm1.run import directory as run_directory
from tm1.run import fingerprint as run_fingerprint
from tm1.run import receipt as run_receipt

#: A minimal project config, in the shape the loader hands to fingerprint():
#: scenario applied, templates still literal.
CFG = {
    "run_dir": "{runs_root}/proj/A-001",
    "runs_root": "E:/runs",
    "project": "proj",
    "scenario": "A",
    "run": "A-001",
    "model_year": 2023,
    "steps": [
        {"copy_inputs": {"input_hwy": {"from": "M:/nets/hwy", "to": "{run_dir}/hwy"}}},
        {"iterate": {"count": 3, "steps": [
            {"simulate_ctramp": {"threads": 24, "sample_rate": {1: 0.15}}},
            {"hwy_assign": {"job": "a.job", "cluster_nodes": 48}},
        ]}},
    ],
}


def _receipt(run_dir: Path, fingerprint: str, status: str = "running") -> None:
    run_receipt.Receipt(
        project="proj", scenario="A", run=1, fingerprint=fingerprint,
        machine="test", pid=1, status=status,
    ).write(run_dir)


# --- the fingerprint ---------------------------------------------------------


def test_the_same_config_fingerprints_the_same() -> None:
    """Trivially, but it is the property everything else rests on."""
    assert run_fingerprint.fingerprint(CFG) == run_fingerprint.fingerprint(dict(CFG))


def test_where_a_run_is_written_does_not_change_it() -> None:
    """Otherwise every machine computes a different hash for the same scenario.

    `.env` differs per machine, so `runs_root` and everything derived from it
    would make "already done" unrecognisable anywhere but where it ran.
    """
    elsewhere = {**CFG, "runs_root": "D:/other", "run_dir": "D:/other/proj/A-001"}

    assert run_fingerprint.fingerprint(elsewhere) == run_fingerprint.fingerprint(CFG)


def test_the_run_iteration_does_not_change_it() -> None:
    """`-NNN` is chosen *by* the fingerprint, so it must not feed back into it."""
    second = {**CFG, "run": "A-002", "run_dir": "{runs_root}/proj/A-002"}

    assert run_fingerprint.fingerprint(second) == run_fingerprint.fingerprint(CFG)


def test_tuning_a_machine_does_not_change_it() -> None:
    """Tuning a machine must never invalidate its result.

    cluster_nodes and threads are result-neutral by construction, which is what
    keeps runs from different machines comparable at all.
    """
    tuned = json.loads(json.dumps(CFG))
    tuned["steps"][1]["iterate"]["steps"][0]["simulate_ctramp"]["threads"] = 12
    tuned["steps"][1]["iterate"]["steps"][1]["hwy_assign"]["cluster_nodes"] = 24

    assert run_fingerprint.fingerprint(tuned) == run_fingerprint.fingerprint(CFG)


def test_a_model_value_does_change_it() -> None:
    """The point of the whole thing: a different model is a different run."""
    changed = {**CFG, "model_year": 2035}

    assert run_fingerprint.fingerprint(changed) != run_fingerprint.fingerprint(CFG)


def test_an_input_source_changes_it() -> None:
    """Repointing land use is the commonest override there is."""
    changed = json.loads(json.dumps(CFG))
    changed["steps"][0]["copy_inputs"]["input_hwy"]["from"] = "M:/other/hwy"

    assert run_fingerprint.fingerprint(changed) != run_fingerprint.fingerprint(CFG)


def test_a_referenced_file_changes_it(tmp_path: Path) -> None:
    """A variant job edited in place changes what runs without changing a value."""
    (tmp_path / "variants").mkdir()
    variant = tmp_path / "variants" / "SetTolls_cordon.job"
    variant.write_text("original", encoding="utf-8")
    cfg = {**CFG, "steps": [{"set_tolls": {"job": "variants/SetTolls_cordon.job"}}]}

    before = run_fingerprint.fingerprint(cfg, run_fingerprint.referenced_files(cfg, tmp_path))
    variant.write_text("edited", encoding="utf-8")
    after = run_fingerprint.fingerprint(cfg, run_fingerprint.referenced_files(cfg, tmp_path))

    assert before != after


# --- choosing the directory --------------------------------------------------


def test_the_first_run_of_a_scenario_is_001(tmp_path: Path) -> None:
    """And the directory exists afterwards -- allocation is a claim, not a plan."""
    run_no, path, state = run_directory.allocate(tmp_path, "A001-NOPK-2035", "abc")

    assert (run_no, path.name, state) == (1, "A001-NOPK-2035-001", run_directory.NEW)
    assert path.is_dir()


def test_an_unfinished_run_with_the_same_fingerprint_is_resumed(tmp_path: Path) -> None:
    """What makes `--resume-at` and the per-step sentinels mean what they say."""
    _, first, _ = run_directory.allocate(tmp_path, "A", "abc")
    _receipt(first, "abc", status="running")

    run_no, path, state = run_directory.allocate(tmp_path, "A", "abc")

    assert (run_no, path, state) == (1, first, run_directory.RESUME)


def test_a_finished_unchanged_run_is_reported_not_repeated(tmp_path: Path) -> None:
    """Asking again for a run that is done gets an answer, not another run.

    Silently starting a second hundred-gigabyte run would take fifteen hours to
    say what can be said immediately.
    """
    _, first, _ = run_directory.allocate(tmp_path, "A", "abc")
    _receipt(first, "abc", status="complete")

    run_no, path, state = run_directory.allocate(tmp_path, "A", "abc")

    assert (run_no, path, state) == (1, first, run_directory.COMPLETE)


def test_rerun_asks_for_one_anyway_and_keeps_the_finished_result(
    tmp_path: Path,
) -> None:
    """`--rerun` lands beside the old run, never over it."""
    _, first, _ = run_directory.allocate(tmp_path, "A", "abc")
    _receipt(first, "abc", status="complete")
    (first / "result.txt").write_text("kept", encoding="utf-8")

    run_no, path, state = run_directory.allocate(tmp_path, "A", "abc", rerun=True)

    assert (run_no, path.name, state) == (2, "A-002", run_directory.NEW)
    assert (first / "result.txt").read_text(encoding="utf-8") == "kept"


def test_a_changed_scenario_lands_beside_its_predecessor(tmp_path: Path) -> None:
    """The land use refresh: -002 appears, -001 stays intact.

    Never on top: the old run's outputs are a result someone may still be using,
    and its per-step sentinels would make a half-overwrite look complete.
    """
    _, first, _ = run_directory.allocate(tmp_path, "A", "abc")
    _receipt(first, "abc")
    (first / "marker.txt").write_text("round one", encoding="utf-8")

    run_no, second, state = run_directory.allocate(tmp_path, "A", "def")

    assert (run_no, second.name, state) == (2, "A-002", run_directory.NEW)
    assert (first / "marker.txt").read_text(encoding="utf-8") == "round one"


def test_an_unreadable_receipt_does_not_block_the_project(tmp_path: Path) -> None:
    """One corrupt run directory costs that run, not the ability to work at all."""
    _, first, _ = run_directory.allocate(tmp_path, "A", "abc")
    (first / run_receipt.TM1_DIR).mkdir(parents=True, exist_ok=True)
    (first / run_receipt.TM1_DIR / run_receipt.RECEIPT).write_text("{ not json", encoding="utf-8")

    run_no, _path, state = run_directory.allocate(tmp_path, "A", "abc")

    assert (run_no, state) == (2, run_directory.NEW)


def test_a_directory_taken_between_check_and_create_is_skipped(tmp_path: Path) -> None:
    """Two machines forcing the same stale scenario must not both own the number."""
    (tmp_path / "A-001").mkdir(parents=True)

    run_no, path, _ = run_directory.allocate(tmp_path, "A", "abc")

    assert (run_no, path.name) == (2, "A-002")


# --- the guards --------------------------------------------------------------


def test_a_long_run_directory_is_refused() -> None:
    """Cube and the Java stack are not long-path aware, and a run nests ~160 more."""
    with pytest.raises(ValueError, match="characters"):
        run_directory.check_length(Path("E:/" + "x" * run_directory.MAX_RUN_DIR_LEN))


def test_a_short_one_is_fine() -> None:
    """A realistic run directory has to pass, or the guard is just an outage."""
    run_directory.check_length(Path("E:/runs/proj/A001-NOPK-2035-001"))


def test_the_receipt_round_trips(tmp_path: Path) -> None:
    """It is what the shared index reads, so it has to survive being written."""
    _receipt(tmp_path, "abc", status="complete")

    assert run_receipt.read_receipt(tmp_path)["status"] == "complete"
