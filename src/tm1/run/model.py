"""Step orchestrator — runs steps declared in the project's config.

Each step is a module (or any object) exposing ``run(config_dir, cfg, **kwargs)``.
Steps run in the order written.  ``steps:`` is a list of ``name: {config}`` entries
(a mapping also works, but only the list form can name a step twice -- the warm
start and the loop each carry their own copy of the assignment steps).  "What runs,
and when" is answerable by reading the config top to bottom.

Two entries nest, and they are the only ones::

    steps:
      - copy_inputs: {...}          # runs once, where it is written
      - warmstart:                  # runs once, at iteration 0
          - hwy_assign: {job: ..., skip_if_exists: "hwy/iter0/LOADEA.net"}
      - iterate:                    # rounds 1..count
          count: 3
          steps:
            - hwy_assign: {job: ...}
      - summarize: {...}            # runs once, at the final round

``warmstart:`` is ``RunModel.bat``'s ``set ITER=0`` pass: assign the staged demand
once, so round 1 has congested skims to read.  A step's round is decided by where
it is written and nowhere else -- there is no per-step ``iteration:`` key.

A step outside ``iterate:`` may declare ``skip_if_exists: <path>`` -- its work is
done when that file is on disk, so a rerun walks past it and a deleted file forces
a rebuild.  The key is refused inside ``iterate:``: the loop is the part of the run
that always re-runs, and its outputs land on the same paths every round, so an
existence check cannot tell this round's product from the last one's.

A project may add its own steps -- typically pre- or post-processing -- by
pointing at Python code::

    steps:
      copy_inputs: {...}
      simulate_ctramp: {...}
      assignment: {...}
      vmt_vht_metrics:
        script: "hooks.py:vmt_vht_metrics"     # path, relative to the project dir
      trip_length_report:
        module: "mtc_local.reports:trip_lengths"   # importable dotted path

There is no separate "hook" concept: a pre-processing step is one written before
the step it prepares for, a post-processing step one written after.  Custom steps
get the same contract as built-in ones -- the same resolved ``cfg``, the same
``**kwargs``, the same ``"skipped"`` return sentinel -- and can be targeted
individually with ``tm1 run --steps <name>``.

``script``/``module`` may name the function after a colon; without one, ``run`` is
used, matching the built-in steps.  Naming it lets one file hold several steps.

A step may instead run a program the harness cannot call in-process — a Cube
``.job``, or anything else, spawned as a subprocess::

    steps:
      set_tolls:
        job: "CTRAMP/scripts/preprocess/SetTolls.job"    # relative to run_dir
      csv_to_dbf:
        command: "CTRAMP/scripts/preprocess/csvToDbf.py"
        args: ["hwy/tolls.csv", "hwy/tolls.dbf"]

**Writing the code yourself? Use ``script:`` or ``module:``.**  They are imported
and called with the resolved ``cfg``, so the step can pass values to later steps
and return ``"skipped"``.  ``command:`` gets none of that -- only argv, an
environment, and an exit code -- and exists for programs the harness does not own,
today the legacy ``RunModel.bat`` corpus.  Pointing ``command:`` at something in the
project directory is an error naming ``script:``, because that is where your own
code lives.

``job:``/``command:`` are executed rather than imported, so they name no entrypoint
and resolve against ``run_dir`` rather than the project directory — that is the
directory ``RunModel.bat`` ran its artifacts from, and every one of them assumes it.
See :mod:`tm1.steps.external`.

Built-in step names always win: a project can add steps but never redefine one.

``cfg`` is shared across steps, so a step *may* modify it to pass computed values
downstream (a pre-processing step that resolves a path for the step after it, for
example).  This is supported; it also means an ill-behaved step can affect later
ones.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

import yaml

from tm1 import add_run_logfile, fmt_elapsed, remove_run_logfile
from tm1.project import scenarios as scenarios_mod
from tm1.project.config import load_config
from tm1.project.overrides import validate as validate_scenarios
from tm1.run import directory as run_directory
from tm1.run import receipt as run_receipt
from tm1.run.iterations import (
    apply_resume,
    apply_until,
    fmt_plan,
    iteration_plan,
    resume_token,
    select_steps,
    skip_target,
)
from tm1.run.prepare import PreparedRun, prepare_run
from tm1.status import slack
from tm1.status.slack import notify
from tm1.steps import DEFAULT_STEPS, load_step

log = logging.getLogger(__name__)


def _resolve_slack_level(cfg: dict, slack_level: str | bool | None) -> None:
    """CLI flag wins, then the project's `slack:` key, then "minimal"."""
    if slack_level is not None:
        slack.level = "verbose" if slack_level is True else slack_level
        return
    cfg_slack = cfg.get("slack", "minimal")
    slack.level = cfg_slack if isinstance(cfg_slack, str) else "off"


