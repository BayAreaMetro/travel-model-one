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


def resolve_templates(sources: dict[str, str]) -> dict[str, str]:
    """Expand ``{key}`` placeholders in values using sibling keys."""
    resolved = dict(sources)
    for _ in range(10):
        changed = False
        for k, v in resolved.items():
            if not isinstance(v, str):
                continue
            new = v
            for rk, rv in resolved.items():
                if isinstance(rv, str):
                    new = new.replace(f"{{{rk}}}", rv)
            if new != v:
                resolved[k] = new
                changed = True
        if not changed:
            break
    return resolved
