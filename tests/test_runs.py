"""Tests for run identity: which directory a run uses, and why.

The run number is chosen by hand (``--run-number``), not guessed: two machines
each picking their own next-available number independently could otherwise land
on the same one for two different runs, with nothing left afterwards to tell
them apart. What is left to check here is narrower than it used to be --
whether the named directory already has a run in it, and whether ``--resume-at``
agrees with that -- but getting it wrong is still expensive in a way a wrong
message is not: silently mixing two attempts into one directory, or refusing a
resume that has every right to continue.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from tm1.run import directory as run_directory
from tm1.run import receipt as run_receipt
from tm1.run.model import _begin_run, run_model


def _receipt(run_dir: Path, status: str = "running") -> None:
    run_receipt.Receipt(
        project="proj", scenario="A", run=1, machine="test", pid=1, status=status,
    ).write(run_dir)


# --- choosing the directory --------------------------------------------------


def test_a_fresh_run_number_is_created(tmp_path: Path) -> None:
    """Nothing there yet, and not resuming -- a new directory is made."""
    path, state = run_directory.resolve(tmp_path, "A001-NOPK-2035", 1, resume=False)

    assert (path.name, state) == ("A001-NOPK-2035_001", run_directory.NEW)
    assert path.is_dir()


def test_an_empty_existing_directory_counts_as_fresh(tmp_path: Path) -> None:
    """A directory with nothing written into it yet is not "a run in progress"."""
    (tmp_path / "A_001").mkdir(parents=True)

    path, state = run_directory.resolve(tmp_path, "A", 1, resume=False)

    assert (path.name, state) == ("A_001", run_directory.NEW)


def test_resuming_a_populated_run_continues_it(tmp_path: Path) -> None:
    """What makes `--resume-at` and the per-step sentinels mean what they say."""
    first, _ = run_directory.resolve(tmp_path, "A", 1, resume=False)
    _receipt(first)

    path, state = run_directory.resolve(tmp_path, "A", 1, resume=True)

    assert (path, state) == (first, run_directory.RESUME)


def test_running_fresh_into_a_populated_directory_is_refused(tmp_path: Path) -> None:
    """Running the pipeline again would not fail -- it would silently mix two attempts."""
    first, _ = run_directory.resolve(tmp_path, "A", 1, resume=False)
    _receipt(first)

    with pytest.raises(ValueError, match="already has a run in it"):
        run_directory.resolve(tmp_path, "A", 1, resume=False)


def test_resuming_a_run_that_is_not_there_is_refused(tmp_path: Path) -> None:
    """--resume-at presupposes a previous run, not whatever stale matrices happen to be there."""
    with pytest.raises(ValueError, match="needs a run already under way"):
        run_directory.resolve(tmp_path, "A", 1, resume=True)


def test_a_changed_scenario_lands_beside_its_predecessor(tmp_path: Path) -> None:
    """A land use refresh: --run-number 2 appears, _001 stays intact.

    Never on top: the old run's outputs are a result someone may still be
    using, and its per-step sentinels would make a half-overwrite look complete.
    """
    first, _ = run_directory.resolve(tmp_path, "A", 1, resume=False)
    _receipt(first)
    (first / "marker.txt").write_text("round one", encoding="utf-8")

    second, state = run_directory.resolve(tmp_path, "A", 2, resume=False)

    assert (second.name, state) == ("A_002", run_directory.NEW)
    assert (first / "marker.txt").read_text(encoding="utf-8") == "round one"


def test_the_first_run_of_a_scenario_can_be_any_number(tmp_path: Path) -> None:
    """Nothing here assumes 1 -- the model user's own numbering is the only one."""
    path, state = run_directory.resolve(tmp_path, "A", 7, resume=False)

    assert (path.name, state) == ("A_007", run_directory.NEW)


# --- the guards --------------------------------------------------------------


def test_a_long_run_directory_is_refused() -> None:
    """Cube and the Java stack are not long-path aware, and a run nests ~160 more."""
    with pytest.raises(ValueError, match="characters"):
        run_directory.check_length(Path("E:/" + "x" * run_directory.MAX_RUN_DIR_LEN))


