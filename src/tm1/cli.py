"""Command-line interface for tm1.

Usage::

    tm1 run base_2023_ctramp
    tm1 run base_2023_ctramp --steps setup
    tm1 run base_2023_ctramp --iterations 3
    tm1 run base_2023_ctramp --slack verbose

Restart a failed run at the step that died, rather than from the beginning::

    tm1 run base_2023_ctramp --resume-at assignment
    tm1 run base_2023_ctramp --resume-at 2:assignment

The project also takes a path, so it can live outside the repo::

    tm1 run E:/runs/my_project

Ask where a run got to -- from another shell, during or after it::

    tm1 status base_2023_ctramp

List the cases a project declares, checking every address resolves::

    tm1 cases base_2023_ctramp
"""

import argparse
import sys
from pathlib import Path

from tm1 import cases as cases_mod
from tm1 import setup_logging
from tm1.config import load_config
from tm1.runner import run_model
from tm1.status import status

#: The directory holding projects, relative to the repo root.
PROJECTS_DIR = "projects"

#: The file that identifies a project directory.
CONFIG_NAME = "config.yaml"


def _find_repo_root() -> Path:
    """Locate the repo root (the directory holding pyproject.toml).

    Walks up from cwd first, then falls back to the installed package's own
    location, so ``tm1 run`` works from outside the repo -- e.g. when pointing
    at a project directory kept elsewhere.
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
        "the project as a full path to a project directory."
    )
    raise FileNotFoundError(msg)


def _resolve_config_dir(project: str, repo_root: Path) -> Path:
    """Resolve *project* as either a path or a name under ``projects/``.

    A path lets projects live outside the repo (private configs, scratch runs)
    without needing a bespoke launcher script.
    """
    as_path = Path(project).expanduser()
    if (as_path / CONFIG_NAME).is_file():
        return as_path.resolve()

    named = repo_root / PROJECTS_DIR / project
    if (named / CONFIG_NAME).is_file():
        return named

    available = sorted(
        d.name for d in (repo_root / PROJECTS_DIR).glob("*")
        if (d / CONFIG_NAME).is_file()
    )
    msg = (
        f"No {CONFIG_NAME} for {project!r} (looked in {as_path} and "
        f"{named}).\nAvailable in this repo: {', '.join(available) or '(none)'}"
    )
    sys.exit(msg)


def _project_arg(args: argparse.Namespace) -> str:
    """The project named positionally, or by the deprecated ``--scenario``."""
    project = args.project or args.scenario
    if not project:
        sys.exit(
            "No project given. Pass a name under projects/ (e.g. "
            "`tm1 run base_2023_ctramp`) or a path to a project directory."
        )
    if args.scenario:
        sys.stderr.write(
            "warning: --scenario is deprecated; pass the project positionally, "
            f"e.g. `tm1 {args.command} {project}`\n"
        )
    return str(project)


def cmd_run(args: argparse.Namespace) -> None:
    """Execute the 'run' subcommand."""
    repo_root = _find_repo_root()
    config_dir = _resolve_config_dir(_project_arg(args), repo_root)
    run_model(
        config_dir=config_dir,
        steps=args.steps or None,
        slack_level=args.slack,
        base_model_dir=repo_root,
        iterations=args.iterations,
        resume_at=args.resume_at,
        until=args.until,
    )


def cmd_cases(args: argparse.Namespace) -> None:
    """Execute the 'cases' subcommand: expand cases.yaml and check every one."""
    config_dir = _resolve_config_dir(_project_arg(args), _find_repo_root())
    expansion = cases_mod.load(config_dir)
    sys.stdout.write(f"\n{cases_mod.render(expansion)}\n")

    problems = cases_mod.validate(load_config(config_dir), expansion)
    if problems:
        joined = "\n  ".join(problems)
        sys.exit(
            f"\n{len(problems)} address(es) do not resolve against "
            f"config.yaml:\n  {joined}"
        )


def cmd_status(args: argparse.Namespace) -> None:
    """Execute the 'status' subcommand."""
    config_dir = _resolve_config_dir(_project_arg(args), _find_repo_root())
    # Written to stdout rather than logged: it is a report, not a run event, and
    # it must not land in the run log of a run happening in another shell.
    sys.stdout.write(status(config_dir) + "\n")


def _add_project_argument(parser: argparse.ArgumentParser) -> None:
    """The project selector: positional, with the old flag kept as an alias."""
    parser.add_argument(
        "project",
        nargs="?",
        help=(
            f"Project name (folder under {PROJECTS_DIR}/, e.g. base_2023_ctramp) "
            f"or a path to any directory containing a {CONFIG_NAME}"
        ),
    )
    # Deprecated: the interface this PR is replacing. Kept so instructions
    # already circulating keep working; delete once nobody is running them.
    parser.add_argument("--scenario", default=None, help=argparse.SUPPRESS)


def main() -> None:
    """Parse arguments and dispatch to subcommands."""
    setup_logging()

    parser = argparse.ArgumentParser(prog="tm1", description="Travel Model One CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run project pipeline (or selected steps)")
    _add_project_argument(run_parser)
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
        "--slack",
        choices=["off", "minimal", "verbose"],
        default=None,
        help="Slack notification level (default: from project config, or 'minimal')",
    )

    cases_parser = sub.add_parser(
        "cases",
        help="List the cases a project declares, and check every address",
    )
    _add_project_argument(cases_parser)

    status_parser = sub.add_parser(
        "status",
        help="Show where the newest run got to, and how to resume it",
    )
    _add_project_argument(status_parser)

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "cases":
        cmd_cases(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)
