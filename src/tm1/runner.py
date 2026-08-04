"""Step orchestrator — runs steps declared in scenario_config.yaml.

Each step is a module (or any object) exposing ``run(scenario_dir, cfg, **kwargs)``.
Steps are flat: every step is a top-level key under ``steps:``, and they run in the
order written.  There is no grouping and no nesting, so "what runs, and when" is
answerable by reading the config top to bottom.

A scenario may add its own steps -- typically pre- or post-processing -- by
pointing at Python code::

    steps:
      copy_inputs: {...}
      simulate_ctramp: {...}
      assignment: {...}
      vmt_vht_metrics:
        script: "hooks.py:vmt_vht_metrics"     # path, relative to the scenario dir
      trip_length_report:
        module: "mtc_local.reports:trip_lengths"   # importable dotted path

There is no separate "hook" concept: a pre-processing step is one written before
the step it prepares for, a post-processing step one written after.  Custom steps
get the same contract as built-in ones -- the same resolved ``cfg``, the same
``**kwargs``, the same ``"skipped"`` return sentinel -- and can be targeted
individually with ``tm1 run --steps <name>``.

``script``/``module`` may name the function after a colon; without one, ``run`` is
used, matching the built-in steps.  Naming it lets one file hold several steps.

Built-in step names always win: a scenario can add steps but never redefine one.

``cfg`` is shared across steps, so a step *may* modify it to pass computed values
downstream (a pre-processing step that resolves a path for the step after it, for
example).  This is supported; it also means an ill-behaved step can affect later
ones.
"""

import importlib
import importlib.util
import logging
import os
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType

import yaml

import tm1.steps.assignment as assignment_step
import tm1.steps.build.highway_networks as build_highway_networks_step
import tm1.steps.build.hsr_trips as build_hsr_trips_step
import tm1.steps.build.nonmotorized_skims as build_nonmotorized_skims_step
import tm1.steps.build.transit_lines as build_transit_lines_step
import tm1.steps.configure_ctramp as configure_ctramp_step
import tm1.steps.convert_skims as convert_skims_step
import tm1.steps.filter_popsyn as filter_popsyn_step
import tm1.steps.populationsim as populationsim_step
import tm1.steps.prepare_survey as prepare_survey_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate_activitysim as simulate_activitysim_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
import tm1.steps.summaries.calibration as calibration_step
import tm1.steps.summaries.core as core_step
import tm1.steps.walk_access_buffers as walk_access_buffers_step
import tm1.steps.warmstart as warmstart_step
from tm1 import add_run_logfile, remove_run_logfile, slack
from tm1.config import load_config, resolve_templates
from tm1.slack import notify

log = logging.getLogger(__name__)


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed time as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m:02d}m"


#: Built-in steps, mapped to the callable that runs each one.  Values are plain
#: callables so a single module can supply several steps, and so built-in and
#: scenario-supplied steps resolve to exactly the same kind of thing.
STEPS: dict[str, Callable] = {
    "copy_inputs": setup_step.run,
    "walk_access_buffers": walk_access_buffers_step.run,
    "build_highway_networks": build_highway_networks_step.run,
    "build_nonmotorized_skims": build_nonmotorized_skims_step.run,
    "build_transit_lines": build_transit_lines_step.run,
    "build_hsr_trips": build_hsr_trips_step.run,
    "warmstart": warmstart_step.run,
    "filter_popsyn": filter_popsyn_step.run,
    "configure_ctramp": configure_ctramp_step.run,
    "convert_skims": convert_skims_step.run,
    "prepare_survey": prepare_survey_step.run,
    "populationsim": populationsim_step.run,
    "simulate_activitysim": simulate_activitysim_step.run,
    "simulate_ctramp": simulate_ctramp_step.run,
    "assignment": assignment_step.run,
    "core_summaries": core_step.run,
    "calibration": calibration_step.run,
}

DEFAULT_STEPS = list(STEPS.keys())

#: Keys a scenario uses to point a step at its own code.
_CUSTOM_KEYS = ("script", "module")

#: Function called on a custom step's module when none is named after a colon.
_DEFAULT_ENTRYPOINT = "run"


def _split_entrypoint(target: str) -> tuple[str, str]:
    """Split ``"hooks.py:vmt_vht_metrics"`` into target and function name.

    Only splits when the trailing segment is a Python identifier, so Windows
    drive letters survive: ``E:/runs/prep.py`` keeps its colon, because
    ``/runs/prep.py`` is not an identifier.
    """
    head, sep, tail = target.rpartition(":")
    if sep and tail.isidentifier():
        return head, tail
    return target, _DEFAULT_ENTRYPOINT


