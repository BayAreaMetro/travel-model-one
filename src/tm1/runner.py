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

A step may instead run a program the harness cannot call in-process — a Cube
``.job``, or anything else, spawned as a subprocess::

    steps:
      set_tolls:
        job: "CTRAMP/scripts/preprocess/SetTolls.job"    # relative to proj_dir
      csv_to_dbf:
        command: "CTRAMP/scripts/preprocess/csvToDbf.py"
        args: ["hwy/tolls.csv", "hwy/tolls.dbf"]

**Writing the code yourself? Use ``script:`` or ``module:``.**  They are imported
and called with the resolved ``cfg``, so the step can pass values to later steps
and return ``"skipped"``.  ``command:`` gets none of that -- only argv, an
environment, and an exit code -- and exists for programs the harness does not own,
today the legacy ``RunModel.bat`` corpus.  Pointing ``command:`` at something in the
scenario directory is an error naming ``script:``, because that is where your own
code lives.

``job:``/``command:`` are executed rather than imported, so they name no entrypoint
and resolve against ``proj_dir`` rather than the scenario directory — that is the
directory ``RunModel.bat`` ran its artifacts from, and every one of them assumes it.
See :mod:`tm1.steps.external`.

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

import tm1.steps.assignment as assignment_step
import tm1.steps.external as external_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
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
    "simulate_ctramp": simulate_ctramp_step.run,
    "assignment": assignment_step.run,
}

DEFAULT_STEPS = list(STEPS.keys())

#: Keys a scenario uses to point a step at code the runner does not supply.
#: ``script``/``module`` are imported and called; ``job``/``command`` are spawned
#: (see :mod:`tm1.steps.external`).  Order matters only for the error messages.
_CUSTOM_KEYS = ("script", "module", *external_step.KEYS)

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

#: Key on ``iterate`` naming the slice of the body that runs once, before the loop.
_WARM_START = "warm_start"

#: The round a warm start runs as -- ``RunModel.bat``'s ``set ITER=0``.
_WARM_START_ITERATION = 0


def _warm_start_entries(it_cfg: dict) -> list[tuple[str, dict | None]]:
    """Parse ``warm_start:`` into ``(step name, its own config or None)``.

    An entry is either a bare name, reusing the loop body's definition of that
    step, or a single-key mapping defining a step the warm start alone has::

        warm_start:
          - hwy_assign                       # as the loop defines it
          - seed_average_networks:           # warm start only
              module: "tm1.steps.staging:seed_average_networks"

    The bare form is the point: iteration 0 runs a *slice of the loop body*, not a
    second copy of it, so the steps are named once and referenced here.
    """
    declared = it_cfg.get(_WARM_START) or []
    if not isinstance(declared, list):
        msg = (
            f"`{_ITERATE}.{_WARM_START}` must be a list of step names -- the slice "
            f"of the loop body that iteration 0 runs. Got {type(declared).__name__}."
        )
        raise TypeError(msg)

    entries: list[tuple[str, dict | None]] = []
    for item in declared:
        if isinstance(item, str):
            entries.append((item, None))
            continue
        if isinstance(item, dict) and len(item) == 1:
            name, cfg = next(iter(item.items()))
            entries.append((str(name), cfg or {}))
            continue
        msg = (
            f"`{_ITERATE}.{_WARM_START}` entries are either a step name, or a "
            f"single name with its own config. Got: {item!r}"
        )
        raise ValueError(msg)
    return entries


def _warm_start_definitions(it_cfg: dict) -> dict:
    """Step configs the warm start alone defines, keyed by name.

    A bare name needs nothing here -- it reuses the loop body's definition, and the
    plan supplies iteration 0, so the *same* config runs as a different round.  Only
    entries that carry their own body contribute.
    """
    body = it_cfg.get("steps") or {}
    own_definitions: dict = {}
    for name, own in _warm_start_entries(it_cfg):
        if own is None:
            if name not in body:
                msg = (
                    f"`{_ITERATE}.{_WARM_START}` names {name!r}, which the loop body "
                    f"does not define. Either add it to `steps:`, or give it a config "
                    f"here if only the warm start runs it."
                )
                raise ValueError(msg)
            continue
        own_definitions[name] = own
    return own_definitions


def _flatten_steps(steps_cfg: dict) -> dict:
    """Step configs with the loop body lifted alongside the top-level steps.

    Lets step lookup stay uniform: a step inside ``iterate`` resolves exactly as
    one outside it.
    """
    flat: dict = {}
    for name, step_cfg in steps_cfg.items():
        if name == _ITERATE:
            flat.update((step_cfg or {}).get("steps") or {})
            # Warm-start-only steps, which the loop body never runs.
            flat.update(_warm_start_definitions(step_cfg or {}))
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

    The loop starts at 1.  ``RunModel.bat``'s iteration 0 is a *warm start* -- it
    assigns a previous run's demand to produce the first skims, and jumps past the
    skim, demand and non-residential blocks -- so it is a named step before the
    loop, not a round of it.
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

        # The warm start runs first, as iteration 0: RunModel.bat's `set ITER=0`
        # block, which calls the same body and jumps straight to :hwyAssign.
        # Validated here rather than at load time, so a name that matches nothing
        # is caught while the plan is being built -- before any step has run.
        _warm_start_definitions(it_cfg)
        plan += [
            (name, _WARM_START_ITERATION)
            for name, _ in _warm_start_entries(it_cfg)
        ]

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


