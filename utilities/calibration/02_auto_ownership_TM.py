import pandas as pd
import numpy as np
import os
import sys
import shutil
import logging

from pathlib import Path

# Import the calibration framework
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, add_county_info
from calibration_data_models import (
    AutoOwnershipCountySummary,
    AutoOwnershipLongSummary,
    AutoOwnershipTAZSummary,
    validate_dataframe
)

class AutoOwnershipCalibration(CalibrationBase):
    """Calibration processor for auto ownership."""
    
    def __init__(self, config_file: str = None):
        super().__init__("02", config_file)
    
    def process_data(self) -> dict:
        """Process the auto ownership data."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS INPUT DATA\n{sep}")

        self.logger.info("Loading input data files:")
        self.logger.info(f'TAZ Data: {self.config.get('data_sources', 'taz_data')}')
        self.logger.info(f"Auto Ownership: {self.submodel_config['ao_results']}")
        # Load input data
        pop_households = pd.read_csv(self.submodel_config['input_file'])[['HHID', 'TAZ', 'PERSONS']]
        taz_data = pd.read_csv(self.config.get('data_sources', 'taz_data'))
        ao_results = pd.read_csv(self.submodel_config['ao_results'])
        
        # Add TAZ and PERSONS to ao_results
        ao_results = ao_results.merge(pop_households, left_on='HHID', right_on='HHID', how='left')
        
        # Add COUNTY and county name
        ao_results = add_county_info(ao_results, taz_data, self.county_lookup, taz_col='TAZ',)

        # Summarize by county and auto ownership
        ao_county = ao_results.groupby(['COUNTY', 'county_name', 'AO']).size().reset_index(name='num_hh')
        ao_county['num_hh'] = ao_county['num_hh'] / self.sampleshare
        
        # Pivot to spread format
        ao_county_spread = ao_county.pivot(index=['COUNTY', 'county_name'], columns='AO', values='num_hh')
        ao_county_spread = ao_county_spread.fillna(0).reset_index()
        ao_county_spread.columns = ao_county_spread.columns.astype(str)
        
        # Summarize by TAZ and auto ownership (long format)
        ao_taz = ao_results.groupby(['TAZ', 'AO']).size().reset_index(name='num_hh')
        ao_taz['num_hh'] = ao_taz['num_hh'] / self.sampleshare
        ao_taz['source'] = 'Model'
        ao_taz = ao_taz.rename(columns={'AO': 'num_vehicles'})
        
        # TAZ spread format
        ao_taz_spread = ao_taz.pivot(index=['TAZ', 'source'], columns='num_vehicles', values='num_hh')
        ao_taz_spread = ao_taz_spread.fillna(0).reset_index()
        ao_taz_spread.columns = ao_taz_spread.columns.astype(str)
        print(ao_taz)
        
        return {
            'county_summary': ao_county_spread,
            'taz_long': ao_taz,
            'taz_spread': ao_taz_spread
        }
    
    def validate_outputs(self, results: dict):
        """Validate outputs before generating the files and updating excel"""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VAlIDATION\n{sep}")

        # Validate county summary
        if results['county_summary'] is not None:
            validate_dataframe(results['county_summary'], AutoOwnershipCountySummary, expected_rows= 9)
            self.logger.info("Auto Ownership County Summary Validated")

        # Validate TAZ Summaries
        if results['taz_spread'] is not None:
            validate_dataframe(results['taz_spread'], AutoOwnershipTAZSummary)
            self.logger.info("Auto Ownership TAZ Summary Validated")

        
        if results['taz_long'] is not None:
            validate_dataframe(results['taz_long'], AutoOwnershipLongSummary)
            self.logger.info("Auto Ownership TAZ Long Summary Validated")



    def generate_outputs(self, results: dict):
        """Generate output files and Excel updates."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")
        # County summary
        county_file = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM.csv"
        results['county_summary'].to_csv(county_file, index = False)
        self.write_dataframe_to_sheet(results['county_summary'], start_row=3, start_col=1,
                                     source_row=1, source_col=1, source_text=f"Source: {county_file}")
        
        # TAZ summaries
        results['taz_long'] = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM_long.csv"
        results['taz_spread'] = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM.csv"
        
        # Copy ACS comparison file
        #TODO: Update and Verify source
        acs_source = "M:/Data/Census/ACS/ACS2013-2017/B08201 Household Size by Vehicles Available/vehiclesAvailableByTazACS_long.csv"
        acs_dest = os.path.join(self.output_dir, f"{self.submodel}_auto_ownership_TAZ_ACS.csv")
        try:
            shutil.copy(acs_source, acs_dest)
            print(f"Copied ACS data to {acs_dest}")
        except Exception as e:
            print(f"Warning: Could not copy ACS file: {e}")


def main():
    """Main entry point for the auto ownership calibration."""
    calibration = AutoOwnershipCalibration()
    calibration.run()


if __name__ == "__main__":
    main()