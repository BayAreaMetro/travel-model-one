r"""Run programs the harness does not own: Cube ``.job`` files, and anything else.

Two config keys, for the two kinds of thing that cannot be called in-process::

    set_tolls:
      job: "CTRAMP/scripts/preprocess/SetTolls.job"

    csv_to_dbf:
      command: "CTRAMP/scripts/preprocess/csvToDbf.py"
      args: ["hwy/tolls.csv", "hwy/tolls.dbf"]

``job:`` runs a Cube Voyager program through :func:`run_cube_job`, which handles the
cluster and Cube's own exit-code convention.  ``command:`` spawns a program: a
``.py`` gets this interpreter (never a bare ``python`` -- the venv is the point),
anything else is executed directly.

.. warning:: **Prefer ``script:`` / ``module:`` for code you write yourself.**

    Those import your module and call ``run(scenario_dir, cfg, **kwargs)``, so a
    step gets the resolved config, can pass computed values to later steps, and can
    return the ``"skipped"`` sentinel.  A subprocess gets none of that: it sees only
    argv and the environment, and its only channel back is an exit code.

    ``command:`` exists for programs the harness *cannot* call in-process --
    today, the legacy ``RunModel.bat`` corpus.  Reaching for it to run your own
    Python is a shell-out where a function call would do.

**Why the legacy corpus runs here rather than being ported.**  ``RunModel.bat`` is
orchestration, and orchestration is what the harness replaces.  The artifacts it
invokes are not: a ``.job`` is a Cube program and a preprocess ``.py`` is a model
input generator.  Running them unmodified, from where they already live, is what
lets the harness claim parity -- it drives the legacy corpus rather than
reimplementing it, and phase 4 then replaces them one at a time.

Paths resolve against ``proj_dir``, not the scenario directory, and ``cwd`` is fixed
there rather than configurable.  Every legacy script assumes the directory
``RunModel.bat`` gave it; run from anywhere else, its bare relative paths resolve
against the wrong tree and it fails obscurely -- or worse, quietly reads the wrong
file.

Two placeholders survive config loading and are filled at step time: ``{iteration}``,
the current round, and ``{env:NAME}``, the value of an environment variable.  The
latter is how a config *extends* a variable rather than replacing it --
``PATH: "C:/tools;{env:PATH}"`` is the ``.bat``'s ``%PATH%`` idiom, which a spawned
environment would otherwise lose.  Both work in ``args:``, ``env:``, ``cwd:`` and
``commpath:``.

``cwd:`` moves a step's working directory, relative to ``proj_dir``.  The transit
jobs are why it exists: ``trnAssign.bat`` runs them from
``trn/TransitAssignment.iter{N}`` and they write relative to it.  ``commpath:``
goes with it -- Cube's cluster directory defaults to ``<cwd>/commpath``, so a job
run outside ``proj_dir`` has to say where its nodes should talk.

``iteration:`` pins a step to a round.  Steps inside ``iterate:`` get theirs from
the loop; the warm-start steps sit outside it and say ``iteration: 0``, which is
``RunModel.bat``'s ``set ITER=0``.

**``args:`` is the argv the program receives, not a transliteration of the ``.bat``
line.**  ``RunModel.bat`` sets its empty variables to a single space on purpose
("NOTE the blank ones should have a space"), and ``cmd`` collapses those on
expansion, so ``python x.py complexDwell %EMPTY% complexAccess %EMPTY%`` arrives as
four arguments, not six.  Writing the ``""`` out literally passes arguments the
script never saw, and can crash it.  Expand each ``%VAR%`` the way ``cmd`` would,
then write down what is left.

Legacy artifacts take their parameters from the *environment*, not from arguments:
``HwyAssign.job`` reads ``%ITER%``, the feedback jobs read ``%WGT%``,
``IxForecasts_horizon.job`` reads ``%MODEL_YEAR%`` and ``%FUTURE%``.
:func:`model_environment` reproduces what the ``.bat`` set; a scenario adds the rest
in an ``env:`` block::

    env:
      EN7: DISABLED        # required -- RunModel.bat refuses to start without it

``EN7`` is deliberately not defaulted: guessing it silently changes what the model
does.
"""

import logging
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from tm1.assignment.cube.runner import run_cube_job

log = logging.getLogger(__name__)

#: Config keys this module handles.  Both are resolved by :func:`make_step`.
JOB_KEY = "job"
COMMAND_KEY = "command"
KEYS: tuple[str, ...] = (JOB_KEY, COMMAND_KEY)

