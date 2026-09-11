"""Read and validate the converter's dependency-free JSON configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .errors import ConfigurationError

SUPPORTED_CONFIG_VERSION = 1
SUPPORTED_SOURCES = frozenset({"network_wrangler"})
EXPECTED_KEYS = frozenset({"config_version", "source", "output_directory"})


@dataclass(frozen=True, slots=True)
class ConverterConfig:
    """Settings needed to choose the current preparation behavior."""

    config_version: int
    source: str
    output_directory: Path


def load_config(path: Path) -> ConverterConfig:
    """Load a JSON configuration and reject ambiguous or unknown settings."""

    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file does not exist: {path}") from error
    except OSError as error:
        raise ConfigurationError(f"Could not read configuration file {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"Configuration file is not valid JSON: {path} "
            f"(line {error.lineno}, column {error.colno})"
        ) from error

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration must be a JSON object.")

    unknown_keys = sorted(set(raw) - EXPECTED_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"Unknown configuration setting(s): {', '.join(unknown_keys)}")

    missing_keys = sorted(EXPECTED_KEYS - set(raw))
    if missing_keys:
        raise ConfigurationError(f"Missing configuration setting(s): {', '.join(missing_keys)}")

    version = raw["config_version"]
    if version != SUPPORTED_CONFIG_VERSION:
        raise ConfigurationError(
            f"Unsupported config_version {version!r}; expected {SUPPORTED_CONFIG_VERSION}."
        )

    source = raw["source"]
    if source not in SUPPORTED_SOURCES:
        choices = ", ".join(sorted(SUPPORTED_SOURCES))
        raise ConfigurationError(f"Unsupported source {source!r}; choose one of: {choices}.")

    output = raw["output_directory"]
    if not isinstance(output, str) or not output.strip():
        raise ConfigurationError("output_directory must be a non-empty string.")

    output_path = Path(output)
    if output_path.is_absolute():
        raise ConfigurationError("output_directory must be relative to --model-dir.")

    return ConverterConfig(
        config_version=version,
        source=source,
        output_directory=output_path,
    )