def _report_step(label: str, name: str, result: object, elapsed: float) -> None:
    """Record a finished step, distinguishing a real run from a self-skip."""
    if result == "skipped":
        notify(f"[{label}] {name} already done, skipped", verbose_only=True)
        log.info("--- Skipped: %s ---", name)
        return
    elapsed_str = fmt_elapsed(elapsed)
    notify(f"[{label}] {name} done ({elapsed_str})", verbose_only=True)
    log.info("--- Done: %s (%s) ---", name, elapsed_str)


def _report_resume(
    full_plan: list[tuple[str, int]], plan: list[tuple[str, int]], n_iters: int
) -> None:
    """State what a resumed run will skip and run, before it does any of it.

    Printed up front so a mistyped iteration is caught by reading the skipped
    list -- resuming at ``3:assignment`` would show ``simulate_ctramp@3`` as
    skipped, i.e. about to assign demand that was never generated.
    """
    if len(plan) >= len(full_plan):
        return
    skipped = full_plan[: len(full_plan) - len(plan)]
    log.info("Resuming at %s, iteration %d of %d", plan[0][0], plan[0][1], n_iters)
    log.info("  skipping %d already-completed step(s): %s",
             len(skipped), fmt_plan(skipped, n_iters))
    log.info("  running %d: %s", len(plan), fmt_plan(plan, n_iters))


def _sample_str(sample_rate: object) -> str:
    """The sample rate for the start notification, flat or per-round.

    ``sample_rate:`` is either one number for every round or a mapping of round
    to rate -- RunModel.bat's 0.15/0.30/0.50 ramp.  Formatting the mapping as a
    number raises, which happened before the run log opened and so reported as a
    bare TypeError rather than a config problem.
    """
    if sample_rate is None:
        return "per-iteration ramp"
    if isinstance(sample_rate, dict):
        return " -> ".join(f"{rate:.0%}" for _, rate in sorted(sample_rate.items()))
    return f"{sample_rate:.0%}"


def _notify_start(
    label: str, steps: list[str], configs: dict[tuple[str, int], dict],
    n_iters: int, kwargs: dict,
) -> None:
    """Announce what is about to run.

    Reads the demand step's config off the plan entries: it sits inside
    ``iterate``, so a top-level lookup would silently report defaults.
    """
    sim_cfg = next(
        (
            entry_cfg for (name, _), entry_cfg in configs.items()
            if name in ("simulate_ctramp", "simulate_activitysim")
        ),
        {},
    )
    sample_rate = kwargs.get("sample_rate") or sim_cfg.get("sample_rate")
    sample_str = _sample_str(sample_rate)
    notify(
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | threads: {sim_cfg.get('threads', 1)} | "
        f"shadow pricing: {'on' if sim_cfg.get('shadow_pricing', False) else 'off'}\n"
        f"  • iterations: {n_iters}"
    )


def _start_run_log(cfg: dict, label: str, steps: list[str]) -> logging.Handler | None:
    """Open a per-run log file under ``{run_dir}/logs`` and record what is starting.

    ``RunModel.bat`` appended a line to ``logs/feedback.rpt`` per milestone; this
    keeps the whole run instead -- every step boundary, every Cube job result and
    any traceback -- at DEBUG, while the console stays at INFO.

    The filename carries a timestamp so concurrent or repeated runs never write
    into each other's log, and so a failed run's log survives the next attempt.
    Returns None when no ``run_dir`` is configured, leaving console-only logging.
    """
    run_dir = cfg.get("run_dir")
    if not run_dir:
        return None

    log_cfg = cfg.get("logging", {}) or {}
    log_dir = Path(log_cfg.get("dir") or Path(run_dir) / "logs")
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")

    # pid separates concurrent runs on one machine; the counter separates runs
    # started within the same second.  FileHandler appends, so a name collision
    # would silently merge two runs into one log.
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"tm1_{stamp}_{os.getpid()}.log"
    attempt = 1
    while path.exists():
        path = log_dir / f"tm1_{stamp}_{os.getpid()}_{attempt}.log"
        attempt += 1

    level = getattr(logging, str(log_cfg.get("level", "DEBUG")).upper(), logging.DEBUG)
    handler = add_run_logfile(path, level=level)

    log.info("Run log: %s", path)
    log.debug("project=%s  steps=%s", label, ", ".join(steps))
    log.debug("run_dir=%s", run_dir)
    return handler


