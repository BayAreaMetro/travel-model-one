#%%
import pandas as pd
import numpy as np
import os
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


#%%
class CalibrationConfig:
    """Configuration manager for calibration scripts."""
    
    def __init__(self, config_file: str = None, submodel: str = None):
        self.config = {}
        
        # Load config file
        config_file = config_file or 'E:/GitHub/travel-model-one/utilities/calibration/calibration_config.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
    
    def get(self, section: str, key: str, fallback: str = None) -> str:
        """Get configuration value with variable substitution."""
        value = self.config.get(section, {}).get(key, fallback)
        if isinstance(value, str) and '{' in value:
            # Perform variable substitution
            general = self.config.get('general', {})
            value = value.format(
                target_dir=general.get('target_dir', ''),
                calib_iter=general.get('calib_iter', ''),
                iter=general.get('iter', '')
            )
        return value
    
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
        self.output_dir = os.path.join(self.target_dir)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.sampleshare = self.config.getfloat('general', 'sampleshare', 1.0)
        
        # Set up Excel workbook
        self._setup_workbook()
        
        # Print configuration
        self._print_config()
    
    def _setup_workbook(self):
        """Set up Excel workbook paths and load template."""
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
        
        # Load workbook with optimizations for speed
        # try:
        #     print(f"Loading Excel workbook from {self.workbook_blank}...")
        #     self.calib_workbook = load_workbook(
        #         self.workbook_blank,
        #         data_only=True,
        #         keep_links = False
        #     )
        #     self.modeldata_sheet = self.calib_workbook['modeldata']
        #     print(f"Excel workbook loaded successfully")
        #     print(f"Excel workbook loaded")
        # except Exception as e:
        #     print(f"Skipping Excel workbook: {e}")
        #     self.calib_workbook = None
        #     self.modeldata_sheet = None
        try: 
            print(f"Loading Excel workbook from {self.workbook_blank}...")
            self.calib_workbook = xw.Book(self.workbook_blank)
            self.modeldata_sheet = self.calib_workbook.sheets['modeldata']
        except Exception as e:
            print(f"Skipping Excel workbook: {e}")
            self.calib_workbook = None
            self.modeldata_sheet = None


    def _print_config(self):
        """Print configuration summary."""
        print(f"Submodel: {self.submodel} - {self.submodel_config['name']}")
        print(f"TARGET_DIR  = {self.target_dir}")
        print(f"ITER        = {self.config.get('general', 'iter')}")
        print(f"SAMPLESHARE = {self.sampleshare}")
        print(f"CALIB_ITER  = {self.config.get('general', 'calib_iter')}")
        print(f"EXCEL_WORKBOOK = {self.workbook_blank}")
    

    def write_dataframe_to_sheet(self, df: pd.DataFrame, start_row: int, start_col: int, sheet_name: str ="modeldata",
                                source_row: int = None, source_col: int = None, source_text: str = ""):
        """Write DataFrame to Excel sheet with optional source annotation."""
        if not self.calib_workbook:
            print(f"Warning: Calibration Workbook does not exist")
            return

        try:
            sheet = self.calib_workbook.sheets[sheet_name]
            sheet.range((start_row, start_col)).value = df

            if source_row and source_col and source_text:
                sheet.range((source_row, source_col)).value = source_text
            # with pd.ExcelWriter(self.workbook_blank, engine= 'openpyxl', mode= 'a', if_sheet_exists='overlay') as writer:
            #     df.to_excel(writer, sheet_name = sheet_name, index = False, startrow=start_row, startcol = start_col)

            # if source_row and source_col and source_text:
            #     self.calib_workbook[sheet_name].cell(row = source_row, column= source_col).value = source_text

            # for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True)):
            #     for c_idx, value in enumerate(row):
            #         self.modeldata_sheet.cell(row=start_row + r_idx, column=start_col + c_idx, value=value)
            
            # if source_row and source_col and source_text:
            #     self.modeldata_sheet.cell(row=source_row, column=source_col).value = source_text
                
        except Exception as e:
            print(f"Warning: Could not write to Excel sheet: {e}")
    
    def save_workbook(self):
        """Save the Excel workbook."""
        print(self.calib_workbook)
        if self.calib_workbook:
            try:
                self.calib_workbook.save(self.workbook_temp)
                print(f"Wrote {self.workbook_temp}")
                self.calib_workbook.close()
            except Exception as e:
                print(f"Warning: Could not save Excel workbook: {e}")
                self.calib_workbook.close()
        else:
            print("Did not save workbook")
    
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

# def attach_distance_skim() -> pd.DataFrame:
    