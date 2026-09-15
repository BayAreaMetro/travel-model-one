import argparse
import logging
import time

from src.utils import setup_logging, load_config
from src.data.od_projection.prepare_projection_inputs import prepare_inputs
from src.data.od_projection.crosswalk import build_crosswalk
from src.data.od_projection.projection import project_matrices
from src.data.od_projection.format_mtc_output import format_mtc_output
from src.data.od_projection.projection import project_matrices
from src.data.od_projection.trip_generation import internal_gates_generation, get_od_marginals

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
    matrixes_to_project = list(cfg["projection"].get("from_matrices_to_project", data["from_omx"].list_matrices()))

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
    # Zones: This is a TAZ in the CSFTDM that is projected to a TAZ in TM-1-6 with 
    # the crosswalk of step 2 if they fall withing the MTC area. If not, they are 
    # mapped to the closeest gateway in the TM-1/6 model (e.g TAZ 1455 - 1575)

    # Gates: This is node in the CSFTDM that has a position in OD matrix. Nodes that
    #  fall withing the MTC area are assigned to the overlaping MTC 1454 TAZ, all 
    # other nodes are mapped to the closest gateway in the TM-1.6. 

    # To separate 

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
        matrixes_names = matrixes_to_project,
        zone_types = ["internal_gate", "internal_zone"],
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
        matrixes_names = matrixes_to_project, 
        zone_types = ["internal_gate"]
    )

    logger.info("[3/5] Projecting Zones only …")
    for name in data["projected_zones_and_gates"].list_matrices():
        zone_and_gates = np.array(data["projected_zones_and_gates"][name])
        gates =  np.array(data["projected_gates"][name])
        zones = np.maximum(zone_and_gates - gates, 0)
        data["projected_zones_only"][name] = zones

    logger.info("[3/5] Done in %.1fs", time.perf_counter() - t3)

    # ── Step 4: format MTC output files ───────────────────────────
    logger.info("[4/5] Formatting MTC output files …")
    t4 = time.perf_counter()
    format_mtc_output(
        sw_projection=data["projected_zones_and_gates"] , 
        mtc_format_configs=cfg["mtc_format"])
    logger.info("[4/5] Done in %.1fs", time.perf_counter() - t4)


    # ── Step 5: Computing Production and attraction marginal from SW data  ───────────────────────────
    # Production and attraction marginal for internal-internal TAZs, 
    # gateways (internal-external, external-internal and external-external),
    # and special generators (transportation logistic nodes). 

    # These production/attraction vectors are used to re-estimate trip 
    # generation equation in TM1.7 Truck Updates. 

    logger.info("[5/5] Computing Production and attraction marginal from SW data …")
    t5 = time.perf_counter()
    data["zones_generation"] = get_od_marginals(
        matrixes_names = matrixes_to_project,
        source_matrices= data["projected_zones_only"], 
        index_range = (1, 1454) # internal-internal trips
    )
    fpath = Path(cfg["output"]["zones_generation"]) 
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["zones_generation"].to_csv(fpath, index=False)

    data["gateways_generation"] = get_od_marginals(
        matrixes_names = matrixes_to_project,
        source_matrices= data["projected_zones_only"], 
        index_range = (1455, 1475) # internal-external, external-internal, and external-external trips
    )
    fpath = Path(cfg["output"]["gateways_generation"]) 
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["gateways_generation"].to_csv(fpath, index=False)
    
    data["tln_generation"] = internal_gates_generation(
        matrixes_names = matrixes_to_project,
        source_matrices = data["from_omx"],
        crosswalk = data["crosswalk"]
    )

    fpath = Path(cfg["output"]["tln_generation"]) 
    fpath.parent.mkdir(parents=True, exist_ok=True)
    data["tln_generation"].to_csv(fpath, index=False)
    logger.info("[5/5] Done in %.1fs", time.perf_counter() - t5)

    # # ───── END OF PIPELINE ───────────────────────────────────────────────────────

    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1fs", time.perf_counter() - t0)
    data["from_omx"].close()
    data["projected_zones_and_gates"].close()
    data["projected_zones_only"].close()
    data["projected_gates_only"].close()
    # logger.info(
    #     "Projected OMX : %s", cfg["paths"]["output_omx"]
    # )
    # logger.info(
    #     "MTC format    : %s",
    #     cfg["mtc_format"]["output_omx_pattern"].replace("{tod}", "*"),
    # )
    logger.info("=" * 60)


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
