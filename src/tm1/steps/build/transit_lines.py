r"""Stage the per-period transit line files (RunModel.bat step 4.5).

Native replacement for ``transitDwellAccess.py``'s *Simple* mode, which
``RunModel.bat`` line 239 runs as::

    transitDwellAccess.py NORMAL NoExtraDelay Simple complexDwell %COMPLEXMODES_DWELL% \\
                          complexAccess %COMPLEXMODES_ACCESS%

and which needs the NetworkWrangler library.  That dependency is dropped: with
the shipped configuration the pass does no work on the line data.

**What the legacy pass actually does.**  ``RunModel.bat`` sets both
``COMPLEXMODES_DWELL`` and ``COMPLEXMODES_ACCESS`` to *empty* (lines 146-147;
the populated variants on 140-141 are commented out), so Wrangler's
``addDelay`` runs with no complex dwell or access modes and changes nothing in
the line file.  The script then writes ``transitOriginal{P}.lin`` once per
period from the same parsed network, so all five outputs are identical.

Verified against the reference run: its five ``transitOriginal{P}.lin`` are
byte-identical to each other, and identical to ``INPUT/trn/transitLines.lin``
across all 33,275 substantive lines.  The only textual residue of Wrangler's
parse/write round trip is cosmetic and ignored by ``trnbuild``:

- 105 blank lines dropped,
- the leading ``;###... From: <authoring path>`` comment rewritten to
  ``;###... From: transitLines.lin``,
- one provenance comment reflowed onto the end of the preceding data line.

This step therefore copies rather than reconstructing those artefacts: cloning
a parser's whitespace quirks into new code would be cargo cult, and the
substantive content is what ``trnbuild`` reads.

.. warning:: THIS STEP IS ONLY VALID WHILE THE COMPLEX DWELL MODES ARE EMPTY.

    ``RunModel.bat`` lines 140-141 carry a commented-out configuration::

        COMPLEXMODES_DWELL=21 24 27 28 30 70 80 81 83 84 87 88
        COMPLEXMODES_ACCESS=21 24 27 28 30 70 80 81 83 84 87 88 110 120 130

    If anyone enables those, Wrangler applies **real, mode-dependent dwell and
    access delay** and the five period files stop being copies of the input and
    of each other.  A plain copy would then silently produce wrong transit
    running times -- no error, just a different model.  ``dwell_modes`` and
    ``access_modes`` exist below purely to make that case fail loudly.  If you
    are here because you set them: the delay logic lives in NetworkWrangler's
    ``TransitNetwork.addDelay``, and porting it is a project of its own.

Config::

    build_transit_lines:
      from: "{proj_dir}/trn/transitLines.lin"
      to: "{proj_dir}/trn"
"""

import logging
import shutil
from pathlib import Path

from tm1.steps.build import resolve_path

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Write ``transitOriginal{PERIOD}.lin`` for each of the five time periods."""
    step_cfg = cfg.get("steps", {}).get("build_transit_lines", {}) or {}
    source = resolve_path(step_cfg, cfg, "from", "trn", "transitLines.lin")
    out_dir = resolve_path(step_cfg, cfg, "to", "trn")

    # Present so an enabled complex-dwell configuration cannot pass silently.
    for key in ("dwell_modes", "access_modes"):
        modes = step_cfg.get(key)
        if modes:
            msg = (
                f"build_transit_lines: {key}={modes!r} requires the mode-dependent "
                f"dwell/access delay this step does not implement (see the module "
                f"docstring). Port NetworkWrangler's TransitNetwork.addDelay first."
            )
            raise NotImplementedError(msg)

    targets = [out_dir / f"transitOriginal{period}.lin" for period in PERIODS]
    if not kwargs.get("force", False) and all(t.exists() for t in targets):
        log.info("Transit line files already staged in %s", out_dir)
        return "skipped"

    if not source.exists():
        msg = f"build_transit_lines input missing: {source}"
        raise FileNotFoundError(msg)

    out_dir.mkdir(parents=True, exist_ok=True)
    for target in targets:
        shutil.copy2(source, target)
    log.info("Wrote %d period line files from %s", len(targets), source.name)
    return None
