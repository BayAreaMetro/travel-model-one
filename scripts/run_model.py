"""Quick-launch convenience script for the base_2023 scenario.

For the full CLI, use::

    tm1 run --scenario base_2023
    tm1 run --scenario base_2023 --force-setup --slack minimal
"""

import logging
import sys
from pathlib import Path

from setup_scenario import setup
from tm1.runner import run

_REPO_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(run(
        scenario_dir=_REPO_ROOT / "scenarios" / "base_2023",
        setup_fn=setup,
        base_model_dir=_REPO_ROOT,
        force_setup=False,
        slack_level="minimal",
    ))
