r"""Ablation test runner for ActivitySim.

Runs ActivitySim with models cumulatively enabled in logical groups that mirror
the CTRAMP ablation stages. After each stage, outputs are saved for comparison
with CTRAMP ablation results using the calibration evaluator.

Ablation stages (cumulative):
    1. uwsl          - school_location, workplace_location
    2. pre_tour      - + auto_ownership_simulate, free_parking
    3. cdap          - + cdap_simulate
    4. mandatory     - + mandatory_tour_frequency, mandatory_tour_scheduling,
                         tour_mode_choice_simulate
    5. joint         - + joint_tour_frequency, joint_tour_composition,
                         joint_tour_participation, joint_tour_destination,
                         joint_tour_scheduling
    6. nonmandatory  - + non_mandatory_tour_frequency,
                         non_mandatory_tour_destination,
                         non_mandatory_tour_scheduling
    7. atwork        - + atwork_subtour_frequency, atwork_subtour_destination,
                         atwork_subtour_scheduling, atwork_subtour_mode_choice
    8. stops         - + stop_frequency, trip_purpose, trip_destination,
                         trip_purpose_and_destination, trip_scheduling,
                         trip_mode_choice, write_trip_matrices

Each run is cumulative: stage N includes all models from stages 1..N,
plus the always-required initialization models.

Usage:
    python scripts/dev/ablation_activitysim.py
"""

import logging
import shutil
import socket
import sys
import time
from pathlib import Path

import yaml

from tm1.slack import notify

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (single source of truth for all configuration)
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(r"E:\Tests\tm1a_test")
CTRAMP_PROJECT_DIR = Path(r"E:\Tests\tm1_ctramp_test")
DEFAULT_SAMPLE_RATE = 0.15
DEFAULT_SEED = 42
DEFAULT_NUM_PROCESSES = 40

# ---------------------------------------------------------------------------
# Model lists
# ---------------------------------------------------------------------------

# These always run — they set up data structures, not behavioral choices.
INIT_MODELS: list[str] = [
    "initialize_landuse",
    "initialize_households",
    "compute_accessibility",
]

# Each stage is (name, list_of_models_to_ADD).
# Models are cumulative: stage N runs INIT_MODELS + all models from stages 1..N.
STAGES: list[tuple[str, list[str]]] = [
    ("uwsl", [
        "school_location",
        "workplace_location",
    ]),
    # ("pre_tour", [
    #     "auto_ownership_simulate",
    #     "free_parking",
    # ]),
    # ("cdap", [
    #     "cdap_simulate",
    # ]),
    # ("mandatory", [
    #     "mandatory_tour_frequency",
    #     "mandatory_tour_scheduling",
    #     "tour_mode_choice_simulate",
    # ]),
    # ("joint", [
    #     "joint_tour_frequency",
    #     "joint_tour_composition",
    #     "joint_tour_participation",
    #     "joint_tour_destination",
    #     "joint_tour_scheduling",
    # ]),
    # ("nonmandatory", [
    #     "non_mandatory_tour_frequency",
    #     "non_mandatory_tour_destination",
    #     "non_mandatory_tour_scheduling",
    # ]),
    # ("atwork", [
    #     "atwork_subtour_frequency",
    #     "atwork_subtour_destination",
    #     "atwork_subtour_scheduling",
    #     "atwork_subtour_mode_choice",
    # ]),
    # ("stops", [
    #     "stop_frequency",
    #     "trip_purpose",
    #     "trip_destination",
    #     "trip_purpose_and_destination",
    #     "trip_scheduling",
    #     "trip_mode_choice",
    #     "write_trip_matrices",
    # ]),
]

# ActivitySim output files to capture after each stage.
OUTPUT_PATTERNS: list[str] = [
    "final_households.csv",
    "final_persons.csv",
    "final_tours.csv",
    "final_trips.csv",
    "final_joint_tour_participants.csv",
    "final_land_use.csv",
]

# Mapping: stage name → calibration submodels that become available at that stage.
# Cumulative: stage N runs all submodels from stages 1..N that have data.
STAGE_SUBMODELS: dict[str, list[str]] = {
    "uwsl": ["work_school_location"],
    "pre_tour": ["auto_ownership"],
    "cdap": ["daily_activity_pattern"],
    "mandatory": ["tour_mode_choice", "nonwork_dest_choice"],
    "joint": [],
    "nonmandatory": [],
    "atwork": [],
    "stops": ["trip_mode_choice"],
}


def _count_households(project_dir: Path) -> int:
    """Count rows in the input households CSV (excludes header)."""
    hh_file = project_dir / "data" / "households.csv"
    with hh_file.open() as f:
        return sum(1 for _ in f) - 1  # subtract header


