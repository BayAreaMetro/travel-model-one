"""Non-work destination choice calibration submodel (submodel 09)."""
import argparse
import os
import sys
import numpy as np
import pandas as pd


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, add_county_info, create_histogram_tlfd
from calibration_data_models import (
    NonMandAvgTourLength,
    NonMandTourLengthFrequency,
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

    def __init__(
        self,
        config_file: str = None,
        county_filters: list[str] | None = None,
    ):
        super().__init__("09", config_file)
        config_counties = self.submodel_config.get("county_filter_values")
        if county_filters is None and config_counties:
            if isinstance(config_counties, str):
                county_filters = [token.strip() for token in config_counties.split(",") if token.strip()]
            elif isinstance(config_counties, list):
                county_filters = [str(token).strip() for token in config_counties if str(token).strip()]

        self.county_filters = county_filters or []

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
        results = self._build_summary_tables(tour_results)

        # Optional second run for selected counties (full run is always retained).
        if self.county_filters:
            county_name_lookup = {name.lower(): name for name in self.county_lookup.values()}
            selected_counties = set()
            for token in self.county_filters:
                raw = str(token).strip()
                if not raw:
                    continue
                if raw.isdigit():
                    county_name = self.county_lookup.get(int(raw))
                else:
                    county_name = county_name_lookup.get(raw.replace("_", " ").lower())
                if county_name:
                    selected_counties.add(county_name)

            if not selected_counties:
                self.logger.warning(
                    "County filter requested but no valid counties were resolved; skipping filter run."
                )
                filtered_tours = pd.DataFrame(columns=tour_results.columns)
            else:
                taz_data = pd.read_csv(
                    self.config.get("data_sources", "taz_data"),
                    usecols=["ZONE", "COUNTY"],
                )
                tours_with_county = add_county_info(
                    tour_results,
                    taz_data,
                    self.county_lookup,
                    taz_col="orig_taz",
                    county_col_name="orig_county_id",
                    county_name_col="orig_county",
                )
                tours_with_county = add_county_info(
                    tours_with_county,
                    taz_data,
                    self.county_lookup,
                    taz_col="dest_taz",
                    county_col_name="dest_county_id",
                    county_name_col="dest_county",
                )

                county_mask = tours_with_county["orig_county"].isin(selected_counties) | tours_with_county[
                    "dest_county"
                ].isin(selected_counties)

                filtered_tours = tours_with_county.loc[county_mask, tour_results.columns]
                self.logger.info(
                    "County-filtered run selected %d of %d tours using counties=%s",
                    len(filtered_tours),
                    len(tour_results),
                    sorted(selected_counties),
                )

            results["county_filtered"] = self._build_summary_tables(filtered_tours)

        return results

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")

        expected_rows = 51 if self.bats_data else 150
        validate_dataframe(results["tour_tlfd"], NonMandTourLengthFrequency, expected_rows=expected_rows)
        self.logger.info("✓ Non-work TLFD validated")

        validate_dataframe(results["avg_tour_lengths"], NonMandAvgTourLength, expected_rows=7)
        self.logger.info("✓ Average tour length summary validated")

        if "county_filtered" in results:
            validate_dataframe(
                results["county_filtered"]["tour_tlfd"],
                NonMandTourLengthFrequency,
                expected_rows=expected_rows,
            )
            validate_dataframe(
                results["county_filtered"]["avg_tour_lengths"],
                NonMandAvgTourLength,
                expected_rows=7,
            )
            self.logger.info("✓ County-filtered non-work outputs validated")

    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
            tlfd_file = f"{self.output_dir}/BATS2023_TLFD.csv"
            results["tour_tlfd"].to_csv(tlfd_file, index=False)
            self.write_dataframe_to_sheet(
                results["tour_tlfd"],
                sheet_name="BATS 2023 TLFD",
                start_row=3,
                start_col=2,
                source_row=1,
                source_col=2,
                source_text=f"Source: {tlfd_file}",
            )
            self.logger.info(f"Saving tour length frequency distributions to {tlfd_file}")

            avg_tour_length_file = f"{self.output_dir}/BATS2023_avgtourlen.csv"
            results["avg_tour_lengths"].to_csv(avg_tour_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_tour_lengths"],
                sheet_name="BATS 2023 TLFD",
                start_row=58,
                start_col=3,
                source_row=57,
                source_col=3,
                source_text=f"Source: {avg_tour_length_file}",
            )
            self.logger.info(f"Saving average tour lengths to {avg_tour_length_file}")

            if "county_filtered" in results:
                tlfd_filtered = f"{self.output_dir}/BATS2023_TLFD_county_filtered.csv"
                results["county_filtered"]["tour_tlfd"].to_csv(tlfd_filtered, index=False)
                self.logger.info(f"Saving county-filtered tour length distributions to {tlfd_filtered}")

                avg_filtered = f"{self.output_dir}/BATS2023_avgtourlen_county_filtered.csv"
                results["county_filtered"]["avg_tour_lengths"].to_csv(avg_filtered, index=False)
                self.logger.info(f"Saving county-filtered average tour lengths to {avg_filtered}")
        else:
            tlfd_file = f"{self.output_dir}/09_nonwork_destination_TM_TLFD.csv"
            results["tour_tlfd"].to_csv(tlfd_file, index=False)
            self.write_dataframe_to_sheet(
                results["tour_tlfd"],
                start_row=3,
                start_col=1,
                source_row=2,
                source_col=1,
                source_text=f"Source: {tlfd_file}",
            )
            self.logger.info(f"Saving tour length frequency distributions to {tlfd_file}")

            avg_tour_length_file = f"{self.output_dir}/09_nonwork_destination_TM_avgtourlen.csv"
            results["avg_tour_lengths"].to_csv(avg_tour_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_tour_lengths"],
                start_row=3,
                start_col=10,
                source_row=2,
                source_col=10,
                source_text=f"Source: {avg_tour_length_file}",
            )
            self.logger.info(f"Saving average tour lengths to {avg_tour_length_file}")

            if "county_filtered" in results:
                tlfd_filtered = f"{self.output_dir}/09_nonwork_destination_TM_TLFD_county_filtered.csv"
                results["county_filtered"]["tour_tlfd"].to_csv(tlfd_filtered, index=False)
                self.logger.info(f"Saving county-filtered tour length distributions to {tlfd_filtered}")

                avg_filtered = f"{self.output_dir}/09_nonwork_destination_TM_avgtourlen_county_filtered.csv"
                results["county_filtered"]["avg_tour_lengths"].to_csv(avg_filtered, index=False)
                self.logger.info(f"Saving county-filtered average tour lengths to {avg_filtered}")


def main():
    """Parse CLI arguments and run the non-work destination choice calibration."""
    parser = argparse.ArgumentParser(description="Non-work destination choice calibration")
    parser.add_argument("--config", default=None, help="Path to calibration_config.yaml (default: same directory as this script)")
    parser.add_argument(
        "--counties",
        default=None,
        help=(
            "Optional comma-separated county list for a second filtered run "
            "(accepts county names or numeric county IDs)."
        ),
    )
    args = parser.parse_args()

    counties = None
    if args.counties:
        counties = [token.strip() for token in args.counties.split(",") if token.strip()]

    calibration = NonWorkDestinationChoiceCalibration(
        config_file=args.config,
        county_filters=counties,
    )
    calibration.logger.info("Starting non-work destination choice calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")


if __name__ == "__main__":
    main()