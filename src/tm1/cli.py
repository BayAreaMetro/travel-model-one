"""Command-line interface for tm1.

Usage::

    tm1 run --scenario base_2023
    tm1 run --scenario base_2023 --steps setup convert_skims
    tm1 run --scenario base_2023 --iterations 3
    tm1 run --scenario base_2023 --force --slack verbose
"""

import argparse
import sys
from pathlib import Path

from tm1 import setup_logging
from tm1.runner import run_model


def _find_repo_root() -> Path:
    """Walk up from cwd to find the repo root (contains pyproject.toml)."""
    p = Path.cwd().resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find repo root (no pyproject.toml above cwd)")


def cmd_run(args):
    repo_root = _find_repo_root()
    scenario_dir = repo_root / "scenarios" / args.scenario
    run_model(
        scenario_dir=scenario_dir,
        steps=args.steps or None,
        slack_level=args.slack,
        base_model_dir=repo_root,
        force=args.force,
        iterations=args.iterations,
    )


def main():
    setup_logging()

    parser = argparse.ArgumentParser(prog="tm1", description="Travel Model One CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run scenario pipeline (or selected steps)")
    run_parser.add_argument(
        "--scenario", required=True,
        help="Scenario name (folder under scenarios/, e.g. base_2023)",
    )
    run_parser.add_argument(
        "--steps", nargs="+", metavar="STEP",
        help="Run specific steps instead of the full pipeline",
    )
    run_parser.add_argument(
        "--iterations", type=int, default=None,
        help="Override simulate iteration count (0 = static skims, no assignment)",
    )
    run_parser.add_argument(
        "--force", action="store_true",
        help="Force rebuild of data files during setup",
    )
    run_parser.add_argument(
        "--slack", choices=["off", "minimal", "verbose"], default="minimal",
        help="Slack notification level (default: minimal)",
    )

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)
