"""ActivitySim ablation runner.

Runs ActivitySim with models cumulatively enabled per stage, collecting
output CSVs. Calibration reports are generated separately by evaluate_stages.py.

Usage:
    python scripts/migration_validation/ablation_activitysim.py
    python scripts/migration_validation/ablation_activitysim.py --config other.yaml
"""

import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import yaml
from evaluate_stages import evaluate_stages

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "ablation_config.yaml"

INIT_MODELS = ["initialize_landuse", "initialize_households", "compute_accessibility"]

OUTPUT_FILES = [
    "final_households.csv", "final_persons.csv", "final_tours.csv",
    "final_trips.csv", "final_joint_tour_participants.csv", "final_land_use.csv",
]


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def build_models_list(stages: list[dict], up_to: int) -> list[str]:
    models = list(INIT_MODELS)
    for s in stages[:up_to]:
        models.extend(s["activitysim_models"])
    if "write_tables" not in models:
        models.append("write_tables")
    return models


def write_stage_settings(
    stage_dir: Path, models: list[str], *, sample_size: int, seed: int,
    num_processes: int, shadow_pricing: bool = False,
) -> Path:
    cfg_dir = stage_dir / "_ablation_configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    mp_steps = [{"name": "mp_initialize", "begin": "initialize_landuse"}]
    if "compute_accessibility" in models:
        mp_steps.append({
            "name": "mp_accessibility", "begin": "compute_accessibility",
            "slice": {"tables": ["accessibility"], "exclude": True},
        })
    hh_begin = next((m for m in models if m not in INIT_MODELS and m != "write_tables"), None)
    if hh_begin:
        mp_steps.append({
            "name": "mp_households", "begin": hh_begin,
            "slice": {"tables": ["households", "persons"]},
        })
    # write_trip_matrices writes shared OMX files — must run sequentially
    summarize_begin = "write_trip_matrices" if "write_trip_matrices" in models else "write_tables"
    mp_steps.append({"name": "mp_summarize", "begin": summarize_begin})

    settings = {
        "inherit_settings": True,
        "models": models,
        "households_sample_size": sample_size,
        "rng_base_seed": seed,
        "num_processes": num_processes,
        "multiprocess": num_processes > 1,
        "multiprocess_steps": mp_steps,
        "chunk_size": 0,
        "use_shadow_pricing": shadow_pricing,
        "checkpointing": False,
        "resume_after": None,
    }
    (cfg_dir / "settings.yaml").write_text(
        yaml.dump(settings, default_flow_style=False, sort_keys=False),
    )
    return cfg_dir


def _kill_stale_activitysim(output_dir: Path) -> None:
    """Kill leftover activitysim processes whose ``-o`` points at *output_dir*.

    On Windows a crashed subprocess can leave a zombie python.exe that keeps
    log-file handles (e.g. ``settings_checker.log``) locked, blocking the
    next run.  Unix doesn't enforce mandatory file locks, so this is a no-op
    there.
    """
    if sys.platform != "win32":
        return
    try:
        import psutil
    except ImportError:
        return
    our_pid = os.getpid()
    target = str(output_dir.resolve()).lower()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        if proc.info["pid"] == our_pid:
            continue
        try:
            cmdline = proc.info["cmdline"] or []
            # Match: python -m activitysim run … -o <output_dir>
            if "activitysim" not in " ".join(cmdline).lower():
                continue
            for i, arg in enumerate(cmdline):
                if arg == "-o" and i + 1 < len(cmdline):
                    if cmdline[i + 1].lower() == target:
                        log.warning("Killing stale activitysim pid %d", proc.pid)
                        proc.kill()
                        proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def _force_remove(path: Path) -> None:
    """Remove a file, falling back to truncation if a zombie process holds it."""
    try:
        path.unlink()
    except PermissionError:
        import gc
        gc.collect()
        try:
            path.unlink()
        except PermissionError:
            log.warning("Could not delete %s — truncating instead", path)
            path.write_text("")


def clean_output(output_dir: Path) -> None:
    _kill_stale_activitysim(output_dir)
    # Remove all pipeline dirs (main + per-process mp_*-pipeline dirs)
    for pipe in output_dir.glob("*pipeline.parquetpipeline"):
        shutil.rmtree(pipe, ignore_errors=True)
    for pat in OUTPUT_FILES:
        for f in output_dir.glob(pat):
            _force_remove(f)
    # Log / state files that ActivitySim may hold open via FileHandlers
    for name in (
        "activitysim.log", "settings_checker.log", "input_checker.log",
        "mem.csv", "memory_profile.csv", "breadcrumbs.yaml",
    ):
        lf = output_dir / name
        if lf.exists():
            _force_remove(lf)