def _report_step(label: str, name: str, result: object, elapsed: float) -> None:
    """Record a finished step, distinguishing a real run from a self-skip."""
    if result == "skipped":
        notify(f"[{label}] {name} already done, skipped")
        log.info("--- Skipped: %s ---", name)
        return
    elapsed_str = _fmt_elapsed(elapsed)
    notify(f"[{label}] {name} done ({elapsed_str})")
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
             len(skipped), _fmt_plan(skipped, n_iters))
    log.info("  running %d: %s", len(plan), _fmt_plan(plan, n_iters))


def _notify_start(
    label: str, steps: list[str], flat_steps_cfg: dict, n_iters: int, kwargs: dict
) -> None:
    """Announce what is about to run.

    Reads the demand step from the *flattened* configs: it normally sits inside
    ``iterate``, so a top-level lookup would silently report defaults.
    """
    sim_cfg = (
        flat_steps_cfg.get("simulate_ctramp")
        or flat_steps_cfg.get("simulate_activitysim")
        or {}
    )
    sample_rate = kwargs.get("sample_rate") or sim_cfg.get("sample_rate")
    sample_str = "per-iteration ramp" if sample_rate is None else f"{sample_rate:.0%}"
    notify(
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | threads: {sim_cfg.get('threads', 1)} | "
        f"shadow pricing: {'on' if sim_cfg.get('shadow_pricing', False) else 'off'}\n"
        f"  • iterations: {n_iters}"
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


def _sole_custom_key(step_name: str, declared: list[str]) -> str:
    """The one custom key a step declares, or an error explaining the alternatives."""
    if len(declared) > 1:
        named = ", ".join(repr(k) for k in declared)
        msg = f"Step {step_name!r} declares {named}; use exactly one."
        raise ValueError(msg)

    if not declared:
        msg = (
            f"Unknown step: {step_name!r}. Built-in steps are "
            f"{', '.join(STEPS)}. To run your own code, give the step a "
            f"'script:' (path relative to the scenario directory) or a "
            f"'module:' (importable dotted path) -- both imported and called. To "
            f"spawn a program the harness does not own, give it a 'job:' (Cube "
            f".job) or a 'command:', both relative to proj_dir."
        )
        raise ValueError(msg)

    return declared[0]


def _load_step(step_name: str, steps_cfg: dict, scenario_dir: Path) -> Callable:
    """Resolve a step name to the callable that runs it.

    Built-in steps take precedence.  Anything else declares either native Python
    (``script:``, a path relative to the scenario directory, or ``module:``, an
    importable dotted path, each optionally naming a function after a colon) or a
    legacy artifact to run in place (``job:``/``legacy_script:``, relative to
    ``proj_dir``).
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

    key = _sole_custom_key(step_name, declared)

    # Legacy artifacts are executed, not imported: there is no module to load and
    # no entrypoint to name, so they resolve before the import machinery below.
    if key in external_step.KEYS:
        log.info("Step %s -> legacy %s at %s", step_name, key, step_cfg[key])
        return external_step.make_step(step_name, step_cfg)

    target, func_name = _split_entrypoint(step_cfg[key])

    if key == "module":
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
    t0_total = time.time()

    try:
        # `--iterations N` overrides iterate.count for this run.
        full_plan = _iteration_plan(steps_cfg, steps, override=kwargs.get("iterations"))
        n_iters = max((i for _, i in full_plan), default=1)
        plan = _apply_resume(full_plan, kwargs.get("resume_at"), cfg.get("proj_dir"))
        _report_resume(full_plan, plan, n_iters)
        prev_iter = None
        _notify_start(label, steps, flat_steps_cfg, n_iters, kwargs)

        for name, iteration in plan:
            run_step = _load_step(name, flat_steps_cfg, scenario_dir)

            if n_iters > 1 and iteration != prev_iter:
                log.info("=== Iteration %d of %d ===", iteration, n_iters)
                prev_iter = iteration

            log.info("--- Step: %s ---", name)
            t0_step = time.time()
            try:
                # Merged rather than passed positionally: an explicit caller-supplied
                # `iteration` would otherwise be a duplicate-keyword TypeError.
                # `step_name` lets a step find its own config block when a scenario
                # gives it a name of its own -- the same function can then appear
                # twice under different names, as the warm-start steps do.
                result = run_step(
                    scenario_dir, cfg,
                    **{**kwargs, "iteration": iteration, "step_name": name},
                )
            except KeyboardInterrupt:
                log.warning("Cancelled during %s", name)
                notify(f":no_entry_sign: {label} cancelled during {name}")
                raise
            except Exception as e:
                # exc_info so the run log keeps the traceback, not just the message
                log.exception("Step %s failed: %s", name, e)  # noqa: TRY401
                # The failed step did not finish, so resuming includes it.
                log.error(  # noqa: TRY400 -- traceback already logged above
                    "Resume with: tm1 run --scenario %s --resume-at %s",
                    scenario_dir.name,
                    resume_token(full_plan, name, iteration),
                )
                notify(f":exclamation: {label} failed at {name}: {e}")
                raise
            _report_step(label, name, result, time.time() - t0_step)

        total = time.time() - t0_total
        notify(f"Finished {label} in {_fmt_elapsed(total)} :white_check_mark:")
    finally:
        # Detached even on failure, so the log is flushed and a second run in the
        # same process does not append to it.
        remove_run_logfile(log_handler)
