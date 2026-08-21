r"""Tests for input staging.

Two behaviours are load-bearing and neither is obvious from the config: directory
entries **merge** rather than replace, because ``RunModel.bat`` copies two sources
into ``nonres\\``; and staging **never overwrites** unless the entry says
so, because entries later in the pipeline write into the same directories and a
re-run must not undo them.
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


def test_overwrite_is_declared_by_the_entry_that_needs_it(tree: Path) -> None:
    """SetUpModel.bat's `copy /Y` lands a strategy file on top of a staged one.

    Per entry rather than a global flag: the swap is part of what the run *is*, so
    it belongs in the config next to the file it replaces.
    """
    base = {"hwy": {"from": str(tree / "src_a"), "to": str(tree / "out")}}
    _run(tree, base)
    (tree / "out" / "ixDaily.tpp").write_text("stale")

    _run(tree, {"hwy": {**base["hwy"], "overwrite": True}})

    assert (tree / "out" / "ixDaily.tpp").read_text() == "ix"


def test_include_selects_and_exclude_wins(tree: Path) -> None:
    """The warmstart entry: only *.tpp, minus the two ixDaily files.

    SetUpModel.bat copies then `del`s them; never copying is not the same thing on a
    resumed run, where the delete would have to undo an earlier attempt's copy.
    """
    _run(tree, {
        "warmstart": {
            "from": str(tree / "src_a"),
            "to": str(tree / "out"),
            "include": ["*.tpp"],
            "exclude": ["ixDaily*.tpp"],
        },
    })

    assert _contents(tree / "out") == ["airpax/nested.tpp"]


def test_a_file_entry_may_rename(tree: Path) -> None:
    """`2023b_tripsAirPaxEA.tpp` -> `tripsAirPaxEA.tpp`, per model year."""
    _run(tree, {
        "airpax_ea": {
            "from": str(tree / "src_a" / "ixDaily.tpp"),
            "to": str(tree / "out" / "renamed.tpp"),
        },
    })

    assert (tree / "out" / "renamed.tpp").read_text() == "ix"


def test_an_unknown_entry_key_is_refused_by_name(tree: Path) -> None:
    """A misspelled key would otherwise stage the wrong bytes and say nothing."""
    with pytest.raises(ValueError, match="excludes"):
        _run(tree, {
            "hwy": {
                "from": str(tree / "src_a"),
                "to": str(tree / "out"),
                "excludes": ["*.tpp"],
            },
        })


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
