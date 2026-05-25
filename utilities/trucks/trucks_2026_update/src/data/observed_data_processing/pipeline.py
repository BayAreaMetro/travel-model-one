import argparse
import logging
import time
from pathlib import Path

from src.utils import setup_logging, load_config, save 
from src.data.observed_data_processing.aadtt import estimate_caltrans_aadtt, estimate_bata_aadtt
from src.data.observed_data_processing.georeference_caltrans_station_counts import georeference_control_stations
from src.data.observed_data_processing.match_stations_to_links import match_stations_to_links

logger = logging.getLogger(__name__)

def run_pipeline(config_path: str = "configs/observed_data_processing_configs.yaml") -> None: 
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
    logger.info("Starting Observed Data Processing pipeline")
    logger.info("Config: %s", config_path)
    logger.info("=" * 60)

    if log_path:
        logger.info("Log file: %s", log_path)

    data = {}

    output_paths = cfg["outputs"]

    # ── Step 1: Estimates AADTT ─────────────────────────────────────────────
    logger.info("[1a/5] Estimates Caltrans AADTT …")
    t1 = time.perf_counter()
    data["caltrans_aadtt"] = estimate_caltrans_aadtt(cfg)
    save(data["caltrans_aadtt"], Path(output_paths["caltrans_aadtt"]))
    logger.info("[1a/5] Estimates Caltrans AADTT Done in %.1fs", time.perf_counter() - t1)

    logger.info("[1b/5] Estimates BATA AADTT …")
    t1 = time.perf_counter()
    data["bata_aadtt"] = estimate_bata_aadtt(cfg)
    save(data["bata_aadtt"], Path(output_paths["bata_aadtt"]))
    logger.info("[1b/5] Estimates BATA AADTT Done in %.1fs", time.perf_counter() - t1)

    # ── Step 2: Georeference Station Locations ────────────────────────────────
    logger.info("[2/5] Georeferencing station locations …")
    t2 = time.perf_counter()
    station_locations = georeference_control_stations(data["caltrans_aadtt"], cfg)
    save(station_locations, Path(output_paths["station_locations_shp"]))
    save(station_locations, Path(output_paths["station_locations_csv"]))
    logger.info("[2/5] Georeferencing station locations Done in %.1fs", time.perf_counter() - t2)

    # ── Step 3: Matching geo-references count station to network links ────────────────────────────────
    logger.info("[3/5] Matching geo-references count station to network links …")
    t3 = time.perf_counter()
    crosswalk = match_stations_to_links(station_locations, cfg)
    save(crosswalk, Path(output_paths["crosswalk"]))
    logger.info("[3/5] Matching geo-references count station to network links Done in %.1fs", time.perf_counter() - t3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Observed Data Processing pipeline.")
    parser.add_argument(
        "--config", default="configs/observed_data_processing_configs.yaml",
        help="Path to YAML config file (default: configs/observed_data_processing_configs.yaml)",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