def test_a_short_one_is_fine() -> None:
    """A realistic run directory has to pass, or the guard is just an outage."""
    run_directory.check_length(Path("E:/runs/proj/A001-NOPK-2035_001"))


def test_the_receipt_round_trips(tmp_path: Path) -> None:
    """It is what the shared index reads, so it has to survive being written."""
    _receipt(tmp_path, status="complete")

    assert run_receipt.read_receipt(tmp_path)["status"] == "complete"


# --- --run-number end to end --------------------------------------------------


@pytest.fixture
def runs_root() -> Path:
    """A short-path temp directory for TM1_RUNS_ROOT.

    Not ``tmp_path``: pytest's own is already long enough (it encodes the test's
    name) that a run_dir under it trips ``check_length()`` by itself, which is a
    property of that fixture, not of anything under test here.
    """
    path = Path(tempfile.mkdtemp(prefix="tm1-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path, steps: str = "",
) -> Path:
    """A synthetic checkout with one scenario, and TM1_RUNS_ROOT pointed at *runs_root*."""
    monkeypatch.setenv("TM1_RUNS_ROOT", str(runs_root))
    (tmp_path / "default-configs").mkdir()
    (tmp_path / "default-configs" / "ctramp-cube-model.yaml").write_text(
        f"steps:\n{steps}", encoding="utf-8",
    )
    project = tmp_path / "proj"
    project.mkdir()
    (project / "scenarios.yaml").write_text("scenarios:\n  A-2023:\n", encoding="utf-8")
    return project


def test_run_number_is_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """`tm1 run` never guesses a number -- it has to be told."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")

    with pytest.raises(ValueError, match="run-number"):
        _begin_run(project, {})


def test_a_fresh_run_number_starts_a_new_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """The plain case: an unused number simply starts a new run there."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")

    prepared, _label = _begin_run(project, {"run_number": 1})

    assert prepared.state == run_directory.NEW
    assert prepared.run_dir.name == "A-2023_001"


def test_resume_at_continues_an_existing_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """The ordinary case: pointing --run-number at the run already under way."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")
    prepared, _label = _begin_run(project, {"run_number": 1})

    resumed, _label = _begin_run(project, {"run_number": 1, "resume_at": "copy_inputs"})

    assert resumed.run_dir == prepared.run_dir
    assert resumed.state == run_directory.RESUME


def test_steps_alone_continues_an_existing_run_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """--steps names existing steps to rerun -- the same as --resume-at, not a fresh start."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")
    prepared, _label = _begin_run(project, {"run_number": 1})

    resumed, _label = _begin_run(project, {"run_number": 1, "steps": ["copy_inputs"]})

    assert resumed.run_dir == prepared.run_dir
    assert resumed.state == run_directory.RESUME


def test_a_full_run_into_an_existing_run_number_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """Without --resume-at, a populated --run-number is a mistake, not a merge."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")
    _begin_run(project, {"run_number": 1})

    with pytest.raises(ValueError, match="already has a run in it"):
        _begin_run(project, {"run_number": 1})


def test_cli_steps_reaches_run_model_not_just_begin_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """run_model's own `steps` parameter, not just _begin_run's kwargs dict.

    cli.cmd_run passes `steps` to run_model as its own named parameter, not
    folded into the kwargs run_model forwards to _begin_run -- a run_model-level
    regression that a _begin_run-only test cannot see.
    """
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")
    _begin_run(project, {"run_number": 1})

    run_model(project, steps=["copy_inputs"], run_number=1)  # must not raise


def test_resume_at_on_an_unused_run_number_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runs_root: Path,
) -> None:
    """Naming a number is not enough; --resume-at also needs one already in use."""
    project = _project(tmp_path, monkeypatch, runs_root, steps="  - copy_inputs: {}\n")

    with pytest.raises(ValueError, match="needs a run already under way"):
        _begin_run(project, {"run_number": 1, "resume_at": "copy_inputs"})
