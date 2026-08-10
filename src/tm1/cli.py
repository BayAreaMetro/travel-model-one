"""Command-line interface for tm1.

Usage::

    tm1 run --scenario base_2023_ctramp
    tm1 run --scenario base_2023_ctramp --steps setup
    tm1 run --scenario base_2023_ctramp --iterations 3
    tm1 run --scenario base_2023_ctramp --force --slack verbose

Restart a failed run at the step that died, rather than from the beginning::

    tm1 run --scenario base_2023_ctramp --resume-at assignment
    tm1 run --scenario base_2023_ctramp --resume-at 2:assignment

``--scenario`` also takes a path, so a scenario can live outside the repo::

    tm1 run --scenario E:/runs/my_scenario
"""

import argparse
import sys
from pathlib import Path

from tm1 import setup_logging
from tm1.runner import run_model


def _find_repo_root() -> Path:
    """Locate the repo root (the directory holding pyproject.toml).

    Walks up from cwd first, then falls back to the installed package's own
    location, so ``tm1 run`` works from outside the repo -- e.g. when pointing
    ``--scenario`` at a scenario directory kept elsewhere.
    """
    p = Path.cwd().resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent

    pkg_root = Path(__file__).resolve().parents[2]
    if (pkg_root / "pyproject.toml").exists():
        return pkg_root

    msg = (
        "Could not find the repo root (no pyproject.toml above the working "
        "directory or the installed package). Run from inside the repo, or pass "
        "--scenario as a full path to a scenario directory."
    )
    raise FileNotFoundError(msg)


def _resolve_scenario_dir(scenario: str, repo_root: Path) -> Path:
    """Resolve ``--scenario`` as either a path or a name under ``scenarios/``.

    A path lets scenarios live outside the repo (private configs, scratch runs)
    without needing a bespoke launcher script.
    """
    as_path = Path(scenario).expanduser()
    if (as_path / "scenario_config.yaml").is_file():
        return as_path.resolve()

    named = repo_root / "scenarios" / scenario
    if (named / "scenario_config.yaml").is_file():
        return named

    available = sorted(
        d.name for d in (repo_root / "scenarios").glob("*")
        if (d / "scenario_config.yaml").is_file()
    )
    msg = (
        f"No scenario_config.yaml for {scenario!r} (looked in {as_path} and "
        f"{named}).\nAvailable in this repo: {', '.join(available) or '(none)'}"
    )
    sys.exit(msg)


def cmd_run(args: argparse.Namespace) -> None:
    """Execute the 'run' subcommand."""
    repo_root = _find_repo_root()
    scenario_dir = _resolve_scenario_dir(args.scenario, repo_root)
    run_model(
        scenario_dir=scenario_dir,
        steps=args.steps or None,
        slack_level=args.slack,
        base_model_dir=repo_root,
        force=args.force,
        iterations=args.iterations,
        resume_at=args.resume_at,
        until=args.until,
    )


def main() -> None:
    """Parse arguments and dispatch to subcommands."""
    setup_logging()

    parser = argparse.ArgumentParser(prog="tm1", description="Travel Model One CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run scenario pipeline (or selected steps)")
    run_parser.add_argument(
        "--scenario",
        required=True,
        help=(
            "Scenario name (folder under scenarios/, e.g. base_2023_ctramp) "
            "or a path to any directory containing a scenario_config.yaml"
        ),
    )
    run_parser.add_argument(
        "--steps",
        nargs="+",
        metavar="STEP",
        help="Run specific steps instead of the full pipeline",
    )
    run_parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Override simulate iteration count (0 = static skims, no assignment)",
    )
    run_parser.add_argument(
        "--resume-at",
        metavar="[N:]STEP",
        default=None,
        help=(
            "Restart a previous run at STEP, which itself runs; everything "
            "before it is skipped. Prefix with an iteration (e.g. 2:assignment) "
            "when the step runs in more than one. The step re-runs from the "
            "start, never continues part-way"
        ),
    )
    run_parser.add_argument(
        "--until",
        metavar="[N:]STEP",
        default=None,
        help=(
            "Stop after STEP, which itself runs -- the mirror of --resume-at, and "
            "combinable with it to run any slice. Prefix with an iteration "
            "(e.g. 0:publish_networks for the end of the warm start) when the step "
            "runs in more than one"
        ),
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild of data files during setup",
    )
    run_parser.add_argument(
        "--slack",
        choices=["off", "minimal", "verbose"],
        default=None,
        help="Slack notification level (default: from scenario config, or 'minimal')",
    )

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)
