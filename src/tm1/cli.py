"""Command-line interface for tm1.

Usage::

    tm1 run ctramp_2023
    tm1 run ctramp_2023 --steps setup
    tm1 run ctramp_2023 --iterations 3
    tm1 run ctramp_2023 --slack verbose

Restart a failed run at the step that died, rather than from the beginning::

    tm1 run ctramp_2023 --resume-at assignment
    tm1 run ctramp_2023 --resume-at 2:assignment

The project also takes a path, so it can live outside the repo::

    tm1 run E:/runs/my_project

Ask where a run got to -- from another shell, during or after it::

    tm1 status ctramp_2023

List the cases a project declares, checking every address resolves::

    tm1 cases ctramp_2023
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import yaml

from tm1 import setup_logging
from tm1.project import cases as cases_mod
from tm1.project.config import load_config, missing_env
from tm1.project.overrides import validate as validate_cases
from tm1.run.model import AlreadyCompleteError, run_model
from tm1.run.prepare import RUNS_ROOT_VAR
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
            "`tm1 run ctramp_2023`) or a path to a project directory."
        )
    if args.scenario:
        sys.stderr.write(
            "warning: --scenario is deprecated; pass the project positionally, "
            f"e.g. `tm1 {args.command} {project}`\n"
        )
    return str(project)


#: What a broken project raises.  Every one of these is deliberate -- the module
#: that raises it writes the message for the person who has to fix the config -- so
#: the CLI prints that message and nothing else.  A traceback here would bury a
#: usable sentence under ten lines of stack, and the reader is a modeller, not the
#: author of the harness.
#:
#: A step that fails mid-run is different: its traceback goes to the run log
#: (see `_report_failure`), so nothing is lost by keeping the console clean.
_CONFIG_PROBLEMS = (FileNotFoundError, KeyError, ValueError, TypeError, yaml.YAMLError)


def _run_cleanly(work: Callable[[], None]) -> None:
    """Run *work*, reporting a broken project as a message rather than a stack."""
    try:
        work()
    except _CONFIG_PROBLEMS as exc:
        # KeyError's str() is the repr of its argument, which wraps an already
        # quoted message in another layer of quotes.
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        sys.exit(f"\nerror: {message}\n")


def cmd_run(args: argparse.Namespace) -> None:
    """Execute the 'run' subcommand."""
    repo_root = _find_repo_root()
    config_dir = _resolve_config_dir(_project_arg(args), repo_root)
    try:
        run_model(
            config_dir=config_dir,
            steps=args.steps or None,
            slack_level=args.slack,
            base_model_dir=repo_root,
            case=args.case,
            rerun=args.rerun,
            iterations=args.iterations,
            resume_at=args.resume_at,
            until=args.until,
        )
    except AlreadyCompleteError as done:
        sys.exit(str(done))


def cmd_cases(args: argparse.Namespace) -> None:
    """Execute the 'cases' subcommand: expand cases.yaml and check every one."""
    config_dir = _resolve_config_dir(_project_arg(args), _find_repo_root())

    # Config first: with an unreadable config.yaml there is nothing to check the
    # cases against, and printing the table anyway would report success to anyone
    # reading stdout or piping it.
    cfg = load_config(config_dir)
    expansion = cases_mod.load(config_dir)
    sys.stdout.write(f"\n{cases_mod.render(expansion)}\n")

    problems = [
        f"{name} is not set (see .env.example)"
        for name in missing_env(cfg, also=(RUNS_ROOT_VAR,))
    ]
    problems += validate_cases(cfg, expansion)
    if problems:
        joined = "\n  ".join(problems)
        sys.exit(f"\n{len(problems)} problem(s) to fix before running:\n  {joined}\n")


def cmd_status(args: argparse.Namespace) -> None:
    """Execute the 'status' subcommand."""
    config_dir = _resolve_config_dir(_project_arg(args), _find_repo_root())
    # Written to stdout rather than logged: it is a report, not a run event, and
    # it must not land in the run log of a run happening in another shell.
    sys.stdout.write(status(config_dir, args.case) + "\n")


def _add_project_argument(parser: argparse.ArgumentParser) -> None:
    """The project selector: positional, with the old flag kept as an alias."""
    parser.add_argument(
        "project",
        nargs="?",
        help=(
            f"Project name (folder under {PROJECTS_DIR}/, e.g. ctramp_2023) "
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
        "--case",
        metavar="ID",
        default=None,
        help=(
            "Which case to run, when the project declares more than one "
            "(`tm1 cases <project>` lists them)"
        ),
    )
    run_parser.add_argument(
        "--rerun",
        action="store_true",
        help=(
            "Run a case again even though it finished unchanged; the new run "
            "lands beside the old one rather than over it"
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
    status_parser.add_argument(
        "--case", metavar="ID", default=None,
        help="Which case to report on, when the project declares more than one",
    )

    args = parser.parse_args()

    if args.command == "run":
        _run_cleanly(lambda: cmd_run(args))
    elif args.command == "cases":
        _run_cleanly(lambda: cmd_cases(args))
    elif args.command == "status":
        _run_cleanly(lambda: cmd_status(args))
    else:
        parser.print_help()
        sys.exit(1)
