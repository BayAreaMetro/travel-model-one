import argparse
import logging
import time
from pathlib import Path

from src.utils import setup_logging, load_config, save 
from src.data.observed.caltrans.aadtt import estimate_caltrans_aadtt
from src.data.observed.caltrans.georeference_caltrans_station_counts import georeference_control_stations
from src.data.observed.caltrans.match_stations_to_links import match_stations_to_links
from src.data.observed.caltrans.standardize import standardize_observed_aadtt

logger = logging.getLogger(__name__)

def run_pipeline(config_path: str = "configs/observed/caltrans_2018.yaml") -> None: 
    """
    Execute the full observed data processing pipeline.

    Parameters
    ----------
    config_path : str
        Path to the YAML configuration file.
    """
    log_path = setup_logging(log_dir="data/logs", log_name="observed_data_processing")
    cfg = load_config(config_path)
    t0  = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Starting Caltrans 2018 Data Processing pipeline")
    logger.info("Config: %s", config_path)
    logger.info("=" * 60)

    if log_path:
        logger.info("Log file: %s", log_path)

    output_paths = cfg["outputs"]

    # ── Step 1: Estimates AADTT ─────────────────────────────────────────────
    logger.info("[1/4] Estimates Caltrans AADTT …")
    t1 = time.perf_counter()
    caltrans_aadtt = estimate_caltrans_aadtt(cfg)
    save(caltrans_aadtt, Path(output_paths["caltrans_aadtt"]))
    logger.info("[1/4] Estimates Caltrans AADTT Done in %.1fs", time.perf_counter() - t1)

    # ── Step 2: Georeference Station Locations ────────────────────────────────
    logger.info("[2/4] Georeferencing station locations …")
    t2 = time.perf_counter()
    station_locations = georeference_control_stations(caltrans_aadtt, cfg)
    save(station_locations, Path(output_paths["station_locations_shp"]))
    save(station_locations, Path(output_paths["station_locations_csv"]))
    logger.info("[2/4] Georeferencing station locations Done in %.1fs", time.perf_counter() - t2)

    # ── Step 3: Matching geo-references count station to network links ────────────────────────────────
    logger.info("[3/4] Matching geo-references count station to network links …")
    t3 = time.perf_counter()
    crosswalk = match_stations_to_links(station_locations, cfg)
    save(crosswalk, Path(output_paths["crosswalk"]))
    logger.info("[3/4] Matching geo-references count station to network links Done in %.1fs", time.perf_counter() - t3)

    # ── Step 4: Standarize Observed Output ────────────────────────────────
    logger.info("[4/4] Standarize observed Caltrans AADTT …")
    t4 = time.perf_counter()
    observed= standardize_observed_aadtt(caltrans_aadtt, crosswalk)
    save(observed, Path(output_paths["standardized_observed_aadtt"]))
    logger.info("[4/4] Standarize observed Caltrans AADTT  Done in %.1fs", time.perf_counter() - t4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Caltrans 2018 Data Processing pipeline.")
    parser.add_argument(
        "--config", default="configs/observed/caltrans_2018.yaml",
        help="Path to YAML config file (default: configs/observed/caltrans_2018.yaml)",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
