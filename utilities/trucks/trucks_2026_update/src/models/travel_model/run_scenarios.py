"""CLI entry point — load the YAML, validate it, run every scenario.

Usage
-----
    python -m models.travel_model.run_scenarios --config configs/travel_model_scenarios.yaml

One command, one YAML file, no flags to remember. Scenarios marked
``skip_if_exists: true`` still get their outputs converted fresh every run, even
though their folder and ``.bat`` are left alone.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from .config import RunConfig
from .pipeline import run_all


def main() -> None:
    """Parse ``--config``, validate the YAML into a ``RunConfig``, and run everything.

    Raises
    ------
    pydantic.ValidationError
        If the YAML doesn't match the config schema — fix the YAML and rerun.
    """
    parser = argparse.ArgumentParser(description="Run CUBE model scenarios from a YAML config.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/travel_model_scenarios.yaml"),
        help="Path to the scenarios YAML file.",
    )
    args = parser.parse_args()

    config = RunConfig.model_validate(yaml.safe_load(args.config.read_text()))
    run_all(config)


if __name__ == "__main__":
    main()
