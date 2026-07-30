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
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import tm1.steps.assignment as assignment_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
from tm1 import slack
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
    "walk_access_buffers": setup_step.run_walk_access_buffers,
    "simulate_ctramp": simulate_ctramp_step.run,
    "assignment": assignment_step.run,
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

    # Slack level: CLI flag wins, then yaml key, then default "minimal"
    if slack_level is not None:
        slack.level = "verbose" if slack_level is True else slack_level
    else:
        cfg_slack = cfg.get("slack", "minimal")
        slack.level = cfg_slack if isinstance(cfg_slack, str) else "off"

    steps_cfg = cfg.get("steps", {})  # pyright: ignore[reportAttributeAccessIssue]
    if steps is None:
        steps = list(steps_cfg.keys()) or DEFAULT_STEPS  # pyright: ignore[reportAttributeAccessIssue]

    # Gather run parameters for the start notification
    sim_cfg = steps_cfg.get("simulate_ctramp", {}) or {}
    iterations = kwargs.get("iterations") or sim_cfg.get("iterations", 0)
    threads = sim_cfg.get("threads", 1)
    sample_rate = kwargs.get("sample_rate") or sim_cfg.get("sample_rate")
    shadow = sim_cfg.get("shadow_pricing", False)

    sample_str = "per-iteration ramp" if sample_rate is None else f"{sample_rate:.0%}"
    header = (
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | threads: {threads} | "
        f"shadow pricing: {'on' if shadow else 'off'}\n"
        f"  • iterations: {iterations}"
    )
    notify(header)

    t0_total = time.time()

    for name in steps:
        run_step = _load_step(name, steps_cfg, scenario_dir)

        log.info("--- Step: %s ---", name)
        t0_step = time.time()
        try:
            result = run_step(scenario_dir, cfg, **kwargs)
        except KeyboardInterrupt:
            notify(f":no_entry_sign: {label} cancelled during {name}")
            raise
        except Exception as e:
            notify(f":exclamation: {label} failed at {name}: {e}")
            raise
        elapsed = time.time() - t0_step

        if result == "skipped":
            notify(f"[{label}] {name} already done, skipped")
            log.info("--- Skipped: %s ---", name)
        else:
            elapsed_str = _fmt_elapsed(elapsed)
            notify(f"[{label}] {name} done ({elapsed_str})")
            log.info("--- Done: %s (%s) ---", name, elapsed_str)

    total = time.time() - t0_total
    notify(f"Finished {label} in {_fmt_elapsed(total)} :white_check_mark:")
