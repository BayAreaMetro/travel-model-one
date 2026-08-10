r"""The file shuffling ``RunIteration.bat`` does between Cube jobs.

``mkdir``, ``move``, ``copy`` and ``del`` lines, one step each, so they stay visible
in the config rather than disappearing inside a Python function.  They are not
model artifacts -- no ``.job`` or ``.py`` produces them -- but they *are* load
bearing: the next iteration's ``HwySkims`` reads what :func:`publish_networks`
leaves in ``hwy/``.

Each step takes its round from the enclosing ``iterate:`` block, or from its own
``iteration:`` key when it sits outside the loop (the warm start does).

===========================  ==========================================
Step                         ``RunIteration.bat``
===========================  ==========================================
:func:`stage_transit_lines`  ``trnAssign.bat`` 43-63
:func:`stage_loaded_networks`  159-164 -- ``mkdir`` + five ``move``
:func:`seed_average_networks`  177-181 -- the ``ELSE`` copy
:func:`publish_networks`     193-200 -- five ``copy`` + ``del x*.net``
===========================  ==========================================
"""

import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")


def _iteration(cfg: dict, kwargs: dict) -> int:
    """This step's round: its own ``iteration:`` key, else the loop's.

    The name comes from the runner, so one function can serve several steps -- the
    warm start reuses these under ``warmstart_*`` names.
    """
    step_name = str(kwargs.get("step_name", "?"))
    step_cfg = cfg.get("steps", {}).get(step_name) or {}
    declared = step_cfg.get("iteration", kwargs.get("iteration"))
    if declared is None:
        msg = (
            f"Step {step_name!r} needs an iteration: it names files under "
            f"hwy/iter{{N}}/. Put it inside `iterate:`, or give it an "
            f"`iteration:` key (the warm-start steps use `iteration: 0`)."
        )
        raise ValueError(msg)
    return int(declared)


def _iter_dir(cfg: dict, kwargs: dict) -> tuple[Path, Path]:
    """``(hwy/, hwy/iter{N}/)`` for this round, creating the latter."""
    hwy = Path(cfg["proj_dir"]) / "hwy"
    iter_dir = hwy / f"iter{_iteration(cfg, kwargs)}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    return hwy, iter_dir


def stage_transit_lines(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Seed this round's transit assignment directory with its line files.

    ``trnAssign.bat`` 43-63.  Every global iteration starts from the period files
    built at model setup -- faithful for the ``FAST`` configuration, where transit
    does a single pass and never carries lines forward from its own previous round.
    """
    proj_dir = Path(cfg["proj_dir"])
    iteration = _iteration(cfg, kwargs)
    trn = proj_dir / "trn"
    ta_dir = trn / f"TransitAssignment.iter{iteration}"
    ta_dir.mkdir(parents=True, exist_ok=True)

    for period in PERIODS:
        source = trn / f"transitOriginal{period}.lin"
        if not source.is_file():
            msg = (
                f"Transit line file missing: {source}. It is built at model setup "
                f"by the transit_dwell_access step."
            )
            raise FileNotFoundError(msg)
        # Both names: the _0 copy is the round's starting point, the bare one is
        # what trnbuild reads and later passes overwrite.
        shutil.copy2(source, ta_dir / f"transit{period}_0.lin")
        shutil.copy2(source, ta_dir / f"transit{period}.lin")

    log.info("Staged %d transit line files in %s", 2 * len(PERIODS), ta_dir)
    return None


def stage_loaded_networks(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Move this round's assignment output into its iteration directory.

    ``RunIteration.bat`` 159-164.  ``HwyAssign`` writes ``hwy/LOAD{P}.net``; the
    feedback jobs read them from ``hwy/iter{N}/``.
    """
    hwy, iter_dir = _iter_dir(cfg, kwargs)

    for period in PERIODS:
        source = hwy / f"LOAD{period}.net"
        if not source.is_file():
            msg = (
                f"Loaded network missing: {source}. HwyAssign.job writes these; "
                f"check that it ran and succeeded for this iteration."
            )
            raise FileNotFoundError(msg)
        shutil.move(str(source), str(iter_dir / f"LOAD{period}.net"))

    log.info("Moved %d loaded networks into %s", len(PERIODS), iter_dir)
    return None


def seed_average_networks(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Start the running average from this round's assignment.

    ``RunIteration.bat`` 177-181, the ``ELSE`` branch of ``IF %ITER% GTR 1``.  The
    feedback loop averages each round's volumes with the running average of the
    ones before it; the first round has nothing to average against, so its own
    result *is* the average.

    Only the warm start needs this.  From iteration 1 on, ``AverageNetworkVolumes``
    does the job -- see the parity plan's finding 5 for why it can run unguarded.
    """
    _, iter_dir = _iter_dir(cfg, kwargs)

    for period in PERIODS:
        source = iter_dir / f"LOAD{period}_renamed.net"
        if not source.is_file():
            msg = (
                f"Renamed network missing: {source}. "
                f"RenameAssignmentVariables.job writes these; it must run first."
            )
            raise FileNotFoundError(msg)
        shutil.copy2(source, iter_dir / f"avgLOAD{period}.net")

    log.info("Seeded %d averaged networks in %s", len(PERIODS), iter_dir)
    return None


def publish_networks(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Publish this round's averaged networks, and drop the intermediates.

    ``RunIteration.bat`` 193-200.  ``hwy/avgLOAD{P}.net`` is what the *next* round
    reads -- ``HwySkims`` and the transit background both take it from ``hwy/``,
    not from an iteration directory.  The ``x*`` files are AverageNetworkVolumes'
    and CalculateSpeeds' scratch output and nothing reads them again.
    """
    hwy, iter_dir = _iter_dir(cfg, kwargs)

    for period in PERIODS:
        source = iter_dir / f"avgLOAD{period}.net"
        if not source.is_file():
            msg = (
                f"Averaged network missing: {source}. Either "
                f"AverageNetworkVolumes/CalculateSpeeds or the warm start's "
                f"seed_average_networks step must produce it."
            )
            raise FileNotFoundError(msg)
        shutil.copy2(source, hwy / f"avgLOAD{period}.net")

    scratch = sorted(iter_dir.glob("x*.net"))
    for path in scratch:
        path.unlink()

    log.info(
        "Published %d averaged networks to %s (removed %d scratch networks)",
        len(PERIODS), hwy, len(scratch),
    )
    return None
