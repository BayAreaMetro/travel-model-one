"""Project configuration utilities for TM1."""

import os
import re
import sys
from pathlib import Path

import yaml

from tm1.project.scenarios import load as load_scenarios

#: The one machine-specific thing a run needs: where run directories go.  It is a
#: local disk, because Cube's cluster is chatty and a network path is slow.
RUNS_ROOT_VAR = "TM1_RUNS_ROOT"

#: The pipeline every CT-RAMP+Cube project shares -- steps, job paths, the whole
#: warmstart:/iterate: shape.  Found by walking up from a project directory, so a
#: project need not say where its own checkout root is.
_MODEL_FILE = Path("default-configs") / "ctramp-cube-model.yaml"

#: ``{env:NAME}`` -- a value from the environment, which ``tm1`` populates from
#: ``.env`` at import.  This is how a project config stays machine-independent:
#: every path that differs between machines is named here and set in ``.env``,
#: leaving the YAML as the model recipe and nothing else.
_ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def _find_model_file(config_dir: Path) -> Path | None:
    """``default-configs/ctramp-cube-model.yaml``, walking up from *config_dir*.

    None if never found -- *config_dir* is not inside a checkout that has one,
    which is how a synthetic project (tests) keeps working.
    """
    for parent in (config_dir, *config_dir.parents):
        candidate = parent / _MODEL_FILE
        if candidate.is_file():
            return candidate
    return None


def load_config(config_dir: Path) -> dict:
    """A project's config, fully assembled from the shared model plus its own `steps:`.

    There is no per-project pipeline of its own, and no project-level defaults
    layer either: the shared ``default-configs/ctramp-cube-model.yaml`` is the
    only pipeline, and every scenario in ``scenarios.yaml`` overrides the
    model's ``REQUIRED`` placeholders itself, through the same address grammar
    it uses for everything else -- so a scenario is complete on its own reading,
    without also reading a separate block to know what it runs.
    :func:`tm1.project.overrides.validate` refuses a scenario that leaves one of
    those placeholders unresolved.

    ``steps:`` is the one addition applied here rather than by a scenario, and
    genuinely project-wide, so every scenario gets it alike. Two shapes:

    - the name matches a step the shared pipeline already has (empty there on
      purpose, e.g. ``copy_project_inputs``) -> the project's entries are
      merged into it, in the position the shared pipeline put it.
    - it does not -> appended as a new step, after the shared pipeline's own
      (e.g. ``vmt_vht_metrics``, a project's own post-processing hook).
    """
    config_dir = Path(config_dir)
    model_path = _find_model_file(config_dir)
    if model_path is None:
        sys.exit(f"No {_MODEL_FILE} above {config_dir}.")

    with model_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg.pop("_shared_step_bodies", None)  # anchor source only; not part of the pipeline

    for extra in load_scenarios(config_dir).extra_steps:
        _add_step(cfg, extra)
    return cfg


def _add_step(cfg: dict, extra: object) -> None:
    """Merge one of a project's `steps:` entries into *cfg*.

    Fills in a step the shared pipeline already named but left empty (e.g.
    ``copy_project_inputs: {}``), in place -- pipeline position matters for a
    step like that one, and a project cannot say where in the list to insert.
    Anything else is appended as a new step, since the shared pipeline has no
    name -- and so no position -- for it.
    """
    if not isinstance(extra, dict) or len(extra) != 1:
        msg = f"A project's `steps:` entry must be one `name: {{...}}` mapping; got {extra!r}."
        raise TypeError(msg)
    name, body = next(iter(extra.items()))

    existing = next(
        (item[name] for item in cfg["steps"] if isinstance(item, dict) and name in item),
        None,
    )
    if isinstance(existing, dict) and isinstance(body, dict):
        existing.update(body)
    else:
        cfg["steps"] = [*cfg["steps"], extra]


