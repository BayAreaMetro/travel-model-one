r"""Ablation test runner for CTRAMP.

Runs the CTRAMP model with components cumulatively enabled in logical groups,
saving outputs from each stage for comparison with ActivitySim.

Ablation stages:
    1. uwsl          - UsualWorkAndSchoolLocationChoice
    2. pre_tour      - + AutoOwnership, FreeParking
    3. cdap          - + CoordinatedDailyActivityPattern
    4. mandatory     - + IndividualMandatoryTour (Freq, DepartureTime, ModeChoice)
    5. joint         - + JointTour (Freq, Location, DepartureTime, ModeChoice)
    6. nonmandatory  - + IndividualNonMandatoryTour (Freq, Loc, Dep, MC)
    7. atwork        - + AtWorkSubTour (Freq, Location, DepartureTime, ModeChoice)
    8. stops         - + StopFrequency, StopLocation (full model)

Each run is cumulative: stage N includes all components from stages 1..N.

Usage:
    python scripts/ablation_ctramp.py --project-dir E:\\Tests\\tm1_ctramp_test
    python scripts/ablation_ctramp.py --project-dir E:\\Tests\\tm1_ctramp_test --stages 1-4
    python scripts/ablation_ctramp.py --project-dir E:\\Tests\\tm1_ctramp_test --stages 5,6,7,8
"""

import logging
import shutil
import sys
import time
from pathlib import Path

from tm1.slack import notify
from tm1.steps.simulate_ctramp import COMPONENTS, run

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (single source of truth for all configuration)
# ---------------------------------------------------------------------------

DEFAULT_HOST_IP = "localhost"
DEFAULT_SAMPLE_RATE = 0.15
DEFAULT_SEED = 42
DEFAULT_ITERATION = 1

# ---------------------------------------------------------------------------
# Ablation stage definitions
# ---------------------------------------------------------------------------

# Each stage is a (name, list_of_components_to_ADD) tuple.
# Components are cumulative: stage N enables all components from stages 1..N.
STAGES: list[tuple[str, list[str]]] = [
    ("uwsl", [
        "UsualWorkAndSchoolLocationChoice",
    ]),
    ("pre_tour", [
        "AutoOwnership",
        "FreeParking",
    ]),
    ("cdap", [
        "CoordinatedDailyActivityPattern",
    ]),
    ("mandatory", [
        "IndividualMandatoryTourFrequency",
        "MandatoryTourDepartureTimeAndDuration",
        "MandatoryTourModeChoice",
    ]),
    ("joint", [
        "JointTourFrequency",
        "JointTourLocationChoice",
        "JointTourDepartureTimeAndDuration",
        "JointTourModeChoice",
    ]),
    ("nonmandatory", [
        "IndividualNonMandatoryTourFrequency",
        "IndividualNonMandatoryTourLocationChoice",
        "IndividualNonMandatoryTourDepartureTimeAndDuration",
        "IndividualNonMandatoryTourModeChoice",
    ]),
    ("atwork", [
        "AtWorkSubTourFrequency",
        "AtWorkSubTourLocationChoice",
        "AtWorkSubTourDepartureTimeAndDuration",
        "AtWorkSubTourModeChoice",
    ]),
    ("stops", [
        "StopFrequency",
        "StopLocation",
    ]),
]

# Output files to capture from main/ after each stage.
# Not all files exist at every stage — we copy whatever is present.
OUTPUT_PATTERNS: list[str] = [
    "wsLocResults_*.csv",
    "aoResults_*.csv",
    "fpResults_*.csv",
    "cdapResults*.csv",
    "indivTourData_*.csv",
    "jointTourData_*.csv",
    "indivTripData_*.csv",
    "jointTripData_*.csv",
    "ShadowPricing_*.csv",
    "householdData_*.csv",
    "personData_*.csv",
]

# Files to clean between runs. ShadowPricing is excluded because UWSL needs
# the warmstart file (ShadowPricing_5.csv) from the previous full model run.
CLEAN_PATTERNS: list[str] = [
    "wsLocResults_*.csv",
    "aoResults_*.csv",
    "fpResults_*.csv",
    "cdapResults*.csv",
    "indivTourData_*.csv",
    "jointTourData_*.csv",
    "indivTripData_*.csv",
    "jointTripData_*.csv",
    "householdData_*.csv",
    "personData_*.csv",
]


def parse_stages(stage_spec: str) -> list[int]:
    """Parse stage specification like '1-4' or '5,6,7,8' into list of 1-based indices."""
    stages = []
    for part in stage_spec.split(","):
        token = part.strip()
        if "-" in token:
            start, end = token.split("-", 1)
            stages.extend(range(int(start), int(end) + 1))
        else:
            stages.append(int(token))
    return sorted(set(stages))


def build_components(up_to_stage: int) -> dict[str, bool]:
    """Build component dict with all components up to (inclusive) the given stage enabled."""
    enabled: set[str] = set()
    for i in range(up_to_stage):
        _, comps = STAGES[i]
        enabled.update(comps)
    return {c: (c in enabled) for c in COMPONENTS}


