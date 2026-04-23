"""Auto ownership calibration summary."""

import shutil
import sys
from pathlib import Path

import pandas as pd

# Import the calibration framework
sys.path.append(str(Path(__file__).resolve().parent))
import contextlib

from calibration_data_models import (
    AutoOwnershipCountySummary,
    AutoOwnershipLongSummary,
    AutoOwnershipTAZSummary,
    validate_dataframe,
)
from calibration_framework import CalibrationBase, add_county_info


class AutoOwnershipCalibration(CalibrationBase):
    """Calibration processor for auto ownership."""

    def __init__(self, config_file: str | None = None) -> None:
        """Initialize auto ownership calibration."""
        super().__init__("02", config_file)

    def process_data(self) -> dict:
        """Process the auto ownership data."""
        sep = "=" * 80
        self.logger.info("\n%s\nPROCESS INPUT DATA\n%s", sep, sep)

        self.logger.info("Loading input data files:")
        self.logger.info("TAZ Data: %s", self.config.get("data_sources", "taz_data"))
        self.logger.info("Auto Ownership: %s", self.submodel_config["ao_results"])
        # Load input data
        pop_households = pd.read_csv(self.submodel_config["input_file"])[["HHID", "TAZ", "PERSONS"]]
        taz_data = pd.read_csv(self.config.get("data_sources", "taz_data"))
        ao_results = pd.read_csv(self.submodel_config["ao_results"])

        # Add TAZ and PERSONS to ao_results
        ao_results = ao_results.merge(pop_households, left_on="HHID", right_on="HHID", how="left")

        # Add COUNTY and county name
        ao_results = add_county_info(ao_results, taz_data, self.county_lookup, taz_col="TAZ")

        # Summarize by county and auto ownership
        ao_county = (
            ao_results.groupby(["COUNTY", "county_name", "AO"]).size().reset_index(name="num_hh")
        )
        ao_county["num_hh"] = ao_county["num_hh"] / self.sampleshare

        # Pivot to spread format
        ao_county_spread = ao_county.pivot_table(
            index=["COUNTY", "county_name"], columns="AO", values="num_hh"
        )
        ao_county_spread = ao_county_spread.fillna(0).reset_index()
        ao_county_spread.columns = ao_county_spread.columns.astype(str)

        # Summarize by TAZ and auto ownership (long format)
        ao_taz = ao_results.groupby(["TAZ", "AO"]).size().reset_index(name="num_hh")
        ao_taz["num_hh"] = ao_taz["num_hh"] / self.sampleshare
        ao_taz["source"] = "Model"
        ao_taz = ao_taz.rename(columns={"AO": "num_vehicles"})

        # TAZ spread format
        ao_taz_spread = ao_taz.pivot_table(
            index=["TAZ", "source"], columns="num_vehicles", values="num_hh"
        )
        ao_taz_spread = ao_taz_spread.fillna(0).reset_index()
        ao_taz_spread.columns = ao_taz_spread.columns.astype(str)

        return {"county_summary": ao_county_spread, "taz_long": ao_taz, "taz_spread": ao_taz_spread}

    def validate_outputs(self, results: dict) -> None:
        """Validate outputs before generating the files and updating excel."""
        sep = "=" * 80
        self.logger.info("\n%s\nOUTPUT VAlIDATION\n%s", sep, sep)

        # Validate county summary
        if results["county_summary"] is not None:
            validate_dataframe(
                results["county_summary"], AutoOwnershipCountySummary, expected_rows=9
            )
            self.logger.info("Auto Ownership County Summary Validated")

        # Validate TAZ Summaries
        if results["taz_spread"] is not None:
            validate_dataframe(results["taz_spread"], AutoOwnershipTAZSummary)
            self.logger.info("Auto Ownership TAZ Summary Validated")

        if results["taz_long"] is not None:
            validate_dataframe(results["taz_long"], AutoOwnershipLongSummary)
            self.logger.info("Auto Ownership TAZ Long Summary Validated")

    def generate_outputs(self, results: dict) -> None:
        """Generate output files and Excel updates."""
        sep = "=" * 80
        self.logger.info("\n%s\nGENERATE OUTPUTS\n%s", sep, sep)
        # County summary
        county_file = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM.csv"
        results["county_summary"].to_csv(county_file, index=False)
        self.write_dataframe_to_sheet(
            results["county_summary"],
            start_row=3,
            start_col=1,
            source_row=1,
            source_col=1,
            source_text=f"Source: {county_file}",
        )

        # TAZ summaries
        results["taz_long"] = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM_long.csv"
        results["taz_spread"] = f"{self.output_dir}/{self.submodel}_auto_ownership_TAZ_TM.csv"

        # Copy ACS comparison file
        # TODO: Update and Verify source
        acs_source = (
            "M:/Data/Census/ACS/ACS2013-2017/"
            "B08201 Household Size by Vehicles Available/"
            "vehiclesAvailableByTazACS_long.csv"
        )
        acs_dest = Path(self.output_dir) / f"{self.submodel}_auto_ownership_TAZ_ACS.csv"
        with contextlib.suppress(Exception):
            shutil.copy(acs_source, acs_dest)


def main() -> None:
    """Main entry point for the auto ownership calibration."""
    calibration = AutoOwnershipCalibration()
    calibration.run()


if __name__ == "__main__":
    main()
