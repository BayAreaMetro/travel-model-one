"""Turning a project and a scenario into a run that is ready to start.

The order matters:

    load the config -> apply the scenario -> resolve the directory -> inject
    where it landed -> resolve {templates}

This lives under ``run/`` rather than ``project/`` because it is about a run.
:mod:`tm1.project.config` only reads files; it knows nothing about where a run goes.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from tm1.project.config import env_value, load_config, resolve_templates
from tm1.project.overrides import apply_scenario
from tm1.project.scenarios import Scenario
from tm1.project.scenarios import load as load_scenarios
from tm1.run import directory as run_directory

#: Where run directories live, per machine.
RUNS_ROOT_VAR = "TM1_RUNS_ROOT"


@dataclass
class PreparedRun:
    """A scenario, the directory its run uses, and the config as that run sees it."""

    scenario: Scenario
    cfg: dict
    #: The scenario applied but templates still literal (``{run_dir}``,
    #: ``{env:...}``) -- a self-contained config for this scenario, portable
    #: to a fresh run_dir on any machine.  ``cfg`` itself is not, because
    #: injection and template resolution bake in *this* run's own directory.
    applied_cfg: dict
    run_dir: Path
    run_no: int
    #: One of run_directory.NEW / run_directory.RESUME.
    state: str


def _sole_scenario(config_dir: Path, scenario_id: str | None) -> Scenario:
    """The scenario to run: the one named, or the only one the project declares."""
    expansion = load_scenarios(config_dir)
    if scenario_id:
        scenario = expansion.by_id(scenario_id)
        if scenario is None:
            available = ", ".join(c.id for c in expansion.scenarios) or "(none)"
            msg = f"No scenario {scenario_id!r} in {config_dir}.\nDeclared here: {available}"
            raise KeyError(msg)
        return scenario
    if len(expansion.scenarios) == 1:
        return expansion.scenarios[0]
    names = ", ".join(c.id for c in expansion.scenarios) or "(none)"
    msg = (
        f"{config_dir.name} declares {len(expansion.scenarios)} scenarios, so a "
        f"run has to name one: --scenario <ID>.\nDeclared here: {names}"
    )
    raise ValueError(msg)


def prepare_run(
    config_dir: Path, scenario_id: str | None = None, *, run_number: int, resume: bool = False,
) -> PreparedRun:
    """Everything a run needs to start: which scenario, which directory, what config."""
    config_dir = Path(config_dir).resolve()
    scenario = _sole_scenario(config_dir, scenario_id)
    cfg = apply_scenario(load_config(config_dir), scenario)
    # Snapshot before injection mutates `cfg` in place below -- this is the
    # portable "config for this one scenario" written into `.tm1/`.
    applied_cfg = deepcopy(cfg)

    project = config_dir.name
    runs_root = Path(env_value(RUNS_ROOT_VAR, "runs_root"))
    run_dir, state = run_directory.resolve(runs_root, scenario.id, run_number, resume=resume)
    run_directory.check_length(run_dir)

    # Injected rather than declared: where a run is written is not a modelling
    # choice, and a config that stated it could not be run twice.
    cfg["runs_root"] = str(runs_root)
    cfg["project"] = project
    cfg["scenario"] = scenario.id
    cfg["run"] = run_dir.name
    cfg["run_dir"] = str(run_dir)

    resolved = resolve_templates(cfg)
    return PreparedRun(
        scenario=scenario,
        cfg=resolved if isinstance(resolved, dict) else {},
        applied_cfg=applied_cfg,
        run_dir=run_dir,
        run_no=run_number,
        state=state,
    )


def latest_run(config_dir: Path, scenario_id: str | None = None) -> PreparedRun | None:
    """The newest existing run for a scenario, without creating anything.

    What ``tm1 status`` reads: a report must never bring a run directory into
    being just by asking about it.
    """
    config_dir = Path(config_dir).resolve()
    scenario = _sole_scenario(config_dir, scenario_id)
    cfg = apply_scenario(load_config(config_dir), scenario)
    applied_cfg = deepcopy(cfg)

    project = config_dir.name
    runs_root = Path(env_value(RUNS_ROOT_VAR, "runs_root"))
    existing = run_directory.existing_runs(runs_root, scenario.id)
    if not existing:
        return None
    run_no, run_dir = existing[-1]

    cfg["runs_root"] = str(runs_root)
    cfg["project"] = project
    cfg["scenario"] = scenario.id
    cfg["run"] = run_dir.name
    cfg["run_dir"] = str(run_dir)

    resolved = resolve_templates(cfg)
    return PreparedRun(
        scenario=scenario,
        cfg=resolved if isinstance(resolved, dict) else {},
        applied_cfg=applied_cfg,
        run_dir=run_dir,
        run_no=run_no,
        state=run_directory.RESUME,
    )
