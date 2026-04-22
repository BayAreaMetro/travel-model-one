"""Core summaries step: shim ActivitySim outputs for legacy R CoreSummaries.

Creates the CTRAMP-compatible directory layout that CoreSummaries.R expects,
maps ActivitySim outputs to CTRAMP CSV format, and invokes Rscript.

Expected layout under ``work_dir`` (= TARGET_DIR for R):

    work_dir/
        popsyn/hhFile.csv, personFile.csv
        landuse/tazData.csv
        main/householdData_{iter}.csv, personData_{iter}.csv,
             indivTourData_{iter}.csv, jointTourData_{iter}.csv,
             indivTripData_{iter}.csv, jointTripData_{iter}.csv,
             wsLocResults_{iter}.csv
        database/{Cost,Time,Distance,ActiveTime}SkimsDatabase{EA,AM,MD,PM,EV}.csv
        ctramp/scripts/block/hwyParam.block, trnParam.block
        core_summaries/  (output)
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from tm1.steps.ctramp_output import export_ctramp_csvs

log = logging.getLogger(__name__)

_SKIM_DB_PREFIXES = (
    "CostSkimsDatabase",
    "TimeSkimsDatabase",
    "DistanceSkimsDatabase",
    "ActiveTimeSkimsDatabase",
)
_PERIODS = ("EA", "AM", "MD", "PM", "EV")


def run(scenario_dir: Path, cfg: dict, **kwargs: object) -> None:  # noqa: C901, PLR0912, PLR0915
    """Build CTRAMP layout and run R CoreSummaries."""
    # --- Config stuffs ---
    base_model_dir = kwargs.get("base_model_dir", scenario_dir.parent.parent)
    step_cfg = cfg.get("steps", {}).get("core_summaries", {}) or {}
    sim_cfg = cfg.get("steps", {}).get("simulate", {}) or {}
    asim_cfg = sim_cfg.get("activitysim", sim_cfg)  # nested or flat

    # --- Paths stuffs ---
    output_dir = Path(asim_cfg.get("output_dir", scenario_dir / "output"))
    data_dir = Path(asim_cfg.get("data_dir", scenario_dir / "data"))
    reference_run = cfg.get("reference_run", "")
    work_dir = Path(step_cfg.get("work_dir", output_dir.parent / "summarize"))
    r_script = base_model_dir / "model-files" / "scripts" / "core_summaries" / "CoreSummaries.R"

    # ITER tells R which iteration's output files to read (e.g. householdData_3.csv).
    # With iterations=0 (single run, no feedback), we label outputs as iteration 1.
    iterations = sim_cfg.get("iterations", 0)
    iter_label = str(max(iterations, 1))

    log.info("Core summaries: building CTRAMP layout in %s", work_dir)

    # --- Create directory skeleton ---
    for sub in (
        "main",
        "popsyn",
        "landuse",
        "database",
        "ctramp/scripts/block",
        "core_summaries",
        "updated_output",
    ):
        (work_dir / sub).mkdir(parents=True, exist_ok=True)

    # --- Copy popsyn + landuse from ActivitySim data dir ---
    for src, dest in [
        (data_dir / "households.csv", work_dir / "popsyn" / "hhFile.csv"),
        (data_dir / "persons.csv", work_dir / "popsyn" / "personFile.csv"),
        (data_dir / "land_use.csv", work_dir / "landuse" / "tazData.csv"),
    ]:
        if not dest.exists() and src.exists():
            shutil.copy2(src, dest)
            log.info("  Copied %s -> %s", src.name, dest.name)

    # --- Copy skim database CSVs from reference run ---
    # TODO: This could eventually be deprecated when we move away from R and can just read directly
    if reference_run:
        ref_db = Path(reference_run) / "database"
        dest_db = work_dir / "database"
        for prefix in _SKIM_DB_PREFIXES:
            for period in _PERIODS:
                name = f"{prefix}{period}.csv"
                src = ref_db / name
                dest = dest_db / name
                if not dest.exists() and src.exists():
                    shutil.copy2(src, dest)
                    log.info("  Copied skim DB: %s", name)
                elif not src.exists():
                    log.warning("  Missing skim DB in reference run: %s", src)
                else:
                    log.info("  Skim DB already exists: %s", dest.name)

        # --- Copy param blocks from reference run ---
        ref_block = Path(reference_run) / "ctramp" / "scripts" / "block"
        dest_block = work_dir / "ctramp" / "scripts" / "block"
        for name in ("hwyParam.block", "trnParam.block"):
            src = ref_block / name
            dest = dest_block / name
            if not dest.exists() and src.exists():
                shutil.copy2(src, dest)
                log.info("  Copied %s", name)
            elif not src.exists():
                log.warning("  Missing param block in reference run: %s", src)
            else:
                log.info("  Param block already exists: %s", dest.name)

    # --- Map ActivitySim outputs to CTRAMP CSVs ---
    tours_csv = output_dir / "final_tours.csv"
    if not tours_csv.exists():
        log.warning("No ActivitySim output at %s — skipping R summaries", tours_csv)
        return

    export_ctramp_csvs(output_dir, work_dir, iter_label)

    # --- Invoke CoreSummaries.R ---
    r_home = os.environ.get("R_HOME", "")
    if not r_home:
        log.warning("R_HOME not set — cannot run CoreSummaries.R")
        return

    rscript = Path(r_home) / "bin" / "x64" / "Rscript.exe"
    if not rscript.exists():
        log.warning("Rscript not found at %s", rscript)
        return

    # Build environment for R subprocess
    r_env = {
        **os.environ,
        "TARGET_DIR": str(work_dir),
        "ITER": iter_label,
        "SAMPLESHARE": "1.00",
    }

    # Point R library path to the project renv library so packages are found
    renv_lib = base_model_dir / "renv" / "library"
    r_libs_dirs = sorted(renv_lib.glob("*/x86_64-w64-mingw32")) if renv_lib.exists() else []
    if r_libs_dirs:
        r_libs = str(r_libs_dirs[0])
        r_env["R_LIBS"] = r_libs
        r_env["R_LIBS_USER"] = r_libs
        r_env["R_LIBS_SITE"] = r_libs
        log.info("Using renv library: %s", r_libs)
    else:
        log.warning("No renv library found at %s — using system R libraries", renv_lib)

    log.info("Running CoreSummaries.R ...")
    proc = subprocess.Popen(  # noqa: S603
        [str(rscript), "--vanilla", str(r_script)],
        env=r_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        log.info("[R] %s", line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        msg = f"CoreSummaries.R failed with exit code {proc.returncode}"
        raise RuntimeError(msg)
    log.info("CoreSummaries.R complete")
