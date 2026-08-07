"""Merge CT-RAMP's walk-to-transit subzone shares into the land_use table.

``walk_access_buffers`` (``from`` = walkAccessBuffers.float.csv, ``into`` = the
copied land_use.csv) merges CT-RAMP's per-TAZ walk-to-transit subzone shares into
the land_use table.  The mode-choice preprocessors sample each tour end's walk
segment (short/long/none) from these shares to replicate CT-RAMP's transit
availability gates and access walk times.  Declare it after ``copy_inputs``,
since it edits a file that step puts in place.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def merge_walk_access_shares(buffers_csv: Path, land_use_csv: Path) -> None:
    """Join walkAccessBuffers SHRT/LONG shares into land_use (idempotent)."""
    buffers = pd.read_csv(buffers_csv).set_index("TAZ")
    land_use = pd.read_csv(land_use_csv)

    zones = land_use["ZONE"]
    missing = ~zones.isin(buffers.index)
    if missing.any():
        sys.exit(f"{land_use_csv}: {missing.sum()} zones missing from {buffers_csv}")

    land_use["walk_short_share"] = buffers["SHRT"].reindex(zones).to_numpy()
    land_use["walk_long_share"] = buffers["LONG"].reindex(zones).to_numpy()

    total = land_use["walk_short_share"] + land_use["walk_long_share"]
    if (total > 1.0 + 1e-9).any():
        sys.exit(f"{land_use_csv}: SHRT+LONG exceeds 1.0 for some zones")

    land_use.to_csv(land_use_csv, index=False)
    log.info(
        "Merged walk access shares into %s (zone means: short %.3f, long %.3f)",
        land_use_csv,
        land_use["walk_short_share"].mean(),
        land_use["walk_long_share"].mean(),
    )


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> str | None:
    """Merge walk-to-transit subzone shares into the copied land_use table."""
    buffers_cfg = cfg.get("steps", {}).get("walk_access_buffers") or {}
    if not buffers_cfg:
        return "skipped"
    merge_walk_access_shares(Path(buffers_cfg["from"]), Path(buffers_cfg["into"]))
    return None