def _build_plan_table(active_stages: list[int]) -> str:
    """Build a bullet list showing cumulative models per stage."""
    lines: list[str] = []
    cumulative: list[str] = list(INIT_MODELS)
    for s in range(1, len(STAGES) + 1):
        name, models = STAGES[s - 1]
        cumulative.extend(models)
        added = ", ".join(models)
        marker = " :point_right:" if s in active_stages else ""
        lines.append(
            f"\u2022 Stage {s} \u2014 *{name}*: +{added} ({len(cumulative)} total){marker}"
        )
    return "\n".join(lines)


def build_models_list(up_to_stage: int) -> list[str]:
    """Build the full models list for ActivitySim up to the given stage."""
    models = list(INIT_MODELS)
    for i in range(up_to_stage):
        _, stage_models = STAGES[i]
        models.extend(stage_models)
    # Always end with write_tables so we get final_*.csv output
    if "write_tables" not in models:
        models.append("write_tables")
    return models


def write_stage_settings(
    output_dir: Path,
    models: list[str],
    *,
    sample_size: int,
    seed: int,
    num_processes: int,
) -> Path:
    """Write a stage-specific settings.yaml override."""
    override_dir = output_dir / "_ablation_configs"
    override_dir.mkdir(parents=True, exist_ok=True)

    # Build multiprocess_steps that match our truncated models list.
    # ActivitySim requires begin tags to be present in the models list.
    mp_steps: list[dict] = [
        {"name": "mp_initialize", "begin": "initialize_landuse"},
    ]
    if "compute_accessibility" in models:
        mp_steps.append({
            "name": "mp_accessibility",
            "begin": "compute_accessibility",
            "slice": {"tables": ["accessibility"], "exclude": True},
        })
    # Find first model after init phase to start the households step
    hh_begin = next(
        (m for m in models if m not in INIT_MODELS and m != "write_tables"),
        None,
    )
    if hh_begin:
        mp_steps.append({
            "name": "mp_households",
            "begin": hh_begin,
            "slice": {"tables": ["households", "persons"]},
        })
    # Summarize step begins at write_tables (always last)
    mp_steps.append({"name": "mp_summarize", "begin": "write_tables"})

    settings = {
        "inherit_settings": True,
        "models": models,
        "households_sample_size": sample_size,
        "rng_base_seed": seed,
        "num_processes": num_processes,
        "multiprocess": num_processes > 1,
        "multiprocess_steps": mp_steps,
        "chunk_size": 0,
        "use_shadow_pricing": False,
        # Disable checkpointing for speed — we write final tables at end
        "checkpointing": False,
        "resume_after": None,
    }

    settings_file = override_dir / "settings.yaml"
    with settings_file.open("w") as f:
        yaml.dump(settings, f, default_flow_style=False, sort_keys=False)

    return override_dir


def collect_outputs(output_dir: Path, stage_output: Path) -> int:
    """Copy ActivitySim output files to the ablation stage directory."""
    stage_output.mkdir(parents=True, exist_ok=True)
    copied = 0
    for pattern in OUTPUT_PATTERNS:
        for f in output_dir.glob(pattern):
            shutil.copy2(f, stage_output / f.name)
            copied += 1

    # Also copy the log
    log_file = output_dir / "activitysim.log"
    if log_file.exists():
        shutil.copy2(log_file, stage_output / "activitysim.log")

    return copied


# Ordered stage names (always complete, regardless of which are commented in STAGES).
ALL_STAGE_NAMES: list[str] = [
    "uwsl", "pre_tour", "cdap", "mandatory",
    "joint", "nonmandatory", "atwork", "stops",
]


def _get_submodels_for_stage(up_to_stage: int) -> list[str]:
    """Return cumulative list of calibration submodels available through this stage."""
    submodels: list[str] = []
    for i in range(up_to_stage):
        name = ALL_STAGE_NAMES[i]
        submodels.extend(STAGE_SUBMODELS.get(name, []))
    return submodels


