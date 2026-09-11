"""Argument parsing for the dependency-free command line."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .api import ConversionRequest, convert_transit_network
from .config import load_config
from .errors import PTConverterError
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pt-converter",
        description="Prepare static OpenPaths PT network inputs for Travel Model One.",
    )
    parser.add_argument("--model-dir", required=True, type=Path, help="TM1 model-run directory.")
    parser.add_argument("--config", required=True, type=Path, help="Converter JSON configuration.")
    parser.add_argument("--version", action="version", version=__version__)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        result = convert_transit_network(
            ConversionRequest(model_directory=args.model_dir, config=config)
        )
    except PTConverterError as error:
        print(f"PT converter error: {error}", file=sys.stderr)
        return 2

    print("PT converter")
    print(f"Action: {result.action}")
    print(f"Output: {result.output_directory}")
    print(result.message)
    return 0
