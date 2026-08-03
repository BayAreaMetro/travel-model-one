"""The steps a project can name, and the code each one runs.

A step in ``config.yaml`` is a name plus a block. This module turns that pair
into the callable that does the work:

* a **built-in** step -- one of :data:`STEPS` below;
* ``script:``/``module:`` -- native Python, imported and called with the
  resolved config;
* ``job:``/``command:`` -- a program spawned by :mod:`tm1.steps.external`.

All four resolve to the same kind of thing, so a project-supplied step is not a
second-class citizen.

**Adding a step**: write the module, then add one line to :data:`STEPS`. That is
deliberately the whole procedure -- it is the seam every later phase attaches to,
and a one-line change is one a rebase can resolve.
"""

import importlib
import importlib.util
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import tm1.steps.assignment as assignment_step
import tm1.steps.configure_ctramp as configure_ctramp_step
import tm1.steps.external as external_step
import tm1.steps.setup as setup_step
import tm1.steps.filter_popsyn as filter_popsyn_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
import tm1.steps.staging as staging_step

log = logging.getLogger(__name__)


#: Built-in steps, mapped to the callable that runs each one.  Values are plain
#: callables so a single module can supply several steps, and so built-in and
#: project-supplied steps resolve to exactly the same kind of thing.
STEPS: dict[str, Callable] = {
    # Staging: file shuffling the legacy .bat files did inline, between the jobs.
    "make_directories": staging_step.make_directories,
    "stage_transit_lines": staging_step.stage_transit_lines,
    "copy_transit_skims": staging_step.copy_transit_skims,
    "stage_loaded_networks": staging_step.stage_loaded_networks,
    "seed_average_networks": staging_step.seed_average_networks,
    "publish_networks": staging_step.publish_networks,
    # The model itself.
    "copy_inputs": setup_step.run,
    "filter_popsyn": filter_popsyn_step.run,
    "configure_ctramp": configure_ctramp_step.run,
    "simulate_ctramp": simulate_ctramp_step.run,
    "assignment": assignment_step.run,
}

DEFAULT_STEPS = list(STEPS.keys())

#: Keys a project uses to point a step at code the runner does not supply.
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


def _load_script(path: Path, config_dir: Path) -> ModuleType:
    """Import a ``.py`` file as a module, without putting its directory on sys.path.

    The module is registered under a name qualified by the project, so two
    projects that both ship a ``preprocess.py`` do not collide in
    ``sys.modules``.
    """
    spec = importlib.util.spec_from_file_location(
        f"tm1_project_{config_dir.name}_{path.stem}", path
    )
    if spec is None or spec.loader is None:
        msg = f"Could not load step script as a Python module: {path}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    # Registered before exec so the module can import itself / pickle cleanly.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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
            f"'script:' (path relative to the project directory) or a "
            f"'module:' (importable dotted path) -- both imported and called. To "
            f"spawn a program the harness does not own, give it a 'job:' (Cube "
            f".job) or a 'command:', both relative to run_dir."
        )
        raise ValueError(msg)

    return declared[0]


def load_step(step_name: str, step_cfg: dict | None, config_dir: Path) -> Callable:
    """Resolve one step's config block to the callable that runs it.

    Takes the block itself rather than a name to look up, because a name may
    appear more than once in the plan -- the entry identifies the step.

    Built-in steps take precedence.  Anything else declares either native Python
    (``script:``, a path relative to the project directory, or ``module:``, an
    importable dotted path, each optionally naming a function after a colon) or a
    legacy artifact to run in place (``job:``/``command:``, relative to
    ``run_dir``).
    """
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
            path = config_dir / path
        if not path.is_file():
            msg = f"Step {step_name!r}: script not found: {path}"
            raise FileNotFoundError(msg)
        mod = _load_script(path, config_dir)
        target = str(path)

    source = f"{target}:{func_name}"
    if not hasattr(mod, func_name):
        named = "" if func_name == _DEFAULT_ENTRYPOINT else f" (named by {step_name!r})"
        msg = (
            f"Step {step_name!r}: {target} defines no {func_name}(){named}. Steps "
            f"need 'def {func_name}(config_dir, cfg, **kwargs)', the same "
            f"contract as the built-in steps."
        )
        raise AttributeError(msg)

    func = getattr(mod, func_name)
    if not callable(func):
        msg = f"Step {step_name!r} ({source}): {func_name!r} is not callable."
        raise TypeError(msg)

    log.info("Step %s -> custom code at %s", step_name, source)
    return func
