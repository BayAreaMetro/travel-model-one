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
    OBSERVED_TARGETS_SHEET = "BATS 2023"
    OBSERVED_TARGETS_HEADER_ROW = 3
    OBSERVED_TARGETS_START_COL = 2
    OBSERVED_TARGETS_RESULT_TYPES = ["unweighted", "weighted"]
    OBSERVED_TARGETS_FILTERS = ["all", "solano_napa", "north_bay"]


    # UEC Source and Calibration Destination
    UEC_SOURCE_RANGES = {
        "work": ("Work", 8, 22, 57, 59), 
        "univ": ("univ", 8, 22, 56, 58),
        "school": ("scho", 8, 22, 56, 58),
        "escort": ("escort", 8, 22, 57, 59),
        "shop": ("shop", 8, 22, 60, 62),
        "eat": ("eat", 8, 22, 64, 66),
        "maintenance": ("maint", 8, 22, 60, 62),
        "social": ("visit", 8, 22, 64, 66),
        "discretionary": ("discr", 8, 22, 59, 61),
        "atwork": ("subtour", 8, 22, 19, 21),
        "joint": ("escort", 8, 22, 60, 62)
    }
    
    CALIBRATION_DESTINATION_RANGES = {
        "work": ("constants", 4, 18, 6, 8), 
        "univ": ("constants", 4, 18, 9, 11), 
        "school": ("constants", 4, 18, 12, 14), 
        "escort": ("constants", 4, 18, 15, 17), 
        "shop": ("constants", 4, 18, 18, 20), 
        "eat": ("constants", 4, 18, 21, 23), 
        "maintenance":("constants", 4, 18, 24, 26), 
        "social": ("constants", 4, 18, 27, 29), 
        "discretionary": ("constants", 4, 18, 30, 32), 
        "atwork": ("constants", 4, 18, 33, 35), 
        "joint": ("constants", 4, 18, 36, 38), 
    }


    def __init__(self, config_file: str | None = None):
        super().__init__("12", config_file)
#%%
    def _load_tours(self) -> pd.DataFrame:
        """Load and harmonize individual and joint tour tables."""

        all_tour_file = self.submodel_config.get("all_tour_file")
        if all_tour_file:
            all_tour = pd.read_csv(all_tour_file)
            all_tour["indiv_joint"] = np.where(all_tour["joint_tour_id"].isnull(), "indiv", "joint")
            return all_tour

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

        if self.bats_data:
            indiv_cols.append("tour_weight")
            joint_cols.append("joint_tour_weight")

        indiv = pd.read_csv(self.submodel_config["indiv_tour_file"], usecols=indiv_cols)
        indiv["num_participants"] = 1
        indiv["indiv_joint"] = "indiv"

        joint = pd.read_csv(self.submodel_config["joint_tour_file"], usecols=joint_cols)
        joint.rename(columns = {"joint_tour_weight": "tour_weight"})
        joint["person_num"] = joint["tour_participants"].str.split(" ")
        joint["num_participants"] = joint["person_num"].str.len()
        joint["indiv_joint"] = "joint"
        joint = joint.drop(columns=["tour_participants"])
        joint = joint.explode("person_num")

        tours = pd.concat([indiv.drop(columns=["person_id"]), joint], ignore_index=True)
        tours["tour_mode"] = pd.to_numeric(tours["tour_mode"], errors="coerce")


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
        self.logger.info(f"All Tour: {self.submodel_config["all_tour_file"]}")

        tours = self._load_tours()
        tours["simple_purpose"] = self._map_simple_purpose(
            tours["tour_purpose"], tours["indiv_joint"], collapse_joint=True)\

        if self.bats_data:
            ## Cap the maximize number of stops to 4
            tours[["num_ib_stops", "num_ob_stops"]] = tours[["num_ib_stops", "num_ob_stops"]].clip(upper=4)

    
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
        sheet_name = (
        self.OBSERVED_TARGETS_SHEET if self.bats_data else "modeldata"
        )
        csv_name = (
            "12_stop_freq_summary_BATS.csv"
            if self.bats_data
            else "12_stop_freq_summary_TM.csv"
        )

        sheet_target = SheetTarget(
            "stop_freq_summary",
            sheet_name,
            3,
            2,
            csv_name,
            (1, 2),
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
