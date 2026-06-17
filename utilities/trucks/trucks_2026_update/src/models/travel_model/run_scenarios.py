"""
Scenario Runner — Travel Model
====================================

Runs one or more RunIteration.bat scenarios from a shared base model, applying
per-scenario file replacements before execution. See the scenario runner spec
for the full design and YAML schema reference.

Usage
-----
CLI:
    python -m models.travel_model.run_scenarios --config configs/travel_model_scenarios.yaml

Note there is no separate validate-only/dry-run flag (see §2): config validation,
source resolution, extraction, and replacement always run as the first part of
this single invocation, on any platform. Only the .bat and .tpp-to-.omx
conversion steps require Windows and will fail explicitly there if attempted
elsewhere.

Configuration
-------------
All scenarios, replacements, and run parameters are declared in a single
YAML file.

Inputs
------
config : path to a YAML file
    A ``RunConfig`` document (§4.4): a shared ``base_zip``, an ``output_root``,
    and a list of ``scenarios``. Each scenario names its replacements (local
    file paths or GitHub URLs, auto-detected per §4.1) and must explicitly set
    ``skip_if_exists`` (§4.3). Local replacement sources must exist on disk;
    GitHub sources must be valid public file URLs.
base_zip : full-model archive
    The MTC full-model extract (a zip), shared across scenarios unless a
    scenario overrides it. Must contain ``CTRAMP/RunIteration.bat`` (§4.3.1).

Outputs
-------
scenario directories : ``<output_root>/<scenario.name>/``
    One per scenario: the extracted base model with replacements applied.
provenance manifest : ``<scenario_root>/runner_manifest.json``
    Records exactly what went into each run — base zip identity and, per
    replacement, the source and resolved commit SHA for GitHub sources (§6).
converted matrices : ``.omx`` files alongside their source ``.tpp`` outputs
    After a successful (or skipped) model run, the fixed CUBE conversion script
    converts each ``.tpp`` matrix output to a Python-readable ``.omx`` written
    in place (§3a). Not produced if the model run itself failed (§8).
run summary : stdout
    A final report of which scenarios succeeded, were skipped, or failed (§8),
    tracking the model run and the ``.tpp`` → ``.omx`` conversion as independent
    outcomes. Config validation errors are printed in full and the process exits
    non-zero.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from src.models.travel_model.manager import ScenarioManager, Status


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser exposing the single ``--config`` option (no validate-only mode,
        see §2).
    """
    parser = argparse.ArgumentParser(
        prog="python -m models.travel_model.run_scenarios",
        description="CUBE scenario runner — stage files and execute model runs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/travel_model_scenarios.yaml"),
        help="Path to the scenarios YAML file (default: configs/travel_model_scenarios.yaml).",
    )
    return parser


def cmd_run(config_path: Path) -> int:
    """Run all scenarios: validate, extract, replace, manifest, execute, convert. See §2, §8.

    This is the tool's single run path (§2): config validation, source
    resolution, extraction, and replacement always execute; only the ``.bat`` and
    ``.tpp`` → ``.omx`` steps require Windows and fail explicitly off-Windows.

    Parameters
    ----------
    config_path : Path
        Path to the scenarios YAML file.

    Returns
    -------
    int
        Process exit code: ``2`` if the config fails validation, ``1`` if any
        scenario had a model or conversion failure, ``0`` otherwise.
    """
    try:
        manager = ScenarioManager.from_yaml(config_path)
    except ValidationError as exc:
        print(f"config validation failed:\n{exc}", file=sys.stderr)
        return 2

    results = manager.run()
    print(manager.summary(results))

    failed = any(Status.FAILED in (r.model, r.conversion) for r in results)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse arguments and run the scenarios.

    Parameters
    ----------
    argv : list[str] | None, optional
        Argument vector to parse. Defaults to ``None``, meaning use
        ``sys.argv``.

    Returns
    -------
    int
        Process exit code from the run command.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return cmd_run(args.config)


if __name__ == "__main__":
    sys.exit(main())
