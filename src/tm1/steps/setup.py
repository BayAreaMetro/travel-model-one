"""Setup step: create directories and copy input files.

Reads ``cfg["steps"]["setup"]["copy_inputs"]`` — a dict of named entries,
each with ``from`` and ``to`` paths.  If ``from`` is a directory, the entire
tree is copied (or filtered by ``glob`` pattern).  Idempotent: skips
files/dirs that already exist unless ``force=True``.

An optional ``walk_access_buffers`` entry (``from`` = walkAccessBuffers.float.csv,
``into`` = the copied land_use.csv) merges CT-RAMP's per-TAZ walk-to-transit
subzone shares into the land_use table after copying.  The mode-choice
preprocessors sample each tour end's walk segment (short/long/none) from these
shares to replicate CT-RAMP's transit availability gates and access walk times.
"""

import logging
import shutil
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


def _strip_ctrl_z(path: Path) -> None:
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with path.open("r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Copy input files as specified in setup.copy_inputs."""
    force = kwargs.get("force", False)

    setup_cfg = cfg.get("steps", {}).get("setup", {})
    copy_inputs = setup_cfg.get("copy_inputs", {})

    copied = 0
    for name, entry in copy_inputs.items():
        src = Path(entry["from"])
        dest = Path(entry["to"])
        if not src.exists():
            sys.exit(f"Source not found: {src}")

        if src.is_dir():
            pattern = entry.get("glob")
            if pattern:
                # Copy only files matching the glob from a directory.
                dest.mkdir(parents=True, exist_ok=True)
                for f in sorted(src.glob(pattern)):
                    if not f.is_file():
                        continue
                    target = dest / f.name
                    if not force and target.exists():
                        continue
                    shutil.copy2(f, target)
                    copied += 1
                log.info("Copied %s/%s -> %s (%d files)", src, pattern, dest, copied)
            else:
                if not force and dest.exists():
                    log.info("Already exists: %s", dest)
                    continue
                log.info("Copying directory %s -> %s", src, dest)
                shutil.copytree(src, dest, dirs_exist_ok=force)
                copied += 1
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not force and dest.exists():
                log.info("Already exists: %s", dest)
                continue
            log.info("Copying %s -> %s", src, dest)
            shutil.copy2(src, dest)
            _strip_ctrl_z(dest)
            copied += 1

    buffers_cfg = setup_cfg.get("walk_access_buffers")
    if buffers_cfg:
        merge_walk_access_shares(Path(buffers_cfg["from"]), Path(buffers_cfg["into"]))

    log.info("Setup complete: %d item(s) configured, files copied", len(copy_inputs))
    if copied == 0 and not buffers_cfg:
        return "skipped"
    return None
