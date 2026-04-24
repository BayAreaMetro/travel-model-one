"""Usual work and school location calibration summary."""

import argparse

import numpy as np
import pandas as pd

from cubeio import tpp

from .calibration_data_models import (
    AverageTripLength,
    CountyTripSummary,
    TripLengthFrequency,
    validate_dataframe,
)
from .calibration_framework import CalibrationBase, add_county_info, create_histogram_tlfd


class WorkSchoolLocationCalibration(CalibrationBase):
    """Calibration processor for usual work and school location."""

    def __init__(self, config_file: str | None = None, *, config: dict | None = None) -> None:
        """Initialize work/school location calibration."""
        super().__init__("01", config_file, config=config)
        self.bats_data = self.submodel_config.get("bats_data", False)

    def process_data(self) -> dict:  # noqa: PLR0915
        """Process the usual work and school location data."""
        # Load input data
        sep = "=" * 80
        self.logger.info("\n%s\nPROCESS INPUT DATA\n%s", sep, sep)
        self.logger.info("Loading input data files:")
        self.logger.info("TAZ Data: %s", self.config.get("data_sources", "taz_data"))
        self.logger.info("Work School Location: %s", self.submodel_config["input_file"])
        taz_data = pd.read_csv(self.config.get("data_sources", "taz_data"))
        wsloc_results = pd.read_csv(self.submodel_config["input_file"])

        # Load distance skim
        if self.config.get("data_sources", "dist_skim").endswith(".csv"):
            dist_skim = pd.read_csv(
                self.config.get("data_sources", "dist_skim"), header=0, usecols=["orig", "dest", "DIST"]  # noqa: E501
            )
        elif self.config.get("data_sources", "dist_skim").endswith(".tpp"):
            # Load TPP file using tpp package
            _skims = tpp.read_tpp(self.config.get("data_sources", "dist_skim"))
            n_zones = _skims["zones"]
            taz_ids = np.arange(1, n_zones + 1)
            orig, dest = np.meshgrid(taz_ids, taz_ids, indexing="ij")
            dist_skim = pd.DataFrame({
                "orig": orig.ravel(),
                "dest": dest.ravel(),
                "DIST": _skims["data"]["DIST"].ravel(),
            })

        # Add Home COUNTY
        self.logger.info("Merging Home County Data")
        wsloc_results = add_county_info(
            wsloc_results,
            taz_data,
            self.county_lookup,
            taz_col="HomeTAZ",
            county_col_name="HomeCOUNTY",
            county_name_col="HomeCounty_name",
        )

        # Add Work and School COUNTY
        self.logger.info("Merging Work and School County Data")
        wsloc_results = add_county_info(
            wsloc_results,
            taz_data,
            self.county_lookup,
            taz_col="WorkLocation",
            county_col_name="WorkCOUNTY",
            county_name_col="WorkCounty_name",
        )

        wsloc_results = add_county_info(
            wsloc_results,
            taz_data,
            self.county_lookup,
            taz_col="SchoolLocation",
            county_col_name="SchoolCOUNTY",
            county_name_col="SchoolCounty_name",
        )

        # Attach distances from distance skim
        self.logger.info("Attaching work distances...")
        work_dist = dist_skim.rename(
            columns={"orig": "HomeTAZ", "dest": "WorkLocation", "DIST": "WorkDist"}
        )
        wsloc_results = wsloc_results.merge(work_dist, on=["HomeTAZ", "WorkLocation"], how="left")

        self.logger.info("Attaching school distances...")
        school_dist = dist_skim.rename(
            columns={"orig": "HomeTAZ", "dest": "SchoolLocation", "DIST": "SchoolDist"}
        )
        wsloc_results = wsloc_results.merge(
            school_dist, on=["HomeTAZ", "SchoolLocation"], how="left"
        )

        # Save enhanced wsloc_results with distances
        if self.bats_data:
            # Join with PersonData to get weights BEFORE processing
            person_data = pd.read_csv(self.submodel_config["bats_person_data"])
            wsloc_results = wsloc_results.merge(
                person_data[["hh_id", "person_id", "person_weight", "sampleRate"]],
                left_on=["HHID", "PersonID"],
                right_on=["hh_id", "person_id"],
            )
            wsloc_results = wsloc_results.fillna({"person_weight": 0})

            wsloc_with_dist_file = f"{self.target_dir}/MandatoryLocation_with_Distance.csv"

            # Process county summary using person weights
            wsloc_county = (
                wsloc_results.groupby(
                    ["HomeCOUNTY", "HomeCounty_name", "WorkCOUNTY", "WorkCounty_name"]
                )["person_weight"]
                .sum()
                .reset_index(name="num_pers")
            )
        else:
            wsloc_with_dist_file = f"{self.output_dir}/wsloc_results_with_distances.csv"

            # Process county summary using sampleshare

            wsloc_county = (
                wsloc_results.groupby(
                    ["HomeCOUNTY", "HomeCounty_name", "WorkCOUNTY", "WorkCounty_name"]
                )
                .size()
                .reset_index(name="num_pers")
            )
            wsloc_county["num_pers"] = wsloc_county["num_pers"] / self.sampleshare

        county_ids = sorted(self.county_lookup)
        wsloc_county_spread = wsloc_county.pivot_table(
            index="HomeCOUNTY", columns="WorkCOUNTY", values="num_pers"
        )
        wsloc_county_spread = wsloc_county_spread.reindex(index=county_ids, columns=county_ids)
        wsloc_county_spread = wsloc_county_spread.rename(
            index=self.county_lookup, columns=self.county_lookup
        )
        wsloc_county_spread.index.name = "HomeCounty_name"
        wsloc_county_spread = wsloc_county_spread.fillna(0).reset_index()

        wsloc_results.to_csv(wsloc_with_dist_file, index=False)
        self.logger.info("Saved wsloc results with distances to %s", wsloc_with_dist_file)

        # Process trip length distributions and averages
        self.logger.info("Processing trip length distributions...")
        trip_tlfd_results, avg_trip_lengths = self._build_trip_tlfds(wsloc_results)

        # Process average trip lengths
        avg_trip_lengths_df = pd.DataFrame(avg_trip_lengths)
        avg_triplen_spread = avg_trip_lengths_df.pivot_table(
            index="county", columns="trip_type", values="mean_trip_length"
        )
        avg_triplen_spread = avg_triplen_spread.reset_index()

        # Reorder columns
        desired_cols = ["county"] + [
            col for col in ["work", "univ", "school"] if col in avg_triplen_spread.columns
        ]
        avg_triplen_spread = avg_triplen_spread[desired_cols]

        return {
            "county_summary": wsloc_county_spread,
            "trip_tlfd_work": trip_tlfd_results.get("work"),
            "trip_tlfd_univ": trip_tlfd_results.get("univ"),
            "trip_tlfd_school": trip_tlfd_results.get("school"),
            "avg_trip_lengths": avg_triplen_spread,
        }

    # ------------------------------------------------------------------
    # Helpers for process_data
    # ------------------------------------------------------------------

    def _filter_trip_dists(self, wsloc_results: pd.DataFrame, trip_type: str) -> pd.DataFrame:
        """Filter wsloc results to trip distances for a single trip type."""
        if trip_type == "work":
            filter_cols = ["HomeCounty_name", "EmploymentCategory", "WorkDist"]
            if self.bats_data:
                filter_cols.append("person_weight")
            out = wsloc_results[wsloc_results["WorkLocation"] > 0][filter_cols].copy()
            return out.rename(columns={"WorkDist": "DIST"})

        # univ and school share the same base columns
        filter_cols = ["HomeCounty_name", "StudentCategory", "SchoolDist"]
        if self.bats_data:
            filter_cols.append("person_weight")

        category = "College or higher" if trip_type == "univ" else "Grade or high school"
        out = wsloc_results[
            (wsloc_results["SchoolLocation"] > 0) & (wsloc_results["StudentCategory"] == category)
        ][filter_cols].copy()
        return out.rename(columns={"SchoolDist": "DIST"})

    def _compute_hist_and_mean(self, dists: pd.DataFrame) -> tuple[pd.DataFrame, float]:
        """Return (histogram_df, weighted_mean) for a set of trip distances."""
        if self.bats_data:
            hist_df = create_histogram_tlfd(
                dists["DIST"], bins=range(52), weights=dists["person_weight"]
            )
            mean = np.average(dists["DIST"], weights=dists["person_weight"])
        else:
            hist_df = create_histogram_tlfd(dists["DIST"], sampleshare=self.sampleshare)
            mean = dists["DIST"].mean()
        return hist_df, mean

    def _build_trip_tlfds(
        self, wsloc_results: pd.DataFrame
    ) -> tuple[dict[str, pd.DataFrame], list[dict]]:
        """Build TLFDs and average trip lengths for work/univ/school."""
        trip_tlfd_results: dict[str, pd.DataFrame] = {}
        avg_trip_lengths: list[dict] = []
        max_bin = 52 if self.bats_data else 151

        for trip_type in ("work", "univ", "school"):
            trip_dists = self._filter_trip_dists(wsloc_results, trip_type)
            trip_tlfd = pd.DataFrame({"distbin": range(1, max_bin)})

            # Per-county histograms
            for county in self.county_lookup.values():
                county_dists = trip_dists[trip_dists["HomeCounty_name"] == county]
                if len(county_dists) == 0:
                    continue
                hist_df, mean = self._compute_hist_and_mean(county_dists)
                hist_df = hist_df.rename(columns={"count": county})
                trip_tlfd = trip_tlfd.merge(hist_df, on="distbin", how="left")
                avg_trip_lengths.append(
                    {"county": county, "trip_type": trip_type, "mean_trip_length": mean}
                )

            # Total across all counties
            if len(trip_dists) > 0:
                hist_df, total_mean = self._compute_hist_and_mean(trip_dists)
                hist_df = hist_df.rename(columns={"count": "Total"})
                trip_tlfd = trip_tlfd.merge(hist_df, on="distbin", how="left")
                avg_trip_lengths.append(
                    {"county": "Total", "trip_type": trip_type, "mean_trip_length": total_mean}
                )

            # Reorder columns and fill NaN
            county_cols = sorted(
                col for col in trip_tlfd.columns if col not in ("distbin", "Total")
            )
            col_order = (
                ["distbin"] + county_cols + (["Total"] if "Total" in trip_tlfd.columns else [])
            )
            trip_tlfd_results[trip_type] = trip_tlfd[col_order].fillna(0)

        return trip_tlfd_results, avg_trip_lengths

    def validate_outputs(self, results: dict) -> None:
        """Validate outputs before generating the files and updating excel."""
        sep = "=" * 80
        self.logger.info("\n%s\nOUTPUT VAlIDATION\n%s", sep, sep)

        # Validate county summary
        if results["county_summary"] is not None:
            validate_dataframe(results["county_summary"], CountyTripSummary)
            self.logger.info("County Summary Validated")

        # Validate trip length frequency distribution
        expected_rows = 51 if self.bats_data else 150
        for trip_type in ["work", "univ", "school"]:
            df = results[f"trip_tlfd_{trip_type}"]
            if df is not None:
                validate_dataframe(df, TripLengthFrequency, expected_rows)
                self.logger.info("%s TLFD validated", trip_type.capitalize())

        # Validate average trip lengths
        if results["avg_trip_lengths"] is not None:
            validate_dataframe(results["avg_trip_lengths"], AverageTripLength)
            self.logger.info("Average Trip Length Summary Validated")

    def generate_outputs(self, results: dict) -> None:
        """Generate output files and Excel updates."""
        sep = "=" * 80
        self.logger.info("\n%s\nGENERATE OUTPUTS\n%s", sep, sep)

        if self.bats_data:
            trip_types = [("work", 2), ("univ", 15), ("school", 28)]
            for trip_type, col in trip_types:
                if results[f"trip_tlfd_{trip_type}"] is not None:
                    tlfd_file = f"{self.output_dir}/{trip_type}TLFD.csv"
                    results[f"trip_tlfd_{trip_type}"].to_csv(tlfd_file, index=False)
                    self.write_dataframe_to_sheet(
                        results[f"trip_tlfd_{trip_type}"],
                        start_row=4,
                        start_col=col,
                        sheet_name="BATS 2023 TLFD",
                        source_row=2,
                        source_col=col,
                        source_text=f"Source: {tlfd_file}",
                    )

                    self.logger.info(
                        "Saving trip length frequency distributions for %s to %s",
                        trip_type,
                        tlfd_file,
                    )

            # Average trip lengths
            avg_length_file = f"{self.output_dir}/AvgTripLen.csv"
            results["avg_trip_lengths"].to_csv(avg_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_trip_lengths"],
                start_row=3,
                start_col=1,
                sheet_name="BATS 2023 AvgTripLen",
                source_row=1,
                source_col=1,
                source_text=f"Source: {avg_length_file}",
            )
            self.logger.info("Saving average trip lengths to %s", avg_length_file)

        else:
            # County summary
            self.logger.info("Generating output files and Excel updates...")

            county_file = (
                f"{self.output_dir}/{self.submodel}_usual_work_school_location_TM_county.csv"
            )

            results["county_summary"].to_csv(county_file, index=False)

            self.write_dataframe_to_sheet(
                results["county_summary"],
                start_row=4,
                start_col=1,
                source_row=1,
                source_col=1,
                source_text=f"Source: {county_file}",
            )

            self.logger.info("Saving county summary to %s", county_file)
            # Trip length frequency distributions
            trip_types = [("work", 1), ("univ", 14), ("school", 27)]
            for trip_type, col in trip_types:
                if results[f"trip_tlfd_{trip_type}"] is not None:
                    tlfd_file = (
                        f"{self.output_dir}/{self.submodel}"
                        f"_usual_work_school_location_TM_{trip_type}_TLFD.csv"
                    )
                    results[f"trip_tlfd_{trip_type}"].to_csv(tlfd_file, index=False)
                    self.write_dataframe_to_sheet(
                        results[f"trip_tlfd_{trip_type}"],
                        start_row=19,
                        start_col=col,
                        source_row=17,
                        source_col=col,
                        source_text=f"Source: {tlfd_file}",
                    )
                    self.logger.info(
                        "Saving trip length frequency distributions for %s to %s",
                        trip_type,
                        tlfd_file,
                    )

            # Average trip lengths
            avg_length_file = (
                f"{self.output_dir}/{self.submodel}_usual_work_school_location_TM_avgtriplen.csv"
            )
            results["avg_trip_lengths"].to_csv(avg_length_file, index=False)
            self.write_dataframe_to_sheet(
                results["avg_trip_lengths"],
                start_row=4,
                start_col=14,
                source_row=3,
                source_col=14,
                source_text=f"Source: {avg_length_file}",
            )
            self.logger.info("Saving average trip lengths to %s", avg_length_file)


def main() -> None:
    """Main entry point for the usual work and school location calibration."""
    parser = argparse.ArgumentParser(description="Usual work and school location calibration")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to calibration_config.yaml (default: same directory as this script)",
    )
    args = parser.parse_args()

    calibration = WorkSchoolLocationCalibration(config_file=args.config)
    calibration.logger.info("Starting usual work and school location calibration...")
    calibration.run()
    calibration.logger.info("Calibration complete.")


if __name__ == "__main__":
    main()


# %%
