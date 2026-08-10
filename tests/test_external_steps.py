"""Tests for the ``job:`` and ``command:`` step types.

``command:`` is exercised for real -- the scripts under test are written by
the tests and run through the actual interpreter -- because the whole point of the
step type is faithfulness to how ``RunModel.bat`` invoked things: argv, cwd,
environment and exit-code handling.  Mocking the subprocess would test nothing.

``job:`` is exercised with :func:`tm1.assignment.cube.runner.run_cube_job` patched,
since Cube is a licensed binary; what is verified is that the step hands it the
right job path, cwd and environment.
"""

import json
import sys
from pathlib import Path

import pytest

from tm1.runner import _load_step
from tm1.steps import external

#: Cluster size a period-looped Cube job needs, as the real jobs declare.
CLUSTER_NODES = 5

#: A script that records how it was invoked, so a test can assert on argv/cwd/env.
_PROBE = """
import json, os, sys
json.dump(
    {"argv": sys.argv[1:], "cwd": os.getcwd(), "iter": os.environ.get("ITER")},
    open(os.path.join(os.environ["PROBE_OUT"], "probe.json"), "w"),
)
"""

_FAILING = """
import sys
print("something went wrong")
sys.exit(3)
"""


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    """A project directory with a CTRAMP/scripts tree, as a real run has."""
    (tmp_path / "CTRAMP" / "scripts").mkdir(parents=True)
    return tmp_path


def _cfg(proj_dir: Path, name: str, step_cfg: dict, **extra: object) -> dict:
    """A resolved config. ``EN7`` is required, so every scenario must state it."""
    cfg = {
        "proj_dir": str(proj_dir),
        "steps": {name: step_cfg},
        "env": {"EN7": "DISABLED"},
    }
    cfg.update(extra)
    return cfg


def _write_script(proj_dir: Path, name: str, body: str) -> str:
    rel = Path("CTRAMP") / "scripts" / name
    (proj_dir / rel).write_text(body)
    return rel.as_posix()


# --- command: -------------------------------------------------------


def test_command_runs_with_argv_and_project_cwd(proj: Path) -> None:
    """Argv passes through and cwd is proj_dir -- what every legacy script assumes."""
    rel = _write_script(proj, "probe.py", _PROBE)
    step = {"command": rel, "args": ["hwy/tolls.csv", "hwy/tolls.dbf"],
            "env": {"PROBE_OUT": str(proj)}}

    external.make_step("probe", step)(proj, _cfg(proj, "probe", step))

    recorded = json.loads((proj / "probe.json").read_text())
    assert recorded["argv"] == ["hwy/tolls.csv", "hwy/tolls.dbf"]
    assert Path(recorded["cwd"]).resolve() == proj.resolve()


def test_command_substitutes_iteration_in_args_and_env(proj: Path) -> None:
    """``{iteration}`` survives config loading and is filled per round."""
    rel = _write_script(proj, "probe.py", _PROBE)
    step = {"command": rel, "args": ["--iter", "{iteration}"],
            "env": {"PROBE_OUT": str(proj), "ITER": "{iteration}"}}

    external.make_step("probe", step)(proj, _cfg(proj, "probe", step), iteration=2)

    recorded = json.loads((proj / "probe.json").read_text())
    assert recorded["argv"] == ["--iter", "2"]
    assert recorded["iter"] == "2"


def test_command_uses_this_interpreter(proj: Path) -> None:
    """Not a bare ``python``: the legacy extra is installed in *this* environment."""
    rel = _write_script(
        proj, "which.py",
        "import sys, os; open(os.path.join(os.environ['OUT'], 'exe.txt'), 'w')"
        ".write(sys.executable)",
    )
    step = {"command": rel, "env": {"OUT": str(proj)}}

    external.make_step("which", step)(proj, _cfg(proj, "which", step))

    assert (proj / "exe.txt").read_text() == sys.executable


def test_command_nonzero_exit_fails_the_step(proj: Path) -> None:
    """RunModel.bat guards every legacy script with ``if ERRORLEVEL 1 goto done``."""
    rel = _write_script(proj, "boom.py", _FAILING)
    step = {"command": rel}

    with pytest.raises(RuntimeError, match="exited 3"):
        external.make_step("boom", step)(proj, _cfg(proj, "boom", step))


