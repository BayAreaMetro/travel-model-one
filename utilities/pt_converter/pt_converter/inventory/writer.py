"""Write source-inventory reports."""

from __future__ import annotations

import json
from pathlib import Path

from ..errors import OutputWriteError
from .models import SourceInventory


def write_inventory(inventory: SourceInventory, output_path: Path) -> None:
    """Write stable, human-readable JSON, replacing any older report."""

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(inventory.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    except OSError as error:
        raise OutputWriteError(f"Could not write inventory report {output_path}: {error}") from error
