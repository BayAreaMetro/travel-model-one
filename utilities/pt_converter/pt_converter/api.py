"""Public functions used by the command line and future NetworkWrangler code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConverterConfig
from .errors import ConfigurationError, SourceReadError


@dataclass(frozen=True, slots=True)
class ConversionRequest:
    """Everything needed to convert a transit network."""

    model_directory: Path
    config: ConverterConfig


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """A short, testable description of what the conversion did."""

    action: str
    output_directory: Path
    message: str


def convert_transit_network(request: ConversionRequest) -> ConversionResult:
    """Create or validate PT inputs according to the configured source."""

    model_directory = request.model_directory.resolve()
    if not model_directory.is_dir():
        raise SourceReadError(f"Model directory does not exist: {model_directory}")

    output_directory = model_directory / request.config.output_directory

    if request.config.source == "network_wrangler":
        return ConversionResult(
            action="network-wrangler-input-check",
            output_directory=output_directory,
            message=(
                "The Network Wrangler input path is configured. "
                "No PT files were created because conversion is not implemented yet."
            ),
        )

    raise ConfigurationError(
        f"Unsupported source passed to converter: {request.config.source!r}"
    )