def _check_scenarios(config_dir: Path) -> None:
    """Refuse to start when any scenario in the project fails to resolve.

    Checked against the *unresolved* config, which is where addresses are written,
    and reported all at once rather than one failure per attempt: finding scenario
    27's typo fifteen hours in is the failure this exists to prevent.
    """
    problems = validate_scenarios(load_config(config_dir), scenarios_mod.load(config_dir))
    if problems:
        joined = "\n  ".join(problems)
        msg = f"scenarios.yaml does not resolve against the shared model:\n  {joined}"
        raise ValueError(msg)


class AlreadyCompleteError(Exception):
    """Raised when a run is asked for that has already finished unchanged.

    Its own type so the CLI can report it as an ordinary answer -- the run is
    done -- rather than as a failure with a traceback.
    """


def _begin_run(config_dir: Path, kwargs: dict) -> tuple[PreparedRun, str]:
    """Settle which scenario runs where, and stamp the directory before anything else.

    Everything that has to happen before the first step: every scenario is checked
    against the config, the run's directory is chosen, and the receipt and the
    resolved config are written -- so a run that dies in its first minute still
    says what it was and where it came from.

    The label is the *run*, not the project: two scenarios of one project are two
    different runs, and the log, the Slack line and the resume hint all have to
    say which one they mean.
    """
    _check_scenarios(config_dir)
    prepared = prepare_run(
        config_dir, kwargs.get("scenario"), rerun=bool(kwargs.get("rerun")),
    )
    label = f"{config_dir.name}:{prepared.run_dir.name}"
    if prepared.state == run_directory.COMPLETE:
        msg = (
            f"{label} is already complete, and nothing has changed since it ran:\n"
            f"  {prepared.run_dir}\nPass --rerun to run it again anyway, which "
            f"writes a new run beside this one rather than over it."
        )
        raise AlreadyCompleteError(msg)
    _open_run(config_dir, prepared, label, kwargs.get("base_model_dir"))
    return prepared, label


def _report_failure(
    prepared: PreparedRun, label: str, config_dir: Path,
    exc: Exception, token: str, name: str,
) -> None:
    """Record a failed step everywhere it needs to be recorded.

    The log keeps the traceback, the console keeps the command that continues the
    run, Slack keeps the headline, and the receipt keeps ``failed`` -- so the next
    attempt resumes this directory instead of starting a new one.
    """
    # exc_info so the run log keeps the traceback, not just the message.
    log.exception("Step %s failed: %s", name, exc)
    # The failed step did not finish, so resuming includes it.
    log.error(
        "Resume with: tm1 run %s --resume-at %s", config_dir.name, token,
    )
    notify(f":exclamation: {label} failed at {name}: {exc}")
    _close_run(prepared, "failed")


def _close_run(prepared: PreparedRun, status: str) -> None:
    """Record how a run ended, leaving everything else in the receipt alone.

    Read back rather than rebuilt: the receipt written at the start carries the
    machine, pid and git state, and losing those on the way out would make a
    finished run less traceable than an unfinished one.
    """
    receipt = run_receipt.read_receipt(prepared.run_dir)
    if receipt is None:
        return
    receipt["status"] = status
    receipt["ended"] = datetime.now().astimezone().isoformat(timespec="seconds")
    run_receipt.Receipt(**receipt).write(prepared.run_dir)


def _open_run(
    config_dir: Path, prepared: PreparedRun, label: str, repo_root: object,
) -> None:
    """Write the receipt and the resolved config into the run directory."""
    log.info(
        "%s -- %s in %s", label,
        prepared.state, prepared.run_dir,
    )
    run_receipt.Receipt(
        project=config_dir.name,
        scenario=prepared.scenario.id,
        run=prepared.run_no,
        fingerprint=prepared.fingerprint,
        machine=run_receipt.machine_name(),
        pid=os.getpid(),
        started=datetime.now().astimezone().isoformat(timespec="seconds"),
        git=run_receipt.git_state(Path(str(repo_root or config_dir.parent))),
    ).write(prepared.run_dir)
    _write_resolved(prepared.run_dir, prepared.cfg)
    _write_scenario_config(prepared.run_dir, prepared.applied_cfg)