def _load_script(path: Path, scenario_dir: Path) -> ModuleType:
    """Import a ``.py`` file as a module, without putting its directory on sys.path.

    The module is registered under a name qualified by the scenario, so two
    scenarios that both ship a ``preprocess.py`` do not collide in
    ``sys.modules``.
    """
    spec = importlib.util.spec_from_file_location(
        f"tm1_scenario_{scenario_dir.name}_{path.stem}", path
    )
    if spec is None or spec.loader is None:
        msg = f"Could not load step script as a Python module: {path}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    # Registered before exec so the module can import itself / pickle cleanly.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


#: Step name reserved for the global feedback loop.
_ITERATE = "iterate"


def _flatten_steps(steps_cfg: dict) -> dict:
    """Step configs with the loop body lifted alongside the top-level steps.

    Lets step lookup stay uniform: a step inside ``iterate`` resolves exactly as
    one outside it.
    """
    flat: dict = {}
    for name, step_cfg in steps_cfg.items():
        if name == _ITERATE:
            flat.update((step_cfg or {}).get("steps") or {})
        else:
            flat[name] = step_cfg
    return flat


def _iteration_plan(
    steps_cfg: dict, steps: list[str], override: int | None = None
) -> list[tuple[str, int]]:
    """Expand the step list into an ordered ``[(step, iteration)]`` execution plan.

    A *global iteration* is demand plus assignment: demand responds to the
    congested skims the previous assignment produced.  ``RunModel.bat`` expresses
    that by calling ``RunIteration.bat`` N times; here the loop body is nested::

        steps:
          copy_inputs: {}
          iterate:
            count: 3
            steps:
              simulate_ctramp: {}
              assignment: {}
          calibration: {}

    Nesting makes the body contiguous by construction, and names each step once.
    Steps before the loop run at iteration 1; steps after it run once at the final
    iteration, since they summarise the finished run.
    """
    plan: list[tuple[str, int]] = []
    current = 1

    for name in steps:
        if name != _ITERATE:
            plan.append((name, current))
            continue

        it_cfg = steps_cfg.get(_ITERATE)
        if not isinstance(it_cfg, dict):
            msg = (
                f"`{_ITERATE}` must be a block with `count` and `steps`:\n\n"
                f"    {_ITERATE}:\n      count: 3\n      steps:\n"
                f"        simulate_ctramp: {{}}\n        assignment: {{}}"
            )
            raise TypeError(msg)

        count = int(override if override is not None else it_cfg.get("count", 1))
        if count < 1:
            msg = f"{_ITERATE}.count must be >= 1, got {count}"
            raise ValueError(msg)

        body = list((it_cfg.get("steps") or {}).keys())
        if not body:
            msg = f"`{_ITERATE}` declares no steps; the loop body cannot be empty."
            raise ValueError(msg)

        for i in range(1, count + 1):
            plan += [(s, i) for s in body]
        current = count

    return plan


def _fmt_plan(plan: list[tuple[str, int]], n_iters: int) -> str:
    """Render plan entries, showing the iteration only when there is more than one."""
    if n_iters <= 1:
        return ", ".join(s for s, _ in plan)
    return ", ".join(f"{s}@{i}" for s, i in plan)


def resume_token(plan: list[tuple[str, int]], step: str, iteration: int) -> str:
    """The ``--resume-at`` argument that would restart at this point.

    Includes the iteration prefix only when the step appears more than once, so
    the hint printed on failure is the shortest unambiguous form.
    """
    return f"{iteration}:{step}" if sum(s == step for s, _ in plan) > 1 else step