def run_calibration(
    stage_output: Path,
    data_dir: Path,
    *,
    sample_rate: float,
    ctramp_stage_dir: Path | None = None,
    ctramp_project_dir: Path | None = None,
) -> None:
    """Run calibration summaries comparing ActivitySim vs CTRAMP at this stage."""
    from tm1.steps.summaries.calibration import run as run_calib  # noqa: PLC0415

    stage_num = int(stage_output.name.split("_")[0])

    # --- ActivitySim dataset ---
    has_persons = (stage_output / "final_persons.csv").exists()
    has_households = (stage_output / "final_households.csv").exists()
    has_tours = (stage_output / "final_tours.csv").exists()
    has_trips = (stage_output / "final_trips.csv").exists()

    asim_paths: dict[str, str] = {
        "taz_data": str(data_dir / "land_use.csv"),
        "dist_skim": str(data_dir / "skims.omx"),
    }
    if has_households:
        asim_paths["households"] = str(stage_output / "final_households.csv")
        asim_paths["ao_results"] = str(stage_output / "final_households.csv")
    if has_persons:
        asim_paths["wsloc_results"] = str(stage_output / "final_persons.csv")
        asim_paths["cdap_results"] = str(stage_output / "final_persons.csv")
    if has_tours:
        asim_paths["indiv_tour_data"] = str(stage_output / "final_tours.csv")
        asim_paths["joint_tour_data"] = str(stage_output / "final_tours.csv")
    if has_trips:
        asim_paths["indiv_trip_data"] = str(stage_output / "final_trips.csv")

    datasets: list[dict] = [
        {
            "label": "ActivitySim",
            "format": "activitysim",
            "sampleshare": sample_rate,
            "paths": asim_paths,
        },
    ]

    # --- CTRAMP dataset (for comparison) ---
    if ctramp_stage_dir and ctramp_stage_dir.exists() and ctramp_project_dir:
        ctramp_paths: dict[str, str] = {
            "taz_data": str(ctramp_project_dir / "landuse" / "tazData.csv"),
            "dist_skim": str(ctramp_project_dir / "skims" / "nonmotskm.tpp"),
        }
        # Map CTRAMP output files (iteration 1)
        _ctramp_file_map = {
            "wsloc_results": "wsLocResults_1.csv",
            "ao_results": "aoResults_1.csv",
            "cdap_results": "cdapResults_1.csv",
            "indiv_tour_data": "indivTourData_1.csv",
            "joint_tour_data": "jointTourData_1.csv",
            "indiv_trip_data": "indivTripData_1.csv",
            "joint_trip_data": "jointTripData_1.csv",
            "householdData": "householdData_1.csv",
            "personData": "personData_1.csv",
        }
        for table, fname in _ctramp_file_map.items():
            fpath = ctramp_stage_dir / fname
            if fpath.exists():
                ctramp_paths[table] = str(fpath)
        # Households come from popsyn input
        hh_file = ctramp_project_dir / "popsyn" / "hhFile.csv"
        if hh_file.exists():
            ctramp_paths["households"] = str(hh_file)

        datasets.append({
            "label": "CTRAMP",
            "format": "ctramp",
            "sampleshare": sample_rate,
            "paths": ctramp_paths,
        })

    cfg = {
        "steps": {
            "summaries": {
                "calibration": {
                    "output_dir": str(stage_output / "calibration"),
                    "write_csv": True,
                    "datasets": datasets,
                    "submodels": _get_submodels_for_stage(stage_num),
                },
            },
        },
    }

    submodels = cfg["steps"]["summaries"]["calibration"]["submodels"]
    log.info("Running calibration summaries: %s", submodels)
    run_calib(stage_output, cfg)


def clean_output_dir(output_dir: Path) -> None:
    """Remove output files from previous run."""
    if not output_dir.exists():
        return
    # Remove pipeline state so ActivitySim starts fresh
    pipeline_dir = output_dir / "pipeline.parquetpipeline"
    if pipeline_dir.exists():
        shutil.rmtree(pipeline_dir)
    # Remove final CSVs
    for pattern in OUTPUT_PATTERNS:
        for f in output_dir.glob(pattern):
            f.unlink()
    # Remove log
    log_file = output_dir / "activitysim.log"
    if log_file.exists():
        log_file.unlink()


def run_activitysim(
    project_dir: Path,
    override_config_dir: Path,
    output_dir: Path,
) -> None:
    """Launch ActivitySim subprocess."""
    import subprocess  # noqa: PLC0415

    base_model_dir = project_dir.parent / "GitHub" / "travel-model-one"
    # Fall back to finding it relative to this script
    script_dir = Path(__file__).resolve().parent.parent.parent
    if not base_model_dir.exists():
        base_model_dir = script_dir

    # Config chain: ablation override (highest) → scenario → mp defaults → base
    config_dirs = [
        str(override_config_dir),
        str(base_model_dir / "scenarios" / "base_2023" / "configs"),
        str(base_model_dir / "base-models" / "activity" / "configs_mp"),
        str(base_model_dir / "base-models" / "activity" / "configs"),
    ]

    data_dir = project_dir / "data"

    cmd = [
        sys.executable,
        "-m", "activitysim", "run",
        "-d", str(data_dir),
        "-o", str(output_dir),
    ]
    for c in config_dirs:
        cmd.extend(["-c", c])

    log.info("Running: %s", " ".join(cmd))

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:  # pyright: ignore[reportOptionalIterable]
        sys.stdout.write(line)
    rc = proc.wait()

    if rc != 0:
        msg = f"ActivitySim exited with code {rc}"
        raise RuntimeError(msg)


