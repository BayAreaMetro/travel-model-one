"""Input staging steps.

``copy_inputs`` reads ``cfg["steps"]["copy_inputs"]`` — a dict of named entries,
each with ``from`` and ``to`` paths.  If ``from`` is a directory, the entire
tree is copied (or filtered by ``glob`` pattern).  Idempotent: skips
files/dirs that already exist unless ``force=True``.
"""

import logging
import shutil
import sys
from pathlib import Path

from tm1.config import step_config

log = logging.getLogger(__name__)


def _strip_ctrl_z(path: Path) -> None:
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with path.open("r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def _copy_tree(src: Path, dest: Path, *, glob: str | None, force: bool) -> int:
    r"""Copy a directory into *dest*, returning the number of files written.

    File by file rather than :func:`shutil.copytree`, for two reasons.  Two sources
    can **merge** into one directory -- ``RunModel.bat`` 175-177 copies both
    ``INPUT\\nonres`` and ``INPUT\\warmstart\\nonres`` into ``nonres\\``.  And an
    existing file is left alone unless *force*, so re-running staging never clobbers
    what a later step built on top of it.

    ``glob`` selects top-level files only and flattens them into *dest*; without it
    the whole tree is walked and its shape preserved.
    """
    files = (
        [f for f in sorted(src.glob(glob)) if f.is_file()]
        if glob
        else sorted(p for p in src.rglob("*") if p.is_file())
    )

    dest.mkdir(parents=True, exist_ok=True)
    written = 0
    for f in files:
        target = dest / (f.name if glob else f.relative_to(src))
        if not force and target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        written += 1

    log.info("Copied %s%s -> %s (%d files)", src, f"/{glob}" if glob else "", dest, written)
    return written


def run(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Copy input files as specified in the copy_inputs step."""
    force = kwargs.get("force", False)

    copy_inputs = step_config(cfg, "copy_inputs", kwargs)

    copied = 0
    for name, entry in copy_inputs.items():
        src = Path(entry["from"])
        dest = Path(entry["to"])
        if not src.exists():
            sys.exit(f"Source not found: {src}")

        if src.is_dir():
            copied += _copy_tree(src, dest, glob=entry.get("glob"), force=bool(force))
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
