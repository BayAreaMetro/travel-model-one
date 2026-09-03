"""Turning a project and a case into a run that is ready to start.

The order matters and is the whole point:

    load config.yaml -> apply the case -> fingerprint -> allocate a directory
    -> inject where it landed -> resolve {templates}

The fingerprint is taken **before** template resolution, so it sees literal
``{runs_root}/...`` rather than this machine's paths -- which is what lets the same
case be recognised as already-done on a different machine. And the run directory is
allocated **before** injection, because ``run_dir`` is one of the things injected.

This lives under ``run/`` rather than ``project/`` because it is about a run.
:mod:`tm1.project.config` only reads files; it knows nothing about where a run goes.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from tm1.project.cases import Case
from tm1.project.cases import load as load_cases
from tm1.project.config import env_value, load_config, resolve_templates
from tm1.project.overrides import apply_case
from tm1.run import directory as run_directory
from tm1.run import fingerprint as run_fingerprint
from tm1.run import receipt as run_receipt

#: Where run directories live, per machine.
RUNS_ROOT_VAR = "TM1_RUNS_ROOT"


@dataclass
class PreparedRun:
    """A case, the directory its run uses, and the config as that run sees it."""

    case: Case
    cfg: dict
    #: The case applied but templates still literal (``{run_dir}``, ``{env:...}``)
    #: -- a self-contained config.yaml for this case, portable to a fresh run_dir
    #: on any machine.  ``cfg`` itself is not, because injection and template
    #: resolution bake in *this* run's own directory.
    applied_cfg: dict
    run_dir: Path
    run_no: int
    fingerprint: str
    #: One of run_directory.NEW / run_directory.RESUME / run_directory.COMPLETE.
    state: str


def _sole_case(config_dir: Path, case_id: str | None) -> Case:
    """The case to run: the one named, or the only one the project declares."""
    expansion = load_cases(config_dir)
    if case_id:
        case = expansion.by_id(case_id)
        if case is None:
            available = ", ".join(c.id for c in expansion.cases) or "(none)"
            msg = f"No case {case_id!r} in {config_dir}.\nDeclared here: {available}"
            raise KeyError(msg)
        return case
    if len(expansion.cases) == 1:
        return expansion.cases[0]
    names = ", ".join(c.id for c in expansion.cases) or "(none)"
    msg = (
        f"{config_dir.name} declares {len(expansion.cases)} cases, so a run has to "
        f"name one: --case <ID>.\nDeclared here: {names}"
    )
    raise ValueError(msg)


def prepare_run(
    config_dir: Path, case_id: str | None = None, *, rerun: bool = False
) -> PreparedRun:
    """Everything a run needs to start: which case, which directory, what config.

    The order matters and is the point.  The case's overrides go on **before** the
    fingerprint is taken, and the fingerprint is taken **before** ``{env:}`` and
    ``{key}`` resolution -- so template strings are still literal and the same case
    fingerprints identically on every machine.  Only then is the run directory
    allocated and injected, which is why ``{case}-{NNN}`` cannot feed back into the
    fingerprint and make every run look new.
    """
    config_dir = Path(config_dir).resolve()
    case = _sole_case(config_dir, case_id)
    cfg = apply_case(load_config(config_dir), case)
    # Snapshot before injection mutates `cfg` in place below -- this is the
    # portable "config.yaml for this one case" written into `.tm1/`.
    applied_cfg = deepcopy(cfg)

    stamp = run_fingerprint.fingerprint(cfg, run_fingerprint.referenced_files(cfg, config_dir))
    project = config_dir.name
    runs_root = Path(env_value(RUNS_ROOT_VAR, "runs_root"))
    run_no, run_dir, state = run_directory.allocate(
        runs_root / project, case.id, stamp, rerun=rerun,
    )
    run_directory.check_length(run_dir)

    # Injected rather than declared: where a run is written is not a modelling
    # choice, and a config that stated it could not be run twice.
    cfg["runs_root"] = str(runs_root)
    cfg["project"] = project
    cfg["case"] = case.id
    cfg["run"] = run_dir.name
    cfg["run_dir"] = str(run_dir)

    resolved = resolve_templates(cfg)
    return PreparedRun(
        case=case,
        cfg=resolved if isinstance(resolved, dict) else {},
        applied_cfg=applied_cfg,
        run_dir=run_dir,
        run_no=run_no,
        fingerprint=stamp,
        state=state,
    )


def latest_run(config_dir: Path, case_id: str | None = None) -> PreparedRun | None:
    """The newest existing run for a case, without creating anything.

    What ``tm1 status`` reads: a report must never bring a run directory into
    being just by asking about it.
    """
    config_dir = Path(config_dir).resolve()
    case = _sole_case(config_dir, case_id)
    cfg = apply_case(load_config(config_dir), case)
    applied_cfg = deepcopy(cfg)
    stamp = run_fingerprint.fingerprint(cfg, run_fingerprint.referenced_files(cfg, config_dir))

    project = config_dir.name
    runs_root = Path(env_value(RUNS_ROOT_VAR, "runs_root"))
    existing = run_directory.existing_runs(runs_root / project, case.id)
    if not existing:
        return None
    run_no, run_dir = existing[-1]

    cfg["runs_root"] = str(runs_root)
    cfg["project"] = project
    cfg["case"] = case.id
    cfg["run"] = run_dir.name
    cfg["run_dir"] = str(run_dir)

    resolved = resolve_templates(cfg)
    receipt = run_receipt.read_receipt(run_dir) or {}
    return PreparedRun(
        case=case,
        cfg=resolved if isinstance(resolved, dict) else {},
        applied_cfg=applied_cfg,
        run_dir=run_dir,
        run_no=run_no,
        fingerprint=stamp,
        state=(
            run_directory.RESUME if receipt.get("fingerprint") == stamp else run_directory.NEW
        ),
    )
