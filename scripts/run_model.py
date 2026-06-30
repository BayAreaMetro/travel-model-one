"""Quick-launch: run full pipeline for base_2023_activitysim.

For the full CLI, use::

    tm1 run --scenario base_2023_activitysim
    tm1 run --scenario base_2023_activitysim --step activitysim
"""

from pathlib import Path

from tm1 import setup_logging
from tm1.runner import run_model

_REPO_ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    setup_logging()
    run_model(
        scenario_dir=_REPO_ROOT / "scenarios" / "base_2023_activitysim",
        base_model_dir=_REPO_ROOT,
        slack_level=None,
    )