def run_activitysim(
    project_dir: Path, override_dir: Path, output_dir: Path,
    repo_root: Path, config_dirs: list[str],
) -> None:
    dirs = [str(override_dir)] + [str(repo_root / d) for d in config_dirs]
    cmd = [sys.executable, "-m", "activitysim", "run",
           "-d", str(project_dir / "data"), "-o", str(output_dir)]
    for c in dirs:
        cmd.extend(["-c", c])

    log.info("Running: %s", " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:  # pyright: ignore[reportOptionalIterable]
        sys.stdout.write(line)
    if proc.wait() != 0:
        msg = f"ActivitySim exited with code {proc.returncode}"
        raise RuntimeError(msg)


def collect_outputs(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for pat in OUTPUT_FILES:
        for f in src.glob(pat):
            shutil.copy2(f, dst / f.name)
            n += 1
    log_f = src / "activitysim.log"
    if log_f.exists():
        shutil.copy2(log_f, dst / "activitysim.log")
    return n


def run_ablation(cfg: dict) -> None:
    if cfg.get("slack", False):
        from tm1.slack import notify
    else:
        def notify(msg: str) -> None:
            pass

    project_dir = Path(cfg["activitysim_project_dir"])
    repo_root = Path(cfg["repo_root"])
    config_dirs = cfg["asim_config_dirs"]
    output_base = project_dir / "ablation"
    sample_rate = cfg["sample_rate"]
    seed = cfg["seed"]
    num_processes = cfg["num_processes"]
    stages = cfg["stages"]
    active = cfg["active_stages"]
    do_shadow_pricing = cfg.get("shadow_pricing", False)

    hh_file = project_dir / "data" / "households.csv"
    total_hh = sum(1 for _ in hh_file.open()) - 1
    sample_size = int(total_hh * sample_rate)

    names = [stages[s - 1]["name"] for s in active]
    label = f"ablation [{','.join(names)}] HH={sample_size:,} ({sample_rate:.0%})"

    notify(f"Starting ActivitySim {label} on {socket.gethostname()}")
    log.info("Active stages: %s", names)

    asim_output = project_dir / "output"
    t_total = time.time()
    any_failed = False

    for stage_num in active:
        stage = stages[stage_num - 1]
        stage_name = stage["name"]
        stage_dir = output_base / f"{stage_num:02d}_{stage_name}"

        if (stage_dir / "final_households.csv").exists():
            log.info("Stage %d (%s) already exists — skipping", stage_num, stage_name)
            notify(f":fast_forward: Stage {stage_num} ({stage_name}) already done — skipping")
            continue

        models = build_models_list(stages, stage_num)

        log.info("-" * 60)
        log.info("STAGE %d/%d: %s (%d models)", stage_num, len(stages), stage_name, len(models))

        clean_output(asim_output)

        override_dir = write_stage_settings(
            stage_dir, models, sample_size=sample_size, seed=seed,
            num_processes=num_processes, shadow_pricing=do_shadow_pricing,
        )

        t0 = time.time()
        failed = False
        try:
            run_activitysim(project_dir, override_dir, asim_output, repo_root, config_dirs)
        except Exception:
            failed = any_failed = True
            log.exception("STAGE %d FAILED", stage_num)

        elapsed = time.time() - t0
        n = collect_outputs(asim_output, stage_dir)
        log.info("Stage %d: %.1f min, %d files → %s", stage_num, elapsed / 60, n, stage_dir)

        if failed:
            # Later stages depend on this one — no point continuing.
            notify(f":boom: ActivitySim stage {stage_num} ({stage_name}) failed "
                   f"after {elapsed / 60:.1f} min — aborting remaining stages")
            break

        notify(f":white_check_mark: ActivitySim stage {stage_num}/{len(stages)} "
               f"({stage_name}) done in {elapsed / 60:.1f} min, {n} files")
        
        # Run evaluation for this stage immediately after completion, so that we have results even if later stages fail.
        try:
            evaluate_stages(cfg)
        except Exception:
            log.exception("Evaluation failed for stage %d (%s)", stage_num, stage_name)

    total_min = (time.time() - t_total) / 60
    status = ":warning: finished with failures" if any_failed else ":white_check_mark: Finished"
    notify(f"{status} ActivitySim {label} \u2014 {total_min:.1f} min total")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_PATH
    run_ablation(load_config(config_path))
