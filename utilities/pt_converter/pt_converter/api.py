"""Public functions used by the command line and future NetworkWrangler code."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ConverterConfig
from .errors import ConfigurationError, SourceReadError, ValidationError
from .inventory import IssueSeverity, NetworkWranglerInputReader, write_inventory


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
        inventory = NetworkWranglerInputReader().inspect(model_directory)
        inventory_path = output_directory / "source_inventory.json"
        write_inventory(inventory, inventory_path)
        error_count = sum(
            issue.severity == IssueSeverity.ERROR for issue in inventory.issues
        )
        if error_count:
            raise ValidationError(
                f"Network Wrangler inputs have {error_count} error(s). "
                f"Review {inventory_path}."
            )
        return ConversionResult(
            action="inspect-network-wrangler-inputs",
            output_directory=output_directory,
            message=(
                f"Inspected {len(inventory.files)} source file(s) and "
                f"{inventory.transit_lines.count} transit line(s). "
                f"Inventory: {inventory_path}. No PT assignment files were created."
            ),
        )

    raise ConfigurationError(
        f"Unsupported source passed to converter: {request.config.source!r}"
    )
