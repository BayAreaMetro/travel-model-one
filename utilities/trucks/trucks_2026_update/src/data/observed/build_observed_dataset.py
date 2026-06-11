"""Build the unified observed truck count dataset from Caltrans and BATA sources.

Combines two independent observed-data pipelines into one standardised table
used for model validation and calibration:

* **Caltrans 2018** — permanent count station data aggregated from hourly
  vehicle-class CSVs by district.
* **BATA 2023** — Bay Area Toll Authority toll-plaza axle counts.

Each source pipeline is run independently and produces an output that conforms
to the shared observed schema (see :mod:`src.data.observed.schema`).  The two
outputs are concatenated, re-validated, and saved to a single file.

Inputs (via CLI or defaults)
-----------------------------
``--caltrans-config`` : str
    Path to the Caltrans pipeline YAML config.
    Default: ``configs/observed/caltrans_2018.yaml``.
``--bata-config`` : str
    Path to the BATA pipeline YAML config.
    Default: ``configs/observed/bata_2023.yaml``.
``--output`` : str
    Path where the merged dataset is saved.
    Default: ``data/interim/observed_data/observed_dataset_merged.csv``.

Output
------
A single file (format determined by extension) with columns:
``count_location_id``, ``link_id``, ``tod``, ``truck_type_1``,
``truck_type_2``, ``type``, ``source``, ``quality_flag``, ``volume``.
Sources present: ``caltrans_2018``, ``bata_2023``.
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

from src.utils import setup_logging, save
from src.data.observed.caltrans.pipeline import run_pipeline as run_caltrans_pipeline
from src.data.observed.bata.pipeline import run_pipeline as run_bata_pipeline
from src.data.observed.schema import validate_observed_schema

logger = logging.getLogger(__name__)


def run_pipeline(
    caltrans_config: str,
    bata_config: str,
    output_path: str,
) -> None:
    """Run both source pipelines and merge their outputs into a unified dataset.

    Executes the Caltrans and BATA pipelines sequentially, concatenates the
    two standardised outputs, re-validates the combined schema, and saves the
    result to ``output_path``.

    Parameters
    ----------
    caltrans_config : str
        Path to the Caltrans pipeline YAML configuration file.
    bata_config : str
        Path to the BATA pipeline YAML configuration file.
    output_path : str
        Destination path for the merged dataset.  Format is inferred from
        the file extension (e.g. ``.csv``, ``.parquet``).

    Returns
    -------
    None
    """

    log_path = setup_logging(log_dir="data/logs", log_name="observed_build")

    logger.info("=" * 60)
    logger.info("Building unified observed dataset")
    logger.info("Caltrans config: %s", caltrans_config)
    logger.info("BATA config: %s", bata_config)
    logger.info("Output path: %s", output_path)
    logger.info("=" * 60)


    caltrans_df = run_caltrans_pipeline(caltrans_config)
    bata_df = run_bata_pipeline(bata_config)

    combined = pd.concat([caltrans_df, bata_df], ignore_index=True)
    combined = validate_observed_schema(combined)

    # ── Log summary statistics ────────────────────────────────
    logger.info("Combined dataset summary:")
    logger.info("  Total records: %d", len(combined))
    logger.info("  Unique link_ids: %d", combined["link_id"].nunique())
    logger.info("  Unique count locations: %d", combined["count_location_id"].nunique())
    logger.info("  Truck types 1: %s", sorted(combined["truck_type_1"].unique().tolist()))
    logger.info("  Truck types 2: %s", sorted(combined["truck_type_2"].unique().tolist()))
    logger.info("  Sources: %s", sorted(combined["source"].unique().tolist()))
    logger.info("  TOD periods: %s", sorted(combined["tod"].unique().tolist()))
    logger.info("  Quality flags: %s", sorted(combined["quality_flag"].unique().tolist()))
    logger.info("  Volume range: [%.2f, %.2f]", combined["volume"].min(), combined["volume"].max())

    output_file = Path(output_path)
    save(combined, output_file)

    logger.info("=" * 60)
    logger.info("✅ Successfully saved unified observed dataset to %s", output_file)
    logger.info("=" * 60)


def main() -> None:
    """Entry point for the unified observed dataset build script.

    Parses ``--caltrans-config``, ``--bata-config``, and ``--output`` from
    the command line and delegates to :func:`run_pipeline`.

    Returns
    -------
    None
    """
    parser = argparse.ArgumentParser(
        description="Build unified observed dataset from multiple sources"
    )

    parser.add_argument(
        "--caltrans-config",
        default="configs/observed/caltrans_2018.yaml",
        help="Path to Caltrans pipeline config file",
    )

    parser.add_argument(
        "--bata-config",
        default="configs/observed/bata_2023.yaml",
        help="Path to BATA pipeline config file",
    )

    parser.add_argument(
        "--output",
        default="data/interim/observed_data/observed_dataset_merged.csv",
        help="Path to save combined observed dataset",
    )

    args = parser.parse_args()
    run_pipeline(
        caltrans_config=args.caltrans_config,
        bata_config=args.bata_config,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
