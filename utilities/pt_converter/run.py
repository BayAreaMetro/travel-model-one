"""Convert transit network files to OpenPaths PT-compatible files."""

import argparse
from pathlib import Path

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert TM1 transit network files to "
            "OpenPaths PT-compatible files."
        )
    )

    parser.add_argument(
        "--model-dir",
        required=True,
        type=Path,
        help="Model-run directory containing the trn and hwy folders.",
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="JSON file containing the converter settings.",
    )

    return parser.parse_args()


def main():
    # TODO: Write PT-compatible transit network files
    return None


if __name__ == "__main__":
    raise SystemExit(main())
