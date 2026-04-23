import os
import sys

import pandas as pd

# Import the calibration framework
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_data_models import (
    CDAPSummary,
    CDAPSummaryBATS,
    CTRAMPPersonType,
    validate_dataframe,
)
from calibration_framework import CalibrationBase


class DailyActivityPatternCalibration(CalibrationBase):
    """Calibration processor for coordinated daily activity pattern."""

    def __init__(self, config_file: str | None = None) -> None:
        super().__init__("04", config_file)
        self.bats_data = self.submodel_config.get("bats_data", False)

    def process_data(self) -> dict:
        """Process the coordinated daily activity pattern data."""
        # Load input data
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS DATA\n{sep}")
        cdap_results = pd.read_csv(self.submodel_config["input_file"])
        self.logger.info(f"Reading in CDAP Input File: {self.submodel_config['input_file']}")
        CTRAMPPersonTypeLookUp = {person.label: person.id for person in CTRAMPPersonType}

        if self.bats_data:
            cdap_results["person_type"] = cdap_results["type"].map(CTRAMPPersonTypeLookUp)
            cdap_results = cdap_results.fillna({"person_weight": 0})
            cdap_ptype = (
                cdap_results.groupby(["person_type", "activity_pattern"])["person_weight"]
                .sum()
                .reset_index(name="num_pers")
            )

            return {"person_type_summary": cdap_ptype}

        # Summarize by person type and activity string
        cdap_ptype = (
            cdap_results.groupby(["PersonType", "ActivityString"])
            .size()
            .reset_index(name="num_pers")
        )
        cdap_ptype["num_pers"] = cdap_ptype["num_pers"] / self.sampleshare

        # Pivot to spread format
        cdap_ptype_spread = cdap_ptype.pivot(
            index="PersonType", columns="ActivityString", values="num_pers"
        )
        cdap_ptype_spread = cdap_ptype_spread.fillna(0).reset_index()

        return {"person_type_summary": cdap_ptype_spread}

    def validate_outputs(self, results: dict) -> None:
        """Validate outputs before generating the files and updating excel."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VAlIDATION\n{sep}")

        # Validate person type summary
        if results["person_type_summary"] is not None:
            if self.bats_data:
                validate_dataframe(results["person_type_summary"], CDAPSummaryBATS)
                self.logger.info("Person Type BATS Summary Validated")
            else:
                validate_dataframe(results["person_type_summary"], CDAPSummary)
                self.logger.info("Person Type Summary Validated")

    def generate_outputs(self, results: dict) -> None:
        """Generate output files and Excel updates."""
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        # Person type summary
        if results["person_type_summary"] is not None:
            if self.bats_data:
                summary_file = f"{self.output_dir}/dap_summaries.csv"
                self.write_dataframe_to_sheet(
                    results["person_type_summary"],
                    start_row=2,
                    start_col=2,
                    sheet_name="BATS 2023",
                    source_row=1,
                    source_col=2,
                    source_text=f"Source: {summary_file}",
                )
            else:
                summary_file = f"{self.output_dir}/{self.submodel}_daily_activity_pattern_TM.csv"
                self.write_dataframe_to_sheet(
                    results["person_type_summary"],
                    start_row=2,
                    start_col=1,
                    source_row=1,
                    source_col=1,
                    source_text=f"Source: {summary_file}",
                )

            results["person_type_summary"].to_csv(summary_file, index=False)
            self.logger.info(f"Saving person type summary to {summary_file}")


def main() -> None:
    """Main entry point for the daily activity pattern calibration."""
    calibration = DailyActivityPatternCalibration()
    calibration.run()


if __name__ == "__main__":
    main()
