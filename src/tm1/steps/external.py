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

    Those import your module and call ``run(config_dir, cfg, **kwargs)``, so a
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

Paths resolve against ``run_dir``, not the project directory, and ``cwd`` is fixed
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

``cwd:`` moves a step's working directory, relative to ``run_dir``.  The transit
jobs are why it exists: ``trnAssign.bat`` runs them from
``trn/TransitAssignment.iter{N}`` and they write relative to it.  ``commpath:``
goes with it -- Cube's cluster directory defaults to ``<cwd>/commpath``, so a job
run outside ``run_dir`` has to say where its nodes should talk.

A step's iteration is decided by where it sits inside ``iterate:`` -- before
``iteration_zero_begins`` it runs at iterations 1..count, at or after it also at
iteration 0, ``RunModel.bat``'s ``set ITER=0``.  ``{iteration}`` above expands to
that number.

``verify:`` names the artifacts a step must have produced::

    prep_assign:
      job: "CTRAMP/scripts/assign/PrepAssign.job"
      verify: ["main/trips{PERIOD}.tpp"]

An exit code says the program ran, not that it did anything.  ``PrepAssign.job``
returns cleanly when the CT-RAMP trip lists it reads are absent, and the empty
matrices then surface minutes later as an unrelated ``HwyAssign.job`` failure --
so the run reports the wrong step.  A step that declares its outputs fails where
the fault is.  ``{PERIOD}`` expands over the five assignment periods, which keeps
the common case one line.  This is only for external steps: a ``module:`` or
``script:`` step is called in-process and raises.

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
:func:`model_environment` reproduces what the ``.bat`` set; a project adds the rest
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

from cube.job import run_cube_job
from tm1.assignment.cube.highway import PERIODS

log = logging.getLogger(__name__)

#: Config keys this module handles.  Both are resolved by :func:`make_step`.
JOB_KEY = "job"
COMMAND_KEY = "command"
KEYS: tuple[str, ...] = (JOB_KEY, COMMAND_KEY)

#: Artifacts a step declares it produces, checked once it returns.
VERIFY_KEY = "verify"

#: Expanded over the five assignment periods in a ``verify:`` entry, so the usual
#: case -- one artifact per period -- stays a single line.
_PERIOD_REF = "{PERIOD}"

#: Seconds before a spawned program is presumed hung.  Generous:
#: SkimsDatabase-scale work parses large networks and runs slower still.
DEFAULT_TIMEOUT = 7200

#: How much captured output to quote when a program fails.  The full text is on
#: disk; this is what lands in the run log, where it is actually read.
_TAIL_LINES = 40

#: Values ``RunModel.bat`` hard-codes for the whole run (lines 135-147).  Project
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

#: Project-wide environment block.  A step's own ``env:`` layers on top of it,
#: so the same key name means the same thing at both scopes.
ENV_BLOCK = "env"


