"""PopulationSim step (stub).

Uses pre-built synthetic population from the reference run.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run(
    scenario_dir: Path,  # noqa: ARG001
    cfg: dict,  # noqa: ARG001
    **kwargs: object,  # noqa: ARG001
) -> None:
    """Use existing synthetic population (stub)."""
    log.info("PopulationSim: using existing synthetic population (stub)")
