"""
CLI entry point for the scenario runner. See §10.

Two modes:
  --validate-only   Parse and validate the YAML config without touching the filesystem
                    destructively. Runnable on macOS (§3, Phase 3).
  (default)         Full run: extract, replace, write manifest, execute .bat (Windows only).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m models.travel-model.cli",
        description="CUBE scenario runner — stage files and execute model runs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/scenarios.yaml"),
        help="Path to the scenarios YAML file (default: config/scenarios.yaml).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate config and sources without running or modifying the filesystem.",
    )
    return parser


def cmd_validate_only(config_path: Path) -> int:
    """Parse and validate the RunConfig; print a summary or errors. See Phase 3."""
    raise NotImplementedError("--validate-only mode not yet implemented")


def cmd_run(config_path: Path) -> int:
    """Full scenario run: extract, replace, manifest, execute. See Phase 7."""
    raise NotImplementedError("Full run mode not yet implemented")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.validate_only:
        return cmd_validate_only(args.config)
    return cmd_run(args.config)


if __name__ == "__main__":
    sys.exit(main())