def _resolve_target(
    target: str, run_dir: Path, config_dir: Path, step_name: str, key: str
) -> Path:
    """Locate the program, relative to ``run_dir`` unless absolute."""
    path = Path(str(target)).expanduser()
    if not path.is_absolute():
        path = run_dir / path
    if path.is_file():
        return path

    # Almost always someone reaching for the wrong key: the project directory is
    # where a step's *own* code lives, and own code should be called, not spawned.
    if (config_dir / str(target)).is_file():
        msg = (
            f"Step {step_name!r}: {key}: {target!r} was not found under run_dir "
            f"({run_dir}), but it does exist in the project directory. Code you "
            f"wrote yourself should use 'script:' instead -- it is imported and "
            f"called with the resolved config, rather than spawned with only argv "
            f"and an environment. {key!r} is for programs the harness cannot call "
            f"in-process."
        )
        raise ValueError(msg)

    msg = (
        f"Step {step_name!r}: {key} not found: {path}. Paths are relative to "
        f"run_dir ({run_dir}), because that is the directory RunModel.bat ran "
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

    Precedence, lowest first: :data:`_BAT_DEFAULTS`, the :data:`PER_ITERATION` row,
    then the project's ``env:`` block -- which is where ``MODEL_YEAR`` and ``FUTURE``
    now live, since they are environment variables like every other entry there.

    ``env:`` winning last makes it a real escape hatch -- and a way to depart
    from ``RunModel.bat`` silently.  Overriding a per-iteration value is a
    deliberate break with parity, not a configuration tweak.
    """
    env = dict(_BAT_DEFAULTS)
    env["MODEL_DIR"] = str(Path(cfg["run_dir"]))

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
            f"reads it directly. Set it under {ENV_BLOCK}: in the project config "
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


def _write_output(run_dir: Path, step_name: str, text: str) -> Path:
    """Persist a program's captured output, mirroring how Cube jobs keep theirs."""
    logs = run_dir / "logs"
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


def _working_dir(step_cfg: dict, run_dir: Path, values: dict) -> Path:
    """Where the program runs.  ``run_dir`` unless the step says otherwise.

    The transit jobs are the reason this is configurable at all: ``trnAssign.bat``
    runs them from ``trn/TransitAssignment.iter{N}``, and they write their outputs
    relative to it.  Everything else runs where ``RunModel.bat`` ran it.
    """
    declared = step_cfg.get("cwd")
    if not declared:
        return run_dir
    path = Path(_substitute(declared, values)).expanduser()
    return path if path.is_absolute() else run_dir / path


def _run_job(
    step_name: str, step_cfg: dict, run_dir: Path, config_dir: Path,
    env: dict[str, str], values: dict,
) -> None:
    """Run one Cube ``.job`` through the existing Cube runner."""
    job = _resolve_target(
        step_cfg[JOB_KEY], run_dir, config_dir, step_name, JOB_KEY
    )
    cluster_nodes = step_cfg.get("cluster_nodes")
    cwd = _working_dir(step_cfg, run_dir, values)
    cwd.mkdir(parents=True, exist_ok=True)

    # Cube's cluster communication directory defaults to <cwd>/commpath.  A job run
    # outside run_dir needs it stated, or its nodes talk in the wrong place.
    commpath = step_cfg.get("commpath")

    log.info("%s: %s", step_name, job.name)
    run_cube_job(
        job, cwd,
        env_extra=dict(env),
        cluster_nodes=int(cluster_nodes) if cluster_nodes else None,
        commpath=run_dir / _substitute(commpath, values) if commpath else None,
        timeout=float(step_cfg.get("timeout", DEFAULT_TIMEOUT)),
    )


def _run_command(
    step_name: str, step_cfg: dict, run_dir: Path, config_dir: Path,
    env: dict[str, str], values: dict,
) -> None:
    """Spawn one program, with the argv, cwd and environment ``RunModel.bat`` gave it."""
    program = _resolve_target(
        step_cfg[COMMAND_KEY], run_dir, config_dir, step_name, COMMAND_KEY
    )
    args = [_substitute(a, values) for a in (step_cfg.get("args") or [])]
    # Inherited, not replaced: legacy scripts need PATH, SystemRoot and the rest of
    # a working Windows environment as much as they need ITER.
    full_env = {**os.environ, **env}
    cwd = _working_dir(step_cfg, run_dir, values)
    cwd.mkdir(parents=True, exist_ok=True)

    argv = _argv(program, args)
    log.info("%s: %s %s", step_name, program.name, " ".join(args))

    result = subprocess.run(  # noqa: S603
        argv, cwd=cwd, env=full_env, capture_output=True, text=True,
        timeout=float(step_cfg.get("timeout", DEFAULT_TIMEOUT)), check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    logfile = _write_output(run_dir, step_name, output)

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


def _verify_outputs(
    step_name: str, step_cfg: dict, run_dir: Path, values: dict
) -> None:
    """Check the artifacts a step declared under ``verify:``.

    A clean exit means the program ran, not that it produced anything.
    ``PrepAssign.job`` is the case that motivated this: it returns 0 when the
    CT-RAMP trip lists it reads are missing, and the empty ``trips{PERIOD}.tpp``
    then fails ``HwyAssign.job`` minutes later, blaming the wrong step.

    Zero bytes counts as missing.  A Cube job that opens its output and writes
    nothing leaves the file behind, and that is the shape this failure takes.
    """
    declared = step_cfg.get(VERIFY_KEY) or []
    if isinstance(declared, str):
        declared = [declared]

    expected: list[str] = []
    for entry in declared:
        text = _substitute(entry, values)
        if _PERIOD_REF in text:
            expected.extend(text.replace(_PERIOD_REF, period) for period in PERIODS)
        else:
            expected.append(text)

    missing = []
    for entry in expected:
        path = Path(entry).expanduser()
        path = path if path.is_absolute() else run_dir / path
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(path)

    if missing:
        names = "\n  ".join(str(p) for p in missing)
        msg = (
            f"Step {step_name!r} returned cleanly but did not produce what it "
            f"declares under {VERIFY_KEY}:\n  {names}\n"
            f"The step's own log is in {run_dir / 'logs'}; the fault is here, not "
            f"in whatever reads these next."
        )
        raise FileNotFoundError(msg)

    if expected:
        log.debug("%s: verified %d output(s)", step_name, len(expected))


def make_step(step_name: str, step_cfg: dict) -> Callable[..., str | None]:
    """Build the ``run(config_dir, cfg, **kwargs)`` callable for an external step.

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

    def run(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:
        run_dir = Path(cfg["run_dir"])
        # The runner supplies the round, from the block this step is written in.
        # The step_cfg lookup is for direct calls -- a config that states its own
        # `iteration:` is refused by the runner before it gets here.
        iteration = step_cfg.get("iteration", kwargs.get("iteration", ""))
        values = {"iteration": iteration}
        env = _step_env(cfg, step_cfg, values)
        if key == JOB_KEY:
            _run_job(step_name, step_cfg, run_dir, Path(config_dir), env, values)
        else:
            _run_command(
                step_name, step_cfg, run_dir, Path(config_dir), env, values
            )
        _verify_outputs(step_name, step_cfg, run_dir, values)
        return None

    run.__name__ = step_name
    run.__doc__ = f"Run the {key} declared by step {step_name!r}."
    return run