#: Seconds before a spawned program is presumed hung.  Generous: transitDwellAccess
#: parses a 33k-line transit network, and SkimsDatabase-scale work is slower still.
DEFAULT_TIMEOUT = 7200

#: How much captured output to quote when a program fails.  The full text is on
#: disk; this is what lands in the run log, where it is actually read.
_TAIL_LINES = 40

#: Values ``RunModel.bat`` hard-codes for the whole run (lines 135-147).  Scenario
#: defaults, overridable through ``env:``.
#:
#: ``COMPLEXMODES_*`` are a single space, not empty -- the ``.bat`` says so
#: explicitly ("NOTE the blank ones should have a space").  Nothing reads them as
#: environment variables today; they are here so the environment matches what the
#: legacy corpus was written against.  What *is* load-bearing is the argv they
#: expand to, which is stated directly in ``args:`` -- see the module note above.
_BAT_DEFAULTS: dict[str, str] = {
    "MAXITERATIONS": "3",
    "TRNCONFIG": "FAST",
    "COMPLEXMODES_DWELL": " ",
    "COMPLEXMODES_ACCESS": " ",
}

#: ``RunModel.bat``'s per-iteration environment, transcribed literally from its
#: four blocks (lines 252-255, 276-281, 300-305, 324-329).  Every Cube job in the
#: feedback and assignment steps reads these.
#:
#: Kept as a table rather than computed, because a table can be audited against the
#: ``.bat`` line by line and a formula cannot.  Iteration 0 setting no ``SAMPLESHARE``
#: or ``SEED`` is not an omission: it runs no demand model, so nothing samples.
PER_ITERATION: dict[int, dict[str, str]] = {
    0: {"PREV_ITER": "0", "WGT": "1.0",  "PREV_WGT": "0.00"},
    # PREV_ITER is 0, not the .bat's 1 -- the one deliberate departure.  At 1 the
    # averaging job reads hwy/iter1/avgload{P}.net, the file it is about to write,
    # which is why the .bat skips it and copies instead.  Pointing at iteration 0
    # and weighting it 0.00 gives the same volumes with no branch, and
    # trnAssign.bat:15-16 already applies this same fix locally.  See the parity
    # plan's finding 5 -- CTIM provenance changes and is verified there.
    1: {"PREV_ITER": "0", "WGT": "1.0",  "PREV_WGT": "0.00",
        "SAMPLESHARE": "0.15", "SEED": "0"},
    2: {"PREV_ITER": "1", "WGT": "0.50", "PREV_WGT": "0.50",
        "SAMPLESHARE": "0.30", "SEED": "0"},
    3: {"PREV_ITER": "2", "WGT": "0.33", "PREV_WGT": "0.67",
        "SAMPLESHARE": "0.50", "SEED": "0"},
}

#: Scenario config key -> environment variable, for values the harness already
#: states explicitly instead of slicing out of a directory name.
_FROM_CONFIG: dict[str, str] = {"model_year": "MODEL_YEAR", "future": "FUTURE"}

#: Scenario-wide environment block.  A step's own ``env:`` layers on top of it,
#: so the same key name means the same thing at both scopes.
ENV_BLOCK = "env"


def _resolve_target(
    target: str, proj_dir: Path, scenario_dir: Path, step_name: str, key: str
) -> Path:
    """Locate the program, relative to ``proj_dir`` unless absolute."""
    path = Path(str(target)).expanduser()
    if not path.is_absolute():
        path = proj_dir / path
    if path.is_file():
        return path

    # Almost always someone reaching for the wrong key: the scenario directory is
    # where a step's *own* code lives, and own code should be called, not spawned.
    if (scenario_dir / str(target)).is_file():
        msg = (
            f"Step {step_name!r}: {key}: {target!r} was not found under proj_dir "
            f"({proj_dir}), but it does exist in the scenario directory. Code you "
            f"wrote yourself should use 'script:' instead -- it is imported and "
            f"called with the resolved config, rather than spawned with only argv "
            f"and an environment. {key!r} is for programs the harness cannot call "
            f"in-process."
        )
        raise ValueError(msg)

    msg = (
        f"Step {step_name!r}: {key} not found: {path}. Paths are relative to "
        f"proj_dir ({proj_dir}), because that is the directory RunModel.bat ran "
        f"its artifacts from and every one of them assumes it."
    )
    raise FileNotFoundError(msg)


