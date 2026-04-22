"""Step orchestrator — runs steps declared in scenario_config.yaml.

Each step is a module with a ``run(scenario_dir, cfg, **kwargs)`` function.
"""

import logging
from pathlib import Path

import tm1.steps.calibration_summaries as calibration_summaries_step
import tm1.steps.convert_skims as convert_skims_step
import tm1.steps.core_summaries as core_summaries_step
import tm1.steps.populationsim as populationsim_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate as simulate_step
from tm1 import slack
from tm1.config import load_config, resolve_templates
from tm1.slack import notify

log = logging.getLogger(__name__)

STEPS = {
    "setup": setup_step,
    "convert_skims": convert_skims_step,
    "populationsim": populationsim_step,
    "simulate": simulate_step,
    "core_summaries": core_summaries_step,
    "calibration_summaries": calibration_summaries_step,
}

DEFAULT_STEPS = list(STEPS.keys())


def run_model(
    scenario_dir: Path,
    steps: list[str] | None = None,
    slack_level: str | bool | None = "minimal",
    **kwargs: object,
) -> None:
    """Run a sequence of pipeline steps for a scenario.

    Parameters
    ----------
    scenario_dir : Path
        Path to the scenario directory.
    steps : list[str], optional
        Steps to run.  If None, uses step keys from config or DEFAULT_STEPS.
    slack_level : str
        "false", "minimal", or "verbose".
    **kwargs
        Passed through to each step's ``run()`` function.
        Common: ``base_model_dir``, ``force``.
    """
    slack.level = "verbose" if slack_level is True else (slack_level or "off")
    scenario_dir = Path(scenario_dir).resolve()
    label = scenario_dir.name

    cfg = resolve_templates(load_config(scenario_dir))
    steps_cfg = cfg.get("steps", {})  # pyright: ignore[reportAttributeAccessIssue]
    if steps is None:
        steps = list(steps_cfg.keys()) or DEFAULT_STEPS  # pyright: ignore[reportAttributeAccessIssue]

    # Pass full config to steps so they can read both their own
    # section (cfg["steps"]["<name>"]) and top-level keys like reference_run.
    def on_checkpoint(name: str) -> None:
        notify(f"Completed checkpoint: {name}", verbose_only=True)

    notify(f"Starting {label}: {', '.join(steps)}")

    for step_name in steps:
        mod = STEPS.get(step_name)
        if mod is None:
            msg = f"Unknown step: {step_name!r}"
            raise ValueError(msg)

        notify(f"[{label}] {step_name}")
        log.info("--- Step: %s ---", step_name)

        try:
            mod.run(scenario_dir, cfg, on_checkpoint=on_checkpoint, **kwargs)
        except KeyboardInterrupt:
            notify(f":no_entry_sign: {label} cancelled during {step_name}")
            raise
        except Exception as e:
            notify(f":exclamation: {label} failed at {step_name}: {e}")
            raise

        log.info("--- Done: %s ---", step_name)

    notify(f"Finished {label} :white_check_mark:")
