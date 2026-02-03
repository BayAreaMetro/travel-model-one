import pandas as pd
import numpy as np
import os
import sys
import yaml
import argparse
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class CalibrationConfig:
    """Configuration manager for calibration scripts."""
    
    def __init__(self, config_file: str = None, submodel: str = None):
        self.config = {}
        
        # Load config file
        config_file = config_file or 'calibration_config.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        
        # Override with environment variables if set
        self._load_env_overrides()
        
        # Override with command line arguments
        self._load_cli_args()
        
        # Set current submodel
        self.submodel = submodel
        
        # Validate and process
        self._validate_config()
        self._substitute_variables()
        
    def _load_env_overrides(self):
        """Override config with environment variables."""
        env_mappings = {
            'TARGET_DIR': ('general', 'target_dir'),
            'ITER': ('general', 'iter'),
            'SAMPLESHARE': ('general', 'sampleshare'),
            'CODE_DIR': ('general', 'code_dir'),
            'CALIB_ITER': ('general', 'calib_iter')
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                if section not in self.config:
                    self.config[section] = {}
                self.config[section][key] = value
    
    def _load_cli_args(self):
        """Override config with command line arguments."""
        parser = argparse.ArgumentParser(add_help=False)  # Don't interfere with main script args
        parser.add_argument('--target-dir')
        parser.add_argument('--iter')
        parser.add_argument('--sampleshare')
        parser.add_argument('--code-dir')
        parser.add_argument('--calib-iter')
        
        args, unknown = parser.parse_known_args()
        
        if 'general' not in self.config:
            self.config['general'] = {}
            
        if args.target_dir:
            self.config['general']['target_dir'] = args.target_dir
        if args.iter:
            self.config['general']['iter'] = args.iter
        if args.sampleshare:
            self.config['general']['sampleshare'] = args.sampleshare
        if args.code_dir:
            self.config['general']['code_dir'] = args.code_dir
        if args.calib_iter:
            self.config['general']['calib_iter'] = args.calib_iter
    
    def _validate_config(self):
        """Validate required configuration values."""
        required = [
            ('general', 'target_dir'),
            ('general', 'iter'),
            ('general', 'code_dir'),
            ('general', 'calib_iter')
        ]
        
        missing = []
        for section, key in required:
            if section not in self.config or key not in self.config[section] or not str(self.config[section][key]).strip():
                missing.append(f"{section}.{key}")
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    def _substitute_variables(self):
        """Substitute variables in config values."""
        substitutions = {
            'target_dir': self.get('general', 'target_dir').replace('\\', '/'),
            'iter': self.get('general', 'iter'),
            'calib_iter': self.get('general', 'calib_iter'),
            'code_dir': self.get('general', 'code_dir').replace('\\', '/')
        }
        
        # Apply substitutions to all sections
        for section_name, section in self.config.items():
            if isinstance(section, dict):
                for key, value in section.items():
                    if isinstance(value, str):
                        try:
                            self.config[section_name][key] = value.format(**substitutions)
                        except (KeyError, ValueError):
                            # Skip if substitution fails
                            pass
    
    def get(self, section: str, key: str, fallback: str = None) -> str:
        """Get configuration value."""
        return self.config.get(section, {}).get(key, fallback)
    
    def getfloat(self, section: str, key: str, fallback: float = None) -> float:
        """Get configuration value as float."""
        value = self.config.get(section, {}).get(key, fallback)
        return float(value) if value is not None else fallback
    
    def getint(self, section: str, key: str, fallback: int = None) -> int:
        """Get configuration value as integer."""
        value = self.config.get(section, {}).get(key, fallback)
        return int(value) if value is not None else fallback
    
    def get_county_lookup(self) -> pd.DataFrame:
        """Get county lookup DataFrame."""
        if 'counties' not in self.config:
            # Default county lookup
            return pd.DataFrame({
                'COUNTY': [1, 2, 3, 4, 5, 6, 7, 8, 9],
                'county_name': ["San Francisco", "San Mateo", "Santa Clara", "Alameda",
                               "Contra Costa", "Solano", "Napa", "Sonoma", "Marin"]
            })
        
        counties = []
        county_names = []
        for county_id, name in self.config['counties'].items():
            counties.append(int(county_id))
            county_names.append(name)
        
        return pd.DataFrame({
            'COUNTY': counties,
            'county_name': county_names
        })
    
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
        self.output_dir = os.path.join(self.target_dir, f"OUTPUT_{self.config.get('general', 'calib_iter')}", "calibration")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.sampleshare = self.config.getfloat('general', 'sampleshare', 1.0)
        
        # Set up Excel workbook
        self._setup_workbook()
        
        # Print configuration
        self._print_config()
    
    def _setup_workbook(self):
        """Set up Excel workbook paths and load template."""
        workbook_template = self.submodel_config['workbook_template']
        submodel_name = self.submodel_config['name']
        
        workbook_base = self.config.get('general', 'workbook_base_path', 
                                       'M:/Development/Travel Model One/Calibration/Version 1.5.2')
        
        self.workbook_path = f"{workbook_base}/{self.submodel} {submodel_name}/{workbook_template}.xlsx"
        self.workbook_temp = self.workbook_path.replace('.xlsx', '_temp.xlsx')
        self.workbook_blank = os.path.join(self.config.get('general', 'code_dir'), 
                                          "workbook_templates", f"{workbook_template}_blank.xlsx")
        
        # Load workbook
        try:
            self.calib_workbook = load_workbook(self.workbook_blank)
            self.modeldata_sheet = self.calib_workbook['modeldata']
        except Exception as e:
            print(f"Warning: Could not load Excel workbook {self.workbook_blank}: {e}")
            self.calib_workbook = None
            self.modeldata_sheet = None
    
    def _print_config(self):
        """Print configuration summary."""
        print(f"Submodel: {self.submodel} - {self.submodel_config['name']}")
        print(f"TARGET_DIR  = {self.target_dir}")
        print(f"ITER        = {self.config.get('general', 'iter')}")
        print(f"SAMPLESHARE = {self.sampleshare}")
        print(f"CALIB_ITER  = {self.config.get('general', 'calib_iter')}")
    
    def save_csv(self, df: pd.DataFrame, filename: str) -> str:
        """Save DataFrame to CSV file."""
        outfile = os.path.join(self.output_dir, filename)
        df.to_csv(outfile, index=False)
        print(f"Wrote {outfile}")
        return outfile
    
    def write_dataframe_to_sheet(self, df: pd.DataFrame, start_row: int, start_col: int, 
                                source_row: int = None, source_col: int = None, source_text: str = ""):
        """Write DataFrame to Excel sheet with optional source annotation."""
        if not self.modeldata_sheet:
            return
        
        try:
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True)):
                for c_idx, value in enumerate(row):
                    self.modeldata_sheet.cell(row=start_row + r_idx, column=start_col + c_idx, value=value)
            
            if source_row and source_col and source_text:
                self.modeldata_sheet.cell(row=source_row, column=source_col).value = source_text
                
        except Exception as e:
            print(f"Warning: Could not write to Excel sheet: {e}")
    
    def save_workbook(self):
        """Save the Excel workbook."""
        if self.calib_workbook:
            try:
                self.calib_workbook.save(self.workbook_temp)
                print(f"Wrote {self.workbook_temp}")
            except Exception as e:
                print(f"Warning: Could not save Excel workbook: {e}")
    
    @abstractmethod
    def process_data(self) -> Dict[str, pd.DataFrame]:
        """Process the calibration data. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def generate_outputs(self, results: Dict[str, pd.DataFrame]):
        """Generate output files and Excel updates. Must be implemented by subclasses."""
        pass
    
    def run(self):
        """Execute the complete calibration process."""
        try:
            results = self.process_data()
            self.generate_outputs(results)
            self.save_workbook()
        except Exception as e:
            print(f"Error during calibration processing: {e}")
            raise


def create_histogram_tlfd(data: pd.Series, bins: range = None, sampleshare: float = 1.0) -> pd.DataFrame:
    """Create trip length frequency distribution histogram."""
    if bins is None:
        bins = range(151)
    
    hist, bin_edges = np.histogram(data, bins=bins)
    return pd.DataFrame({
        'distbin': list(bins)[1:],
        'count': hist / sampleshare
    })