#: ``{env:NAME}`` -- the value of an environment variable, read at step time.
_ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute(value: object, values: dict[str, object]) -> str:
    """Fill placeholders left unresolved by config loading.

    ``resolve_templates`` runs once at load, so two kinds of reference survive to
    here: ``{iteration}``, which varies per round, and ``{env:NAME}``, which reads
    the process environment.  The latter is how a config extends a variable rather
    than replacing it -- ``PATH: "C:/tools;{env:PATH}"`` is the ``.bat``'s
    ``%PATH%`` idiom, which a spawned environment would otherwise lose.
    """
    text = str(value)
    for key, replacement in values.items():
        text = text.replace("{" + key + "}", str(replacement))
    return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), text)


def model_environment(cfg: dict, iteration: object = None) -> dict[str, str]:
    """The environment ``RunModel.bat`` gave every artifact it invoked.

    Legacy jobs and scripts read their parameters from the environment, not from
    arguments -- ``HwyAssign.job`` reads ``%ITER%``, ``IxForecasts_horizon.job``
    reads ``%MODEL_YEAR%`` and ``%FUTURE%``, the feedback jobs read ``%WGT%``.  The
    ``.bat`` set these by assignment before each block; this reproduces them.

    Precedence, lowest first: :data:`_BAT_DEFAULTS`, values the scenario already
    states explicitly (``model_year``/``future``), the :data:`PER_ITERATION` row,
    then the scenario's ``env:`` block.

    ``env:`` winning last makes it a real escape hatch -- and a way to depart
    from ``RunModel.bat`` silently.  Overriding a per-iteration value is a
    deliberate break with parity, not a configuration tweak.
    """
    env = dict(_BAT_DEFAULTS)
    env["MODEL_DIR"] = str(Path(cfg["proj_dir"]))

    for key, name in _FROM_CONFIG.items():
        if cfg.get(key) is not None:
            env[name] = str(cfg[key])

    if iteration is not None and str(iteration) != "":
        round_ = int(iteration)
        if round_ not in PER_ITERATION:
            msg = (
                f"No RunModel.bat environment for iteration {round_}: the .bat "
                f"defines {min(PER_ITERATION)}-{max(PER_ITERATION)} and no more. "
                f"Its WGT/PREV_WGT follow method-of-successive-averages, so a "
                f"further round would need 1/{round_}, but extrapolating is a "
                f"change to the model, not a configuration one. Add the row to "
                f"PER_ITERATION deliberately, or keep the loop within range."
            )
            raise ValueError(msg)
        env["ITER"] = str(iteration)
        env.update(PER_ITERATION[round_])

    values = {"iteration": iteration if iteration is not None else ""}
    env.update({
        str(k): _substitute(v, values) for k, v in (cfg.get(ENV_BLOCK) or {}).items()
    })

    if "EN7" not in env:
        msg = (
            f"Legacy steps need EN7 in the environment: RunModel.bat refuses to "
            f"start without it (lines 115-128), and updateTelecommute_forEN7.py "
            f"reads it directly. Set it under {ENV_BLOCK}: in the scenario config "
            f"-- 'ENABLED' or 'DISABLED'. It is deliberately not defaulted, because "
            f"guessing it silently changes what the model does."
        )
        raise ValueError(msg)

    return env


def _step_env(cfg: dict, step_cfg: dict, values: dict[str, object]) -> dict[str, str]:
    """The full environment for one step: the model's, plus its own ``env:`` block."""
    env = model_environment(cfg, values.get("iteration"))
    declared = step_cfg.get("env") or {}
    env.update({str(k): _substitute(v, values) for k, v in declared.items()})
    return env


def _write_output(proj_dir: Path, step_name: str, text: str) -> Path:
    """Persist a program's captured output, mirroring how Cube jobs keep theirs."""
    logs = proj_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / f"{step_name}.log"
    path.write_text(text, encoding="utf-8", errors="replace")
    return path


def _argv(program: Path, args: list[str]) -> list[str]:
    """The command line to spawn.

    A ``.py`` runs under :data:`sys.executable`, never a bare ``python``: the extras
    a legacy script needs (NetworkWrangler, dbfpy3, xlrd) are installed into *this*
    environment, and ``python`` would find whichever interpreter is first on PATH.
    Anything else is assumed to be executable and runs itself.
    """
    if program.suffix.lower() == ".py":
        return [sys.executable, str(program), *args]
    return [str(program), *args]


def _working_dir(step_cfg: dict, proj_dir: Path, values: dict) -> Path:
    """Where the program runs.  ``proj_dir`` unless the step says otherwise.

    The transit jobs are the reason this is configurable at all: ``trnAssign.bat``
    runs them from ``trn/TransitAssignment.iter{N}``, and they write their outputs
    relative to it.  Everything else runs where ``RunModel.bat`` ran it.
    """
    declared = step_cfg.get("cwd")
    if not declared:
        return proj_dir
    path = Path(_substitute(declared, values)).expanduser()
    return path if path.is_absolute() else proj_dir / path


