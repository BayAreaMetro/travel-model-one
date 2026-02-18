import pandas as pd
import numpy as np
import os
import logging
import sys
import yaml
import argparse
from pathlib import Path
try:
    import xlwings as xw
    USE_XLWINGS = True
    xw.App().visible = False
except ImportError:
    from openpyxl import load_workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    USE_XLWINGS = False
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List



class CalibrationConfig:
    """Configuration manager for calibration scripts."""
    
    def __init__(self, config_file: str = None, submodel: str = None):
        self.config = {}
        self.raw_config = {}
        
        # Load config file
        config_file = config_file or 'E:/GitHub/travel-model-one/utilities/calibration/calibration_config.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.raw_config = yaml.safe_load(f)
                self.config = self._substitute_parameters(self.raw_config)
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    def _substitute_parameters(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively substitute parameters in configuration."""
        # Get parameters from general section
        params = config.get('general', {})
        
        def substitute_value(value):
            """Recursively substitute parameters in values."""
            if isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            elif isinstance(value, str) and '{' in value:
                try:
                    return value.format(**params)
                except KeyError as e:
                    self.logger.info(f"Warning: Missing parameter {e} in string: {value}")
                    return value
            else:
                return value
        
        return substitute_value(config)
    
    def get(self, section: str, key: str, fallback: str = None) -> str:
        """Get configuration value (already substituted)."""
        value = self.config.get(section, {}).get(key, fallback)
        return value
    
    def get_path(self, section: str, key: str, fallback: str = None, validate: bool = False) -> str:
        """Get file path from configuration with optional validation."""
        path = self.get(section, key, fallback)
        if validate and path and not os.path.exists(path):
            self.logger.warning(f"Warning: Path does not exist: {path}")
        return path
    
    def get_all_paths(self, section: str, validate: bool = False) -> Dict[str, str]:
        """Get all file paths from a configuration section."""
        section_config = self.config.get(section, {})
        paths = {}
        for key, value in section_config.items():
            if isinstance(value, str) and ('/' in value or '\\' in value or value.endswith('.csv') or value.endswith('.xlsx')):
                paths[key] = value
                if validate and not os.path.exists(value):
                    self.logger.warning(f"Warning: {key} path does not exist: {value}")
        return paths
    
    def getfloat(self, section: str, key: str, fallback: float = None) -> float:
        """Get configuration value as float."""
        value = self.config.get(section, {}).get(key, fallback)
        return float(value) if value is not None else fallback
    
    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """Get configuration value as integer."""
        value = self.config.get(section, {}).get(key, fallback)
        return int(value) if value is not None else fallback
    
    def get_county_lookup(self) -> dict:
        """Get county lookup dictionary mapping county ID to county name."""
        if 'counties' not in self.config:
            # Default county lookup
            return {
                1: "San Francisco",
                2: "San Mateo",
                3: "Santa Clara",
                4: "Alameda",
                5: "Contra Costa",
                6: "Solano",
                7: "Napa",
                8: "Sonoma",
                9: "Marin"
            }
        
        # Convert config to dictionary
        return {int(county_id): name for county_id, name in self.config['counties'].items()}
    
    def get_submodel_config(self, submodel: str) -> Dict[str, str]:
        """Get configuration for specific submodel."""
        section_name = f"calibration_{submodel}"
        if section_name not in self.config:
            raise ValueError(f"No configuration found for submodel: {submodel}")
        
        return self.config[section_name]


class CalibrationBase(ABC):
    """Base class for calibration processing."""
    
    def __init__(self, submodel: str, config_file: str = None):
        self.config = CalibrationConfig(config_file, submodel)
        self.submodel = submodel
        self.submodel_config = self.config.get_submodel_config(submodel)
        
        # Set up paths
        self.target_dir = self.config.get('general', 'target_dir')
        self.output_dir = f"{self.target_dir}/Output_{self.config.get('general', 'calib_iter')}"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.sampleshare = self.config.getfloat('general', 'sampleshare', 1.0)
        
        # Load shared data resources
        self.county_lookup = self.config.get_county_lookup()
        
        # Set up logging
        self._setup_logging()
       
        # Print configuration
        self._print_config()
    
    def _setup_logging(self):
        """Set up logging configuration for calibration script"""
        
        # Create logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers if called multiple times
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Stop messages from bubbling up to the root logger
        self.logger.propagate = False

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (writes to log file)
        log_file = os.path.join(self.output_dir, 'calibration.log')
        file_handler = logging.FileHandler(log_file, mode='a')  # 'w' overwrites, 'a' appends
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.info(f"Logging to: {log_file}")

    def _print_config(self):
        """Print configuration summary."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nCONFIGURATION SUMMARY\n{sep}")
        self.logger.info(f"Submodel: {self.submodel} - {self.submodel_config['name']}")
        self.logger.info(f"TARGET_DIR  = {self.target_dir}")
        self.logger.info(f"ITER        = {self.config.get('general', 'iter')}")
        self.logger.info(f"SAMPLESHARE = {self.sampleshare}")
        self.logger.info(f"CALIB_ITER  = {self.config.get('general', 'calib_iter')}")
        self.logger.info(f"EXCEL_WORKBOOK = {self.submodel_config.get('workbook_template')}")

    def setup_workbook(self):
        """Set up Excel workbook paths and load template."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nWORKBOOK SETUP\n{sep}")
        workbook_template = self.submodel_config.get('workbook_template')
        
        # Skip if no template specified
        if not workbook_template:
            self.calib_workbook = None
            self.modeldata_sheet = None
            return
        
        submodel_name = self.submodel_config['name']
        
        workbook_base = self.config.get('general', 'workbook_base_path', 
                                       'M:/Development/Travel Model One/Calibration/Version 1.7')
        
        self.workbook_path = f"{workbook_base}/{self.submodel} {submodel_name}/{workbook_template}.xlsx"
        self.workbook_temp = self.workbook_path.replace('.xlsx', '_temp.xlsx')
        self.workbook_blank = str(Path(self.config.get('general', 'code_dir')) / "workbook_templates" / f"{workbook_template}_blank.xlsx")
        
        try: 
            self.logger.info(f"Loading Excel workbook from {self.workbook_blank}...")
            self.calib_workbook = xw.Book(self.workbook_blank)
            self.modeldata_sheet = self.calib_workbook.sheets['modeldata']
        except Exception as e:
            self.logger.warning(f"Skipping Excel workbook: {e}")
            self.calib_workbook = None
            self.modeldata_sheet = None
    

    def write_dataframe_to_sheet(self, df: pd.DataFrame, start_row: int, start_col: int, sheet_name: str ="modeldata",
                                source_row: int = None, source_col: int = None, source_text: str = ""):
        """Write DataFrame to Excel sheet with optional source annotation."""
        if not self.calib_workbook:
            self.logger.warning(f"Warning: Calibration Workbook does not exist")
            return

        try:
            sheet = self.calib_workbook.sheets[sheet_name]
            
            # Write headers
            sheet.range((start_row, start_col)).value = df.columns.tolist()
            
            # Write data without index
            sheet.range((start_row + 1, start_col)).value = df.values

            if source_row and source_col and source_text:
                sheet.range((source_row, source_col)).value = source_text
                
        except Exception as e:
            self.logger.warning(f"Warning: Could not write to Excel sheet: {e}")
    
    def save_workbook(self):
        """Save the Excel workbook."""
        self.logger.info(self.calib_workbook)
        if self.calib_workbook:
            try:
                self.calib_workbook.save(self.workbook_temp)
                self.logger.info(f"Wrote {self.workbook_temp}")
                self.calib_workbook.close()
            except Exception as e:
                self.logger.info(f"Warning: Could not save Excel workbook: {e}")
                self.calib_workbook.close()
        else:
            self.logger.info("Did not save workbook")
    
    @abstractmethod
    def process_data(self) -> Dict[str, pd.DataFrame]:
        """Process the calibration data. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def validate_outputs(self, results):
        """Validate the process data. Must be implemented by subclasses"""
        pass

    @abstractmethod
    def generate_outputs(self, results: Dict[str, pd.DataFrame]):
        """Generate output files and Excel updates. Must be implemented by subclasses."""
        pass
    
    def run(self):
        """Execute the complete calibration process."""
        try:
            results = self.process_data()
            self.validate_outputs(results)
            self.setup_workbook()
            self.generate_outputs(results)
            self.save_workbook()
        except Exception as e:
            self.logger.info(f"Error during calibration processing: {e}")
            raise


