"""Run the survey preparation pipeline standalone.

Usage:
    python scripts/prepare_survey.py scenarios/base_2023/bats_config.yaml
    python scripts/prepare_survey.py scenarios/base_2023/bats_config.yaml --force
"""

import argparse
import logging
import sys
from pathlib import Path

from tm1.steps.prepare_survey import _run_pipeline, _should_skip

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run survey preparation pipeline")
    parser.add_argument("config", type=Path, help="Path to pipeline YAML config")
    parser.add_argument("--force", action="store_true", help="Re-run even if outputs exist")
    parser.add_argument("--cache-dir", default=".cache/survey", help="Pipeline cache directory")
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(f"Config not found: {args.config}")

    step_cfg = {"config_path": str(args.config), "cache_dir": args.cache_dir}

    if not args.force and _should_skip(step_cfg, force=False):
        return

    # Add config's directory to sys.path for project-specific clean_*.py steps
    project_dir = str(args.config.parent.resolve())
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    _run_pipeline(args.config, step_cfg)


if __name__ == "__main__":
    main()