def _write_resolved(run_dir: Path, cfg: dict) -> None:
    """Archive the config exactly as this run sees it.

    The answer to "what did this run actually use", written before any step runs
    so it survives a crash: reconstructing it afterwards from the project config
    would show what the project says *now*, not what the run was given.
    """
    path = Path(run_dir) / run_receipt.TM1_DIR / run_receipt.RESOLVED
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def _write_scenario_config(run_dir: Path, applied_cfg: dict) -> None:
    """Archive the scenario merged into the config, templates left open.

    Unlike :func:`_write_resolved`, this one is portable: it names no run_dir, so
    copying it into a project directory (with a one-entry scenarios.yaml beside
    it) re-runs this exact scenario into a fresh run_dir, even after the shared model
    or scenarios.yaml have since moved on.
    """
    path = Path(run_dir) / run_receipt.TM1_DIR / run_receipt.SCENARIO_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(applied_cfg, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def run_model(
    config_dir: Path,
    steps: list[str] | None = None,
    slack_level: str | bool | None = "minimal",
    **kwargs: object,
) -> None:
    """Run a sequence of pipeline steps for a project.

    Parameters
    ----------
    config_dir : Path
        Path to the project directory.
    steps : list[str], optional
        Steps to run.  If None, uses step keys from config or DEFAULT_STEPS.
    slack_level : str
        "false", "minimal", or "verbose".
    **kwargs
        Passed through to each step's ``run()`` function.
        Common: ``base_model_dir``.
    """
    config_dir = Path(config_dir).resolve()
    prepared, label = _begin_run(config_dir, kwargs)
    cfg = prepared.cfg

    _resolve_slack_level(cfg, slack_level)

    steps_cfg = cfg.get("steps") or {name: {} for name in DEFAULT_STEPS}  # pyright: ignore[reportAttributeAccessIssue]

    # Always the config's whole plan: `--steps`, `--resume-at` and `--until`
    # select from it rather than defining one, so a step keeps the round it
    # actually belongs to.  `--iterations N` overrides iterate.count.  Built
    # before the run log opens: a config error is a console conversation, not
    # a run.
    full_plan, configs = iteration_plan(steps_cfg, override=kwargs.get("iterations"))

    declared = list(dict.fromkeys(name for name, _ in full_plan))
    log_handler = _start_run_log(cfg, label, steps or declared)
    t0_total = time.time()

    try:
        n_iters = max((i for _, i in full_plan), default=1)
        plan = select_steps(full_plan, steps)
        plan = apply_resume(plan, kwargs.get("resume_at"), cfg.get("run_dir"))
        plan = apply_until(plan, kwargs.get("until"))
        _report_resume(full_plan, plan, n_iters)
        prev_iter = None
        _notify_start(label, steps or declared, configs, n_iters, kwargs)

        for name, iteration in plan:
            step_cfg = configs[(name, iteration)]

            # The step's declared product is already on disk: its work is done.
            # Announced before the skip check, not after: a skipped step still
            # belongs to its round, and anything placing it by the last banner --
            # a reader, or `tm1 status` -- would file it under the previous one.
            if n_iters > 1 and iteration != prev_iter:
                log.info("=== Iteration %d of %d ===", iteration, n_iters)
                prev_iter = iteration

            skip = skip_target(step_cfg, cfg)
            if skip is not None:
                # The round is on the line so `tm1 status` can place a step in the
                # plan exactly, rather than inferring it from position -- a resumed
                # run starts mid-plan, where position alone is ambiguous.
                log.info(
                    "--- Step: %s (iteration %d) -- skipped, %s exists ---",
                    name, iteration, skip,
                )
                notify(f"[{label}] {name} skipped ({skip.name} exists)", verbose_only=True)
                continue

            run_step = load_step(name, step_cfg, config_dir)

            log.info("--- Step: %s (iteration %d) ---", name, iteration)
            t0_step = time.time()
            try:
                # Merged rather than passed positionally: an explicit caller-supplied
                # `iteration` would otherwise be a duplicate-keyword TypeError.
                # `step_cfg` is the entry's own block -- with `steps:` as a list a
                # name may appear twice, so the entry, not the name, identifies it.
                result = run_step(
                    config_dir, cfg,
                    **{
                        **kwargs,
                        "iteration": iteration,
                        "step_name": name,
                        "step_cfg": step_cfg,
                    },
                )
            except KeyboardInterrupt:
                log.warning("Cancelled during %s", name)
                notify(f":no_entry_sign: {label} cancelled during {name}")
                raise
            except Exception as e:
                _report_failure(
                    prepared, label, config_dir, e,
                    resume_token(full_plan, name, iteration), name,
                )
                raise
            _report_step(label, name, result, time.time() - t0_step)

        total = time.time() - t0_total
        # Logged as well as notified: it is how `tm1 status` tells a finished run
        # from one that stopped on the last step it happened to reach.
        log.info("=== Finished %s in %s ===", label, fmt_elapsed(total))
        notify(f"Finished {label} in {fmt_elapsed(total)} :white_check_mark:")
        # Only now, and only on the way out cleanly: `complete` is what stops the
        # next run from reopening this directory, so a run that died must not
        # claim it.  A killed harness leaves `running`, which is exactly right --
        # the work is unfinished and the next attempt should continue it.
        _close_run(prepared, "complete")
    finally:
        # Detached even on failure, so the log is flushed and a second run in the
        # same process does not append to it.
        remove_run_logfile(log_handler)
