import argparse
import logging
import time

from src.utils import setup_logging, load_config
from src.data.od_projection.prepare_projection_inputs import prepare_inputs
from src.data.od_projection.crosswalk import build_crosswalk
from src.data.od_projection.projection import project_matrices
# from src.data.od_projection.format_mtc_output import format_mtc_output
from src.data.od_projection.projection import project_matrices

import numpy as np
import pandas as pd
import geopandas as gpd
import openmatrix as omx
from pathlib import Path

logger = logging.getLogger(__name__)


def run_pipeline(config_path: str = "configs/od_projection_configs.yaml") -> None:
    """
    Execute the full FROM → TO matrix projection pipeline.

    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    """
    log_path = setup_logging(log_dir="data/logs", log_name="od_projection")
    cfg = load_config(config_path)
    t0 = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Starting matrix projection pipeline")
    logger.info("Config: %s", config_path)
    logger.info("=" * 60)
    
    if log_path:
        logger.info("Log file: %s", log_path)


    # Load data 
    data = {
        "from_shapefile": gpd.read_file(cfg["input"]["from_shapefile"]), 
        "from_network_nodes": gpd.read_file(cfg["input"]["from_network_nodes"]),
        "from_omx": omx.open_file(cfg["input"]["from_omx"], "r"),
        "to_shapefile": gpd.read_file(cfg["input"]["to_shapefile"]), 
        "to_network_nodes": gpd.read_file(cfg["input"]["to_network_nodes"]),
        "tm_land_use": pd.read_csv(cfg["input"]["tm_land_use"])
    }

    output_path = cfg["output"]

    # ── Step 1: Data Preprocessing ─────────────────────────────────────────────────
    logger.info("[1/5] Data Preparation …")
    t1 = time.perf_counter()
    data = prepare_inputs(data, cfg)
    logger.info("[1/5] Done in %.1fs — Data Preparation", time.perf_counter() - t1)

    # ── Step 2: build crosswalk ────────────────────────────────────────────────
    logger.info("[2/5] Building crosswalk …")
    t2 = time.perf_counter()
    data["crosswalk"] = build_crosswalk(
        from_zones = data["from_shapefile"],
        from_gate_nodes = data["from_gate_nodes"],
        to_zones = data["to_shapefile"], 
        to_gate_nodes= data["to_gate_nodes"],
        weights= data["truck_trip_gen_tm16"][["all_trucks_production", "all_trucks_attraction"]], 
        sliver_cfg= cfg["slivers"]
    )
    fpath = Path(output_path["crosswalk"])
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["crosswalk"].to_csv(fpath, index=False)
    logger.info("[2/5] Done in %.1fs", time.perf_counter() - t2)

    # ── Step 3: project matrices ───────────────────────────────────────────────
    logger.info("[3/5] Projecting matrices …")
    t3 = time.perf_counter()
    logger.info("[3/5] Projecting Zones & Gates …")
    data["projected_zones_and_gates"]  = project_matrices(
        source_matrices = data["from_omx"],
        target_matrices = data["projected_zones_and_gates"],
        crosswalk = data["crosswalk"],
        row_weight_col= cfg["projection"]["row_weight"],
        col_weight_col= cfg["projection"]["column_weight"],
        offset = cfg["zones"]["offset"],
        n_from = cfg["zones"]["from_matrix_size"],
        n_to = cfg["zones"]["to_matrix_size"],
        matrixes_names = cfg["projection"]["from_matrices_to_project"], 
        zone_types = ["internal_gate", "internal_zone"],
    )

    logger.info("[3/5] Projecting Zones only …")
    data["projected_zones"]  = project_matrices(
        source_matrices = data["from_omx"],
        target_matrices = data["projected_zones_only"],
        crosswalk = data["crosswalk"],
        row_weight_col= cfg["projection"]["row_weight"],
        col_weight_col= cfg["projection"]["column_weight"],
        offset = cfg["zones"]["offset"],
        n_from = cfg["zones"]["from_matrix_size"],
        n_to = cfg["zones"]["to_matrix_size"],
        matrixes_names = cfg["projection"]["from_matrices_to_project"], 
        zone_types = ["internal_zone"]
    )

    logger.info("[3/5] Projecting Gates only …")
    data["projected_gates"]  = project_matrices(
        source_matrices = data["from_omx"],
        target_matrices = data["projected_gates_only"],
        crosswalk = data["crosswalk"],
        row_weight_col= cfg["projection"]["row_weight"],
        col_weight_col= cfg["projection"]["column_weight"],
        offset = cfg["zones"]["offset"],
        n_from = cfg["zones"]["from_matrix_size"],
        n_to = cfg["zones"]["to_matrix_size"],
        matrixes_names = cfg["projection"]["from_matrices_to_project"], 
        zone_types = ["internal_gate"]
    )

    logger.info("[3/5] Done in %.1fs", time.perf_counter() - t3)

    # 

    # # ── Step 5: format MTC output files ───────────────────────────
    # logger.info("[5/5] Formatting MTC output files …")
    # t5 = time.perf_counter()
    # format_mtc_output(cfg)
    # logger.info("[5/5] Done in %.1fs", time.perf_counter() - t5)

    # # ───── END OF PIPELINE ───────────────────────────────────────────────────────

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1fs", time.perf_counter() - t0)
    # logger.info(
    #     "Projected OMX : %s", cfg["paths"]["output_omx"]
    # )
    # logger.info(
    #     "MTC format    : %s",
    #     cfg["mtc_format"]["output_omx_pattern"].replace("{tod}", "*"),
    # )
    logger.info("=" * 60)


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FROM→TO matrix projection pipeline.")
    parser.add_argument(
        "--config", default="configs/od_projection_configs.yaml",
        help="Path to YAML config file (default: configs/od_projection_configs.yaml)",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
