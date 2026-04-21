"""Scenario configuration utilities for TM1."""

import sys
from pathlib import Path

import yaml


def load_config(scenario_dir: Path) -> dict:
    """Load scenario_config.yaml from *scenario_dir*."""
    cfg_path = Path(scenario_dir) / "scenario_config.yaml"
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def resolve_templates(obj, variables: dict[str, str] | None = None):
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