def _apply_resume(
    plan: list[tuple[str, int]],
    resume_at: str | None,
    proj_dir: str | Path | None = None,
) -> list[tuple[str, int]]:
    """Drop everything before *resume_at*, which itself **runs**.

    Takes ``step`` or ``iteration:step``; the prefix is needed only when a step
    appears more than once, which happens only inside ``iterate`` with
    ``count > 1``.  A bare name matching several entries is an error rather than
    a guess -- picking the wrong round costs hours of Cube.

    The named step re-runs from the start; it is never continued part-way.  Cube
    jobs are not transactional, so a killed ``HwyAssign`` leaves partial ``.net``
    and ``.tpp`` files that only a fresh run overwrites cleanly.
    """
    if not resume_at:
        return plan

    # "Resume" presupposes a previous run.  Without this, pointing it at an empty
    # project directory would skip staging and demand, then assign whatever stale
    # matrices happened to be lying around.
    if proj_dir is not None:
        p = Path(proj_dir)
        if not p.is_dir() or not any(p.iterdir()):
            msg = (
                f"--resume-at needs a project directory a previous run populated; "
                f"{p} is {'missing' if not p.is_dir() else 'empty'}. Run without "
                f"--resume-at to start from the beginning."
            )
            raise ValueError(msg)

    prefix, _, name = resume_at.rpartition(":")
    name = name.strip()
    want = int(prefix.strip()) if prefix.strip() else None

    matches = [
        i for i, (step, it) in enumerate(plan)
        if step == name and (want is None or it == want)
    ]
    n_iters = max((i for _, i in plan), default=1)

    if not matches:
        msg = (
            f"--resume-at {resume_at!r} matches nothing in this run.\n"
            f"Planned: {_fmt_plan(plan, n_iters)}\n"
            f"Give a step name, or iteration:step to pick a round."
        )
        raise ValueError(msg)

    if want is None and len(matches) > 1:
        rounds = ", ".join(f"{plan[i][1]}:{name}" for i in matches)
        msg = (
            f"--resume-at {name!r} is ambiguous -- it runs in {len(matches)} "
            f"iterations. Say which: {rounds}"
        )
        raise ValueError(msg)

    return plan[matches[0] :]


def _resolve_slack_level(cfg: dict, slack_level: str | bool | None) -> None:
    """CLI flag wins, then the scenario's `slack:` key, then "minimal"."""
    if slack_level is not None:
        slack.level = "verbose" if slack_level is True else slack_level
        return
    cfg_slack = cfg.get("slack", "minimal")
    slack.level = cfg_slack if isinstance(cfg_slack, str) else "off"


def _report_step(name: str, result: object, elapsed: float) -> None:
    """Record a finished step, distinguishing a real run from a self-skip.

    Log only.  Per-step Slack messages were the bulk of a run's notifications
    and none of its signal -- a reader wants to hear about starting, finishing
    and failing, not about each of a dozen steps.
    """
    if result == "skipped":
        log.info("--- Skipped: %s ---", name)
        return
    log.info("--- Done: %s (%s) ---", name, _fmt_elapsed(elapsed))


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
             len(skipped), _fmt_plan(skipped, n_iters))
    log.info("  running %d: %s", len(plan), _fmt_plan(plan, n_iters))


def _notify_start(
    label: str,
    steps: list[str],
    flat_steps_cfg: dict,
    n_iters: int,
    kwargs: dict,
    scenario_dir: Path | None = None,
    log_path: Path | None = None,
) -> None:
    """Announce what is about to run.

    Reads the demand step from the *flattened* configs: it normally sits inside
    ``iterate``, so a top-level lookup would silently report defaults.  The two
    demand models describe their run differently -- ActivitySim by household
    sample size and process count, CT-RAMP by sample rate and thread count -- so
    each reports in its own terms.  The log path is included so a reader can
    follow the run without first finding the machine.
    """
    asim_cfg = flat_steps_cfg.get("simulate_activitysim") or {}
    if asim_cfg:
        base = kwargs.get("base_model_dir") or (
            scenario_dir.parent.parent if scenario_dir else Path()
        )
        asim = _merged_asim_settings(asim_cfg, base)
        sample = asim.get("households_sample_size", 0)
        sample_str = "full" if sample == 0 else f"{sample:,} HH"
        threads = asim.get("num_processes", 1)
        shadow = asim.get("use_shadow_pricing", False)
    else:
        sim_cfg = flat_steps_cfg.get("simulate_ctramp") or {}
        rate = kwargs.get("sample_rate") or sim_cfg.get("sample_rate")
        sample_str = "per-iteration ramp" if rate is None else f"{rate:.0%}"
        threads = sim_cfg.get("threads", 1)
        shadow = sim_cfg.get("shadow_pricing", False)

    notify(
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | threads: {threads} | "
        f"shadow pricing: {'on' if shadow else 'off'}\n"
        f"  • iterations: {n_iters}"
        + (f"\n  • log: {log_path}" if log_path else "")
    )


def _prepare_plan(
    steps_cfg: dict, steps: list[str], cfg: dict, kwargs: dict
) -> tuple[list[tuple[str, int]], list[tuple[str, int]], int]:
    """Build the execution plan, apply ``--resume-at``, and report what is skipped.

    Returns ``(full_plan, plan, n_iters)`` -- the full plan is kept because
    ``resume_token`` needs it to tell an ambiguous step name from a unique one.
    """
    full_plan = _iteration_plan(steps_cfg, steps, override=kwargs.get("iterations"))
    n_iters = max((i for _, i in full_plan), default=1)
    plan = _apply_resume(full_plan, kwargs.get("resume_at"), cfg.get("proj_dir"))
    _report_resume(full_plan, plan, n_iters)
    return full_plan, plan, n_iters