def test_command_output_is_kept_on_disk(proj: Path) -> None:
    """Captured output survives the failure that makes it worth reading."""
    rel = _write_script(proj, "boom.py", _FAILING)
    step = {"command": rel}

    with pytest.raises(RuntimeError, match="something went wrong"):
        external.make_step("boom", step)(proj, _cfg(proj, "boom", step))

    assert "something went wrong" in (proj / "logs" / "boom.log").read_text()


def test_missing_command_names_proj_dir(proj: Path) -> None:
    """The error says which directory paths resolve against, since that is the trap."""
    step = {"command": "CTRAMP/scripts/absent.py"}

    with pytest.raises(FileNotFoundError, match="relative to proj_dir"):
        external.make_step("absent", step)(proj, _cfg(proj, "absent", step))


def test_non_python_program_runs_itself(proj: Path) -> None:
    """Only a .py gets an interpreter in front of it; anything else executes itself.

    The interpreter is a convenient non-``.py`` program to prove it with: prefixed
    wrongly, the argv would be ``python python.exe -c ...`` and the spawn would fail.
    """
    marker = proj / "ran.txt"
    step = {
        "command": sys.executable,
        "args": ["-c", f"open(r'{marker}', 'w').write('ok')"],
    }

    external.make_step("direct", step)(proj, _cfg(proj, "direct", step))

    assert marker.read_text() == "ok"


def test_pointing_command_at_scenario_code_names_script(proj: Path, tmp_path: Path) -> None:
    """The likely mistake: your own hook, reached for with the wrong key."""
    scenario_dir = tmp_path / "scenario"
    scenario_dir.mkdir()
    (scenario_dir / "hooks.py").write_text("def run(*a, **k): pass\n")
    step = {"command": "hooks.py"}

    with pytest.raises(ValueError, match="should use 'script:'"):
        external.make_step("hook", step)(scenario_dir, _cfg(proj, "hook", step))


# --- job: -----------------------------------------------------------------


