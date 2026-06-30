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

from src.models.travel_model.config import RunConfig
from src.models.travel_model.pipeline import run_all
from src.evaluation.run_evaluation import run_evaluation


def main() -> None:
    """Parse ``--config``, validate the YAML into a ``RunConfig``, and run everything.

    After all scenarios have been attempted, run the evaluation pipeline over the
    scenarios that completed successfully (see
    :func:`src.evaluation.run_evaluation.run_evaluation`).

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

    raw_cfg = yaml.safe_load(args.config.read_text())
    config = RunConfig.model_validate(raw_cfg)
    completed_scenarios = run_all(config)
    run_evaluation(raw_cfg, completed_scenarios)


if __name__ == "__main__":
    main()
