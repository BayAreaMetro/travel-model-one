r"""Input staging.

``copy_inputs`` is ``SetUpModel.bat`` step 3 and ``RunModel.bat`` 172-178, in one
step.  It reads ``copy_inputs:`` from the project config -- named entries, each
with ``from`` and ``to`` -- and runs them **in the order written**, so a later
entry may read what an earlier one staged.  That ordering is what lets one step
both assemble ``INPUT/`` from its sources and then fill the working directories
from ``INPUT/``.

There is no reference run.  Each entry names where its bytes actually come from,
the way ``SetUpModel.bat`` named ``INPUT_NETWORK`` / ``INPUT_POPLU`` /
``NONRES_INPUT_DIR``, and the model's own code comes from this checkout.

An entry::

    input_hwy:
      from: "{env:TM1_M_DRIVE}/.../net_2023_Baseline/hwy"
      to: "{run_dir}/INPUT/hwy"
      include: ["*.tpp"]        # optional; only these, matched against the path
      exclude: ["ixDaily*.tpp"] #   relative to `from`.  exclude wins.
      overwrite: true           # optional; default is never to clobber

``from`` may be a directory or a single file; a file entry may rename, which is
how ``SetUpModel.bat`` turns ``2023b_tripsAirPaxEA.tpp`` into
``tripsAirPaxEA.tpp``.

Two sources may **merge** into one directory -- ``RunModel.bat`` 175-177 copies
both ``INPUT\nonres`` and ``INPUT\warmstart\nonres`` into ``nonres\`` -- so the
copy is file by file rather than :func:`shutil.copytree`.

Nothing is overwritten unless the entry says ``overwrite: true``.  Re-running
staging therefore never clobbers what a later step built on top of it, and the
files a strategy deliberately swaps in say so in the config rather than
depending on a global flag.
"""

import fnmatch
import logging
import shutil
import sys
from pathlib import Path

from tm1.project.config import step_config

log = logging.getLogger(__name__)

#: Keys an entry may declare.  Anything else is refused by name, so a typo is an
#: error rather than a silently ignored instruction.
_ENTRY_KEYS = frozenset({"from", "to", "include", "exclude", "overwrite"})


def _strip_ctrl_z(path: Path) -> None:
    """Remove trailing Ctrl-Z (0x1a) if present (legacy Windows EOF)."""
    with path.open("r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x1a":
            log.info("  Stripping trailing Ctrl-Z from %s", path.name)
            f.seek(-1, 2)
            f.truncate()


def _selected(rel: Path, include: list[str], exclude: list[str]) -> bool:
    r"""Whether a file at *rel* (relative to ``from``) is staged.

    Patterns are :mod:`fnmatch` globs against the forward-slash relative path,
    so ``*.tpp`` reads the same on both platforms.  ``exclude`` wins: it is how
    ``SetUpModel.bat``'s two ``del INPUT\\warmstart\\nonres\\ixDaily*.tpp`` lines
    are expressed, and a file that is never copied cannot be left behind by a
    resumed run the way a deleted one can.
    """
    text = rel.as_posix()
    if include and not any(fnmatch.fnmatch(text, pat) for pat in include):
        return False
    return not any(fnmatch.fnmatch(text, pat) for pat in exclude)


def _copy_tree(
    src: Path, dest: Path, *, include: list[str], exclude: list[str], overwrite: bool
) -> int:
    """Copy a directory into *dest*, preserving shape, returning files written."""
    dest.mkdir(parents=True, exist_ok=True)
    written = 0
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)
        if not _selected(rel, include, exclude):
            continue
        target = dest / rel
        if target.exists() and not overwrite:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        written += 1

    log.info("Copied %s -> %s (%d files)", src, dest, written)
    return written


def _copy_file(src: Path, dest: Path, *, overwrite: bool) -> int:
    """Copy a single file, which may rename it.  Returns 1 if written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not overwrite:
        log.info("Already exists: %s", dest)
        return 0
    log.info("Copying %s -> %s", src, dest)
    shutil.copy2(src, dest)
    _strip_ctrl_z(dest)
    return 1


def _check_keys(name: str, entry: dict) -> None:
    """Refuse an unknown key by name, listing what is allowed."""
    unknown = sorted(set(entry) - _ENTRY_KEYS)
    if unknown:
        msg = (
            f"copy_inputs entry {name!r} declares {', '.join(unknown)}; "
            f"allowed keys are {', '.join(sorted(_ENTRY_KEYS))}."
        )
        raise ValueError(msg)


def run(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Stage every entry declared under ``copy_inputs``, in order."""
    copy_inputs = step_config(cfg, "copy_inputs", kwargs)

    copied = 0
    for name, entry in copy_inputs.items():
        _check_keys(name, entry)
        src = Path(entry["from"])
        dest = Path(entry["to"])
        if not src.exists():
            sys.exit(f"copy_inputs[{name}]: source not found: {src}")

        overwrite = bool(entry.get("overwrite", False))
        if src.is_dir():
            copied += _copy_tree(
                src, dest,
                include=list(entry.get("include") or []),
                exclude=list(entry.get("exclude") or []),
                overwrite=overwrite,
            )
        else:
            copied += _copy_file(src, dest, overwrite=overwrite)

    log.info("copy_inputs: %d entries, %d file(s) written", len(copy_inputs), copied)
    # "Nothing to do" is the whole step doing nothing, not one entry: an entry
    # that legitimately finds everything in place must not mask the ones that
    # did work.
    return "skipped" if copied == 0 else None
