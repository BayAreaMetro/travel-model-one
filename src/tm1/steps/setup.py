"""Setup step: create directories and copy input files.

Reads ``cfg["setup"]["inputs"]`` and copies each source file into the
ActivitySim data directory.  Idempotent: skips files that already exist
unless ``force=True``.
"""

import logging
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)

CSV_FILE_MAP = {
    "land_use": "land_use.csv",
    "households": "households.csv",
    "persons": "persons.csv",
}


def _strip_ctrl_z(path: Path):
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with open(path, "r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Create data directory and copy input CSVs."""
    force = kwargs.get("force", False)

    data_dir = Path(cfg["activitysim"]["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    inputs = cfg.get("setup", {}).get("inputs", {})

    for key, dest_name in CSV_FILE_MAP.items():
        src_path = inputs.get(key)
        if src_path is None:
            log.warning("No source configured for %s, skipping", key)
            continue
        src = Path(src_path)
        dest = data_dir / dest_name
        if not force and dest.exists():
            log.info("Already exists: %s", dest.name)
            continue
        if not src.exists():
            sys.exit(f"Source not found: {src}")
        log.info("Copying %s -> %s", src, dest)
        shutil.copy2(src, dest)
        _strip_ctrl_z(dest)

    log.info("--- Data directory: %s ---", data_dir)
    for p in sorted(data_dir.iterdir()):
        size_mb = p.stat().st_size / 1_048_576
        log.info("  %-20s %8.1f MB", p.name, size_mb)
