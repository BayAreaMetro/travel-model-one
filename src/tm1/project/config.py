"""Project configuration utilities for TM1."""

import os
import re
import sys
from pathlib import Path

import yaml

#: The one machine-specific thing a run needs: where run directories go.  It is a
#: local disk, because Cube's cluster is chatty and a network path is slow.
RUNS_ROOT_VAR = "TM1_RUNS_ROOT"

#: ``{env:NAME}`` -- a value from the environment, which ``tm1`` populates from
#: ``.env`` at import.  This is how a project config stays machine-independent:
#: every path that differs between machines is named here and set in ``.env``,
#: leaving the YAML as the model recipe and nothing else.
_ENV_REF = re.compile(r"\{env:([A-Za-z_][A-Za-z0-9_]*)\}")


def load_config(config_dir: Path) -> dict:
    """Load config.yaml from *config_dir*."""
    cfg_path = Path(config_dir) / "config.yaml"
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    `tm1 cases` takes rather than in hour nine of a run.  *also* names variables the
    harness itself reads, which the config does not mention.
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
