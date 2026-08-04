from pathlib import Path
from typing import Any
import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def _load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load the calibration report configuration from a YAML file.

    Returns:
        The configuration dictionary.
    """
    with config_path.open() as f:
        return yaml.safe_load(f)

_cfg = _load_config()

# Directories
BATS_DIR = Path(_cfg["bats_dir"])
CHTS_DIR = Path(_cfg["chts_dir"])

# Fully-resolved file paths