def run_ablation(  # noqa: PLR0915
    project_dir: Path,
    output_base: Path,
    *,
    sample_rate: float = DEFAULT_SAMPLE_RATE,
    seed: int = DEFAULT_SEED,
    num_processes: int = DEFAULT_NUM_PROCESSES,
    stages: list[int] | None = None,
    ctramp_project_dir: Path | None = None,
) -> None:
    """Run the full ActivitySim ablation sequence."""
    if stages is None:
        stages = list(range(1, len(STAGES) + 1))

    total_hh = _count_households(project_dir)
    sample_size = int(total_hh * sample_rate)
    log.info("Households: %d total, sampling %d (%.0f%%)", total_hh, sample_size, sample_rate * 100)

    stage_names = [STAGES[s - 1][0] for s in stages if 1 <= s <= len(STAGES)]
    label = f"ablation [{','.join(stage_names)}] HH={sample_size:,} ({sample_rate:.0%})"

    plan_text = _build_plan_table(stages)
    log.info("Ablation plan:\n%s", plan_text)
    notify(
        f":microscope: Starting ActivitySim {label} "
        f"on {socket.gethostname()}\n{plan_text}"
    )

    log.info("=" * 60)
    log.info("ACTIVITYSIM ABLATION: %d stages, sample=%d HH", len(stages), sample_size)
    log.info("Project: %s", project_dir)
    log.info("Output:  %s", output_base)
    log.info("=" * 60)

    asim_output_dir = project_dir / "output"
    t_total = time.time()
    any_failed = False

    for stage_num in stages:
        if stage_num < 1 or stage_num > len(STAGES):
            log.error("Invalid stage: %d (valid: 1-%d)", stage_num, len(STAGES))
            continue

        stage_name, stage_models = STAGES[stage_num - 1]
        models = build_models_list(stage_num)

        log.info("")
        log.info("-" * 60)
        log.info(
            "STAGE %d/%d: %s (%d models)",
            stage_num, len(STAGES), stage_name, len(models),
        )
        log.info("  Adding: %s", ", ".join(stage_models))
        log.info("-" * 60)

        # Clean previous outputs
        clean_output_dir(asim_output_dir)

        # Write stage-specific config override
        override_dir = write_stage_settings(
            output_base / f"{stage_num:02d}_{stage_name}",
            models,
            sample_size=sample_size,
            seed=seed,
            num_processes=num_processes,
        )

        t0 = time.time()
        failed = False
        try:
            run_activitysim(project_dir, override_dir, asim_output_dir)
        except Exception:
            failed = True
            any_failed = True
            log.exception("STAGE %d FAILED", stage_num)
            notify(
                f":boom: ActivitySim stage {stage_num} ({stage_name}) crashed. "
                f"'Tis but a scratch!"
            )
        elapsed = time.time() - t0

        # Collect outputs
        stage_output = output_base / f"{stage_num:02d}_{stage_name}"
        n_files = collect_outputs(asim_output_dir, stage_output)
        log.info(
            "Stage %d complete: %.1f min, %d output files saved to %s",
            stage_num, elapsed / 60, n_files, stage_output,
        )

        # Run calibration summaries (compare with CTRAMP if available)
        if not failed and n_files > 0:
            ctramp_stage = None
            if ctramp_project_dir:
                ctramp_stage = (
                    ctramp_project_dir / "ablation"
                    / f"{stage_num:02d}_{stage_name}"
                )
            try:
                run_calibration(
                    stage_output,
                    project_dir / "data",
                    sample_rate=sample_rate,
                    ctramp_stage_dir=ctramp_stage,
                    ctramp_project_dir=ctramp_project_dir,
                )
            except Exception:
                log.exception(
                    "Calibration summaries failed for stage %d",
                    stage_num,
                )

        if not failed:
            notify(
                f":white_check_mark: ActivitySim stage {stage_num}/{len(STAGES)} "
                f"({stage_name}) done in {elapsed / 60:.1f} min, {n_files} files"
            )

    elapsed_total = (time.time() - t_total) / 60
    log.info("")
    log.info("=" * 60)
    log.info("ABLATION COMPLETE. Results in: %s", output_base)
    log.info("=" * 60)
    if any_failed:
        notify(
            f":warning: ActivitySim {label} finished with failures "
            f"\u2014 {elapsed_total:.1f} min total"
        )
    else:
        notify(
            f":white_check_mark: Finished ActivitySim {label} "
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
        project_dir=PROJECT_DIR,
        output_base=PROJECT_DIR / "ablation",
        sample_rate=DEFAULT_SAMPLE_RATE,
        seed=DEFAULT_SEED,
        ctramp_project_dir=CTRAMP_PROJECT_DIR,
    )
