from pathlib import Path
import argparse
import pandas as pd

from src.models.registry import load_model_specs_from_yaml
from src.models.engine import run_model_suite
from src.utils import setup_logging, load_config

import datetime
import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run regression model suite from YAML specs."
    )

    parser.add_argument(
        "--specs",
        default="configs/model_specs.yaml",
        help="Path to YAML file with model specifications.",
    )

    parser.add_argument(
        "--model-configs",
        default="configs/model_pipeline_configs.yaml",
        help="Path to YAML file with model configuration.",
    )

    # parser.add_argument(
    #     "--geo-cols",
    #     nargs="*",
    #     default=[],
    #     help="Extra columns to include in prediction output (e.g., county district).",
    # )

    # parser.add_argument(
    #     "--agg-cols",
    #     nargs="*",
    #     default=[],
    #     help="Columns to aggregate validation on (e.g., county district).",
    # )

    return parser.parse_args()


def load_data(path: str) -> pd.DataFrame:
    path = Path(path)

    if path.suffix == ".parquet":
        return pd.read_parquet(path)

    if path.suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported file type: {path}")


def main():
    args = parse_args()
    configs = load_config(args.model_configs)

    # Create run-specific output directory
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output = Path(configs.get("output"))
    run_dir = base_output / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Run ID: {run_id}")
    logger.info(f"Output directory: {run_dir}")

    # Copy specs & data for reproducibility
    targets_path = Path(configs["data_sources"]["targets"]["path"])
    features_path = Path(configs["data_sources"]["features"]["path"])
    shutil.copy(args.specs, run_dir / "used_model_specs.yaml")
    shutil.copy(targets_path, run_dir / targets_path.name)
    shutil.copy(features_path, run_dir / features_path.name)

    logger.info("Loading model specs...")
    specs = load_model_specs_from_yaml(args.specs)

    logger.info(f"Loaded {len(specs)} model specs.")

    logger.info("Loading data...")
    features = load_data(features_path)
    targets = load_data(targets_path)
    df = features.merge(
        targets, 
        how="left",
        left_on=configs["data_sources"]["features"]["id"], 
        right_on=configs["data_sources"]["targets"]["id"],
        ) 

    logger.info(f"Data shape: {df.shape}")

    logger.info("Running model suite...")
    outputs = run_model_suite(
        df=df,
        model_specs=specs,
        output_dir=run_dir,
        extra_prediction_cols=configs.get("additional_columns", {}),
        aggregate_group_cols=configs.get("agg_columns", {})
    )

    logger.info("Done.")
    logger.info(f"Outputs written to: {run_dir}")


if __name__ == "__main__":
    main()