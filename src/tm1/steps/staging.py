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

from tm1.config import step_config

log = logging.getLogger(__name__)

PERIODS: tuple[str, ...] = ("EA", "AM", "MD", "PM", "EV")


def _iteration(cfg: dict, kwargs: dict) -> int:
    """This step's round: its own ``iteration:`` key, else the loop's."""
    step_name = str(kwargs.get("step_name", "?"))
    step_cfg = step_config(cfg, step_name, kwargs)
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


def make_directories(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
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

    proj_dir = Path(cfg["proj_dir"])
    made = [n for n in names if not (proj_dir / str(n)).is_dir()]
    for name in names:
        (proj_dir / str(name)).mkdir(parents=True, exist_ok=True)

    log.info("Directories ready in %s (%d created)", proj_dir, len(made))
    return None


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


def copy_transit_skims(scenario_dir: Path, cfg: dict, **kwargs: object) -> str | None:  # noqa: ARG001
    """Lift this round's transit skims out of the iteration directory, into ``skims/``.

    ``trnAssign.bat:231-235``.  ``TransitSkims.job`` writes
    ``trnskm{period}_{access}_{path}_{egress}.avg.iter{S}.tpp`` into
    ``trn/TransitAssignment.iter{N}/``; the copy-up **strips the suffix**, so
    ``skims/`` holds plain ``trnskm{period}_{path}.tpp`` -- the names CT-RAMP and
    ``Accessibility.job`` read.  Keeping the suffix leaves the plain names
    missing, which crashes ``Accessibility.job`` at startup.

    **``S`` is the transit sub-iteration, not the global round.**  It comes from
    ``%TRNASSIGNITER%`` (``TransitSkims.job:431``), a counter internal to
    ``trnAssign.bat`` that starts at 0 and only advances in the ``STANDARD``
    configuration, where transit assignment iterates to convergence.  Under
    ``FAST`` -- one pass, what this pipeline runs -- it stays 0 in *every* global
    round, so round 2's directory holds ``.avg.iter0.tpp`` just as round 0's does.

    The ``.bat`` copies ``%LASTITER_{period}%``, the last sub-iteration reached,
    so this takes the highest one present per skim rather than assuming a number.
    """
    proj_dir = Path(cfg["proj_dir"])
    iteration = _iteration(cfg, kwargs)
    ta_dir = proj_dir / "trn" / f"TransitAssignment.iter{iteration}"
    skims = proj_dir / "skims"
    skims.mkdir(parents=True, exist_ok=True)

    # base name -> (sub-iteration, file), keeping the highest sub-iteration.
    latest: dict[str, tuple[int, Path]] = {}
    for path in sorted(ta_dir.glob("trnskm*.avg.iter*.tpp")):
        base, _, tail = path.name.partition(".avg.iter")
        sub = tail.removesuffix(".tpp")
        if not sub.isdigit():
            continue  # `.avg.iterNEG1.tpp`, TransitSkims.job:424's seed copy
        if base not in latest or int(sub) > latest[base][0]:
            latest[base] = (int(sub), path)

    if not latest:
        msg = (
            f"No transit skims in {ta_dir}. TransitSkims.job writes "
            f"trnskm*.avg.iter{{S}}.tpp there, where S is the transit "
            f"sub-iteration (0 under TRNCONFIG=FAST, not the global round); "
            f"check that it ran for this round."
        )
        raise FileNotFoundError(msg)

    for base, (_, path) in latest.items():
        shutil.copy2(path, skims / f"{base}.tpp")

    subs = sorted({sub for sub, _ in latest.values()})
    log.info(
        "Copied %d transit skims to %s (sub-iteration %s, suffix stripped)",
        len(latest), skims, ", ".join(str(s) for s in subs),
    )
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
