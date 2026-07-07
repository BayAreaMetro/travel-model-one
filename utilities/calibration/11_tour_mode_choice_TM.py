"""Tour mode choice calibration submodel (submodel 11).

This script ports the legacy R workflow to the shared Python calibration framework.
It supports both model-run processing and BATS survey processing:

- Model mode (bats_data = false):
  reads model outputs and scales counts by sampleshare.
- BATS mode (bats_data = true):
  reads BATS-formatted tour files and uses tour_weight for weighted summaries.

Outputs:
- 11_tour_mode_choice_TM.csv
- 11_tour_mode_choice_trnsubmode_TM.csv
- 11_tour_mode_choice_trn_ODdist_TM.csv
- 11_tour_mode_choice_auto_ODdist_TM.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase
from calibration_data_models import TourModeSummary, validate_dataframe


class TourModeChoiceCalibration(CalibrationBase):
    """Calibration processor for tour mode choice summaries."""

    def __init__(self, config_file: str | None = None):
        super().__init__("11", config_file)

        self._auto_suff_cols = ["Autos=0", "Autos<Workers", "Autos>=Workers"]
        self._default_taz_sd_file = (
            Path(__file__).resolve().parents[1] / "geographies" / "taz-superdistrict-county.csv"
        )

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
        ]

        if self.bats_data:
            indiv_cols.append("tour_weight")
            joint_cols.append("tour_weight")

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

    def _load_ferry_skims(self) -> pd.DataFrame:
        """Load ferry skim availability tables used to split LRF tours into LRT vs ferry."""
        skim_dir = self.submodel_config.get("ferry_skim_dir")
        if not skim_dir:
            skim_dir = f"{self.target_dir}/OUTPUT_00/skims"

        rows: list[pd.DataFrame] = []
        for timeperiod in ["EA", "AM", "MD", "PM", "EV"]:
            for submode in ["wlk_lrf_wlk", "drv_lrf_wlk", "wlk_lrf_drv"]:
                skim_path = Path(skim_dir) / f"trnskm{timeperiod}_{submode}.csv"
                if not skim_path.exists():
                    self.logger.warning("Ferry skim file missing, skipping: %s", skim_path)
                    continue

                skim_table = pd.read_csv(skim_path, usecols=["orig", "dest", "ivtFerry"])
                skim_table = skim_table.rename(columns={"orig": "OTAZ", "dest": "DTAZ"})
                skim_table["timeperiod"] = timeperiod
                skim_table["submode"] = submode
                rows.append(skim_table)

        if not rows:
            self.logger.warning("No ferry skims were loaded; LRF tours will remain as LRT.")
            return pd.DataFrame(columns=["OTAZ", "DTAZ", "timeperiod", "submode", "ivtFerry"])

        return pd.concat(rows, ignore_index=True)


    def _attach_auto_sufficiency(self, tours: pd.DataFrame) -> pd.DataFrame:
        """Attach and derive the auto sufficiency classification."""
        tours = tours.copy()

        hh_file = self.submodel_config.get("household_file", f"{self.target_dir}/OUTPUT_{self.calib_iter}/main/householdData_1.csv")
        
        if Path(hh_file).exists():
            hh = pd.read_csv(hh_file, usecols=['hh_id', 'autos', 'workers'])
            tours = tours.merge(hh, on='hh_id', how='left', validate='m:1')
            tours['auto_suff'] =np.where(
                tours['autos'] == 0,
                'Autos=0',
                np.where(tours['autos'] < tours['workers'], "Autos<Workers", "Autos>=Workers")
            )

            return tours
        else:
            raise FileNotFoundError(f"Household Output File not found. Cannot derive auto sufficiency: {hh_file}")


    def _aggregate_num_tours(self, df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        """Aggregate weighted or sample-scaled tour totals for requested groups."""
        if df.empty:
            return pd.DataFrame(columns=group_cols + ["num_tours"])

        grouped = df.copy()
        if self.bats_data and "tour_weight" in grouped.columns:
            grouped["tour_weight"] = pd.to_numeric(grouped["tour_weight"], errors="coerce").fillna(0)
            grouped["num_tours"] = grouped["num_participants"] * grouped["tour_weight"]
            out = grouped.groupby(group_cols, dropna=False, as_index=False)["num_tours"].sum()
        else:
            out = grouped.groupby(group_cols, dropna=False, as_index=False)["num_participants"].sum()
            out = out.rename(columns={"num_participants": "num_tours"})
            out["num_tours"] = out["num_tours"] / self.sampleshare

        return out

    def _pivot_auto_suff(self, summary: pd.DataFrame, idx_cols: list[str]) -> pd.DataFrame:
        """Pivot auto sufficiency rows into columns with stable ordering."""
        if summary.empty:
            return pd.DataFrame(columns=idx_cols + self._auto_suff_cols)

        spread = summary.pivot_table(
            index=idx_cols,
            columns="auto_suff",
            values="num_tours",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()

        spread.columns.name = None
        for col in self._auto_suff_cols:
            if col not in spread.columns:
                spread[col] = 0.0

        return spread[idx_cols + self._auto_suff_cols]

    @staticmethod
    def _period_from_hour(hour_series: pd.Series) -> pd.Series:
        hour = pd.to_numeric(hour_series, errors="coerce").fillna(0)
        return np.select(
            [hour <= 5, hour <= 10, hour <= 15, hour <= 19],
            ["EA", "AM", "MD", "PM"],
            default="EV",
        )

    def _label_lrf_submode(
        self,
        lrf_df: pd.DataFrame,
        skim_out: pd.DataFrame,
        skim_in: pd.DataFrame,
        ferry_label: str,
        lrt_label: str,
    ) -> pd.DataFrame:
        """Classify LRF tours as ferry or LRT using outbound/inbound skim availability."""
        if lrf_df.empty:
            return lrf_df

        out = lrf_df.merge(
            skim_out.rename(
                columns={
                    "OTAZ": "_out_OTAZ",
                    "DTAZ": "_out_DTAZ",
                    "timeperiod": "_out_period",
                    "ivtFerry": "_out_ivtFerry",
                }
            ),
            left_on=["orig_taz", "dest_taz", "outPeriod"],
            right_on=["_out_OTAZ", "_out_DTAZ", "_out_period"],
            how="left",
        )
        out["outFerryAvailable"] = np.where(
            pd.to_numeric(out["_out_ivtFerry"], errors="coerce").fillna(0) > 0,
            1,
            0,
        )

        out = out.merge(
            skim_in.rename(
                columns={
                    "OTAZ": "_in_OTAZ",
                    "DTAZ": "_in_DTAZ",
                    "timeperiod": "_in_period",
                    "ivtFerry": "_in_ivtFerry",
                }
            ),
            left_on=["orig_taz", "dest_taz", "inPeriod"],
            right_on=["_in_DTAZ", "_in_OTAZ", "_in_period"],
            how="left",
        )
        out["inFerryAvailable"] = np.where(
            pd.to_numeric(out["_in_ivtFerry"], errors="coerce").fillna(0) > 0,
            1,
            0,
        )

        ferry_available = (out["outFerryAvailable"] == 1) & (out["inFerryAvailable"] == 1)
        out["trn_submode"] = np.where(ferry_available, ferry_label, lrt_label)

        drop_cols = [
            "_out_OTAZ",
            "_out_DTAZ",
            "_out_period",
            "_out_ivtFerry",
            "_in_OTAZ",
            "_in_DTAZ",
            "_in_period",
            "_in_ivtFerry",
            "outFerryAvailable",
            "inFerryAvailable",
            "lrf_submode",
            "inPeriod",
            "outPeriod",
        ]
        existing_drop = [c for c in drop_cols if c in out.columns]
        return out.drop(columns=existing_drop)

    def _build_transit_submode_table(self, tours: pd.DataFrame, ferry_skim: pd.DataFrame) -> pd.DataFrame:
        """Create transit-only table with submode labels matching the legacy R output."""
        transit = tours[(tours["tour_mode"] >= 9) & (tours["tour_mode"] <= 18)].copy()
        if transit.empty:
            return transit

        non_lrf = transit[~transit["tour_mode"].isin([10, 15])].copy()
        non_lrf_map = {
            9: "Local",
            11: "Express",
            12: "HeavyRail",
            13: "CommRail",
            14: "Local",
            16: "Express",
            17: "HeavyRail",
            18: "CommRail",
        }
        non_lrf["trn_submode"] = non_lrf["tour_mode"].map(non_lrf_map)

        lrf = transit[transit["tour_mode"].isin([10, 15])].copy()
        lrf["lrf_submode"] = np.where(lrf["tour_mode"] == 10, "LRF-Walk", "LRF-Drive")

        if lrf.empty:
            return pd.concat([non_lrf], ignore_index=True)

        # Distinguish between LRT and Ferry by looking at availability
        lrf["outPeriod"] = self._period_from_hour(lrf["end_hour"])
        lrf["inPeriod"] = self._period_from_hour(lrf["start_hour"])

        lrf_walk = lrf[lrf["tour_mode"] == 10].copy()
        lrf_drive = lrf[lrf["tour_mode"] == 15].copy()

        if ferry_skim.empty:
            self.logger.warning("No Ferry Skims - LRF Mode were all assumed to be light rail")
            lrf_walk["trn_submode"] = "LRT-Walk"
            lrf_drive["trn_submode"] = "LRT-Drive"

            lrf_walk = lrf_walk.drop(columns=["lrf_submode", "inPeriod", "outPeriod"], errors="ignore")
            lrf_drive = lrf_drive.drop(columns=["lrf_submode", "inPeriod", "outPeriod"], errors="ignore")
            return pd.concat([non_lrf, lrf_walk, lrf_drive], ignore_index=True)

        skim_walk = ferry_skim[ferry_skim["submode"] == "wlk_lrf_wlk"][
            ["OTAZ", "DTAZ", "timeperiod", "ivtFerry"]
        ]
        skim_drv_out = ferry_skim[ferry_skim["submode"] == "drv_lrf_wlk"][
            ["OTAZ", "DTAZ", "timeperiod", "ivtFerry"]
        ]
        skim_drv_in = ferry_skim[ferry_skim["submode"] == "wlk_lrf_drv"][
            ["OTAZ", "DTAZ", "timeperiod", "ivtFerry"]
        ]

        lrf_walk = self._label_lrf_submode(
            lrf_walk,
            skim_out=skim_walk,
            skim_in=skim_walk,
            ferry_label="Ferry-Walk",
            lrt_label="LRT-Walk",
        )
        lrf_drive = self._label_lrf_submode(
            lrf_drive,
            skim_out=skim_drv_out,
            skim_in=skim_drv_in,
            ferry_label="Ferry-Drive",
            lrt_label="LRT-Drive",
        )

        return pd.concat([non_lrf, lrf_walk, lrf_drive], ignore_index=True)

    @staticmethod
    # Bring this in from Pipeline?
    def _map_simple_purpose(purpose_series: pd.Series) -> pd.Series:
        mapping = {
            "atwork_business": "atwork",
            "atwork_eat": "atwork",
            "atwork_maint": "atwork",
            "eatout": "ind_disc",
            "escort_kids": "ind_maint",
            "escort_no kids": "ind_maint",
            "escort_no_kids": "ind_maint",
            "othdiscr": "ind_disc",
            "othmaint": "ind_maint",
            "school_grade": "school",
            "school_high": "school",
            "shopping": "ind_maint",
            "social": "ind_disc",
            "university": "university",
            "work_low": "work",
            "work_med": "work",
            "work_high": "work",
            "work_very high": "work",
            "work_very_high": "work",
        }
        return purpose_series.astype(str).map(mapping)

    def _load_taz_sd(self) -> pd.DataFrame:
        taz_sd_file = self.submodel_config.get("taz_sd_file", str(self._default_taz_sd_file))
        if not Path(taz_sd_file).exists():
            raise FileNotFoundError(f"TAZ superdistrict file not found: {taz_sd_file}")

        taz_sd = pd.read_csv(taz_sd_file, usecols=["ZONE", "SD_NAME"])
        return taz_sd

    def _build_transit_od_summary(self, transit: pd.DataFrame) -> pd.DataFrame:
        """Summarize transit tours by purpose/submode/access and SD-to-SD pairs."""
        if transit.empty:
            return pd.DataFrame(
                columns=[
                    "key",
                    "trn_access_mode",
                    "trn_submode",
                    "orig_SD",
                    "dest_SD",
                    "simple_purpose",
                    "num_tours",
                ]
            )

        trn = transit.copy()
        trn["simple_purpose"] = self._map_simple_purpose(trn["tour_purpose"])
        trn["simple_purpose"] = trn["simple_purpose"].fillna("other")

        # Combine Ferry-Drive and Ferry-Walk to Ferry and LRT-Drive and LRT-Walk to LRT
        trn["trn_submode"] = (
            trn["trn_submode"]
            .replace({"Ferry-Drive": "Ferry", "Ferry-Walk": "Ferry"})
            .replace({"LRT-Drive": "LRT", "LRT-Walk": "LRT"})
        )
        trn["trn_access_mode"] = np.where(trn["tour_mode"] <= 13, "walk", "drive")

        # Add superdistrict for orig, dest
        taz_sd = self._load_taz_sd()
        trn = trn.merge(
            taz_sd.rename(columns={"ZONE": "orig_taz", "SD_NAME": "orig_SD"}),
            on="orig_taz",
            how="left",
        )
        trn = trn.merge(
            taz_sd.rename(columns={"ZONE": "dest_taz", "SD_NAME": "dest_SD"}),
            on="dest_taz",
            how="left",
        )

        trn["orig_SD"] = trn["orig_SD"].fillna("Unknown")
        trn["dest_SD"] = trn["dest_SD"].fillna("Unknown")

        trn_copy = trn.copy()
        expanded = pd.concat(
            [
                trn_copy,
                trn_copy.assign(simple_purpose="Total"),    # All Purpose
                trn_copy.assign(trn_submode="Total"),       # All submodes
                trn_copy.assign(trn_access_mode="Total"),   # All Access Modes
                trn_copy.assign(simple_purpose="Total",     # Purpose + Submodes
                                trn_submode="Total"),
                trn_copy.assign(simple_purpose="Total",     # Purpose + Access
                                trn_access_mode="Total"),
                trn_copy.assign(trn_submode="Total",        # Submodes + Access
                                trn_access_mode="Total"),
                trn_copy.assign(simple_purpose="Total",     # Purpose + Submodes + Access
                                trn_submode="Total", 
                                trn_access_mode="Total"),
            ],
            ignore_index=True,
        )

        summary = self._aggregate_num_tours(
            expanded,
            ["simple_purpose", "trn_access_mode", "trn_submode", "orig_SD", "dest_SD"],
        )

        summary["key"] = summary[
            ["trn_access_mode", "trn_submode", "orig_SD", "dest_SD", "simple_purpose"]
        ].astype(str).agg("-".join, axis=1)

        return summary[
            [
                "key",
                "trn_access_mode",
                "trn_submode",
                "orig_SD",
                "dest_SD",
                "simple_purpose",
                "num_tours",
            ]
        ]

    def _build_auto_od_summary(self, tours: pd.DataFrame) -> pd.DataFrame:
        """Summarize auto tours by SD-to-SD pairs and grouped purposes."""
        auto = tours[tours["tour_mode"] <= 6].copy()
        if auto.empty:
            return pd.DataFrame(
                columns=["auto_submode", "orig_SD_NAME", "dest_SD_NAME", "simple_purpose", "num_tours"]
            )

        auto["simple_purpose"] = self._map_simple_purpose(auto["tour_purpose"])
        # TODO: Where do the auto submode come from?
        auto["auto_submode"] = auto["tour_mode"].map({1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3})

        auto["simple_purpose2"] = np.select(
            [
                auto["simple_purpose"] == "atwork",
                (auto["simple_purpose"] == "ind_disc") & (auto["indiv_joint"] == "indiv"),
                (auto["simple_purpose"] == "ind_disc") & (auto["indiv_joint"] == "joint"),
                (auto["simple_purpose"] == "ind_maint") & (auto["indiv_joint"] == "indiv"),
                (auto["simple_purpose"] == "ind_maint") & (auto["indiv_joint"] == "joint"),
                auto["simple_purpose"] == "work",
                auto["simple_purpose"] == "university",
                auto["simple_purpose"] == "school",
            ],
            ["ATWRK", "iDISC", "jDISC", "iMAIN", "jMAIN", "WORK", "UNIV", "SCHL"],
            default="OTHER",
        )

        taz_sd = self._load_taz_sd()
        auto = auto.merge(
            taz_sd.rename(columns={"ZONE": "orig_taz", "SD_NAME": "orig_SD_NAME"}),
            on="orig_taz",
            how="left",
        )
        auto = auto.merge(
            taz_sd.rename(columns={"ZONE": "dest_taz", "SD_NAME": "dest_SD_NAME"}),
            on="dest_taz",
            how="left",
        )

        summary = self._aggregate_num_tours(
            auto,
            ["simple_purpose2", "auto_submode", "orig_SD_NAME", "dest_SD_NAME"],
        )
        summary = summary.rename(columns={"simple_purpose2": "simple_purpose"})

        return summary[["auto_submode", "orig_SD_NAME", "dest_SD_NAME", "simple_purpose", "num_tours"]]

    def process_data(self) -> dict:
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS INPUT DATA\n{sep}")

     
            # Make each tour purpose its own column?

        tours = self._load_tours()
        tours = self._attach_auto_sufficiency(tours)

        # Main tour mode summary by auto sufficiency.
        mode_summary_long = self._aggregate_num_tours(
            tours,
            ["auto_suff", "indiv_joint", "tour_purpose", "tour_mode"],
        )
        mode_summary = self._pivot_auto_suff(
            mode_summary_long,
            ["indiv_joint", "tour_purpose", "tour_mode"],
        )

        if self.bats_data:
            return {'tour_mode_summary': mode_summary}

        # Process only for model data
        ferry_skim = self._load_ferry_skims()
        transit = self._build_transit_submode_table(tours, ferry_skim)

        trn_summary_long = self._aggregate_num_tours(
            transit,
            ["auto_suff", "indiv_joint", "tour_purpose", "trn_submode"],
        )
        trn_summary = self._pivot_auto_suff(
            trn_summary_long,
            ["indiv_joint", "tour_purpose", "trn_submode"],
        )

        trn_od_summary = self._build_transit_od_summary(transit)
        auto_od_summary = self._build_auto_od_summary(tours)

        return {
            "tour_mode_summary": mode_summary,
            "transit_mode_summary": trn_summary,
            "transit_od_summary": trn_od_summary,
            "auto_od_summary": auto_od_summary,
        }

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")

        validate_dataframe(results["tour_mode_summary"], TourModeSummary)
        self.logger.info("✓ Tour mode summary validated")

    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
            mode_summary_file = f"{self.output_dir}/BATS2023_tour_mode_choice.csv"
            results['tour_mode_summary'].to_csv(mode_summary_file, index=False)
            self.logger.info("Wrote %s", mode_summary_file)
        else:
            mode_summary_file = f"{self.output_dir}/11_tour_mode_choice_TM.csv"
            trn_summary_file = f"{self.output_dir}/11_tour_mode_choice_trnsubmode_TM.csv"
            trn_od_file = f"{self.output_dir}/11_tour_mode_choice_trn_ODdist_TM.csv"
            auto_od_file = f"{self.output_dir}/11_tour_mode_choice_auto_ODdist_TM.csv"

            results["mode_summary"].to_csv(mode_summary_file, index=False)
            results["transit_mode_summary"].to_csv(trn_summary_file, index=False)
            results["transit_od_summary"].to_csv(trn_od_file, index=False)
            results["auto_od_summary"].to_csv(auto_od_file, index=False)

            self.logger.info("Wrote %s", mode_summary_file)
            self.logger.info("Wrote %s", trn_summary_file)
            self.logger.info("Wrote %s", trn_od_file)
            self.logger.info("Wrote %s", auto_od_file)

            self.write_dataframe_to_sheet(
                results["mode_summary"],
                start_row=2,
                start_col=1,
                sheet_name="modeldata",
                source_row=1,
                source_col=1,
                source_text=f"Source: {mode_summary_file}",
            )
            self.write_dataframe_to_sheet(
                results["transit_mode_summary"],
                start_row=2,
                start_col=11,
                sheet_name="modeldata",
                source_row=1,
                source_col=11,
                source_text=f"Source: {trn_summary_file}",
            )
            self.write_dataframe_to_sheet(
                results["transit_od_summary"],
                start_row=2,
                start_col=19,
                sheet_name="modeldata",
                source_row=1,
                source_col=19,
                source_text=f"Source: {trn_od_file}",
            )



def main():
    parser = argparse.ArgumentParser(description="Tour mode choice calibration")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to calibration_config.yaml (default: same directory as this script)",
    )
    args = parser.parse_args()

    calibration = TourModeChoiceCalibration(config_file=args.config)
    calibration.run()


if __name__ == "__main__":
    main()
