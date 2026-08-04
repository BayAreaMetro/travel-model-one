"""Seed the first demand and assign it, producing the run's first skims.

``RunModel.bat``'s iteration 0: demand models need skims, skims need an
assignment, an assignment needs demand.  A previous run's trip tables break the
tie.  Copies ``{from}/main/*.tpp`` and ``{from}/nonres/*.tpp`` into place
(``RunModel.bat`` 176-177), then assigns at iteration 0 -- which skips the
demand models, ``PrepAssign`` and the non-residential models, per
:func:`tm1.assignment.cube.ctramp.run_iteration`.

The destination is never configured here; it comes from the ``assignment``
step's ``demand:`` pattern, so the trip-table path is stated once and the two
steps cannot drift apart.

Config -- ``from`` is a previous run's warmstart directory, or ``coldstart``::

    warmstart:
      from: "{reference_run}/INPUT/warmstart"

``from: coldstart`` writes zero demand instead, so the assignment returns
free-flow times.  It converges, but is **not** parity with a warm-started run.
It is also new: the legacy has no from-scratch path -- ``utilities/create_warmstart``
only widens an existing warmstart's table set (how the TNC and AV classes were
added), so every MTC warmstart descends from an older one.

A ``from`` that is neither ``coldstart`` nor an existing directory is an error,
so a typo can never quietly become a cold start.
"""

import logging
import shutil
from pathlib import Path

import numpy as np

import tm1.steps.assignment as assignment_step
from cubeio import write_tpp
from tm1.assignment.cube.highway import PERIODS

log = logging.getLogger(__name__)

#: The 29 demand tables Cube assignment reads, in order.  Matches the warmstart
#: files MTC ships and ``utilities/create_warmstart/CreateWarmStart.job``'s output.
TABLES: tuple[str, ...] = (
    "da", "datoll", "sr2", "sr2toll", "sr3", "sr3toll",
    "walk", "bike",
    "wlk_loc_wlk", "wlk_lrf_wlk", "wlk_exp_wlk", "wlk_hvy_wlk", "wlk_com_wlk",
    "drv_loc_wlk", "drv_lrf_wlk", "drv_exp_wlk", "drv_hvy_wlk", "drv_com_wlk",
    "wlk_loc_drv", "wlk_lrf_drv", "wlk_exp_drv", "wlk_hvy_drv", "wlk_com_drv",
    "da_tnc", "s2_tnc", "s3_tnc", "da_av", "s2_av", "s3_av",
)

#: ``from:`` value that means "no previous run -- assign zero demand".
COLD_START = "coldstart"

#: Zone count for cold-start matrices: internal zones only, as the warmstart
#: files MTC ships use (externals carry no warm demand).
_COLD_START_ZONES = 1454

_WARM_START_ITERATION = 0


def _assignment_cfg(cfg: dict) -> dict:
    """The ``assignment`` step's config, whether or not it sits inside ``iterate``.

    It normally lives in the loop body, so a top-level lookup finds nothing.
    """
    steps = cfg.get("steps", {}) or {}
    if "assignment" in steps:
        return steps["assignment"] or {}
    return ((steps.get("iterate") or {}).get("steps") or {}).get("assignment") or {}


def _demand_pattern(cfg: dict) -> str:
    """Where warm demand goes: the ``assignment`` step's declared artifact."""
    pattern = _assignment_cfg(cfg).get("demand")
    if not pattern:
        msg = (
            "warmstart needs the assignment step's `demand:` key to know where to "
            "put the seed trip tables. Declare it on `assignment` in the scenario "
            "(it normally sits inside `iterate:`)."
        )
        raise ValueError(msg)
    return str(pattern)


def seed_from_previous_run(source: Path, demand: str, nonres_dir: Path) -> int:
    """Copy a previous run's trip tables into place.  Returns files copied."""
    main_src, nonres_src = source / "main", source / "nonres"
    if not main_src.is_dir():
        msg = (
            f"warmstart `from` has no main/ directory: {main_src}. Point it at a "
            f"run's INPUT/warmstart (which holds main/ and nonres/)."
        )
        raise FileNotFoundError(msg)

    copied = 0
    for period in PERIODS:
        src = main_src / f"trips{period}.tpp"
        if not src.is_file():
            msg = f"warmstart seed missing: {src}"
            raise FileNotFoundError(msg)
        dest = Path(demand.replace("{PERIOD}", period))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    if nonres_src.is_dir():
        # Iteration 0 does not run the non-residential models, so these truck and
        # internal/external tables are the only such demand it will assign.
        nonres_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(nonres_src.glob("*.tpp")):
            shutil.copy2(src, nonres_dir / src.name)
            copied += 1
    else:
        log.warning("warmstart `from` has no nonres/ directory: %s", nonres_src)

    log.info("warmstart: seeded %d file(s) from %s", copied, source)
    return copied


def seed_cold_start(demand: str, zones: int = _COLD_START_ZONES) -> None:
    """Write zero demand, so the assignment returns free-flow times."""
    empty = {name: np.zeros((zones, zones)) for name in TABLES}
    for period in PERIODS:
        dest = Path(demand.replace("{PERIOD}", period))
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_tpp(dest, empty, zones=zones)
    log.info(
        "warmstart: cold start -- wrote zero demand for %d periods "
        "(%d tables, %d zones); assignment will return free-flow skims",
        len(PERIODS), len(TABLES), zones,
    )


def run(
    scenario_dir: Path,
    cfg: dict,
    **kwargs: object,
) -> str | None:
    """Seed iteration 0's demand, then assign it to produce the first skims."""
    step_cfg = cfg.get("steps", {}).get("warmstart", {}) or {}
    source = step_cfg.get("from")
    if not source:
        msg = (
            "warmstart: needs `from` -- a previous run's INPUT/warmstart directory, "
            f"or {COLD_START!r} to assign zero demand instead."
        )
        raise ValueError(msg)

    demand = _demand_pattern(cfg)
    proj_dir = Path(step_cfg.get("proj_dir") or cfg["proj_dir"])

    if str(source).strip().lower() == COLD_START:
        seed_cold_start(demand, zones=int(step_cfg.get("zones", _COLD_START_ZONES)))
    else:
        source_dir = Path(source)
        if not source_dir.is_dir():
            msg = (
                f"warmstart `from` does not exist: {source_dir}. Fix the path, or "
                f"set `from: {COLD_START}` to deliberately start from zero demand."
            )
            raise FileNotFoundError(msg)
        seed_from_previous_run(source_dir, demand, proj_dir / "nonres")

    # Pinned in a *copy* of the config, not passed as a keyword: `assignment`
    # lets its own `iteration:` key win, so a scenario that pins one would
    # otherwise run the warm start at the wrong number.  `build_skims` is forced
    # on because skims are this pass's entire product.
    steps = dict(cfg.get("steps", {}))
    assign_cfg = dict(_assignment_cfg(cfg))
    assign_cfg["iteration"] = _WARM_START_ITERATION
    assign_cfg["build_skims"] = True
    # Injected at the top level so `assignment.run` finds it there rather than in
    # the loop body it normally lives in.
    steps["assignment"] = assign_cfg
    return assignment_step.run(scenario_dir, {**cfg, "steps": steps}, **kwargs)
