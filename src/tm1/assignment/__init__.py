"""Highway/transit assignment backends.

- :mod:`tm1.assignment.cube` -- the faithful legacy Cube Voyager pipeline, run
  as-is through ``runtpp``.

Entry points are imported from their modules directly rather than re-exported
here, so that using one backend never imports another's dependencies.

The period-placeholder helpers live here because both the demand seam
(:mod:`tm1.steps.assignment`) and the engines that read it need them, and neither
should have to import the other.
"""

#: Placeholders a per-period path pattern may use.  Cube names its matrices
#: ``tripsAM.tpp`` and ActivitySim names its ``trips_am.omx``, so a scenario has to
#: be able to spell either without the engine caring which produced the file.
PERIOD_PLACEHOLDERS: tuple[str, ...] = ("{PERIOD}", "{period}")


def expand_period(pattern: str, period: str) -> str:
    """Substitute *period* into a per-period path pattern.

    ``{PERIOD}`` takes the upper-case form (``AM``), ``{period}`` the lower-case
    one (``am``).
    """
    return pattern.replace("{PERIOD}", period.upper()).replace("{period}", period.lower())


def has_period_placeholder(pattern: str) -> bool:
    """True when *pattern* names one file per time period rather than a single file."""
    return any(placeholder in pattern for placeholder in PERIOD_PLACEHOLDERS)
