"""Non-work destination choice calibration submodel (submodel 09)."""
import argparse
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, SheetTarget, add_county_info, create_histogram_tlfd
from calibration_data_models import (
    NonMandAvgTourLength,
    NonMandTourLengthFrequency,
    validate_dataframe,
)


class NonWorkDestinationChoiceCalibration(CalibrationBase):
    """Calibration processor for non-work destination choice."""

    # Declarative placement of summary tables into workbook cells (modeled vs observed).
    # The unfiltered ("all") tables go to the workbook; filtered subsets are CSV-only.
    MODELED_SHEET_TARGETS = [
        SheetTarget("tour_tlfd_all", "modeldata", 3, 1,
                    "09_nonwork_destination_TM_TLFD.csv", (2, 1)),
        SheetTarget("avg_tour_lengths_all", "modeldata", 3, 10,
                    "09_nonwork_destination_TM_avgtourlen.csv", (2, 10)),
    ]
    OBSERVED_SHEET_TARGETS = [
        SheetTarget("tour_tlfd_all", "BATS 2023 TLFD", 3, 2,
                    "BATS2023_TLFD.csv", (1, 2)),
        SheetTarget("avg_tour_lengths_all", "BATS 2023 TLFD", 58, 3,
                    "BATS2023_avgtourlen.csv", (57, 3)),
    ]

    PURPOSE_GROUPS = {
        "escort": ["escort_kids", "escort_no kids"],
        "shop": ["shopping"],
        "maintenance": ["othmaint"],
        "eatout": ["eatout"],
        "visit": ["social"],
        "discretionary": ["othdiscr"],
        "atwork": ["atwork_business", "atwork_eat", "atwork_maint"],
    }

    UEC_SOURCE_RANGES = {
        "escort1": ("EscortKids", 7, 12, 16),
        "escort2": ("EscortNoKids", 7, 12, 16),
        "shopping": ("Shopping", 7, 12, 16),
        "maint": ("OthMaint", 7, 12, 16),
        "eatout": ("EatOut", 7, 12, 16),
        "social": ("Social", 7, 12, 16),
        "discr": ("OthDiscr", 7, 12, 16),
        "atwork": ("WorkBased", 7, 12, 16),
    }

    CALIBRATION_DESTINATION_RANGES = {
        "escort1": ("calibration", 5, 4, 8),
        "escort2": ("calibration", 5, 4, 8),
        "shopping": ("calibration", 17, 4, 8),
        "maint": ("calibration", 29, 4, 8),
        "eatout": ("calibration", 41, 4, 8),
        "social": ("calibration", 53, 4, 8),
        "discr": ("calibration", 65, 4, 8),
        "atwork": ("calibration", 77, 4, 8),
    }

    def __init__(self, config_file: str = None):
        super().__init__("09", config_file)

    def _build_summary_tables(self, tour_results: pd.DataFrame) -> dict:
        """Build TLFD and average tour length summaries from prepared tour data."""
        if self.bats_data:
            dist_bins = range(1, 52)
            histogram_bins = range(52)
        else:
            dist_bins = range(1, 151)
            histogram_bins = dist_bins

        tlfd = pd.DataFrame({"distbin": dist_bins})
        avg_tour_lengths = []

        self.logger.info("Processing tour length distributions...")
        for tour_type, purposes in self.PURPOSE_GROUPS.items():
            tour_dists = tour_results[tour_results["tour_purpose"].isin(purposes)]

            if self.bats_data:
                valid_mask = tour_dists["DIST"].notna() & tour_dists["tour_weight"].notna()
                dist_values = tour_dists.loc[valid_mask, "DIST"]
                weight_values = tour_dists.loc[valid_mask, "tour_weight"]

                if len(dist_values) == 0 or float(weight_values.sum()) <= 0:
                    hist_df = pd.DataFrame({"distbin": list(histogram_bins)[1:], "count": 0.0})
                    weighted_mean = 0.0
                else:
                    hist_df = create_histogram_tlfd(
                        dist_values,
                        bins=histogram_bins,
                        weights=weight_values,
                    )
                    weighted_mean = float(np.average(dist_values, weights=weight_values))
            else:
                dist_values = tour_dists["DIST"].dropna()
                hist_df = create_histogram_tlfd(
                    dist_values,
                    bins=histogram_bins,
                    sampleshare=self.sampleshare,
                )
                weighted_mean = float(dist_values.mean()) if len(dist_values) > 0 else 0.0

            tlfd = tlfd.merge(
                hist_df.rename(columns={"count": tour_type}),
                on="distbin",
                how="left",
            )

            avg_tour_lengths.append(
                {
                    "tour_type": tour_type,
                    "mean_tour_length": weighted_mean,
                }
            )

        tlfd = tlfd.fillna(0)
        avg_tour_lengths_df = pd.DataFrame(avg_tour_lengths)

        return {
            "tour_tlfd": tlfd,
            "avg_tour_lengths": avg_tour_lengths_df,
        }

    def _load_tours(self) -> pd.DataFrame:
        """Load individual and joint tours into a single harmonized table. 
        
        Tour output includes the following columns:
            - hh_id
            - tour_id
            - tour_category
            - tour_purpose
            - tour_mode
            - start_hour
            - end_hour
            - orig_taz
            - dest_taz
            - num_participants
            - indiv_joint
            - tour_weight
        """
        indiv_tours = pd.read_csv(
            self.submodel_config["indiv_tour_file"],
            usecols=[
                "hh_id",
                "tour_id",
                "tour_category",
                "tour_purpose",
                "tour_mode",
                "start_hour",
                "end_hour",
                "orig_taz",
                "dest_taz",
                "tour_weight"
            ],
        )

        indiv_tours['num_participants'] = 1
        indiv_tours['indiv_joint'] = 'indiv'

        joint_tours = pd.read_csv(
            self.submodel_config["joint_tour_file"],
            usecols=[
                "hh_id",
                "tour_id",
                "tour_category",
                "tour_purpose",
                "tour_mode",
                "start_hour",
                "end_hour",
                "orig_taz",
                "dest_taz",
                'tour_participants',
                "joint_tour_weight"
            ],
        )
        joint_tours.rename(columns = {"joint_tour_weight": "tour_weight"})
        joint_tours['num_participants'] = joint_tours['tour_participants'].str.split(" ").str.len()
        joint_tours['indiv_joint'] = 'joint'
        joint_tours.drop(columns = "tour_participants", inplace = True)

        return pd.concat([indiv_tours, joint_tours], ignore_index=True)

    def process_data(self) -> dict:
        """
        Load inputs, merge spatial attributes, and compute summary statistics.

        Steps:

        1. Read the CTRAMP (or BATS) individual and joint tours files
        2. Process and combined the tour files together via :func:`_load_tours`.
        3. Join skim distances for orig->dest pairs
        4. Build total TLFDs (1-mile bins) for escort, shop, maintenance, eat out,
            visit, discretionary, at-work tour purpose
        5. Compute weighted (BATS) or unweighted/scaled (model) average tour
           lengths by tour type.

        Returns:
            A dict with the following keys:

            ``tour_tlfd``
                Tour Length Frequency Distribution (TLFD) DataFrame by non-mandatory tour purpose
                (distbin column + one column per purpose).
            ``avg_tour_lengths``
                Wide-format DataFrame of mean tour distances
                (rows = purpose, columns = avgTourLength).
        """
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS INPUT DATA\n{sep}")

        tour_results = self._load_tours()
        dist_skim = pd.read_csv(self.config.get('data_sources', 'dist_skim'), header=0,
                               usecols = ['orig', 'dest', 'DIST'])
        tour_results = tour_results.merge(dist_skim, 
                                          left_on= ["orig_taz", "dest_taz"], 
                                          right_on = ['orig', 'dest'], 
                                          how= "left",
                                          validate= 'm:1')
        
        tour_results.to_csv(f"{self.target_dir}/tour_with_dist.csv", index = False)

        taz_data = pd.read_csv(self.config.get("data_sources", "taz_data"), usecols=["ZONE", "COUNTY"])
        tour_results = add_county_info(tour_results, taz_data, self.county_lookup,
                                       taz_col="orig_taz", county_col_name="orig_county_id", county_name_col="orig_county")
        tour_results = add_county_info(tour_results, taz_data, self.county_lookup,
                                       taz_col="dest_taz", county_col_name="dest_county_id", county_name_col="dest_county")

        # One set of summaries per configured county filter ("all" = unfiltered).
        results = {}
        for label, subset in self.iter_county_filters(tour_results):
            summ = self._build_summary_tables(subset)
            results[f"tour_tlfd_{label}"] = summ["tour_tlfd"]
            results[f"avg_tour_lengths_{label}"] = summ["avg_tour_lengths"]
        return results

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")

        expected_rows = 51 if self.bats_data else 150
        for key, df in results.items():
            if key.startswith("tour_tlfd_"):
                validate_dataframe(df, NonMandTourLengthFrequency, expected_rows=expected_rows)
            elif key.startswith("avg_tour_lengths_"):
                validate_dataframe(df, NonMandAvgTourLength, expected_rows=7)
        self.logger.info("\u2713 Non-work outputs validated (all county filters)")

    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        targets = list(self.OBSERVED_SHEET_TARGETS if self.bats_data else self.MODELED_SHEET_TARGETS)
        prefix = "BATS2023" if self.bats_data else "09_nonwork_destination_TM"

        # Filtered subsets (everything except "_all") are CSV-only.
        for key in results:
            if key.endswith("_all"):
                continue
            targets.append(SheetTarget(key, "", 0, 0, f"{prefix}_{key}.csv", None))

        self.write_results_to_workbook(results, targets)


def main():
    """Parse CLI arguments and run the non-work destination choice calibration."""
    parser = argparse.ArgumentParser(description="Non-work destination choice calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    args = parser.parse_args()

    calibration = NonWorkDestinationChoiceCalibration(config_file=args.config)
    calibration.logger.info("Starting non-work destination choice calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")


if __name__ == "__main__":
    main()