def add_county_info(df: pd.DataFrame, taz_data: pd.DataFrame, 
                   county_lookup: dict, taz_col: str = 'TAZ',
                   county_col_name: str = 'COUNTY',
                   county_name_col: str = 'county_name') -> pd.DataFrame:
    """
    Add county information to a DataFrame based on TAZ.
    
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
    taz_county = taz_data[['ZONE', 'COUNTY']].rename(columns={'ZONE': taz_col})
    df = df.merge(taz_county, on=taz_col, how='left')
    
    # Add county name
    df[county_name_col] = df['COUNTY'].map(county_lookup)
    
    # Rename COUNTY column if specified
    if county_col_name != 'COUNTY':
        df = df.rename(columns={'COUNTY': county_col_name})
    
    return df


def create_histogram_tlfd(data: pd.Series, bins: range = None, sampleshare: float = 1.0, 
                         weights: pd.Series = None) -> pd.DataFrame:
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
        hist, bin_edges = np.histogram(data, bins=bins, weights=weights)
        return pd.DataFrame({
            'distbin': list(bins)[1:],
            'count': hist
        })
    else:
        # Use sampleshare scaling
        hist, bin_edges = np.histogram(data, bins=bins)
        return pd.DataFrame({
            'distbin': list(bins)[1:],
            'count': hist / sampleshare
        })

# def attach_distance_skim() -> pd.DataFrame:
    