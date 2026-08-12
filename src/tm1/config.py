"""Scenario configuration utilities for TM1."""

import sys
from pathlib import Path

import yaml


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


def resolve_templates(
    obj: str | dict | list | object, variables: dict[str, str] | None = None
) -> str | dict | list | object:
    """Expand ``{key}`` placeholders recursively.

    If *variables* is None, top-level string values in *obj* are used
    (assuming *obj* is a dict).
    """
    if variables is None:
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
