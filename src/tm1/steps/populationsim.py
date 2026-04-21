"""PopulationSim step (stub).

Uses pre-built synthetic population from the reference run.
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run(scenario_dir: Path, cfg: dict, **kwargs):
    log.info("PopulationSim: using existing synthetic population (stub)")
