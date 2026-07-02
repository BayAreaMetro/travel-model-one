"""Non-work destination choice calibration submodel (submodel 09)."""
import argparse
import os
import sys
import numpy as np
import pandas as pd


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, create_histogram_tlfd
from calibration_data_models import (
    NonMandAvgTripLength,
    NonMandTripLengthFrequency,
    validate_dataframe,
)


class NonWorkDestinationChoiceCalibration(CalibrationBase):
    """Calibration processor for non-work destination choice."""

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
                "tour_weight"
            ],
        )

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
        5. Compute weighted (BATS) or unweighted/scaled (model) average trip
           lengths by tour type.

        Returns:
            A dict with the following keys:

            ``trip_tlfd``
                Tour Length Frequency Distribution (TLFD) DataFrame by non-mandatory trips purpose
                (distbin column + one column per purpose).
            ``avg_trip_lengths``
                Wide-format DataFrame of mean trip distances
                (rows = purpose, columns = avgTripLength).
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
        if self.bats_data:
            dist_bins = range(1, 52)
        else:
            dist_bins = range(1, 151)
        tlfd = pd.DataFrame({"distbin": dist_bins})
        avg_trip_lengths = []

        self.logger.info("Processing trip length distributions...")
        for trip_type, purposes in self.PURPOSE_GROUPS.items():
            trip_dists = tour_results[tour_results["tour_purpose"].isin(purposes)]

            if self.bats_data:
                hist_df = create_histogram_tlfd(trip_dists['DIST'], bins = range(52),
                                                weights=trip_dists['tour_weight'])
                # Weighted average
                weighted_mean = np.average(trip_dists['DIST'], 
                                                weights=trip_dists['tour_weight'])
            else:
                hist_df = create_histogram_tlfd(trip_dists, bins=dist_bins, sampleshare=self.sampleshare)
                weighted_mean = trip_dists['DIST'].mean()
            
            tlfd = tlfd.merge(
                hist_df.rename(columns={"count": trip_type}),
                on="distbin",
                how="left",
            )

            avg_trip_lengths.append(
                {
                    "trip_type": trip_type,
                    "mean_trip_length": weighted_mean
                }
            )

        tlfd = tlfd.fillna(0)
        avg_trip_lengths_df = pd.DataFrame(avg_trip_lengths)

        return {
            "trip_tlfd": tlfd,
            "avg_trip_lengths": avg_trip_lengths_df,
        }

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")

        expected_rows = 51 if self.bats_data else 150
        validate_dataframe(results["trip_tlfd"], NonMandTripLengthFrequency, expected_rows=expected_rows)
        self.logger.info("✓ Non-work TLFD validated")

        validate_dataframe(results["avg_trip_lengths"], NonMandAvgTripLength, expected_rows=7)
        self.logger.info("✓ Average trip length summary validated")

    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
            tlfd_file = f"{self.output_dir}/BATS2023_TLFD.csv"
            results["trip_tlfd"].to_csv(tlfd_file, index=False)
            self.write_dataframe_to_sheet(
                results["trip_tlfd"],
                sheet_name="BATS 2023 TLFD",
                start_row=3,
                start_col=2,
                source_row=1,
                source_col=2,
                source_text=f"Source: {tlfd_file}",
            )
            self.logger.info(f"Saving trip length frequency distributions to {tlfd_file}")

            avg_trip_length_file = f"{self.output_dir}/BATS2023_avgtriplen.csv"
            results["avg_trip_lengths"].to_csv(avg_trip_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_trip_lengths"],
                sheet_name='BATS 2023 TLFD',
                start_row=58,
                start_col=3,
                source_row=57,
                source_col=3,
                source_text=f"Source: {avg_trip_length_file}",

            )
            self.logger.info(f"Saving average trip lengths to {avg_trip_length_file}")
        else:
            tlfd_file = f"{self.output_dir}/09_nonwork_destination_TM_TLFD.csv"
            results["trip_tlfd"].to_csv(tlfd_file, index=False)
            self.write_dataframe_to_sheet(
                results["trip_tlfd"],
                start_row=3,
                start_col=1,
                source_row=2,
                source_col=1,
                source_text=f"Source: {tlfd_file}",
            )
            self.logger.info(f"Saving trip length frequency distributions to {tlfd_file}")

            avg_trip_length_file = f"{self.output_dir}/09_nonwork_destination_TM_avgtriplen.csv"
            results["avg_trip_lengths"].to_csv(avg_trip_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_trip_lengths"],
                start_row=3,
                start_col=10,
                source_row=2,
                source_col=10,
                source_text=f"Source: {avg_trip_length_file}",
            )
            self.logger.info(f"Saving average trip lengths to {avg_trip_length_file}")


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