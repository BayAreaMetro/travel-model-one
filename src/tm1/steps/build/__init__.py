"""Build-once input staging: pristine ``INPUT/`` files -> model-loop inputs.

Every step in this package runs after ``copy_inputs`` and before ``iterate:``,
building an artifact the loop consumes but never rewrites.  They are grouped
here because they share a fate as well as a position: each wraps Cube-era
tooling behind a step whose *artifact* outlives Cube — see the retirement
warning in each module's docstring for what to delete versus re-implement
when the engine goes.

- :mod:`~tm1.steps.build.highway_networks` — tolls.csv -> tolls.dbf (native),
  then SetTolls/SetHovXferPenalties/CreateFiveHighwayNetworks as-is.
- :mod:`~tm1.steps.build.nonmotorized_skims` — CreateNonMotorizedNetwork +
  NonMotorizedSkims as-is -> ``skims/nonmotskm.tpp``.
- :mod:`~tm1.steps.build.transit_lines` — per-period ``transitOriginal{P}.lin``,
  replacing transitDwellAccess.py's Simple mode (and its NetworkWrangler dependency).
- :mod:`~tm1.steps.build.hsr_trips` — high-speed-rail trip tables interpolated to
  the model year, replacing HsrTripGeneration.job.
"""

from pathlib import Path


def resolve_path(
    step_cfg: dict, cfg: dict, key: str, *default_parts: str
) -> Path:
    """A step's path setting, falling back to ``run_dir`` plus *default_parts*.

    ``run_dir`` is consulted only when *key* is absent, so a step whose paths
    are all given explicitly needs no project directory at all -- which is what
    makes these steps testable against a scratch directory.
    """
    explicit = step_cfg.get(key)
    if explicit:
        return Path(explicit)
    run_dir = step_cfg.get("run_dir") or cfg.get("run_dir")
    if not run_dir:
        msg = f"set `{key}`, or `run_dir` to derive it from"
        raise KeyError(msg)
    return Path(run_dir, *default_parts)