def _run_job(
    step_name: str, step_cfg: dict, proj_dir: Path, scenario_dir: Path,
    env: dict[str, str], values: dict,
) -> None:
    """Run one Cube ``.job`` through the existing Cube runner."""
    job = _resolve_target(
        step_cfg[JOB_KEY], proj_dir, scenario_dir, step_name, JOB_KEY
    )
    cluster_nodes = step_cfg.get("cluster_nodes")
    cwd = _working_dir(step_cfg, proj_dir, values)
    cwd.mkdir(parents=True, exist_ok=True)

    # Cube's cluster communication directory defaults to <cwd>/commpath.  A job run
    # outside proj_dir needs it stated, or its nodes talk in the wrong place.
    commpath = step_cfg.get("commpath")

    log.info("%s: %s", step_name, job.name)
    run_cube_job(
        job, cwd,
        env_extra=dict(env),
        cluster_nodes=int(cluster_nodes) if cluster_nodes else None,
        commpath=proj_dir / _substitute(commpath, values) if commpath else None,
        timeout=float(step_cfg.get("timeout", DEFAULT_TIMEOUT)),
    )


def _run_command(
    step_name: str, step_cfg: dict, proj_dir: Path, scenario_dir: Path,
    env: dict[str, str], values: dict,
) -> None:
    """Spawn one program, with the argv, cwd and environment ``RunModel.bat`` gave it."""
    program = _resolve_target(
        step_cfg[COMMAND_KEY], proj_dir, scenario_dir, step_name, COMMAND_KEY
    )
    args = [_substitute(a, values) for a in (step_cfg.get("args") or [])]
    # Inherited, not replaced: legacy scripts need PATH, SystemRoot and the rest of
    # a working Windows environment as much as they need ITER.
    full_env = {**os.environ, **env}
    cwd = _working_dir(step_cfg, proj_dir, values)
    cwd.mkdir(parents=True, exist_ok=True)

    argv = _argv(program, args)
    log.info("%s: %s %s", step_name, program.name, " ".join(args))

    result = subprocess.run(  # noqa: S603
        argv, cwd=cwd, env=full_env, capture_output=True, text=True,
        timeout=float(step_cfg.get("timeout", DEFAULT_TIMEOUT)), check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    logfile = _write_output(proj_dir, step_name, output)

    # RunModel.bat guards every legacy script with `if ERRORLEVEL 1 goto done`, so
    # any non-zero status is fatal -- unlike runtpp, which it checks against 2.
    if result.returncode != 0:
        tail = "\n".join(output.splitlines()[-_TAIL_LINES:])
        msg = (
            f"Step {step_name!r}: {program.name} exited {result.returncode}.\n"
            f"Full output: {logfile}\n"
            f"Last {_TAIL_LINES} lines:\n{tail}"
        )
        raise RuntimeError(msg)

    log.debug("%s: output -> %s", step_name, logfile)


def make_step(step_name: str, step_cfg: dict) -> Callable[..., str | None]:
    """Build the ``run(scenario_dir, cfg, **kwargs)`` callable for an external step.

    Resolution happens at call time, not here, so a missing program is reported when
    the step actually runs rather than when the plan is assembled -- steps routinely
    produce the inputs of later steps.
    """
    declared = [k for k in KEYS if k in step_cfg]
    if len(declared) > 1:
        msg = (
            f"Step {step_name!r} declares both {JOB_KEY!r} and {COMMAND_KEY!r}; "
            f"use one. A .job runs through Cube; anything else is spawned directly."
        )
        raise ValueError(msg)
    key = declared[0]

    def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:
        proj_dir = Path(cfg["proj_dir"])
        # A step may name its own round.  The warm-start steps do: they sit outside
        # `iterate:`, where the runner would otherwise call them iteration 1, and
        # RunModel.bat's `set ITER=0` block is exactly this.
        iteration = step_cfg.get("iteration", kwargs.get("iteration", ""))
        values = {"iteration": iteration}
        env = _step_env(cfg, step_cfg, values)
        if key == JOB_KEY:
            _run_job(step_name, step_cfg, proj_dir, Path(scenario_dir), env, values)
        else:
            _run_command(
                step_name, step_cfg, proj_dir, Path(scenario_dir), env, values
            )
        return None

    run.__name__ = step_name
    run.__doc__ = f"Run the {key} declared by step {step_name!r}."
    return run
