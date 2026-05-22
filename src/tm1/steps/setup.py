"""Setup step: create directories and copy input files.

Reads ``cfg["steps"]["setup"]["copy_inputs"]`` — a dict of named entries,
each with ``from`` and ``to`` paths.  If ``from`` is a directory, the entire
tree is copied (or filtered by ``glob`` pattern).  Idempotent: skips
files/dirs that already exist unless ``force=True``.
"""

import logging
import shutil
import sys
from pathlib import Path

log = logging.getLogger(__name__)


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

    log.info("Setup complete: %d item(s) configured, files copied", len(copy_inputs))
    if copied == 0:
        return "skipped"
    return None
