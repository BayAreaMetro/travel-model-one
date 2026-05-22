"""Step orchestrator — runs steps declared in scenario_config.yaml.

Each step is a module with a ``run(scenario_dir, cfg, **kwargs)`` function.
"""

import logging
import time
from pathlib import Path

import tm1.steps.convert_skims as convert_skims_step
import tm1.steps.populationsim as populationsim_step
import tm1.steps.prepare_survey as prepare_survey_step
import tm1.steps.setup as setup_step
import tm1.steps.simulate_activitysim as simulate_activitysim_step
import tm1.steps.simulate_ctramp as simulate_ctramp_step
import tm1.steps.summaries.calibration as calibration_step
import tm1.steps.summaries.core as core_step
from tm1 import slack
from tm1.config import load_config, resolve_templates
from tm1.slack import notify

log = logging.getLogger(__name__)


def _fmt_elapsed(seconds: float) -> str:
    """Format elapsed time as human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m:02d}m"


STEPS = {
    "setup": setup_step,
    "convert_skims": convert_skims_step,
    "prepare_survey": prepare_survey_step,
    "populationsim": populationsim_step,
    "simulate_activitysim": simulate_activitysim_step,
    "simulate_ctramp": simulate_ctramp_step,
    "summaries": {
        "core": core_step,
        "calibration": calibration_step,
    },
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
    scenario_dir = Path(scenario_dir).resolve()
    label = f"scenarios/{scenario_dir.name}"

    cfg = resolve_templates(load_config(scenario_dir))

    # Slack level: CLI flag wins, then yaml key, then default "minimal"
    if slack_level is not None:
        slack.level = "verbose" if slack_level is True else slack_level
    else:
        cfg_slack = cfg.get("slack", "minimal")
        slack.level = cfg_slack if isinstance(cfg_slack, str) else "off"

    steps_cfg = cfg.get("steps", {})  # pyright: ignore[reportAttributeAccessIssue]
    if steps is None:
        steps = list(steps_cfg.keys()) or DEFAULT_STEPS  # pyright: ignore[reportAttributeAccessIssue]

    # Gather run parameters for the start notification
    sim_cfg = steps_cfg.get("simulate_activitysim", steps_cfg.get("simulate", {}))
    iterations = kwargs.get("iterations") or sim_cfg.get("iterations", 0)

    # Read merged ActivitySim settings from config chain
    asim_cfg = sim_cfg.get("activitysim", sim_cfg) if sim_cfg else {}
    asim_settings: dict = {}
    base_model_dir = kwargs.get("base_model_dir", scenario_dir.parent.parent)
    for c in reversed(asim_cfg.get("configs", [])):
        p = Path(c) if Path(c).is_absolute() else Path(base_model_dir) / c
        sf = p / "settings.yaml"
        if sf.exists():
            import yaml  # noqa: PLC0415

            with sf.open() as f:
                asim_settings.update(yaml.safe_load(f) or {})

    sample = asim_settings.get("households_sample_size", 0)
    nproc = asim_settings.get("num_processes", 1)
    shadow = asim_settings.get("use_shadow_pricing", False)

    sample_str = "full" if sample == 0 else f"{sample:,} HH"
    header = (
        f":rabbit2: Starting {label}\n"
        f"  • steps: {', '.join(steps)}\n"
        f"  • sample: {sample_str} | processors: {nproc} | "
        f"shadow pricing: {'on' if shadow else 'off'}\n"
        f"  • iterations: {iterations}"
    )
    notify(header)

    t0_total = time.time()

    for step_name in steps:
        entry = STEPS.get(step_name)
        if entry is None:
            msg = f"Unknown step: {step_name!r}"
            raise ValueError(msg)

        # Build list of (display_name, module) — compound steps expand to sub-steps
        if isinstance(entry, dict):
            sub_cfg = steps_cfg.get(step_name, {}) or {}
            run_list = [
                (f"{step_name}.{sub}", mod)
                for sub, mod in entry.items()
                if sub in sub_cfg
            ]
            skipped = [s for s in entry if s not in sub_cfg]
            for s in skipped:
                log.info("Skipping %s.%s (not in config)", step_name, s)
        else:
            run_list = [(step_name, entry)]

        for name, mod in run_list:
            log.info("--- Step: %s ---", name)
            t0_step = time.time()
            try:
                result = mod.run(scenario_dir, cfg, **kwargs)
            except KeyboardInterrupt:
                notify(f":no_entry_sign: {label} cancelled during {name}")
                raise
            except Exception as e:
                notify(f":exclamation: {label} failed at {name}: {e}")
                raise
            elapsed = time.time() - t0_step

            if result == "skipped":
                notify(f"[{label}] {name} already done, skipped")
                log.info("--- Skipped: %s ---", name)
            else:
                elapsed_str = _fmt_elapsed(elapsed)
                notify(f"[{label}] {name} done ({elapsed_str})")
                log.info("--- Done: %s (%s) ---", name, elapsed_str)

    total = time.time() - t0_total
    notify(f"Finished {label} in {_fmt_elapsed(total)} :white_check_mark:")
