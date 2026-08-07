import argparse
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

# Import the calibration framework  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, SheetTarget, add_county_info
from calibration_data_models import (
    CTRAMPPersonType,
    CDAPSummary,
    CDAPSummaryBATS,
    validate_dataframe
)


class DailyActivityPatternCalibration(CalibrationBase):
    """Calibration processor for coordinated daily activity pattern."""
    
    # sheet, column, startRow, endRow
    # used for populating current iteration constants in calibration workbook with model UEC input
    # UEC workbook is ".xls" and uses xlrd which is 0-based indexing for rows/columns, but
    # config uses 1-based for readability, so offsets are applied in the reading functions
    UEC_SOURCE_RANGES = {
        "Mandatory":        ("OnePerson",  7, 33, 40),
        "Non-Mandatory":    ("OnePerson", 8, 33, 40),
        "Home":             ("OnePerson", 9, 33, 40),
    }
    # calibration workbook is ".xlsx" and uses openpyxl which is 1-based indexing for rows/columns
    CALIBRATION_DESTINATION_RANGES = {
        "Mandatory":        ("calibration", 3, 31, 38),
        "Non-Mandatory":    ("calibration", 4, 31, 38),
        "Home":             ("calibration", 5, 31, 38),

    }
    

    def __init__(self, config_file: str = None):
        super().__init__("04", config_file)
        self.bats_data = self.submodel_config.get("bats_data", False)
    
    def process_data(self) -> dict:
        """Process the coordinated daily activity pattern data."""
        # Load input data
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS DATA\n{sep}")
        cdap_results = pd.read_csv(self.submodel_config['input_file'])
        self.logger.info(f"Reading in CDAP Input File: {self.submodel_config['input_file']}")
        CTRAMPPersonTypeLookUp = {person.label: person.value for person in CTRAMPPersonType}


        if self.bats_data :
            cdap_results['person_type'] = cdap_results['type'].map(CTRAMPPersonTypeLookUp)
            cdap_results.fillna({'person_weight':0}, inplace = True)

            # Home TAZ comes from household data; attach home county for filtering.
            taz_data = pd.read_csv(self.config.get('data_sources', 'taz_data'), usecols=['ZONE', 'COUNTY'])
            hh = pd.read_csv(self.config.get('data_sources', 'household_file'), usecols=['hh_id', 'taz'])
            cdap_results = cdap_results.merge(hh, on='hh_id', how='left')
            cdap_results = add_county_info(cdap_results, taz_data, self.county_lookup,
                                           taz_col='taz', county_col_name='home_county_id', county_name_col='home_county')

            # One summary per county filter ("all" = unfiltered); filter on home county only.
            results = {}
            for label, subset in self.iter_county_filters(cdap_results, orig_county_col="home_county", dest_county_col=None):
                cdap_ptype = subset.groupby(['person_type', 'activity_pattern'])['person_weight'].sum().reset_index(name='num_pers')
                results[f'person_type_summary_{label}'] = cdap_ptype
            return results

        else:
        # Summarize by person type and activity string
            cdap_ptype = cdap_results.groupby(['PersonType', 'ActivityString']).size().reset_index(name='num_pers')
            cdap_ptype['num_pers'] = cdap_ptype['num_pers'] / self.sampleshare
            
            # Pivot to spread format
            cdap_ptype_spread = cdap_ptype.pivot(index='PersonType', columns='ActivityString', values='num_pers')
            cdap_ptype_spread = cdap_ptype_spread.fillna(0).reset_index()
            
            return {
                'person_type_summary': cdap_ptype_spread
            }
    
    def validate_outputs(self, results:dict):
        """Validate outputs before generating the files and updating excel"""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VAlIDATION\n{sep}")

        if self.bats_data:
            for key, df in results.items():
                if key.startswith('person_type_summary_') and df is not None:
                    validate_dataframe(df, CDAPSummaryBATS)
            self.logger.info("Person Type BATS Summary Validated (all county filters)")
        elif results['person_type_summary'] is not None:
            validate_dataframe(results['person_type_summary'], CDAPSummary)
            self.logger.info("Person Type Summary Validated")


    def generate_outputs(self, results: dict):
        """Generate output files and Excel updates."""

        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
            targets = [SheetTarget("person_type_summary_all", "BATS 2023", 2, 2,
                                   "dap_summaries.csv", (1, 2))]
            for key in results:
                if key.endswith("_all"):
                    continue
                targets.append(SheetTarget(key, "", 0, 0, f"BATS2023_{key}.csv", None))
        else:
            targets = [SheetTarget("person_type_summary", "modeldata", 2, 1,
                                   f"{self.submodel}_daily_activity_pattern_TM.csv", (1, 1))]
        self.write_results_to_workbook(results, targets)



def main():
    """Main entry point for the daily activity pattern calibration."""
    parser = argparse.ArgumentParser(description="Coordinated daily activity pattern calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    args = parser.parse_args()

    calibration = DailyActivityPatternCalibration(config_file=args.config)
    calibration.run()


if __name__ == "__main__":
    main()
