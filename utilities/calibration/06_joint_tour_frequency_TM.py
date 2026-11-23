"""Joint Tour Frequency Calibration

"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, SheetTarget
#from calibration_data_models import TourModeSummaryLong, validate_dataframe
from data_canon.codebook.ctramp import CTRAMPModeType, CTRAMPPersonType, JTFChoice

class JointTourFreqCalibration(CalibrationBase):



    def __init__(self, config_file: str | None = None):
            super().__init__("06", config_file)


    """Script to load household data and aggregate by JTF based on the CTRAMP JTF data dictionary"""
    

    def process_data(self):
        """Process Joint Tour Frequency data"""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\n PROCESS INPUT DATA\n{sep}")
        self.logger.info("Loading input data files:")

    


        # Load household data
        household = pd.read_csv(self.submodel_config['household_data'])

        if self.bats_data:
            jtf_lookup = {jtf.value: jtf.label for jtf in JTFChoice}
            # Map value to labels for jtf_choice
            household["jtf_pattern"] = household["jtf_choice"].map(jtf_lookup)


        joint_frequency = household.pivot_table(
            index=["jtf_choice", "jtf_pattern"],
            values = "hh_weight",
            aggfunc= "sum",
            fill_value=0,
        ).reset_index()

 

        return {
            "joint_frequency" : joint_frequency
        }


    def validate_outputs(self, results):
         return super().validate_outputs(results)

    def generate_outputs(self, results):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        targets = [SheetTarget("joint_frequency", "BATS 2023", 2, 1,
                                           "BATS2023_joint_tour_frequency.csv", (1, 1))]

        self.write_results_to_workbook(results, targets)

def main():
    """Main entry point for the non-mandatory tour frequency calibration."""
    parser = argparse.ArgumentParser(description="Joint Tour Frequency calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    args = parser.parse_args()

    calibration = JointTourFreqCalibration(config_file=args.config)
    calibration.logger.info("Starting joint tour frequency calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")

if __name__ == "__main__":
    main()
