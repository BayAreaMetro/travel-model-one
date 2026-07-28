"""CTRAMP ablation runner.

Runs CTRAMP with components cumulatively enabled per stage, saving outputs
for comparison with ActivitySim.

Usage:
    python scripts/migration_validation/ablation_ctramp.py
    python scripts/migration_validation/ablation_ctramp.py --config other.yaml
"""

import logging
import shutil
import socket
import sys
import time
from pathlib import Path

import yaml

from tm1.steps.simulate_ctramp import COMPONENTS, run

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "ablation_config.yaml"

OUTPUT_PATTERNS = [
    "wsLocResults_*.csv", "aoResults*.csv", "fpResults*.csv",
    "cdapResults*.csv", "indivTourData_*.csv", "jointTourData_*.csv",
    "indivTripData_*.csv", "jointTripData_*.csv", "ShadowPricing_*.csv",
    "householdData_*.csv", "personData_*.csv",
]

# ShadowPricing excluded — UWSL needs warmstart from previous full run
CLEAN_PATTERNS = [p for p in OUTPUT_PATTERNS if not p.startswith("Shadow")]

DEFAULT_ITERATION = 1


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def build_components(stages: list[dict], up_to: int) -> dict[str, bool]:
    enabled: set[str] = set()
    for s in stages[:up_to]:
        enabled.update(s["ctramp_components"])
    return {c: (c in enabled) for c in COMPONENTS}


def collect_outputs(project_dir: Path, dst: Path) -> int:
    main = project_dir / "main"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for pat in OUTPUT_PATTERNS:
        for f in main.glob(pat):
            shutil.copy2(f, dst / f.name)
            n += 1
    logs_src = project_dir / "logs"
    if logs_src.exists():
        logs_dst = dst / "logs"
        logs_dst.mkdir(exist_ok=True)
        for f in logs_src.glob("*.log"):
            if f.stat().st_size > 0:
                shutil.copy2(f, logs_dst / f.name)
    return n


def clean_outputs(project_dir: Path) -> None:
    main = project_dir / "main"
    if not main.exists():
        return
    for pat in CLEAN_PATTERNS:
        for f in main.glob(pat):
            f.unlink()
    logs = project_dir / "logs"
    if logs.exists():
        for f in logs.glob("*.log"):
            f.write_text("")


def run_ablation(cfg: dict) -> None:
    if cfg.get("slack", False):
        from tm1.slack import notify
    else:
        def notify(msg: str) -> None:
            pass

    project_dir = Path(cfg["ctramp_project_dir"])
    output_base = project_dir / "ablation"
    sample_rate = cfg["sample_rate"]
    seed = cfg["seed"]
    stages = cfg["stages"]
    active = cfg["active_stages"]
    do_shadow_pricing = cfg.get("shadow_pricing", True)
    num_processes = cfg.get("num_processes", 1)

    hh_file = project_dir / "popsyn" / "hhFile.csv"
    total_hh = sum(1 for _ in hh_file.open()) - 1
    hh_count = int(total_hh * sample_rate)

    names = [stages[s - 1]["name"] for s in active]
    label = f"ablation [{','.join(names)}] HH={hh_count:,} ({sample_rate:.0%})"

    notify(f"Starting CTRAMP {label} on {socket.gethostname()} with {num_processes} processes")
    log.info("Active stages: %s", names)
    if not do_shadow_pricing:
        log.info("Shadow pricing DISABLED for this run")

    t_total = time.time()
    any_failed = False

    for stage_num in active:
        stage = stages[stage_num - 1]
        stage_name = stage["name"]
        stage_dir = output_base / f"{stage_num:02d}_{stage_name}"

        # Skip if stage already has output
        if stage_dir.exists() and any(stage_dir.glob("*.csv")):
            log.info("Stage %d (%s) already exists — skipping", stage_num, stage_name)
            notify(f":fast_forward: Stage {stage_num} ({stage_name}) already done — skipping")
            continue

        components = build_components(stages, stage_num)
        enabled_n = sum(v for v in components.values())

        log.info("-" * 60)
        log.info("STAGE %d/%d: %s (%d components)", stage_num, len(stages), stage_name, enabled_n)

        clean_outputs(project_dir)

        run_cfg = {"steps": {"simulate_ctramp": {
            "project_dir": str(project_dir), "host_ip": "localhost",
            "iteration": DEFAULT_ITERATION, "sample_rate": sample_rate,
            "seed": seed, "shadow_pricing": do_shadow_pricing,
            "components": components,
        }}}

        t0 = time.time()
        failed = False
        try:
            run(project_dir, run_cfg)
        except Exception:
            failed = any_failed = True
            log.exception("STAGE %d FAILED", stage_num)

        elapsed = time.time() - t0
        stage_dir = output_base / f"{stage_num:02d}_{stage_name}"
        n = collect_outputs(project_dir, stage_dir)
        log.info("Stage %d: %.1f min, %d files → %s", stage_num, elapsed / 60, n, stage_dir)

        if failed:
            notify(f":boom: CTRAMP stage {stage_num} ({stage_name}) failed "
                   f"after {elapsed / 60:.1f} min — aborting remaining stages")
            break

        notify(f":white_check_mark: CTRAMP stage {stage_num}/{len(stages)} "
               f"({stage_name}) done in {elapsed / 60:.1f} min, {n} files")

    total_min = (time.time() - t_total) / 60
    status = ":warning: finished with failures" if any_failed else ":white_check_mark: Finished"
    notify(f"{status} CTRAMP {label} \u2014 {total_min:.1f} min total")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_PATH
    run_ablation(load_config(config_path))
