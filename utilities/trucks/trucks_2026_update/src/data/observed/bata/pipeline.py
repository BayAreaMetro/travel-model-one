"""BATA 2023 observed truck count processing pipeline.

Processes Bay Area Toll Authority (BATA) toll-plaza axle count data from 2023
into a standardised observed AADTT dataset compatible with model validation.

Steps
-----
1. **AADTT estimation** — filter to 2023, aggregate to TOD periods, map axle
   counts to truck classes, and compute mean daily volumes per plaza / TOD /
   vehicle type.
2. **Standardize** — join with a station-to-link crosswalk, rename columns to
    the shared observed schema, and validate the schema.

Inputs (configured via ``configs/observed/bata_2023.yaml``)
-----------------------------------------------------------
``inputs.bata_2023.path`` : str
    Path to the BATA 2023 Excel workbook.
``inputs.bata_2023.tab`` : str
    Sheet name containing the raw axle counts.
``inputs.crosswalk`` : str
    Path to a CSV mapping BATA plaza IDs to network link IDs (build manually)

Output
------
``outputs.standardized_observed_aadtt`` : str (Parquet)
    Validated observed dataset with columns:
    ``count_location_id``, ``link_id``, ``tod``, ``truck_type_1``,
    ``truck_type_2``, ``type`` (``"observed"``), ``source``
    (``"bata_2023"``), ``quality_flag``, ``volume``.
"""
import argparse
import logging
import time
from pathlib import Path

import pandas as pd

from src.utils import setup_logging, load_config, save 
from src.data.observed.bata.aadtt import estimate_bata_aadtt
from src.data.observed.bata.standardize import standardize_observed_aadtt

logger = logging.getLogger(__name__)

def run_pipeline(config_path: str = "configs/observed/bata_2023.yaml") -> pd.DataFrame:
    """Execute the BATA 2023 observed data processing pipeline.

    Loads raw BATA toll plaza counts, estimates AADTT by plaza / TOD /
    vehicle type, joins to a station-link crosswalk, and saves the
    standardised output to disk.

    Parameters
    ----------
    config_path : str, optional
        Path to the YAML configuration file.
        Default is ``"configs/observed/bata_2023.yaml"``.

    Returns
    -------
    pd.DataFrame
        Validated standardised observed dataset.  See module docstring for
        the full column specification.
    """
    log_path = setup_logging(log_dir="data/logs", log_name="observed_data_processing")
    cfg = load_config(config_path)
    t0  = time.perf_counter()
    logger.info("=" * 60)
    logger.info("Starting Bata 2023 Data Processing pipeline")
    logger.info("Config: %s", config_path)
    logger.info("=" * 60)

    if log_path:
        logger.info("Log file: %s", log_path)

    output_paths = cfg["outputs"]

    # ── Step 1: Estimates AADTT ─────────────────────────────────────────────
    logger.info("[1/2] Estimates Bata AADTT …")
    t1 = time.perf_counter()
    data = pd.read_excel(cfg["inputs"]["bata_2023"]["path"], sheet_name=cfg["inputs"]["bata_2023"]["tab"])
    bata_aadtt = estimate_bata_aadtt(data, cfg)
    logger.info("[1/2] Estimates Bata AADTT Done in %.1fs", time.perf_counter() - t1)

    # ── Step 2: Standarize Observed Output ────────────────────────────────
    logger.info("[2/2] Standarize observed Bata AADTT …")
    t4 = time.perf_counter()
    crosswalk = pd.read_csv(cfg["inputs"]["crosswalk"])
    observed= standardize_observed_aadtt(bata_aadtt, crosswalk)
    save(observed, Path(output_paths["standardized_observed_aadtt"]))
    logger.info("[2/2] Standarize observed Bata AADTT  Done in %.1fs", time.perf_counter() - t4)

    return observed


def main() -> None:
    """Entry point for the BATA 2023 pipeline script.

    Parses ``--config`` from the command line and delegates to
    :func:`run_pipeline`.

    Returns
    -------
    None
    """
    parser = argparse.ArgumentParser(description="Run Bata 2023 Data Processing pipeline.")
    parser.add_argument(
        "--config", default="configs/observed/bata_2023.yaml",
        help="Path to YAML config file (default: configs/observed/bata_2023.yaml)",
    )
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
