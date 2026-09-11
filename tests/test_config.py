"""Tests for project config loading -- specifically `{env:NAME}`.

This is what keeps a project's config machine-independent: every path that
differs between machines is named in the config and set in `.env`, so moving a
project to another box is an `.env` edit rather than a YAML edit.

The behaviour worth pinning is that an unset variable is an *error*.  Expanding
it to an empty string would make `run_dir: ""` mean the current working
directory, and a fifteen-hour run would happily write itself there.
"""

import pytest

from pathlib import Path

from tm1.project.config import expand_env, load_config, resolve_templates


def test_an_env_reference_is_replaced_by_its_value(monkeypatch) -> None:  # noqa: ANN001
    """The whole mechanism: a path named in the config, valued in .env."""
    monkeypatch.setenv("TM1_TEST_DIR", "E:/Tests/somewhere")

    assert expand_env("{env:TM1_TEST_DIR}") == "E:/Tests/somewhere"


def test_a_reference_may_sit_inside_a_larger_string(monkeypatch) -> None:  # noqa: ANN001
    """`PATH: "{env:TM1_GAWK_DIR};{env:PATH}"` is the .bat's %PATH% idiom."""
    monkeypatch.setenv("TM1_GAWK_DIR", "C:/gawk/bin")
    monkeypatch.setenv("PATH", "C:/windows")

    assert expand_env("{env:TM1_GAWK_DIR};{env:PATH}") == "C:/gawk/bin;C:/windows"


def test_references_are_expanded_inside_nested_structures(monkeypatch) -> None:  # noqa: ANN001
    """Steps carry their own `env:` and `args:`, so it cannot be top-level only."""
    monkeypatch.setenv("TM1_TEST_DIR", "E:/x")
    cfg = {"env": {"PYTHONPATH": "{env:TM1_TEST_DIR}"}, "args": ["{env:TM1_TEST_DIR}"]}

    assert expand_env(cfg) == {"env": {"PYTHONPATH": "E:/x"}, "args": ["E:/x"]}


def test_non_strings_pass_through_untouched() -> None:
    """Counts, flags and nulls are config too, and none of them interpolate."""
    assert expand_env({"count": 3, "shadow_pricing": True, "dir": None}) == {
        "count": 3, "shadow_pricing": True, "dir": None,
    }


def test_an_unset_variable_is_an_error_naming_it(monkeypatch) -> None:  # noqa: ANN001
    """Silently empty would point a fifteen-hour run at the working directory."""
    monkeypatch.delenv("TM1_NOT_SET", raising=False)

    with pytest.raises(ValueError, match="TM1_NOT_SET is not set"):
        expand_env({"run_dir": "{env:TM1_NOT_SET}"})


def test_the_error_says_where_to_set_it(monkeypatch) -> None:  # noqa: ANN001
    """The fix is one file, so the message names it rather than the mechanism."""
    monkeypatch.delenv("TM1_NOT_SET", raising=False)

    with pytest.raises(ValueError, match=r"\.env\.example"):
        expand_env("{env:TM1_NOT_SET}")


def test_env_expands_before_key_interpolation(monkeypatch) -> None:  # noqa: ANN001
    """`run_dir` comes from .env, and other keys interpolate `{run_dir}`.

    So the environment pass has to run first, or `{run_dir}` resolves to the
    literal `{env:TM1_PROJ_DIR}` and every derived path is nonsense.
    """
    monkeypatch.setenv("TM1_PROJ_DIR", "E:/Tests/run")
    cfg = {
        "run_dir": "{env:TM1_PROJ_DIR}",
        "ctramp_output_dir": "{run_dir}/main",
        "logging": {"dir": "{run_dir}/logs"},
    }

    resolved = resolve_templates(cfg)

    assert resolved["run_dir"] == "E:/Tests/run"
    assert resolved["ctramp_output_dir"] == "E:/Tests/run/main"
    assert resolved["logging"]["dir"] == "E:/Tests/run/logs"


def test_a_config_with_no_env_references_is_unchanged() -> None:
    """The mechanism is opt-in; a fully literal config still loads."""
    cfg = {"run_dir": "E:/Tests/run", "ctramp_output_dir": "{run_dir}/main"}

    resolved = resolve_templates(cfg)

    assert resolved["ctramp_output_dir"] == "E:/Tests/run/main"


# --- a project's `steps:`, against the shared model file ---------------------


def _model_and_project(tmp_path: Path, model_steps: str, project_steps: str) -> Path:
    """A synthetic checkout: default-configs/ at the root, a project below it."""
    (tmp_path / "default-configs").mkdir()
    (tmp_path / "default-configs" / "ctramp-cube-model.yaml").write_text(
        f"steps:\n{model_steps}", encoding="utf-8",
    )
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "scenarios.yaml").write_text(
        f"steps:\n{project_steps}scenarios:\n  A: {{}}\n", encoding="utf-8",
    )
    return project


def test_a_projects_step_fills_in_a_shared_placeholder_in_place(tmp_path: Path) -> None:
    """A step the shared model names but leaves empty is filled in, not appended."""
    project = _model_and_project(
        tmp_path,
        "  - copy_inputs: {a: {from: 'x', to: 'y'}}\n"
        "  - copy_project_inputs: {}\n"
        "  - copy_input_to_working: {}\n",
        "  - copy_project_inputs: {b: {from: 'p', to: 'q'}}\n",
    )

    cfg = load_config(project)

    assert [next(iter(item)) for item in cfg["steps"]] == [
        "copy_inputs", "copy_project_inputs", "copy_input_to_working",
    ]
    assert cfg["steps"][1]["copy_project_inputs"] == {"b": {"from": "p", "to": "q"}}


def test_a_projects_step_is_appended_when_the_shared_model_has_no_such_name(
    tmp_path: Path,
) -> None:
    """No placeholder to fill -- a genuinely new step lands after the shared ones."""
    project = _model_and_project(
        tmp_path,
        "  - copy_inputs: {}\n",
        "  - vmt_vht_metrics: {script: 'hooks.py:vmt_vht_metrics'}\n",
    )

    cfg = load_config(project)

    assert [next(iter(item)) for item in cfg["steps"]] == ["copy_inputs", "vmt_vht_metrics"]