def step_config(cfg: dict, name: str, kwargs: dict | None = None) -> dict:
    """A step's own block from the project config.

    The runner hands each step the exact block it was launched from as
    ``kwargs["step_cfg"]`` — with ``steps:`` as a list the same name may appear
    twice (the warm start and the loop each carry their own copy), so the entry,
    not the name, identifies the block.  Name lookup is the fallback, for direct
    calls in tests and for reading *another* step's block.

    The fallback descends into ``warmstart:`` because its steps are the ones with
    no top-level entry.  It does not descend into ``iterate:``: a loop step's block
    is only reachable by round, which a name does not carry.
    """
    if kwargs is not None and isinstance(kwargs.get("step_cfg"), dict):
        return kwargs["step_cfg"]
    steps = cfg.get("steps")
    if isinstance(steps, dict):
        steps = [{k: v} for k, v in steps.items()]
    if not isinstance(steps, list):
        return {}
    for item in steps:
        if not isinstance(item, dict):
            continue
        if name in item:
            return item[name] or {}
        if "warmstart" in item:
            found = step_config({"steps": item["warmstart"]}, name)
            if found:
                return found
    return {}


def expand_env(obj: str | dict | list | object) -> str | dict | list | object:
    """Replace every ``{env:NAME}`` with that environment variable, recursively.

    An unset variable is an **error**, not an empty string.  Silently expanding
    ``run_dir: "{env:TM1_PROJ_DIR}"`` to ``""`` would point a fifteen-hour run at
    the current working directory and succeed at it.
    """
    if isinstance(obj, str):
        return _ENV_REF.sub(lambda m: env_value(m.group(1), obj), obj)
    if isinstance(obj, dict):
        return {k: expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env(item) for item in obj]
    return obj


def env_references(obj: object) -> set[str]:
    """Every ``{env:NAME}`` the config mentions, anywhere in it."""
    if isinstance(obj, str):
        return set(_ENV_REF.findall(obj))
    if isinstance(obj, dict):
        return set().union(*(env_references(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(env_references(v) for v in obj)) if obj else set()
    return set()


def missing_env(cfg: dict, also: tuple[str, ...] = ()) -> list[str]:
    """Which of the variables this project needs are not set.

    A pre-flight, so that a `.env` copied but not finished is caught in the second
    `tm1 scenarios` takes rather than in hour nine of a run.  *also* names variables
    the harness itself reads, which the config does not mention.
    """
    return sorted(n for n in env_references(cfg) | set(also) if os.environ.get(n) is None)


def env_value(name: str, context: str) -> str:
    """One environment variable, or an error naming it and where to set it."""
    value = os.environ.get(name)
    if value is None:
        msg = (
            f"{{env:{name}}} in {context!r}, but {name} is not set. Machine-specific "
            f"paths live in .env at the repo root -- copy .env.example to .env and "
            f"set {name} there, or export it before running."
        )
        raise ValueError(msg)
    return value


def resolve_templates(
    obj: str | dict | list | object, variables: dict[str, str] | None = None
) -> str | dict | list | object:
    """Expand ``{env:NAME}`` then ``{key}`` placeholders, recursively.

    If *variables* is None, top-level string values in *obj* are used (assuming
    *obj* is a dict) -- and the environment pass runs first, so a key whose own
    value comes from ``.env`` (``run_dir``) is a real path by the time anything
    interpolates ``{run_dir}``.
    """
    if variables is None:
        obj = expand_env(obj)
        if isinstance(obj, dict):
            variables = {k: v for k, v in obj.items() if isinstance(v, str)}
        else:
            return obj

    def _resolve_str(s: str) -> str:
        for _ in range(10):
            new = s
            for k, v in variables.items():
                new = new.replace(f"{{{k}}}", v)
            if new == s:
                break
            s = new
        return s

    if isinstance(obj, str):
        return _resolve_str(obj)
    if isinstance(obj, dict):
        return {k: resolve_templates(v, variables) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_templates(item, variables) for item in obj]
    return obj
