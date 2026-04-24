"""Calibration framework: config management and base class for calibration submodels."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .calibration_data_models import CTRAMPCounty

logger = logging.getLogger(__name__)

try:
    import xlwings as xw

    USE_XLWINGS = True
except ImportError:
    USE_XLWINGS = False


class CalibrationConfig:
    """Configuration manager for calibration scripts."""

    def __init__(
        self,
        config_file: str | None = None,
        _submodel: str | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Load calibration config from *config_file*, or accept a pre-loaded *config* dict."""
        self.config: dict[str, Any] = {}
        self.raw_config: dict[str, Any] = {}

        if config is not None:
            # Accept a pre-loaded dict (e.g. from scenario_config.yaml)
            self.raw_config = dict(config)
            self._apply_env_overrides()
            self.config = self._substitute_parameters(self.raw_config)
        else:
            # Load from file
            config_path = (
                Path(config_file)
                if config_file
                else Path(__file__).parent / "calibration_config.yaml"
            )
            if config_path.exists():
                with config_path.open() as f:
                    self.raw_config = yaml.safe_load(f)
                    self._apply_env_overrides()
                    self.config = self._substitute_parameters(self.raw_config)
            else:
                msg = f"Configuration file not found: {config_path}"
                raise FileNotFoundError(msg)

    def _apply_env_overrides(self) -> None:
        """Override selected general config values from batch environment variables."""
        general = self.raw_config.setdefault("general", {})
        env_to_key = {
            "TARGET_DIR": "target_dir",
            "CODE_DIR": "code_dir",
            "CALIB_ITER": "calib_iter",
            "ITER": "iter",
            "MODEL_DIR": "model_dir",
            "WORKBOOK_BASE_PATH": "workbook_base_path",
        }

        for env_name, config_key in env_to_key.items():
            env_val = os.getenv(env_name)
            if env_val:
                if config_key.endswith(("_dir", "_path")):
                    general[config_key] = Path(env_val).as_posix()
                else:
                    general[config_key] = env_val

    def _substitute_parameters(self, config: dict[str, Any]) -> dict[str, Any]:
        """Recursively substitute parameters in configuration."""
        # Get parameters from general section
        params = config.get("general", {})

        def substitute_value(value: object) -> object:
            """Recursively substitute parameters in values."""
            if isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [substitute_value(item) for item in value]
            if isinstance(value, str) and "{" in value:
                try:
                    return value.format(**params)
                except KeyError as e:
                    logger.info("Missing parameter %s in string: %s", e, value)
                    return value
            return value

        return substitute_value(config)

    def get(self, section: str, key: str, fallback: str | None = None) -> str:
        """Get configuration value (already substituted)."""
        value = self.config.get(section, {}).get(key, fallback)
        return value

    def get_path(
        self, section: str, key: str, fallback: str | None = None, validate: bool = False
    ) -> str:
        """Get file path from configuration with optional validation."""
        path = self.get(section, key, fallback)
        if validate and path and not Path(path).exists():
            logger.warning("Path does not exist: %s", path)
        return path

    def get_all_paths(self, section: str, validate: bool = False) -> dict[str, str]:
        """Get all file paths from a configuration section."""
        section_config = self.config.get(section, {})
        paths = {}
        for key, value in section_config.items():
            if isinstance(value, str) and (
                "/" in value or "\\" in value or value.endswith((".csv", ".xlsx"))
            ):
                paths[key] = value
                if validate and not Path(value).exists():
                    logger.warning("%s path does not exist: %s", key, value)
        return paths

    def getfloat(self, section: str, key: str, fallback: float | None = None) -> float:
        """Get configuration value as float."""
        value = self.config.get(section, {}).get(key, fallback)
        return float(value) if value is not None else fallback

    def getint(self, section: str, key: str, fallback: int | None = None) -> int:
        """Get configuration value as integer."""
        value = self.config.get(section, {}).get(key, fallback)
        return int(value) if value is not None else fallback

    def get_county_lookup(self) -> dict:
        """Get county lookup dictionary mapping county ID to county name."""
        # Use canonical county labels from shared CTRAMP codebook.
        return {county.id: county.label for county in CTRAMPCounty}

    def get_submodel_config(self, submodel: str) -> dict[str, str]:
        """Get configuration for specific submodel."""
        section_name = f"calibration_{submodel}"
        if section_name not in self.config:
            msg = f"No configuration found for submodel: {submodel}"
            raise ValueError(msg)

        return self.config[section_name]


