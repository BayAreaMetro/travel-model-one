r"""The file shuffling ``RunIteration.bat`` does between Cube jobs.

``mkdir``, ``move``, ``copy`` and ``del`` lines, one step each, so they stay visible
in the config rather than disappearing inside a Python function.  They are not
model artifacts -- no ``.job`` or ``.py`` produces them -- but they *are* load
bearing: the next iteration's ``HwySkims`` reads what :func:`publish_networks`
leaves in ``hwy/``.

Each step takes its iteration from where it sits inside ``iterate:`` -- before
``iteration_zero_begins`` (iterations 1..count) or at/after it (iteration 0 too).

===========================  ==========================================
Step                         ``RunIteration.bat``
===========================  ==========================================
:func:`copy_transit_skims`   ``trnAssign.bat``'s copy-up
:func:`stage_loaded_networks`  159-164 -- ``mkdir`` + five ``move``
:func:`seed_average_networks`  177-181 -- the ``ELSE`` copy
:func:`publish_networks`     193-200 -- five ``copy`` + ``del x*.net``
===========================  ==========================================
"""

import logging
import shutil
from pathlib import Path

from tm1.project.config import step_config

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")


def _iteration(cfg: dict, kwargs: dict) -> int:
    """This step's iteration, supplied by the runner."""
    step_name = str(kwargs.get("step_name", "?"))
    step_cfg = step_config(cfg, step_name, kwargs)
    declared = step_cfg.get("iteration", kwargs.get("iteration"))
    if declared is None:
        msg = (
            f"Step {step_name!r} needs an iteration: it names files under "
            f"hwy/iter{{N}}/. Put it inside `iterate:`; written flat, it has no "
            f"iteration."
        )
        raise ValueError(msg)
    return int(declared)


def _iter_dir(cfg: dict, kwargs: dict) -> tuple[Path, Path]:
    """``(hwy/, hwy/iter{N}/)`` for this round, creating the latter."""
    hwy = Path(cfg["run_dir"]) / "hwy"
    iter_dir = hwy / f"iter{_iteration(cfg, kwargs)}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    return hwy, iter_dir


def make_directories(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Create the working directories, ``RunModel.bat`` 156-165.

    Native steps create what they write, so this looks redundant -- but a Cube job
    does not.  ``NonMotorizedSkims.job`` writing to ``skims/nonmotskm.tpp`` fails
    with "the system cannot find the path specified" if ``skims/`` is absent, and
    nothing else creates it: only directories that happen to be ``copy_inputs``
    targets exist by the time the jobs run.  ``skims``, ``popsyn`` and ``database``
    have no staged inputs at all.
    """
    step_cfg = step_config(cfg, str(kwargs.get("step_name", "")), kwargs)
    names = step_cfg.get("dirs")
    if not names:
        msg = (
            "make_directories needs `dirs:` -- the list RunModel.bat 156-165 creates. "
            "It is stated in the config rather than hard-coded because which "
            "directories a run needs is a property of the pipeline, not of this step."
        )
        raise ValueError(msg)

    run_dir = Path(cfg["run_dir"])
    made = [n for n in names if not (run_dir / str(n)).is_dir()]
    for name in names:
        (run_dir / str(name)).mkdir(parents=True, exist_ok=True)

    log.info("Directories ready in %s (%d created)", run_dir, len(made))
    return None


def copy_transit_skims(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Lift this round's transit skims out of the iteration directory, into ``skims/``.

    ``trnAssign.bat``'s copy-up.  ``TransitSkims.job`` writes plain
    ``trnskm{period}_{access}_{path}_{egress}.tpp`` into
    ``trn/TransitAssignment.iter{N}/`` -- a straight copy, no rename: the
    ``STANDARD``/MSA configuration this once had to strip a sub-iteration
    suffix for is gone (simplify_transit_master), and CT-RAMP/``Accessibility.job``
    already read this exact name.

    Excludes ``*_woRegionalFare.tpp``: when the regional fare strategy is on,
    ``apply_regional_transit_fares_to_skims.job`` renames the pre-fare skim
    aside under that name before writing the fare-adjusted version back to the
    plain one, so both exist in the iteration directory -- only the plain name
    is the round's real product.
    """
    run_dir = Path(cfg["run_dir"])
    iteration = _iteration(cfg, kwargs)
    ta_dir = run_dir / "trn" / f"TransitAssignment.iter{iteration}"
    skims = run_dir / "skims"
    skims.mkdir(parents=True, exist_ok=True)

    files = [f for f in ta_dir.glob("trnskm*.tpp") if "_woRegionalFare" not in f.name]
    if not files:
        msg = (
            f"No transit skims in {ta_dir}. TransitSkims.job writes "
            f"trnskm*.tpp there; check that it ran for this round."
        )
        raise FileNotFoundError(msg)

    for path in files:
        shutil.copy2(path, skims / path.name)

    log.info("Copied %d transit skims to %s", len(files), skims)
    return None


def stage_loaded_networks(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
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


def seed_average_networks(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
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


def publish_networks(config_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
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
