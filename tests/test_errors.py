"""What a person sees when the project is wrong.

These are the messages read most often -- a mistyped case, a `.env` copied but not
finished, a YAML block indented one space off -- and they are read by someone who
did not write the harness. A traceback answers "which line of tm1 raised this",
which is not the question being asked.

The other half is what must *not* happen: a genuine bug in the harness has to keep
its traceback, or a wrong answer becomes indistinguishable from a bad config.
"""

from collections.abc import Callable

import pytest
import yaml

from tm1.cli import _run_cleanly
from tm1.project.config import env_references, missing_env


def _boom(exc: Exception) -> Callable[[], None]:
    def raise_it() -> None:
        raise exc
    return raise_it


# --- the .env pre-flight -----------------------------------------------------


def test_every_env_reference_is_found_however_deep() -> None:
    """A missed one is a run that dies at hour nine, not at second one."""
    cfg = {
        "m_drive": "{env:TM1_M_DRIVE}",
        "env": {"PATH": "{env:TM1_GAWK_DIR};{env:PATH}"},
        "steps": [{"copy_inputs": {"input_hwy": {"from": "{env:TM1_M_DRIVE}/nets"}}}],
    }

    assert env_references(cfg) == {"TM1_M_DRIVE", "TM1_GAWK_DIR", "PATH"}


def test_an_unset_variable_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """The `.env` copied but not finished -- the commonest first-run failure."""
    monkeypatch.delenv("TM1_NOT_REAL", raising=False)
    monkeypatch.setenv("TM1_IS_REAL", "x")
    cfg = {"a": "{env:TM1_IS_REAL}", "b": "{env:TM1_NOT_REAL}"}

    assert missing_env(cfg) == ["TM1_NOT_REAL"]


def test_a_variable_the_harness_reads_is_checked_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`TM1_RUNS_ROOT` decides where a run goes and the config never mentions it."""
    monkeypatch.delenv("TM1_RUNS_ROOT", raising=False)

    assert missing_env({}, also=("TM1_RUNS_ROOT",)) == ["TM1_RUNS_ROOT"]


def test_nothing_is_reported_when_everything_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Or the check cries wolf and stops being read."""
    monkeypatch.setenv("TM1_IS_REAL", "x")

    assert missing_env({"a": "{env:TM1_IS_REAL}"}) == []


# --- a broken project reads as a message, a broken harness as a stack --------


@pytest.mark.parametrize("exc", [
    FileNotFoundError("No cases.yaml in /p."),
    ValueError("'model_yaer': no such address. Did you mean model_year?"),
    TypeError("`steps` entries must each be one `name: {config}` mapping."),
    yaml.YAMLError("while parsing a block collection"),
])
def test_a_broken_project_prints_its_message_and_exits(exc: Exception) -> None:
    """Every one of these is raised deliberately, with a message already written."""
    with pytest.raises(SystemExit) as caught:
        _run_cleanly(_boom(exc))

    assert str(exc) in str(caught.value)


def test_a_key_error_is_not_double_quoted() -> None:
    """``KeyError``'s ``str()`` is the repr of its argument, so it needs unwrapping.

    Without this the reader gets ``error: "No case 'X' in /p."`` -- quotes around a
    sentence that already had its own.
    """
    with pytest.raises(SystemExit) as caught:
        _run_cleanly(_boom(KeyError("No case 'X' in /p.")))

    assert "No case 'X' in /p." in str(caught.value)
    assert '"No case' not in str(caught.value)


def test_a_bug_in_the_harness_keeps_its_traceback() -> None:
    """Swallowing this would make a harness bug look like a config mistake.

    The set caught above is the set of things a *project* can get wrong. Anything
    else is ours, and the person debugging it needs the stack.
    """
    with pytest.raises(AttributeError):
        _run_cleanly(_boom(AttributeError("'NoneType' object has no attribute 'x'")))