def test_job_step_passes_path_cwd_and_env(
    proj: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Cube runner gets the resolved job, proj_dir as cwd, and the step's env."""
    calls: list[tuple] = []

    def record(job: str | Path, cwd: str | Path, **kw: object) -> int:
        calls.append((Path(job), Path(cwd), kw))
        return 0

    monkeypatch.setattr(external, "run_cube_job", record)
    rel = _write_script(proj, "SetTolls.job", "; a Cube job\n")
    step = {"job": rel, "env": {"ITER": "{iteration}"}, "cluster_nodes": CLUSTER_NODES}

    external.make_step("set_tolls", step)(proj, _cfg(proj, "set_tolls", step), iteration=1)

    job, cwd, kwargs = calls[0]
    assert job == proj / "CTRAMP" / "scripts" / "SetTolls.job"
    assert cwd == proj
    assert kwargs["cluster_nodes"] == CLUSTER_NODES
    # The step's own env: wins over the derived ITER, and the rest still arrives.
    assert kwargs["env_extra"]["ITER"] == "1"
    assert kwargs["env_extra"]["WGT"] == "1.0"
    assert kwargs["env_extra"]["TRNCONFIG"] == "FAST"


def test_job_without_cluster_nodes_starts_no_cluster(
    proj: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only DistributeMultistep jobs need a cluster; the rest must not start one."""
    calls: list[dict] = []

    def record(job: str | Path, cwd: str | Path, **kw: object) -> int:  # noqa: ARG001
        calls.append(kw)
        return 0

    monkeypatch.setattr(external, "run_cube_job", record)
    rel = _write_script(proj, "SetTolls.job", "; a Cube job\n")
    step = {"job": rel}

    external.make_step("set_tolls", step)(proj, _cfg(proj, "set_tolls", step))

    assert calls[0]["cluster_nodes"] is None


# --- cwd:, commpath:, iteration:, {env:} ----------------------------------


def test_cwd_moves_the_working_directory(proj: Path) -> None:
    """trnAssign.bat runs the transit jobs from the round's own directory."""
    rel = _write_script(proj, "probe.py", _PROBE)
    step = {"command": rel, "cwd": "trn/TransitAssignment.iter{iteration}",
            "env": {"PROBE_OUT": str(proj)}}

    external.make_step("probe", step)(proj, _cfg(proj, "probe", step), iteration=2)

    recorded = json.loads((proj / "probe.json").read_text())
    expected = proj / "trn" / "TransitAssignment.iter2"
    assert Path(recorded["cwd"]).resolve() == expected.resolve()


def test_commpath_is_resolved_against_the_project(
    proj: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job outside proj_dir must say where its cluster nodes talk."""
    calls: list[dict] = []

    def record(job: str | Path, cwd: str | Path, **kw: object) -> int:  # noqa: ARG001
        calls.append(kw)
        return 0

    monkeypatch.setattr(external, "run_cube_job", record)
    rel = _write_script(proj, "TransitAssign.job", "; a Cube job\n")
    step = {"job": rel, "cwd": "trn/TransitAssignment.iter1", "commpath": "commpath"}

    external.make_step("transit_assign", step)(
        proj, _cfg(proj, "transit_assign", step), iteration=1
    )

    assert calls[0]["commpath"] == proj / "commpath"


def test_a_step_key_pins_the_round(proj: Path) -> None:
    """RunModel.bat's `set ITER=0`: the warm-start steps sit outside the loop."""
    rel = _write_script(proj, "probe.py", _PROBE)
    step = {"command": rel, "iteration": 0, "env": {"PROBE_OUT": str(proj)}}

    # the runner supplies iteration=1 for a pre-loop step; the step's key wins
    external.make_step("warmstart_probe", step)(
        proj, _cfg(proj, "warmstart_probe", step), iteration=1
    )

    assert json.loads((proj / "probe.json").read_text())["iter"] == "0"


def test_env_reference_extends_rather_than_replaces(
    proj: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`PATH: "dir;{env:PATH}"` is the .bat's %PATH% idiom -- gawk needs it."""
    monkeypatch.setenv("PATH", "C:/existing")
    cfg = _cfg(proj, "x", {})
    cfg["env"]["PATH"] = "C:/gawk;{env:PATH}"

    assert external.model_environment(cfg)["PATH"] == "C:/gawk;C:/existing"


def test_env_reference_to_an_unset_variable_is_empty(
    proj: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better an empty string than a literal `{env:NAME}` reaching a Cube job."""
    monkeypatch.delenv("TM1_NOT_SET", raising=False)
    cfg = _cfg(proj, "x", {})
    cfg["env"]["THING"] = "a{env:TM1_NOT_SET}b"

    assert external.model_environment(cfg)["THING"] == "ab"


# --- the environment contract ---------------------------------------------


@pytest.mark.parametrize(
    ("iteration", "expected"),
    [
        (0, {"PREV_ITER": "0", "WGT": "1.0", "PREV_WGT": "0.00"}),
        (1, {"PREV_ITER": "0", "WGT": "1.0", "PREV_WGT": "0.00",
             "SAMPLESHARE": "0.15"}),
        (2, {"PREV_ITER": "1", "WGT": "0.50", "PREV_WGT": "0.50",
             "SAMPLESHARE": "0.30"}),
        (3, {"PREV_ITER": "2", "WGT": "0.33", "PREV_WGT": "0.67",
             "SAMPLESHARE": "0.50"}),
    ],
)
def test_per_iteration_env_matches_runmodel_bat(
    proj: Path, iteration: int, expected: dict
) -> None:
    """Transcribed from RunModel.bat 252-255, 276-281, 300-305, 324-329.

    One deliberate departure: PREV_ITER at iteration 1 is 0, not the .bat's 1.
    See the parity plan's finding 5 -- at 1 the averaging job reads the file it
    is about to write, which is the only reason the .bat branches there.
    """
    env = external.model_environment(_cfg(proj, "x", {}), iteration)

    assert env["ITER"] == str(iteration)
    for key, value in expected.items():
        assert env[key] == value


def test_iteration_zero_sets_no_sample_share(proj: Path) -> None:
    """Iteration 0 runs no demand model, so RunModel.bat samples nothing."""
    env = external.model_environment(_cfg(proj, "x", {}), 0)

    assert "SAMPLESHARE" not in env
    assert "SEED" not in env


def test_iteration_beyond_the_bat_is_refused_not_extrapolated(proj: Path) -> None:
    """RunModel.bat defines 0-3; guessing a fifth round's MSA weight changes results."""
    with pytest.raises(ValueError, match=r"No RunModel\.bat environment"):
        external.model_environment(_cfg(proj, "x", {}), 4)


def test_model_year_and_future_come_from_the_scenario(proj: Path) -> None:
    """No longer sliced out of the project folder name, as RunModel.bat did."""
    cfg = _cfg(proj, "x", {}, model_year=2023, future="PBA50")

    env = external.model_environment(cfg)

    assert env["MODEL_YEAR"] == "2023"
    assert env["FUTURE"] == "PBA50"


def test_en7_is_required_never_defaulted(proj: Path) -> None:
    """RunModel.bat 115-128 refuses to start without it; guessing changes results."""
    cfg = {"proj_dir": str(proj), "steps": {}}

    with pytest.raises(ValueError, match="EN7"):
        external.model_environment(cfg)


def test_env_block_overrides_the_derived_values(proj: Path) -> None:
    """The escape hatch wins last -- and departing from the .bat is then explicit."""
    cfg = _cfg(proj, "x", {})
    cfg["env"]["TRNCONFIG"] = "STANDARD"

    assert external.model_environment(cfg, 1)["TRNCONFIG"] == "STANDARD"


def test_complex_modes_default_to_a_space_not_empty(proj: Path) -> None:
    """RunModel.bat 146-147: "NOTE the blank ones should have a space"."""
    env = external.model_environment(_cfg(proj, "x", {}))

    assert env["COMPLEXMODES_DWELL"] == " "
    assert env["COMPLEXMODES_ACCESS"] == " "


def test_command_receives_the_model_environment(proj: Path) -> None:
    """A script sees ITER without the step having to declare it."""
    rel = _write_script(proj, "probe.py", _PROBE)
    step = {"command": rel, "env": {"PROBE_OUT": str(proj)}}

    external.make_step("probe", step)(proj, _cfg(proj, "probe", step), iteration=3)

    assert json.loads((proj / "probe.json").read_text())["iter"] == "3"


# --- resolution through the runner ----------------------------------------


def test_runner_resolves_both_external_keys(proj: Path) -> None:
    """``_load_step`` returns a callable for either key without importing anything."""
    _write_script(proj, "probe.py", _PROBE)
    _write_script(proj, "SetTolls.job", "; a Cube job\n")
    steps_cfg = {
        "csv_to_dbf": {"command": "CTRAMP/scripts/probe.py"},
        "set_tolls": {"job": "CTRAMP/scripts/SetTolls.job"},
    }

    for name in steps_cfg:
        assert callable(_load_step(name, steps_cfg, proj))


def test_declaring_two_kinds_of_step_is_rejected(proj: Path) -> None:
    """A step is one thing: a .job runs through Cube, a .py through the interpreter."""
    steps_cfg = {"muddle": {"job": "a.job", "command": "b.py"}}

    with pytest.raises(ValueError, match="use exactly one"):
        _load_step("muddle", steps_cfg, proj)


def test_builtin_step_cannot_be_redefined_as_external(proj: Path) -> None:
    """Built-in names still win -- the new keys do not open a back door."""
    steps_cfg = {"assignment": {"job": "CTRAMP/scripts/HwyAssign.job"}}

    with pytest.raises(ValueError, match="built in"):
        _load_step("assignment", steps_cfg, proj)


def test_unknown_step_error_mentions_the_external_keys(proj: Path) -> None:
    """The message has to teach all four ways to declare a step, not two."""
    with pytest.raises(ValueError, match="command"):
        _load_step("mystery", {"mystery": {}}, proj)
