"""Non-Mandatory Tour Frequency Calibration

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
from data_canon.codebook.ctramp import CTRAMPModeType, CTRAMPPersonType

class NonMandTourFreqCalibration(CalibrationBase):

    UEC_SOURCE_RANGES = {
        "Full Time Worker":        ("1_FullTimeWorker", 7, 244, 250),
        "Part Time Worker":    ("2_PartTimeWorker", 7, 244, 250),
        "University":             ("3_UnivStudent", 7, 244, 250),
        "Non Worker":   ("4_NonWorker", 7, 244, 250),
        "Retired":    ("5_Retiree", 7, 244, 250),
        "Student of driving age":    ("6_DrivingSchoolChild", 7, 244, 250),
        "Student of non driving age":    ("7_PreDrivingSchoolChild", 7, 244, 250),
        "Child":    ("8_PreSchoolChild", 7, 244, 250),
    }
    # calibration workbook is ".xlsx" and uses openpyxl which is 1-based indexing for rows/columns
    CALIBRATION_DESTINATION_RANGES = {
        "Full Time Worker":        ("calibration", 3, 59, 65),
        "Part Time Worker":    ("calibration", 4, 59, 65),
        "University":             ("calibration", 5, 59, 65),
        "Non Worker":   ("calibration", 6, 59, 65),
        "Retired":    ("calibration", 7, 59, 65),
        "Student of driving age":    ("calibration", 8, 59, 65),
        "Student of non driving age":    ("calibration", 9, 59, 65),
        "Child":    ("calibration", 10, 59, 65),
    }


    def __init__(self, config_file: str | None = None):
            super().__init__("07", config_file)


    """Script to load persons and tours -> Aggregate tours stats to person (tour stats to include purpose)"""
    def _load_tours(self) -> pd.DataFrame:
        "Load and harmonize individual tours table"

        all_tour_file = self.submodel_config.get("all_tour_file")
        if all_tour_file:
            # Filter to only individual tours
            indiv_tour = pd.read_csv(all_tour_file)
            indiv_tour = indiv_tour[indiv_tour["joint_tour_id"].isnull()]

            return indiv_tour

        indiv_cols = [
            "hh_id",
            "person_id",
            "tour_id",
            "person_type",
            "tour_category",
            "tour_purpose",
            "tour_mode",
            "start_hour",
            "end_hour",
            "orig_taz",
            "dest_taz",
            "num_ob_stops",
            "num_ib_stops",
            "sampleRate"
        ]
        if self.bats_data:
            indiv_cols.append("tour_weight")

        indiv_tour = pd.read_csv(self.submodel_config["indiv_tour_file"], usecols=indiv_cols)
        indiv_tour["num_participants"] = 1
        indiv_tour["tour_mode"] = pd.to_numeric(indiv_tour["tour_mode"], errors="coerce")

        if "tour_weight" not in indiv_tour:
             indiv_tour["tour_weight"] = 1 / indiv_tour["sampleRate"]

        return indiv_tour


    def _aggregate_tour_statistics(self,
              tours: pd.DataFrame) -> pd.DataFrame:
        """Aggregate tour statistics by person
        
        Computes:
            - Number of mandatory tours per person
            - Number of non-mandatory tours per person
            - Number of non-mandatory tours per person by purpose
                - Purpose includes: escort, shopping, oth maint, eatout, social, othdiscr

        Args:
            tours: DataFrame with person_id and tour_purpose field. Individual tours only 

        Returns:
            DataFrame with person_id and aggregated statistics
        """
        # Group by person_id and then count tours by purposes (escort, shop, maintenace, eat out, social, other disc)
        escort_purposes = ["escort_no kids", "escort_kids"]
        tour_stats = tours.assign(
            is_escort = tours["tour_purpose"].isin(escort_purposes),
            is_shopping = tours["tour_purpose"] == "shopping",
            is_othmaint = tours["tour_purpose"] == "othmaint",
            is_othdiscr = tours["tour_purpose"] == "othdiscr",
            is_eatout = tours["tour_purpose"] == "eatout",
            is_social = tours["tour_purpose"] == "social" 
        )

        person_stats = tour_stats.groupby("person_id").agg(
            escort_count = ("is_escort", "sum"),
            shopping_count = ("is_shopping", "sum"),
            othmaint_count = ("is_othmaint", "sum"),
            othdiscr_count = ("is_othdiscr", "sum"),
            eatout_count = ("is_eatout", "sum"),
            social_count = ("is_social", "sum")
        )

        return person_stats

    def process_data(self):
        """Process Stop Frequency data"""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\n PROCESS INPUT DATA\n{sep}")
        self.logger.info("Loading input data files:")

        # Load individual tours
        tours = self._load_tours()
        person_stats = self._aggregate_tour_statistics(tours)
        persons = pd.read_csv(self.submodel_config["person_data"])

        if "person_weight" not in persons:
             persons["person_weight"] = 1/persons["sampleRate"]
        persons = persons.merge(person_stats, on="person_id", how="left")

        stats_columns = ["escort_count", "shopping_count", "othmaint_count", "othdiscr_count", "eatout_count", "social_count"]
        persons[stats_columns] = persons[stats_columns].fillna(value=0)

        # Save persons with tour stats
        persons.to_csv(f"{self.output_dir}/persons_w_tour_stats.csv")

        ## Process data now to crosstab with person type and purpose 
        person_order = ["Full-time worker", "Part-time worker", "University student", "Non-worker", "Retired", "Student of driving age", "Student of non-driving age", "Child too young for school"]
        purpose_order = ["escort", "shopping", "othmaint", "eatout", "social", "othdiscr"]
        persons["type"] = pd.Categorical(persons["type"], categories= person_order, ordered=True)

        persons_long = persons.melt(
            id_vars=["person_id", "type", "person_weight"],
            value_vars=stats_columns,
            var_name="purpose",
            value_name="tours_per_person",
        )
        persons_long["purpose"] = persons_long["purpose"].str.removesuffix("_count")
        persons_long["tours_per_person"] = persons_long["tours_per_person"].astype(int)
        person_tour_frequency_long = persons_long.groupby(
            ["type", "purpose", "tours_per_person"],
            observed=True,
            as_index=False
        )["person_weight"].sum()


        person_tour_frequency = persons_long.pivot_table(
             index= "type",
             columns=["purpose", "tours_per_person"],
             values = "person_weight",
             aggfunc="sum"
        )

        # Base tour frequency off of tour file, not persons
        nonmand_tour_purpose = ["escort_no kids", "escort_kids", "shopping", "othmaint", "eatout", "social", "othdiscr"]
        indiv_nonmand_tour = tours[tours["tour_purpose"].isin(nonmand_tour_purpose)].copy()
        person_type_labels = {person.value: person.label for person in CTRAMPPersonType}
        indiv_nonmand_tour["person_type"] = pd.Categorical(
            pd.to_numeric(indiv_nonmand_tour["person_type"], errors="coerce")
            .map(person_type_labels)
            .fillna(indiv_nonmand_tour["person_type"]),
            categories=person_order,
            ordered=True,
        )
        indiv_nonmand_tour["tour_purpose"] = indiv_nonmand_tour["tour_purpose"].replace(
            {"escort_no kids": "escort", "escort_kids": "escort"}
        )
        tour_frequency = indiv_nonmand_tour.pivot_table(
            index="person_type",
            columns=["tour_purpose"],
            values="tour_weight",
            aggfunc="sum",
            fill_value=0, 
            observed=True,
        )

        tour_frequency = tour_frequency.reindex(columns=purpose_order, fill_value=0).reset_index()


        weighted_persons = (
            persons.groupby("type", observed=True)["person_weight"]
            .sum()
            .reindex(person_order, fill_value=0)
        )
        tours_per_person = (
            tour_frequency.set_index("person_type")
            .reindex(index=weighted_persons.index, columns=purpose_order, fill_value=0)
            .div(weighted_persons.where(weighted_persons > 0), axis=0)
            .rename_axis("person_type")
            .reset_index()
        )
   
        return {
            "person_tour_frequency_long" : person_tour_frequency_long,
            "person_tour_frequency": person_tour_frequency,
            "tour_frequency": tour_frequency,
            "tours_per_person": tours_per_person,
        }


    def validate_outputs(self, results):
         return super().validate_outputs(results)

    def generate_outputs(self, results):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
             sheet_name = "BATS 2023"
             csv_name = "BATS2023"
             suffix =""
        else:
             sheet_name = "modeldata"
             csv_name = "07"
             suffix = "_TM"
            
        targets = [
            SheetTarget("person_tour_frequency_long", sheet_name, 4, 2, f"{csv_name}_inmf_long{suffix}.csv", (1,1)),
            SheetTarget("person_tour_frequency", sheet_name, 4, 7, f"{csv_name}_inmf{suffix}.csv", (1,7)),
            SheetTarget("tour_frequency", sheet_name, 20, 7, f"{csv_name}_num_indiv_nonmandatory_tours{suffix}.csv", (18,7)),
            SheetTarget("tours_per_person", sheet_name, 33 , 7, f"{csv_name}_tours_per_person{suffix}.csv", (31,7))
            ]


        self.write_results_to_workbook(results, targets)

def main():
    """Main entry point for the non-mandatory tour frequency calibration."""
    parser = argparse.ArgumentParser(description="Non Mandatory Tour Frequency calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    args = parser.parse_args()

    calibration = NonMandTourFreqCalibration(config_file=args.config)
    calibration.logger.info("Starting non-mandatory tour frequency calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")

if __name__ == "__main__":
    main()
