"""Command-line interface for tm1.

Usage::

    tm1 run --scenario base_2023
    tm1 run --scenario base_2023 --force-setup --slack minimal
"""

import argparse
import importlib
import logging
import subprocess
import sys
from pathlib import Path

from tm1.runner import run


def _find_repo_root() -> Path:
    """Walk up from cwd to find the repo root (contains pyproject.toml)."""
    p = Path.cwd().resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find repo root (no pyproject.toml above cwd)")


def _get_setup_fn():
    """Import setup_scenario.setup from the scripts/ directory."""
    repo_root = _find_repo_root()
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    mod = importlib.import_module("setup_scenario")
    return mod.setup, repo_root


def cmd_run(args):
    """Run an ActivitySim scenario."""
    setup_fn, repo_root = _get_setup_fn()
    scenario_dir = repo_root / "scenarios" / args.scenario
    sys.exit(run(
        scenario_dir=scenario_dir,
        setup_fn=setup_fn,
        base_model_dir=repo_root,
        force_setup=args.force_setup,
        slack_level=args.slack,
    ))


def main():
    parser = argparse.ArgumentParser(prog="tm1", description="Travel Model One CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run an ActivitySim scenario")
    run_parser.add_argument(
        "--scenario", required=True,
        help="Scenario name (folder under scenarios/, e.g. base_2023)",
    )
    run_parser.add_argument(
        "--force-setup", action="store_true",
        help="Re-copy data files even if they already exist",
    )
    run_parser.add_argument(
        "--slack", choices=["false", "minimal", "verbose"], default="minimal",
        help="Slack notification level (default: minimal)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