def _notify_crash(label: str, elapsed: float, log_path: str | None) -> None:
    """Report a run that ended without either succeeding or raising.

    Reached when the process is torn down under us -- killed, rebooted, the
    interpreter exiting -- so that the last word is not "starting".
    """
    notify(
        f":skull: {label} stopped without finishing after {_fmt_elapsed(elapsed)}"
        + (f"\n  • log: {log_path}" if log_path else "")
    )


def _notify_failure(
    label: str,
    scenario: str,
    step: str,
    error: BaseException,
    resume: str,
    elapsed: float,
    log_path: Path | None,
) -> None:
    """Report a failure with everything needed to act on it.

    The message carries the resume command and the log path deliberately: the
    point of a failure notification is to save a trip to the machine, and the
    error text alone rarely does.
    """
    notify(
        f":exclamation: {label} failed at *{step}* after {_fmt_elapsed(elapsed)}\n"
        f"  • {type(error).__name__}: {error}\n"
        f"  • resume: `tm1 run --scenario {scenario} --resume-at {resume}`"
        + (f"\n  • log: {log_path}" if log_path else "")
    )


def _start_run_log(cfg: dict, label: str, steps: list[str]) -> logging.Handler | None:
    """Open a per-run log file under ``{proj_dir}/logs`` and record what is starting.

    ``RunModel.bat`` appended a line to ``logs/feedback.rpt`` per milestone; this
    keeps the whole run instead -- every step boundary, every Cube job result and
    any traceback -- at DEBUG, while the console stays at INFO.

    The filename carries a timestamp so concurrent or repeated runs never write
    into each other's log, and so a failed run's log survives the next attempt.
    Returns None when no ``proj_dir`` is configured, leaving console-only logging.
    """
    proj_dir = cfg.get("proj_dir")
    if not proj_dir:
        return None

    log_cfg = cfg.get("logging", {}) or {}
    log_dir = Path(log_cfg.get("dir") or Path(proj_dir) / "logs")
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
    log.debug("scenario=%s  steps=%s", label, ", ".join(steps))
    log.debug("proj_dir=%s", proj_dir)
    return handler


def _load_step(step_name: str, steps_cfg: dict, scenario_dir: Path) -> Callable:
    """Resolve a step name to the callable that runs it.

    Built-in steps take precedence.  Anything else must declare ``script:`` (a
    path, relative to the scenario directory unless absolute) or ``module:`` (an
    importable dotted path), either optionally naming a function after a colon.
    """
    step_cfg = steps_cfg.get(step_name)
    declared = (
        [k for k in _CUSTOM_KEYS if k in step_cfg] if isinstance(step_cfg, dict) else []
    )

    if step_name in STEPS:
        if declared:
            msg = (
                f"Step {step_name!r} is built in and cannot be redefined by "
                f"{declared[0]!r}. Rename the custom step, or drop the "
                f"{declared[0]!r} key to use the built-in."
            )
            raise ValueError(msg)
        return STEPS[step_name]

    if len(declared) > 1:
        msg = f"Step {step_name!r} declares both 'script' and 'module'; use one."
        raise ValueError(msg)

    if not declared:
        msg = (
            f"Unknown step: {step_name!r}. Built-in steps are "
            f"{', '.join(STEPS)}. To run your own code, give the step a "
            f"'script:' (path relative to the scenario directory) or a "
            f"'module:' (importable dotted path)."
        )
        raise ValueError(msg)

    target, func_name = _split_entrypoint(step_cfg[declared[0]])

    if declared[0] == "module":
        mod = importlib.import_module(target)
    else:
        path = Path(target).expanduser()
        if not path.is_absolute():
            path = scenario_dir / path
        if not path.is_file():
            msg = f"Step {step_name!r}: script not found: {path}"
            raise FileNotFoundError(msg)
        mod = _load_script(path, scenario_dir)
        target = str(path)

    source = f"{target}:{func_name}"
    if not hasattr(mod, func_name):
        named = "" if func_name == _DEFAULT_ENTRYPOINT else f" (named by {step_name!r})"
        msg = (
            f"Step {step_name!r}: {target} defines no {func_name}(){named}. Steps "
            f"need 'def {func_name}(scenario_dir, cfg, **kwargs)', the same "
            f"contract as the built-in steps."
        )
        raise AttributeError(msg)

    func = getattr(mod, func_name)
    if not callable(func):
        msg = f"Step {step_name!r} ({source}): {func_name!r} is not callable."
        raise TypeError(msg)

    log.info("Step %s -> custom code at %s", step_name, source)
    return func


