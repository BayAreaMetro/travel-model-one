"""Evaluate ablation stages — run calibration reports for existing output.

Walks the ablation output directory, builds calibration datasets (survey,
ActivitySim, CTRAMP) for each completed stage, and generates HTML reports.

Usage:
    python scripts/migration_validation/evaluate_stages.py
    python scripts/migration_validation/evaluate_stages.py --config other.yaml
"""

import logging
import sys
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "ablation_config.yaml"

ASIM_TABLE_MAP = [
    ("households", "final_households.csv"),
    ("ao_results", "final_households.csv"),
    ("wsloc_results", "final_persons.csv"),
    ("cdap_results", "final_persons.csv"),
    ("indiv_tour_data", "final_tours.csv"),
    ("joint_tour_data", "final_tours.csv"),
    ("indiv_trip_data", "final_trips.csv"),
]


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def get_calibration_submodels(stages: list[dict], up_to: int) -> list[str]:
    subs = []
    for s in stages[:up_to]:
        subs.extend(s.get("calibration_submodels", []))
    return subs


def build_survey_dataset(survey_dir: Path, ctramp_dir: Path, survey_cfg: dict) -> dict | None:
    if not survey_dir.exists():
        return None
    paths = {
        "taz_data": str(ctramp_dir / "landuse" / "tazData.csv"),
        "dist_skim": str(ctramp_dir / "skims" / "nonmotskm.tpp"),
    }
    for table, fname in survey_cfg["files"].items():
        p = survey_dir / fname
        if p.exists():
            paths[table] = str(p)
    return {
        "label": survey_cfg["label"], "format": survey_cfg["format"],
        "weight_col": survey_cfg["weight_col"], "paths": paths,
    }


def build_asim_dataset(stage_output: Path, data_dir: Path, sample_rate: float) -> dict:
    paths: dict[str, str] = {
        "taz_data": str(data_dir / "land_use.csv"),
        "dist_skim": str(data_dir / "skims.omx"),
    }
    for key, fname in ASIM_TABLE_MAP:
        if (stage_output / fname).exists():
            paths[key] = str(stage_output / fname)
    return {"label": "ActivitySim", "format": "activitysim",
            "sampleshare": sample_rate, "paths": paths}


def build_ctramp_dataset(
    ctramp_stage: Path, ctramp_dir: Path,
    ctramp_output_files: dict, sample_rate: float,
) -> dict | None:
    if not ctramp_stage.exists():
        return None
    paths = {
        "taz_data": str(ctramp_dir / "landuse" / "tazData.csv"),
        "dist_skim": str(ctramp_dir / "skims" / "nonmotskm.tpp"),
    }
    for table, fname in ctramp_output_files.items():
        p = ctramp_stage / fname
        if p.exists():
            paths[table] = str(p)
        else:
            log.warning("CTRAMP stage %s missing %s (%s)", ctramp_stage.name, table, fname)
    return {"label": "CTRAMP", "format": "ctramp",
            "sampleshare": sample_rate, "paths": paths}


def evaluate_stage(  # noqa: PLR0913
    stage_output: Path, stage_num: int, stages: list[dict],
    project_dir: Path, ctramp_dir: Path, survey_dir: Path,
    sample_rate: float, survey_cfg: dict,
    ctramp_output_files: dict,
    *,
    output_dir: Path,
) -> None:
    from tm1.steps.summaries.calibration import run as run_calib  # noqa: PLC0415

    datasets: list[dict] = []

    survey_ds = build_survey_dataset(survey_dir, ctramp_dir, survey_cfg)
    if survey_ds:
        datasets.append(survey_ds)

    datasets.append(build_asim_dataset(stage_output, project_dir / "data", sample_rate))

    stage_name = stages[stage_num - 1]["name"]
    ctramp_stage = ctramp_dir / "ablation" / f"{stage_num:02d}_{stage_name}"
    ctramp_ds = build_ctramp_dataset(
        ctramp_stage, ctramp_dir, ctramp_output_files, sample_rate,
    )
    if ctramp_ds:
        datasets.append(ctramp_ds)

    submodels = get_calibration_submodels(stages, stage_num)
    log.info("Stage %d (%s): submodels=%s, datasets=%d",
             stage_num, stage_name, submodels, len(datasets))

    run_cfg = {"steps": {"summaries": {"calibration": {
        "output_dir": str(output_dir),
        "write_csv": False, "datasets": datasets, "submodels": submodels,
    }}}}
    run_calib(stage_output, run_cfg)


def evaluate_stages(cfg: dict) -> None:
    project_dir = Path(cfg["activitysim_project_dir"])
    ctramp_dir = Path(cfg["ctramp_project_dir"])
    survey_dir = Path(cfg["survey_dir"])
    output_base = Path(cfg["output_dir"])
    ablation_dir = project_dir / "ablation"
    stages = cfg["stages"]
    active = cfg["active_stages"]
    sample_rate = cfg["sample_rate"]
    survey_cfg = cfg["survey"]
    ctramp_output_files = cfg["ctramp_output_files"]

    for stage_num in active:
        stage_name = stages[stage_num - 1]["name"]
        stage_dir = ablation_dir / f"{stage_num:02d}_{stage_name}"

        if not (stage_dir / "final_households.csv").exists():
            log.info("Stage %d (%s) has no output — skipping", stage_num, stage_name)
            continue

        stage_output_dir = output_base / f"{stage_num:02d}_{stage_name}"
        try:
            evaluate_stage(
                stage_dir, stage_num, stages,
                project_dir, ctramp_dir, survey_dir,
                sample_rate, survey_cfg,
                ctramp_output_files,
                output_dir=stage_output_dir,
            )
        except Exception:
            log.exception("Evaluation failed for stage %d (%s)", stage_num, stage_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_PATH
    evaluate_stages(load_config(config_path))
