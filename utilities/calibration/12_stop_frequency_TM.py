# %%
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, SheetTarget, add_county_info
from calibration_data_models import TourModeSummaryLong, validate_dataframe

class StopFrequencyCalibration(CalibrationBase):
    """Calibration processor for stop frequency summaries."""


    # Observed (BATS): which wide summaries and county filters get written to the
    # 'targets' sheet (all results are still written to CSV). Blocks are split by
    # simple_purpose (stacked vertically), and each county filter occupies the
    # next set of columns to the right in the same format.
    OBSERVED_TARGETS_SHEET = "targets"
    OBSERVED_TARGETS_HEADER_ROW = 3
    OBSERVED_TARGETS_START_COL = 2
    OBSERVED_TARGETS_RESULT_TYPES = ["unweighted", "weighted"]
    OBSERVED_TARGETS_FILTERS = ["all", "solano_napa", "north_bay"]


    # UEC Source and Calibration Destination
    UEC_SOURCE_RANGES = {

    }
    
    CALIBRATION_DESTINATION_RANGES = {
    
    }


    def __init__(self, config_file: str | None = None):
        super().__init__("12", config_file)
#%%
    def _load_tours(self) -> pd.DataFrame:
        """Load and harmonize individual and joint tour tables."""
        indiv_cols = [
            "hh_id",
            "person_id",
            "tour_id",
            "tour_category",
            "tour_purpose",
            "tour_mode",
            "start_hour",
            "end_hour",
            "orig_taz",
            "dest_taz",
            "num_ob_stops",
            "num_ib_stops"
        ]
        joint_cols = [
            "hh_id",
            "tour_participants",
            "tour_id",
            "tour_category",
            "tour_purpose",
            "tour_mode",
            "start_hour",
            "end_hour",
            "orig_taz",
            "dest_taz",           
            "num_ob_stops",
            "num_ib_stops"
        ]

        indiv = pd.read_csv(self.submodel_config["indiv_tour_file"], usecols=indiv_cols)
        indiv["num_participants"] = 1
        indiv["indiv_joint"] = "indiv"

        joint = pd.read_csv(self.submodel_config["joint_tour_file"], usecols=joint_cols)
        joint["tour_participants"] = joint["tour_participants"].fillna("").astype(str)
        joint["num_participants"] = joint["tour_participants"].str.split().str.len().clip(lower=1)
        joint["indiv_joint"] = "joint"
        joint = joint.drop(columns=["tour_participants"])

        tours = pd.concat([indiv.drop(columns=["person_id"]), joint], ignore_index=True)
        tours["tour_mode"] = pd.to_numeric(tours["tour_mode"], errors="coerce")

        if self.bats_data and "tour_weight" not in tours.columns:
            tours["tour_weight"] = 1.0

        return tours
    
    @staticmethod
    def _map_simple_purpose(purpose_series: pd.Series, indiv_joint_series: pd.Series,
                            collapse_joint: bool = True) -> pd.Series:
        """Mapping simple purpose; when collapse_joint, joint tours become 'joint'."""
        mapping = {
            "atwork_business": "atwork",
            "atwork_eat": "atwork",
            "atwork_maint": "atwork",
            "eatout": "eatout",
            "escort_kids": "escort",
            "escort_no kids": "escort",
            "escort_no_kids": "escort",
            "othdiscr": "ind_disc",
            "othmaint": "ind_maint",
            "school_grade": "school",
            "school_high": "school",
            "shopping": "shop",
            "social": "social",
            "university": "university",
            "work_low": "work",
            "work_med": "work",
            "work_high": "work",
            "work_very high": "work",
            "work_very_high": "work",
        }
        simple = purpose_series.astype(str).map(mapping)
        if collapse_joint:
            simple = simple.where(indiv_joint_series.astype(str) != "joint", "joint")
        return simple
    
    def process_data(self):
        """Process Stop Frequency data"""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\n PROCESS INPUT DATA\n{sep}")
        self.logger.info("Loading input data files:")
        self.logger.info(f"Individual Tour: {self.submodel_config["indiv_tour_file"]}")
        self.logger.info(f"Joint Tour: {self.submodel_config["joint_tour_file"]}")

        tours = self._load_tours()
        tours["simple_purpose"] = self._map_simple_purpose(
            tours["tour_purpose"], tours["indiv_joint"], collapse_joint=True)

    
        tours["outbound_inbound"] = tours["num_ob_stops"].astype(str) + " out, " + tours["num_ib_stops"].astype(str) + " in"
        tours = tours.rename(columns = {"num_participants": "num_tours"})
        tours["num_tours"] = tours["num_tours"] / self.sampleshare

        stop_freq_summary = self.pivot_with_total(
            tours, idx_cols = ["outbound_inbound"], columns_col = "simple_purpose", 
            value_col= "num_tours", 
            ordered_cols=["work", "university", "school", "escort", "shop", "ind_maint", "eatout", "social", "ind_disc", "atwork", "joint"]
        ) 


        return {
            "stop_freq_summary": stop_freq_summary
        }

    def validate_outputs(self, results):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nVALIDATE OUTPUTS\n{sep}")
        print(results)

    def generate_outputs(self, results):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")
        sheet_target = SheetTarget(
        "stop_freq_summary", "modeldata", 3, 2, 
        "12_stop_freq_summary_TM.csv", (1,2)
        )

        self.write_results_to_workbook(results, [sheet_target])



def main():
    """Main entry point for the auto ownership calibration."""
    parser = argparse.ArgumentParser(description="Auto ownership calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    args = parser.parse_args()

    calibration = StopFrequencyCalibration(config_file=args.config)
    calibration.logger.info("Starting auto ownership calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")

if __name__ == "__main__":
    main()
