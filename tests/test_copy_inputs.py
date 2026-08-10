r"""Tests for input staging.

Two behaviours are load-bearing and neither is obvious from the config: directory
entries **merge** rather than replace, because ``RunModel.bat`` copies two sources
into ``nonres\\``; and staging **never overwrites**, because entries later in the
pipeline write into the same directories and a re-run must not undo them.
"""

from pathlib import Path

import pytest

from tm1.steps import setup


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Two source directories, one with a nested subdirectory like INPUT/nonres."""
    (tmp_path / "src_a" / "airpax").mkdir(parents=True)
    (tmp_path / "src_a" / "ixDaily.tpp").write_text("ix")
    (tmp_path / "src_a" / "airpax" / "nested.tpp").write_text("air")
    (tmp_path / "src_b").mkdir()
    (tmp_path / "src_b" / "warm.tpp").write_text("warm")
    return tmp_path


def _run(tmp_path: Path, entries: dict, **kwargs: object) -> object:
    return setup.run(tmp_path, {"steps": {"copy_inputs": entries}}, **kwargs)


def _contents(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_a_directory_is_copied_with_its_shape(tree: Path) -> None:
    """INPUT/nonres has an airpax/ subdirectory, so a flat copy would lose it."""
    _run(tree, {"nonres": {"from": str(tree / "src_a"), "to": str(tree / "out")}})

    assert _contents(tree / "out") == ["airpax/nested.tpp", "ixDaily.tpp"]


def test_two_sources_merge_into_one_directory(tree: Path) -> None:
    r"""Both INPUT\nonres and INPUT\warmstart\nonres land in nonres\.

    RunModel.bat 175-177 copies them one after the other, so the second must not be
    skipped just because the directory already exists.
    """
    _run(tree, {
        "nonres": {"from": str(tree / "src_a"), "to": str(tree / "out")},
        "warmstart_nonres": {"from": str(tree / "src_b"), "to": str(tree / "out")},
    })

    assert _contents(tree / "out") == ["airpax/nested.tpp", "ixDaily.tpp", "warm.tpp"]


def test_restaging_does_not_clobber_what_a_later_step_wrote(tree: Path) -> None:
    """Later steps write into the same directories staging created.

    csv_to_dbf writes hwy/tolls.dbf, transit_dwell_access writes trn/*.lin.  A
    re-run of copy_inputs must leave their output alone.
    """
    entries = {"hwy": {"from": str(tree / "src_a"), "to": str(tree / "out")}}
    _run(tree, entries)
    (tree / "out" / "ixDaily.tpp").write_text("built by a later step")

    result = _run(tree, entries)

    assert result == "skipped"
    assert (tree / "out" / "ixDaily.tpp").read_text() == "built by a later step"


def test_force_restages_over_existing_files(tree: Path) -> None:
    """`--force` is the way to start clean without deleting the project directory."""
    entries = {"hwy": {"from": str(tree / "src_a"), "to": str(tree / "out")}}
    _run(tree, entries)
    (tree / "out" / "ixDaily.tpp").write_text("stale")

    _run(tree, entries, force=True)

    assert (tree / "out" / "ixDaily.tpp").read_text() == "ix"


def test_glob_takes_top_level_files_only(tree: Path) -> None:
    """`glob: "*"` is how trn/ skips the reference run's iteration directories."""
    _run(tree, {
        "trn": {"from": str(tree / "src_a"), "to": str(tree / "out"), "glob": "*"},
    })

    assert _contents(tree / "out") == ["ixDaily.tpp"]


def test_later_entries_can_read_what_earlier_ones_wrote(tree: Path) -> None:
    """The config stages INPUT/ first, then copies out of it -- so order is a contract."""
    _run(tree, {
        "input": {"from": str(tree / "src_a"), "to": str(tree / "proj" / "INPUT")},
        "airpax": {
            "from": str(tree / "proj" / "INPUT" / "airpax"),
            "to": str(tree / "proj" / "nonres"),
        },
    })

    assert _contents(tree / "proj" / "nonres") == ["nested.tpp"]


def test_a_missing_source_stops_the_run(tree: Path) -> None:
    """Staging silently short of a directory would fail much later, inside Cube."""
    with pytest.raises(SystemExit):
        _run(tree, {"absent": {"from": str(tree / "nope"), "to": str(tree / "out")}})
