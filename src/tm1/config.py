"""Scenario configuration utilities for TM1."""

import os
import re
import sys
from pathlib import Path

import yaml

#: ``{env:NAME}`` -- a value from the environment, which ``tm1`` populates from
#: ``.env`` at import.  This is how a scenario config stays machine-independent:
#: every path that differs between machines is named here and set in ``.env``,
#: leaving the YAML as the model recipe and nothing else.
_ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def load_config(scenario_dir: Path) -> dict:
    """Load scenario_config.yaml from *scenario_dir*."""
    cfg_path = Path(scenario_dir) / "scenario_config.yaml"
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def step_config(cfg: dict, name: str, kwargs: dict | None = None) -> dict:
    """A step's own block from the scenario config.

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
    ``proj_dir: "{env:TM1_PROJ_DIR}"`` to ``""`` would point a fifteen-hour run at
    the current working directory and succeed at it.
    """
    if isinstance(obj, str):
        return _ENV_REF.sub(lambda m: _env_value(m.group(1), obj), obj)
    if isinstance(obj, dict):
        return {k: expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env(item) for item in obj]
    return obj


def _env_value(name: str, context: str) -> str:
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
    value comes from ``.env`` (``proj_dir``) is a real path by the time anything
    interpolates ``{proj_dir}``.
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
