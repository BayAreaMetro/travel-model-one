"""Setup step: create directories and copy input files.

Reads ``cfg["steps"]["setup"]["copy_inputs"]`` — a dict of named entries,
each with ``from`` and ``to`` paths.  Idempotent: skips files that already
exist unless ``force=True``.
"""

import logging
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def _strip_ctrl_z(path: Path):
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with open(path, "r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def run(scenario_dir: Path, cfg: dict, **kwargs):
    """Copy input files as specified in setup.copy_inputs."""
    force = kwargs.get("force", False)

    setup_cfg = cfg.get("steps", {}).get("setup", {})
    copy_inputs = setup_cfg.get("copy_inputs", {})

    for name, entry in copy_inputs.items():
        src = Path(entry["from"])
        dest = Path(entry["to"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not force and dest.exists():
            log.info("Already exists: %s", dest)
            continue
        if not src.exists():
            sys.exit(f"Source not found: {src}")
        log.info("Copying %s -> %s", src, dest)
        shutil.copy2(src, dest)
        _strip_ctrl_z(dest)

    log.info("Setup complete: copied %d file(s)", len(copy_inputs))