def _merged_asim_settings(sim_cfg: dict, base_model_dir: object) -> dict:
    """Merge ``settings.yaml`` down the ActivitySim config-inheritance chain."""
    asim_cfg = sim_cfg.get("activitysim", sim_cfg) if sim_cfg else {}
    settings: dict = {}
    for c in reversed(asim_cfg.get("configs", [])):
        p = Path(c) if Path(c).is_absolute() else Path(str(base_model_dir)) / c
        sf = p / "settings.yaml"
        if sf.exists():
            with sf.open(encoding="utf-8") as f:
                settings.update(yaml.safe_load(f) or {})
    return settings


def run_model(
    scenario_dir: Path,
    steps: list[str] | None = None,
    slack_level: str | bool | None = "minimal",
    **kwargs: object,
) -> None:
    """Run a sequence of pipeline steps for a scenario.

    Parameters
    ----------
    scenario_dir : Path
        Path to the scenario directory.
    steps : list[str], optional
        Steps to run.  If None, uses step keys from config or DEFAULT_STEPS.
    slack_level : str
        "false", "minimal", or "verbose".
    **kwargs
        Passed through to each step's ``run()`` function.
        Common: ``base_model_dir``, ``force``.
    """
    scenario_dir = Path(scenario_dir).resolve()
    label = f"scenarios/{scenario_dir.name}"

    cfg = resolve_templates(load_config(scenario_dir))

    _resolve_slack_level(cfg, slack_level)

    steps_cfg = cfg.get("steps", {})  # pyright: ignore[reportAttributeAccessIssue]
    if steps is None:
        steps = list(steps_cfg.keys()) or DEFAULT_STEPS  # pyright: ignore[reportAttributeAccessIssue]

    # Step lookup sees the loop body as ordinary steps, so `--steps assignment`
    # works whether or not assignment sits inside `iterate`.
    flat_steps_cfg = _flatten_steps(steps_cfg)

    log_handler = _start_run_log(cfg, label, steps)
    log_path = getattr(log_handler, "baseFilename", None)
    t0_total = time.time()
    # Cleared once the run reaches a definite end.  Anything else -- a kill, a
    # reboot, an interpreter teardown -- leaves it set, and the finally block
    # reports that rather than going silent.
    unfinished = True

    try:
        # `--iterations N` overrides iterate.count for this run.
        full_plan, plan, n_iters = _prepare_plan(steps_cfg, steps, cfg, kwargs)
        prev_iter = None
        _notify_start(
            label, steps, flat_steps_cfg, n_iters, kwargs, scenario_dir, log_path
        )

        for name, iteration in plan:
            run_step = _load_step(name, flat_steps_cfg, scenario_dir)

            if n_iters > 1 and iteration != prev_iter:
                log.info("=== Iteration %d of %d ===", iteration, n_iters)
                notify(f"[{label}] iteration {iteration} of {n_iters}", verbose_only=True)
                prev_iter = iteration

            log.info("--- Step: %s ---", name)
            t0_step = time.time()
            try:
                # Merged rather than passed positionally: an explicit caller-supplied
                # `iteration` would otherwise be a duplicate-keyword TypeError.
                result = run_step(scenario_dir, cfg, **{**kwargs, "iteration": iteration})
            except KeyboardInterrupt:
                log.warning("Cancelled during %s", name)
                notify(f":no_entry_sign: {label} cancelled during {name}")
                raise
            except Exception as e:
                # exc_info so the run log keeps the traceback, not just the message
                log.exception("Step %s failed: %s", name, e)  # noqa: TRY401
                resume = resume_token(full_plan, name, iteration)
                # The failed step did not finish, so resuming includes it.
                log.error(  # noqa: TRY400 -- traceback already logged above
                    "Resume with: tm1 run --scenario %s --resume-at %s",
                    scenario_dir.name, resume,
                )
                _notify_failure(
                    label, scenario_dir.name, name, e, resume,
                    time.time() - t0_total, log_path,
                )
                raise
            _report_step(name, result, time.time() - t0_step)

        total = time.time() - t0_total
        unfinished = False
        notify(f"Finished {label} in {_fmt_elapsed(total)} :white_check_mark:")
    except BaseException:
        # Anything raising has already reported itself, or failed before the run
        # began (a bad --resume-at, a malformed `iterate:`) with the caller
        # watching.  Either way it is not a silent teardown.
        unfinished = False
        raise
    finally:
        if unfinished:
            _notify_crash(label, time.time() - t0_total, log_path)
        # Detached even on failure, so the log is flushed and a second run in the
        # same process does not append to it.
        remove_run_logfile(log_handler)