class CalibrationBase(ABC):
    """Base class for calibration processing."""

    def __init__(
        self,
        submodel: str,
        config_file: str | None = None,
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize calibration for *submodel* using *config_file* or *config* dict."""
        self.config = CalibrationConfig(config_file, submodel, config=config)
        self.submodel = submodel
        self.submodel_config = self.config.get_submodel_config(submodel)

        # Set up parameters
        self.calib_iter = self.config.get("general", "calib_iter")
        if self.calib_iter == "00":
            self.iter = 3
            self.sampleshare = 0.5
        else:
            self.iter = 1
            self.sampleshare = 0.2

        # Check if using BATS data
        self.bats_data = self.submodel_config.get("bats_data", False)

        # Set up paths
        self.target_dir = self.config.get("general", "target_dir")
        if self.bats_data:
            self.output_dir = f"{self.target_dir}/BATS_Summaries"
        else:
            self.output_dir = f"{self.target_dir}/Output_{self.calib_iter}/calibration"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._setup_logging()

        # Load shared data resources
        self.county_lookup = self.config.get_county_lookup()

        # Print configuration
        self._print_config()

    def _setup_logging(self) -> None:
        """Set up logging configuration for calibration script."""
        # Create logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers if called multiple times
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create formatters
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Stop messages from bubbling up to the root logger
        self.logger.propagate = False

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (writes to log file)
        log_file = Path(self.output_dir) / "calibration.log"
        file_handler = logging.FileHandler(log_file, mode="a")  # 'w' overwrites, 'a' appends
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info("Logging to: %s", log_file)

    def _print_config(self) -> None:
        """Print configuration summary."""
        sep = "=" * 80
        self.logger.info("\n%s\nCONFIGURATION SUMMARY\n%s", sep, sep)
        self.logger.info("Submodel: %s - %s", self.submodel, self.submodel_config["name"])
        self.logger.info("TARGET_DIR  = %s", self.target_dir)
        self.logger.info("ITER        = %s", self.iter)
        self.logger.info("SAMPLESHARE = %s", self.sampleshare)
        self.logger.info("CALIB_ITER  = %s", self.calib_iter)
        self.logger.info("EXCEL_WORKBOOK = %s", self.submodel_config.get("workbook_template"))

    def setup_workbook(self) -> None:
        """Set up Excel workbook paths and load template."""
        sep = "=" * 80
        self.logger.info("\n%s\nWORKBOOK SETUP\n%s", sep, sep)
        workbook_template = self.submodel_config.get("workbook_template")

        # Skip if no template specified
        if not workbook_template:
            self.calib_workbook = None
            self.modeldata_sheet = None
            return

        submodel_name = self.submodel_config["name"]

        workbook_base = self.config.get(
            "general",
            "workbook_base_path",
            "M:/Development/Travel Model One/Calibration/Version 1.7",
        )

        self.workbook_path = (
            f"{workbook_base}/{self.submodel} {submodel_name}/{workbook_template}.xlsx"
        )
        self.workbook_temp = self.workbook_path.replace(".xlsx", "_temp.xlsx")
        self.workbook_iter = self.workbook_path.replace(".xlsx", f"_{self.calib_iter}.xlsx")
        self.workbook_blank = str(
            Path(__file__).parent
            / "workbook_templates"
            / f"{workbook_template}_blank.xlsx"
        )

        workbook_dir = Path(self.workbook_path).parent
        workbook_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("Workbook Output Directory: %s", workbook_dir)

        try:
            self.logger.info("Loading Excel workbook from %s...", self.workbook_blank)
            self.calib_workbook = xw.Book(self.workbook_blank)
            self.calib_workbook.app.visible = False
            self.modeldata_sheet = self.calib_workbook.sheets["modeldata"]
        except Exception as e:
            self.logger.warning("Skipping Excel workbook: %s", e)
            self.calib_workbook = None
            self.modeldata_sheet = None

    def write_dataframe_to_sheet(
        self,
        df: pd.DataFrame,
        start_row: int,
        start_col: int,
        sheet_name: str = "modeldata",
        source_row: int | None = None,
        source_col: int | None = None,
        source_text: str = "",
    ) -> None:
        """Write DataFrame to Excel sheet with optional source annotation."""
        if not self.calib_workbook:
            self.logger.warning("Warning: Calibration Workbook does not exist")
            return

        try:
            sheet = self.calib_workbook.sheets[sheet_name]

            # Write headers
            sheet.range((start_row, start_col)).value = df.columns.tolist()

            # Write data without index
            sheet.range((start_row + 1, start_col)).value = df.to_numpy()

            if source_row and source_col and source_text:
                sheet.range((source_row, source_col)).value = source_text

        except (OSError, KeyError) as e:
            self.logger.warning("Could not write to Excel sheet: %s", e)

    def save_workbook(self) -> None:
        """Save the Excel workbook."""
        self.logger.info("Saving calibration workbook to:")
        self.logger.info("Temp Workbook: %s", self.workbook_temp)
        self.logger.info("Iteration Workbook: %s", self.workbook_iter)
        if self.calib_workbook:
            try:
                self.calib_workbook.save(self.workbook_temp)
                self.calib_workbook.save(self.workbook_iter)
                self.logger.info("Wrote %s", self.workbook_temp)
            except Exception as e:
                self.logger.warning("Could not save Excel workbook: %s", e)
            finally:
                try:
                    self.calib_workbook.close()
                except Exception:
                    pass
        else:
            self.logger.info("Did not save workbook")

    @abstractmethod
    def process_data(self) -> dict[str, pd.DataFrame]:
        """Process the calibration data. Must be implemented by subclasses."""

    @abstractmethod
    def validate_outputs(self, results: dict[str, pd.DataFrame]) -> None:
        """Validate the process data. Must be implemented by subclasses."""

    @abstractmethod
    def generate_outputs(self, results: dict[str, pd.DataFrame]) -> None:
        """Generate output files and Excel updates. Must be implemented by subclasses."""

    def run(self) -> None:
        """Execute the complete calibration process."""
        results = self.process_data()
        self.validate_outputs(results)
        self.setup_workbook()
        self.generate_outputs(results)
        self.save_workbook()


def add_county_info(
    df: pd.DataFrame,
    taz_data: pd.DataFrame,
    county_lookup: dict,
    taz_col: str = "TAZ",
    county_col_name: str = "COUNTY",
    county_name_col: str = "county_name",
) -> pd.DataFrame:
    """Add county information to a DataFrame based on TAZ.

    Args:
        df: DataFrame containing TAZ column
        taz_data: DataFrame with ZONE and COUNTY columns
        county_lookup: Dictionary mapping county ID to county name
        taz_col: Name of TAZ column in df
        county_col_name: Name for output county ID column
        county_name_col: Name for output county name column

    Returns:
        DataFrame with county ID and name columns added

    Example:
        df = add_county_info(results, taz_data, county_lookup, taz_col='HomeTAZ')
    """
    # Merge with TAZ county data
    taz_county = taz_data[["ZONE", "COUNTY"]].rename(columns={"ZONE": taz_col})
    df = df.merge(taz_county, on=taz_col, how="left")

    # Add county name
    df[county_name_col] = df["COUNTY"].map(county_lookup)

    # Rename COUNTY column if specified
    if county_col_name != "COUNTY":
        df = df.rename(columns={"COUNTY": county_col_name})

    return df


def create_histogram_tlfd(
    data: pd.Series,
    bins: range | None = None,
    sampleshare: float = 1.0,
    weights: pd.Series | None = None,
) -> pd.DataFrame:
    """Create trip length frequency distribution histogram.

    Args:
        data: Distance values
        bins: Bin edges for histogram
        sampleshare: Sample share to scale up counts (used when weights not provided)
        weights: Individual weights for each observation (for survey data)

    Returns:
        DataFrame with distbin and count columns
    """
    if bins is None:
        bins = range(151)

    if weights is not None:
        # Use weighted histogram
        hist, _bin_edges = np.histogram(data, bins=bins, weights=weights)
        return pd.DataFrame({"distbin": list(bins)[1:], "count": hist})
    # Use sampleshare scaling
    hist, _bin_edges = np.histogram(data, bins=bins)
    return pd.DataFrame({"distbin": list(bins)[1:], "count": hist / sampleshare})


# def attach_distance_skim() -> pd.DataFrame:
