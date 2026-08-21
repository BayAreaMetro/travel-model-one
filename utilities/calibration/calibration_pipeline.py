"""Driver that runs all configured calibration submodels for a single config.

For a given ``calibration_config*.yaml`` this script runs each submodel that has
a ``calibration_<id>`` section, in order, reusing each submodel's own
``run()`` pipeline (process -> validate -> workbook). Submodels absent from the
config are skipped. Failures are reported per submodel; use
``--continue-on-error`` to keep going after a failure.

Usage::

    python calibration_pipeline.py --config calibration_config.yaml
    python calibration_pipeline.py --config calibration_config_BATS.yaml --submodels 09,11
    python calibration_pipeline.py --config calibration_config.yaml --continue-on-error
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import traceback
from pathlib import Path

from calibration_framework import CalibrationConfig

# Registry of submodels: id -> (script filename, class name). Order = run order.
SUBMODELS: list[tuple[str, str, str]] = [
    ("01", "01_usual_work_school_location_TM.py", "WorkSchoolLocationCalibration"),
    ("02", "02_auto_ownership_TM.py", "AutoOwnershipCalibration"),
    ("04", "04_daily_activity_pattern_TM.py", "DailyActivityPatternCalibration"),
    ("09", "09_nonwork_destination_choice_TM.py", "NonWorkDestinationChoiceCalibration"),
    ("11", "11_tour_mode_choice_TM.py", "TourModeChoiceCalibration"),
    ("15", "15_trip_mode_choice_TM.py", "TripModeChoiceCalibration"),
]


def _load_submodel_class(filename: str, class_name: str):
    """Import a submodel module by file path (names start with digits) and return its class."""
    path = Path(__file__).resolve().parent / filename
    if not path.exists():
        raise FileNotFoundError(f"Submodel script not found: {path}")

    spec = importlib.util.spec_from_file_location(f"submodel_{class_name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def run_pipeline(config_file: str | None, only: set[str] | None,
                 continue_on_error: bool) -> int:
    """Run each configured submodel; return process exit code (0 = all ok)."""
    config = CalibrationConfig(config_file)

    ran: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for submodel_id, filename, class_name in SUBMODELS:
        if only and submodel_id not in only:
            continue

        if config.get_submodel_config(submodel_id) is None:
            print(f"[skip] Submodel {submodel_id}: not configured in this config.")
            skipped.append(submodel_id)
            continue

        print(f"\n{'=' * 80}\n[run ] Submodel {submodel_id} ({class_name})\n{'=' * 80}")
        try:
            calibration_cls = _load_submodel_class(filename, class_name)
            calibration_cls(config_file=config_file).run()
            ran.append(submodel_id)
            print(f"[done] Submodel {submodel_id}")
        except Exception:
            failed.append(submodel_id)
            print(f"[fail] Submodel {submodel_id}:\n{traceback.format_exc()}")
            if not continue_on_error:
                break

    print(f"\n{'=' * 80}\nPIPELINE SUMMARY\n{'=' * 80}")
    print(f"  ran     ({len(ran)}): {', '.join(ran) or '-'}")
    print(f"  skipped ({len(skipped)}): {', '.join(skipped) or '-'}")
    print(f"  failed  ({len(failed)}): {', '.join(failed) or '-'}")

    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description="Run all configured calibration submodels.")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to calibration_config*.yaml (default: calibration_config.yaml next to the scripts).",
    )
    parser.add_argument(
        "--submodels",
        default=None,
        help="Optional comma-separated subset of submodel ids to run (e.g. '09,11').",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep running remaining submodels after a failure (default: stop).",
    )
    args = parser.parse_args()

    only = None
    if args.submodels:
        only = {token.strip() for token in args.submodels.split(",") if token.strip()}

    sys.exit(run_pipeline(args.config, only, args.continue_on_error))


if __name__ == "__main__":
    main()