def collect_outputs(project_dir: Path, output_dir: Path) -> int:
    """Copy output files from project main/ to the ablation output directory."""
    main_dir = project_dir / "main"
    if not main_dir.exists():
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for pattern in OUTPUT_PATTERNS:
        for f in main_dir.glob(pattern):
            shutil.copy2(f, output_dir / f.name)
            copied += 1

    # Also copy logs for debugging
    logs_src = project_dir / "logs"
    logs_dst = output_dir / "logs"
    if logs_src.exists():
        logs_dst.mkdir(exist_ok=True)
        for f in logs_src.glob("*.log"):
            if f.stat().st_size > 0:
                shutil.copy2(f, logs_dst / f.name)

    return copied


def clean_outputs(project_dir: Path) -> None:
    """Remove output files from main/ before a fresh run."""
    main_dir = project_dir / "main"
    if not main_dir.exists():
        return
    for pattern in CLEAN_PATTERNS:
        for f in main_dir.glob(pattern):
            f.unlink()

    # Clear logs for clean tailing
    logs_dir = project_dir / "logs"
    if logs_dir.exists():
        for f in logs_dir.glob("*.log"):
            f.write_text("")


def _build_plan_table(active_stages: list[int]) -> str:
    """Build a formatted ablation plan showing cumulative components per stage."""
    lines = ["Stage | Name             | + Added this stage"]
    lines.append("------+------------------+--------------------------------------------")
    cumulative: list[str] = []
    for s in range(1, len(STAGES) + 1):
        name, comps = STAGES[s - 1]
        cumulative.extend(comps)
        added = ", ".join(comps)
        marker = " *" if s in active_stages else ""
        lines.append(f"  {s}   | {name:<16} | +{added} (={len(cumulative)} total){marker}")
    return "\n".join(lines)


def run_ablation(
    project_dir: Path,
    output_base: Path,
    *,
    host_ip: str = DEFAULT_HOST_IP,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    seed: int = DEFAULT_SEED,
    stages: list[int] | None = None,
    slack: bool = True,
) -> None:
    """Run the full ablation sequence."""
    if stages is None:
        stages = list(range(1, len(STAGES) + 1))

    stage_names = [STAGES[s - 1][0] for s in stages if 1 <= s <= len(STAGES)]
    label = f"ablation [{','.join(stage_names)}] sample={sample_rate}"

    plan_text = _build_plan_table(stages)
    log.info("Ablation plan:\n%s", plan_text)
    if slack:
        notify(
            f":test_tube: Starting {label} with python (Yes python!)\n```\n{plan_text}\n```"
        )

    log.info("=" * 60)
    log.info("CTRAMP ABLATION: %d stages, sample_rate=%.2f", len(stages), sample_rate)
    log.info("Project: %s", project_dir)
    log.info("Output:  %s", output_base)
    log.info("=" * 60)

    t_total = time.time()

    for stage_num in stages:
        if stage_num < 1 or stage_num > len(STAGES):
            log.error("Invalid stage number: %d (valid: 1-%d)", stage_num, len(STAGES))
            continue

        stage_name, stage_comps = STAGES[stage_num - 1]
        components = build_components(stage_num)
        enabled_count = sum(1 for v in components.values() if v)

        log.info("")
        log.info("-" * 60)
        log.info("STAGE %d/%d: %s (%d components enabled)",
                 stage_num, len(STAGES), stage_name, enabled_count)
        log.info("  Adding: %s", ", ".join(stage_comps))
        log.info("-" * 60)

        # Clean previous outputs
        clean_outputs(project_dir)

        # Build config
        cfg = {
            "steps": {
                "simulate_ctramp": {
                    "project_dir": str(project_dir),
                    "host_ip": host_ip,
                    "iteration": DEFAULT_ITERATION,
                    "sample_rate": sample_rate,
                    "seed": seed,
                    "components": components,
                }
            }
        }

        t0 = time.time()
        failed = False
        try:
            run(project_dir, cfg)
        except Exception:
            failed = True
            log.exception("STAGE %d FAILED", stage_num)
            if slack:
                notify(
                    f":boom: Stage {stage_num} ({stage_name}) just failed. "
                    f"Java giveth, Java taketh away."
                )
            # Still try to collect whatever outputs were produced
        elapsed = time.time() - t0

        # Collect outputs
        stage_output = output_base / f"{stage_num:02d}_{stage_name}"
        n_files = collect_outputs(project_dir, stage_output)
        log.info("Stage %d complete: %.1f min, %d output files saved to %s",
                 stage_num, elapsed / 60, n_files, stage_output)

        if not failed and slack:
            notify(
                f":white_check_mark: Stage {stage_num}/{len(STAGES)} ({stage_name}) "
                f"done in {elapsed / 60:.1f} min, {n_files} files"
            )

    elapsed_total = (time.time() - t_total) / 60
    log.info("")
    log.info("=" * 60)
    log.info("ABLATION COMPLETE. Results in: %s", output_base)
    log.info("=" * 60)
    if slack:
        notify(
            f":white_check_mark: Finished {label}, much rejoicing! "
            f"\u2014 {elapsed_total:.1f} min total"
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    run_ablation(
        project_dir=Path(r"E:\Tests\tm1_ctramp_test"),
        output_base=Path(r"E:\Tests\tm1_ctramp_test\ablation"),
        sample_rate=DEFAULT_SAMPLE_RATE,
        seed=DEFAULT_SEED,
        slack=True,
    )
