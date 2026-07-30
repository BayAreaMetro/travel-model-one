"""Scenario-specific pipeline steps for base_2023_ctramp.

Anything in here is ordinary Python, wired in from ``scenario_config.yaml``::

    steps:
      extract_key_files:
        script: "hooks.py:extract_key_files"

A step is any function taking ``(scenario_dir, cfg, **kwargs)`` -- the same
contract the built-in steps use.  Where it appears under ``steps:`` decides when
it runs: before ``simulate_ctramp`` makes it pre-processing, after ``assignment``
makes it post-processing.  Return ``"skipped"`` to record a no-op.
"""

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

#: Files ExtractKeyFiles.bat pulls that this pipeline can produce today, as
#: (source relative to proj_dir, destination relative to extractor/).  ``{iter}``
#: expands to the assignment iteration, standing in for the batch file's %ITER%.
_EXTRACT = (
    ("hwy/iter{iter}/avgload5period.net", "avgload5period.net"),
    ("hwy/iter{iter}/avgload5period.csv", "avgload5period.csv"),
    ("main/tripsEA.tpp", "main/tripsEA.tpp"),
    ("main/tripsAM.tpp", "main/tripsAM.tpp"),
    ("main/tripsMD.tpp", "main/tripsMD.tpp"),
    ("main/tripsPM.tpp", "main/tripsPM.tpp"),
    ("main/tripsEV.tpp", "main/tripsEV.tpp"),
    ("logs/feedback.rpt", "feedback.rpt"),
    ("logs/HwySkims.debug", "HwySkims.debug"),
)

#: Directories ExtractKeyFiles.bat also collects, which need the post-processing
#: phase this pipeline does not yet run.  Reported so the gap stays visible
#: rather than looking like the extract simply found nothing.
_NEEDS_POSTPROCESSING = (
    "logsums", "core_summaries", "updated_output", "metrics", "emfac",
    "offmodel", "shapefile",
)


def extract_key_files(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,
    **kwargs: object,  # noqa: ARG001
) -> str | None:
    """Collect key model outputs into ``extractor/`` for export and summarising.

    The Python counterpart of ``utilities/RTP/ExtractKeyFiles.bat``, covering the
    subset this pipeline currently produces.  The rest of that batch file reads
    directories built by the post-processing phase (logsums, core summaries,
    metrics, EMFAC), which is not yet ported -- those are logged as skipped.
    """
    proj_dir = Path(cfg["proj_dir"])
    iteration = cfg.get("steps", {}).get("assignment", {}).get("iteration") or 1

    extractor = proj_dir / "extractor"
    extractor.mkdir(parents=True, exist_ok=True)

    copied, missing = 0, []
    for src_tmpl, dest_rel in _EXTRACT:
        src = proj_dir / src_tmpl.format(iter=iteration)
        if not src.is_file():
            missing.append(src_tmpl.format(iter=iteration))
            continue
        dest = extractor / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    if missing:
        log.warning("extract_key_files: %d file(s) not found: %s",
                    len(missing), ", ".join(missing))

    log.info(
        "extract_key_files: %d file(s) -> %s. Not collected (needs the "
        "post-processing phase): %s",
        copied, extractor, ", ".join(_NEEDS_POSTPROCESSING),
    )
    return None if copied else "skipped"
