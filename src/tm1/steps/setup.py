r"""Input staging.

``copy_inputs`` is ``SetUpModel.bat`` step 3 and ``RunModel.bat`` 172-178 -- two
steps, one mechanism.  ``copy_inputs`` assembles ``INPUT/`` from its real sources
(the M drive, this checkout); ``copy_input_to_working`` then fills the working
directories (``hwy/``, ``trn/``, ...) from ``INPUT/``.  Split by name because they
do different things -- one reaches outside the run, the other reshuffles what is
already inside it -- but both read a ``name: {from, to, ...}`` block the same way,
so one function runs either, keyed by whichever step named it.

An entry::

    input_hwy:
      from: "{env:TM1_M_DRIVE}/.../net_2023_Baseline/hwy"
      to: "{run_dir}/INPUT/hwy"
      include: ["*.tpp"]        # optional; only these, matched against the path
      exclude: ["ixDaily*.tpp"] #   relative to `from`.  exclude wins.
      overwrite: true           # optional; default is never to clobber
      variant:                  # optional; {dest name: path relative to `from`},
        tazData.csv: "parking_strategy/tazData_v01.csv"  #   copied on top after
      enabled: true             # optional; false skips the entry entirely

``from`` may be a directory or a single file; a file entry may rename, which is
how ``SetUpModel.bat`` turns ``2023b_tripsAirPaxEA.tpp`` into
``tripsAirPaxEA.tpp``.

``variant`` is how a strategy swaps in one file from inside a directory entry's own
``from:`` -- a parking-strategy ``tazData.csv`` living in a ``parking_strategy/``
subdirectory of the same land use release, say -- without restating the whole source
path a second time.  It always overwrites, the same as a renamed file entry landing on
a directory: the swap is declared, not defaulted into.

``concat`` takes ``from``'s place for an entry built by concatenation rather than
copying -- ``SetUpModel_PBA50Plus.bat``'s bus-on-shoulder override does
``copy /b a+b c``, byte for byte, to combine two network-project override files into
one::

    mod_links_brt:
      concat: ["{run_dir}/INPUT/hwy/a.csv", "{run_dir}/INPUT/hwy/b.csv"]
      to: "{run_dir}/INPUT/hwy/mod_links_BRT.csv"

No CSV-aware merge (e.g. de-duping a header row): the downstream job already handles
whatever the concatenation produces, and doing it differently here would stop being
what the batch file produced.

``enabled: false`` drops an entry entirely, the same switch a step itself takes --
how a Blueprint-only strategy override sits inert in a project's own
`copy_project_inputs:` without applying to every scenario: off by default, a
scenario turns one on rather than restating the whole entry.

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
_ENTRY_KEYS = frozenset(
    {"from", "to", "include", "exclude", "overwrite", "variant", "concat", "enabled"},
)


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


def _copy_variant(src: Path, dest: Path, variant: dict) -> int:
    """Land named files from *src* onto *dest*, always overwriting.

    *variant* is ``{dest name: path relative to src}`` -- named relative to the
    entry's own ``from:`` rather than restated absolutely, so the swap moves with
    it if a scenario repoints the whole entry.
    """
    written = 0
    for dest_name, rel_src in variant.items():
        source = src / rel_src
        if not source.exists():
            msg = f"variant {rel_src!r} not found under {src}"
            raise FileNotFoundError(msg)
        target = dest / dest_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        _strip_ctrl_z(target)
        written += 1
        log.info("Copied variant %s -> %s", source, target)
    return written


def _copy_concat(sources: list[Path], dest: Path, *, overwrite: bool) -> int:
    """Concatenate *sources* into *dest*, in order, byte for byte.

    ``copy /b a+b c``, not a CSV-aware merge -- see the module docstring.
    """
    if dest.exists() and not overwrite:
        log.info("Already exists: %s", dest)
        return 0
    for source in sources:
        if not source.exists():
            msg = f"concat: source not found: {source}"
            raise FileNotFoundError(msg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        for source in sources:
            out.write(source.read_bytes())
    log.info("Concatenated %d file(s) -> %s", len(sources), dest)
    return 1


def _check_keys(name: str, entry: dict) -> None:
    """Refuse an unknown key by name, listing what is allowed."""
    unknown = sorted(set(entry) - _ENTRY_KEYS)
    if unknown:
        msg = (
            f"entry {name!r} declares {', '.join(unknown)}; "
            f"allowed keys are {', '.join(sorted(_ENTRY_KEYS))}."
        )
        raise ValueError(msg)
    if "concat" in entry and "from" in entry:
        msg = f"entry {name!r}: declare `from` or `concat`, not both."
        raise ValueError(msg)
    if "concat" not in entry and "from" not in entry:
        msg = f"entry {name!r}: needs `from` or `concat`."
        raise ValueError(msg)


def run(
    config_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Stage every entry declared under this step's block, in order.

    Runs as either ``copy_inputs`` or ``copy_input_to_working`` -- same
    mechanism, different sources -- so every message names the step that was
    actually launched (``kwargs["step_name"]``) rather than assuming which one.
    """
    step_name = str(kwargs.get("step_name") or "copy_inputs")
    entries = step_config(cfg, step_name, kwargs)

    copied = 0
    for name, entry in entries.items():
        try:
            _check_keys(name, entry)
        except ValueError as exc:
            raise ValueError(f"{step_name} {exc}") from exc
        if entry.get("enabled", True) is False:
            continue

        dest = Path(entry["to"])
        overwrite = bool(entry.get("overwrite", False))

        concat = entry.get("concat")
        if concat is not None:
            try:
                copied += _copy_concat([Path(p) for p in concat], dest, overwrite=overwrite)
            except FileNotFoundError as exc:
                raise FileNotFoundError(f"{step_name} {exc}") from exc
            continue

        src = Path(entry["from"])
        if not src.exists():
            sys.exit(f"{step_name}[{name}]: source not found: {src}")

        if src.is_dir():
            copied += _copy_tree(
                src, dest,
                include=list(entry.get("include") or []),
                exclude=list(entry.get("exclude") or []),
                overwrite=overwrite,
            )
            variant = entry.get("variant")
            if variant:
                try:
                    copied += _copy_variant(src, dest, variant)
                except FileNotFoundError as exc:
                    raise FileNotFoundError(f"{step_name} {exc}") from exc
        else:
            copied += _copy_file(src, dest, overwrite=overwrite)

    log.info("%s: %d entries, %d file(s) written", step_name, len(entries), copied)
    # "Nothing to do" is the whole step doing nothing, not one entry: an entry
    # that legitimately finds everything in place must not mask the ones that
    # did work.
    return "skipped" if copied == 0 else None
