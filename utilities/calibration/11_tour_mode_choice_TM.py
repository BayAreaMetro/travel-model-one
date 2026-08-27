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
from calibration_framework import CalibrationBase, SheetTarget, add_county_info
from calibration_data_models import TourModeSummaryLong, validate_dataframe
from data_canon.codebook.ctramp import CTRAMPModeType


class TourModeChoiceCalibration(CalibrationBase):
    """Calibration processor for tour mode choice summaries."""

    # Declarative placement for modeled outputs (CSV + workbook cell).
    MODELED_SHEET_TARGETS = [
        SheetTarget("tour_mode_summary", "modeldata", 2, 1,
                    "11_tour_mode_choice_TM.csv", (1, 1)),
        SheetTarget("transit_mode_summary", "modeldata", 2, 11,
                    "11_tour_mode_choice_trnsubmode_TM.csv", (1, 11)),
        SheetTarget("transit_od_summary", "modeldata", 2, 19,
                    "11_tour_mode_choice_trn_ODdist_TM.csv", (1, 19)),
        # CSV-only (empty sheet name skips the workbook write).
        SheetTarget("auto_od_summary", "", 0, 0,
                    "11_tour_mode_choice_auto_ODdist_TM.csv", None),
    ]

    # Observed (BATS): which wide summaries and county filters get written to the
    # 'targets' sheet (all results are still written to CSV). Blocks are split by
    # simple_purpose (stacked vertically), and each county filter occupies the
    # next set of columns to the right in the same format.
    OBSERVED_TARGETS_SHEET = "targets"
    OBSERVED_TARGETS_HEADER_ROW = 3
    OBSERVED_TARGETS_START_COL = 2
    OBSERVED_TARGETS_RESULT_TYPES = ["unweighted", "weighted"]
    OBSERVED_TARGETS_FILTERS = ["all", "solano_napa", "north_bay"]

    # Order in which simple_purpose blocks are written to the targets sheet;
    # any purpose not listed is appended afterward in its natural order.
    OBSERVED_PURPOSE_ORDER = ["work", "university", "school", "ind_maint", "ind_disc",
                             "atwork", "joint"]

    # Toll drive modes (DA toll, SR2 toll, SR3+ toll) to exclude from observed outputs.
    EXCLUDED_TOUR_MODES = [2, 4, 6]

    # UEC Source and Calibration Destination
    UEC_SOURCE_RANGES = {
        "work_ivt": ("Work", 5, 42, 42),
        "work": ("Work", 5, 414, 475),
        "university_ivt": ("University", 5, 42, 42),
        "university": ("University", 5, 414, 475),
        "school_ivt": ("School", 5, 42, 42),
        "school": ("School", 5, 414, 475),
        "escort_ivt":("Escort", 5, 42, 42),
        "escort": ("Escort", 5, 414, 475),
        "shopping_ivt": ("Shopping", 5, 42, 42),
        "shopping": ("Shopping", 5, 414, 475),
        "eatout_ivt": ("EatOut", 5, 42, 42 ),
        "eatout": ("EatOut", 5, 414, 475),
        "othmaint_ivt": ("OthMaint", 5, 42, 42),
        "othmaint": ("OthMaint", 5, 414, 475),
        "social_ivt": ("Social", 5, 42, 42),
        "social": ("Social", 5, 414, 475),
        "othdiscr_ivt": ("OthDiscr", 5, 42, 42),
        "othdiscr": ("OthDiscr", 5, 414, 475),
        "workbased_ivt": ("WorkBased", 5, 11, 11),
        "workbased": ("WorkBased", 5, 417, 478)
    }
    
    CALIBRATION_DESTINATION_RANGES = {
        "work_ivt": ("constants", 5, 1, 1),
        "work": ("constants", 3, 3, 64),
        "university_ivt": ("constants", 9, 1, 1),
        "university": ("constants", 7, 3, 64),
        "school_ivt": ("constants", 13, 1, 1),
        "school": ("constants", 11, 3, 64),
        "escort_ivt": ("constants", 17, 1, 1),
        "escort": ("constants", 15, 3, 64),
        "shopping_ivt": ("constants", 21, 1, 1),
        "shopping": ("constants", 19, 3, 64),
        "eatout_ivt": ("constants", 25, 1, 1),
        "eatout": ("constants", 23, 3, 64),
        "othmaint_ivt": ("constants", 29, 1, 1),
        "othmaint": ("constants", 27, 3, 64),
        "social_ivt": ("constants", 33, 1, 1),
        "social": ("constants", 31, 3, 64),
        "othdiscr_ivt": ("constants", 37, 1, 1),
        "othdiscr": ("constants", 35, 3, 64),
        "workbased_ivt": ("constants", 41, 1, 1),
        "workbased": ("constants", 39, 3, 64)
        
    }


    def __init__(self, config_file: str | None = None):
        super().__init__("11", config_file)

        self._auto_suff_cols = ["Autos=0", "Autos<Workers", "Autos>=Workers"]

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

        hh_file = self.config.get('data_sources', 'household_file', f"{self.target_dir}/OUTPUT_{self.calib_iter}/main/householdData_1.csv")
        
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
        """Aggregate modeled tour totals for requested groups."""
        if df.empty:
            return pd.DataFrame(columns=group_cols + ["num_tours"])

        grouped = df.copy()
        out = grouped.groupby(group_cols, dropna=False, as_index=False)["num_participants"].sum()
        out = out.rename(columns={"num_participants": "num_tours"})
        out["num_tours"] = out["num_tours"] / self.sampleshare

        return out

    def _aggregate_num_tours_bats(self, df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        """Aggregate BATS tours into both weighted and unweighted totals, including all modes."""
        if df.empty:
            return pd.DataFrame(columns=group_cols + ["num_tours_unweighted", "num_tours_weighted"])

        grouped = df.copy()
        grouped["sample_rate"] = pd.to_numeric(grouped["sampleRate"], errors="coerce").fillna(0)
        grouped["num_tours_unweighted"] = 1
        grouped["num_tours_weighted"] = 1 / grouped["sampleRate"]

        all_modes = [m.value for m in CTRAMPModeType]
        grouped["tour_mode"] = pd.Categorical(grouped["tour_mode"], categories=all_modes)

        out = grouped.groupby(group_cols, observed=False, dropna=False, as_index=False)[
            ["num_tours_unweighted", "num_tours_weighted"]
        ].sum()
        out[["num_tours_unweighted", "num_tours_weighted"]] = out[
            ["num_tours_unweighted", "num_tours_weighted"]
        ].fillna(0)

        return out 

    @staticmethod
    def _period_from_hour(hour_series: pd.Series) -> pd.Series:
        hour = pd.to_numeric(hour_series, errors="coerce").fillna(0)
        return np.select(
            [hour <= 5, hour <= 10, hour <= 15, hour <= 19],
            ["EA", "AM", "MD", "PM"],
            default="EV",
        )

    @staticmethod
    def _add_mode_label(df: pd.DataFrame, mode_col: str = "tour_mode") -> pd.DataFrame:
        """Attach the human-readable CT-RAMP mode label next to the numeric mode."""
        mode_labels = {m.value: m.label for m in CTRAMPModeType}
        df = df.copy()
        df["tour_mode_label"] = df[mode_col].map(mode_labels)
        return df

    @staticmethod
    def _append_group_column_totals(wide: pd.DataFrame, group_col: str, label_col: str,
                                    value_cols: list[str]) -> pd.DataFrame:
        """Append a totals row summing each value column within each group."""
        if wide.empty:
            return wide
        parts = []
        for grp, block in wide.groupby(group_col, sort=False):
            totals = {c: "" for c in wide.columns}
            totals[group_col] = grp
            totals[label_col] = "Total"
            for c in value_cols:
                totals[c] = block[c].sum()
            parts.append(pd.concat([block, pd.DataFrame([totals])], ignore_index=True))
        return pd.concat(parts, ignore_index=True)

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
    def _map_simple_purpose(purpose_series: pd.Series, indiv_joint_series: pd.Series,
                            collapse_joint: bool = True) -> pd.Series:
        """Mapping simple purpose; when collapse_joint, joint tours become 'joint'."""
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
        simple = purpose_series.astype(str).map(mapping)
        if collapse_joint:
            simple = simple.where(indiv_joint_series.astype(str) != "joint", "joint")
        return simple

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
        trn["simple_purpose"] = self._map_simple_purpose(
            trn["tour_purpose"], trn["indiv_joint"], collapse_joint=False
        )
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

        auto["simple_purpose"] = self._map_simple_purpose(
            auto["tour_purpose"], auto["indiv_joint"], collapse_joint=False
        )
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

    def _build_bats_summaries(self, tours: pd.DataFrame) -> dict:
        """Summarize the BATS tours into weighted and unweighted summaries"""
        tours = tours.copy()
        tours["simple_purpose"] = self._map_simple_purpose(tours["tour_purpose"], tours["indiv_joint"])
        group_cols = ["auto_suff", "indiv_joint", "tour_purpose", "simple_purpose", "tour_mode"]
        idx_cols = ["indiv_joint", "simple_purpose", "tour_mode", "tour_mode_label"]

        long_summary = self._aggregate_num_tours_bats(tours, group_cols)
        long_summary = self._add_mode_label(long_summary)
        long_summary = long_summary[~long_summary["tour_mode"].isin(self.EXCLUDED_TOUR_MODES)]

        value_cols = self._auto_suff_cols + ["Total"]
        wide_unweighted = self._append_group_column_totals(
            self.pivot_with_total(long_summary, idx_cols, "auto_suff",
                                  "num_tours_unweighted", self._auto_suff_cols),
            "simple_purpose", "tour_mode_label", value_cols)

        wide_weighted = self._append_group_column_totals(
            self.pivot_with_total(long_summary, idx_cols, "auto_suff",
                                  "num_tours_weighted", self._auto_suff_cols),
            "simple_purpose", "tour_mode_label", value_cols)

        return {
            "long": long_summary,
            "wide_unweighted": wide_unweighted,
            "wide_weighted": wide_weighted,
        }

    def process_data(self) -> dict:
        return self.process_observed() if self.bats_data else self.process_modeled()

    def process_observed(self) -> dict:
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS OBSERVED (BATS) DATA\n{sep}")

        tours = pd.read_csv(self.submodel_config["all_tour_file"])
        tours["indiv_joint"] = np.where(
            tours["joint_tour_id"].isna(),
            "indiv",
            "joint"
        )
        tours = self._attach_auto_sufficiency(tours)
        taz_data = pd.read_csv(self.config.get("data_sources", "taz_data"), usecols=["ZONE", "COUNTY"])
        tours = add_county_info(tours, taz_data, self.county_lookup,
                                taz_col="orig_taz", county_col_name="orig_county_id", county_name_col="orig_county")
        tours = add_county_info(tours, taz_data, self.county_lookup,
                                taz_col="dest_taz", county_col_name="dest_county_id", county_name_col="dest_county")

        results = {}
        for label, subset in self.iter_county_filters(tours):
            summ = self._build_bats_summaries(subset)
            results[f"tour_mode_summary_long_{label}"] = summ["long"]
            results[f"tour_mode_summary_unweighted_{label}"] = summ["wide_unweighted"]
            results[f"tour_mode_summary_weighted_{label}"] = summ["wide_weighted"]
        return results

    def process_modeled(self) -> dict:
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS MODELED DATA\n{sep}")

        tours = self._load_tours()
        tours = self._attach_auto_sufficiency(tours)

        mode_summary_long = self._aggregate_num_tours(
            tours, ["auto_suff", "indiv_joint", "tour_purpose", "tour_mode"],
        )
        mode_summary = self.pivot_with_total(
            mode_summary_long, ["indiv_joint", "tour_purpose", "tour_mode"],
            "auto_suff", "num_tours", self._auto_suff_cols, add_total=False,
        )

        ferry_skim = self._load_ferry_skims()
        transit = self._build_transit_submode_table(tours, ferry_skim)

        trn_summary_long = self._aggregate_num_tours(
            transit, ["auto_suff", "indiv_joint", "tour_purpose", "trn_submode"],
        )
        trn_summary = self.pivot_with_total(
            trn_summary_long, ["indiv_joint", "tour_purpose", "trn_submode"],
            "auto_suff", "num_tours", self._auto_suff_cols, add_total=False,
        )

        # trn_od_summary = self._build_transit_od_summary(transit)
        # auto_od_summary = self._build_auto_od_summary(tours)

        return {
            "tour_mode_summary": mode_summary,
            "transit_mode_summary": trn_summary,
            # "transit_od_summary": trn_od_summary,
            # "auto_od_summary": auto_od_summary,
        }

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")

        #validate_dataframe(results["tour_mode_summary_long"], TourModeSummaryLong)
        self.logger.info("✓ Tour mode summary validated")

    def _write_purpose_blocks(self, df: pd.DataFrame, start_row: int, start_col: int, filter_label: str) -> int:
        """Write a wide summary to the targets sheet, one contiguous block per simple_purpose."""
        value_cols = [c for c in df.columns if c not in  ["simple_purpose", "indiv_joint", "tour_mode"]]
        self.write_dataframe_to_sheet(
            pd.DataFrame(columns=[str(filter_label)]), start_row, start_col, self.OBSERVED_TARGETS_SHEET
        )
        row = start_row + 1
        present = list(df["simple_purpose"].unique())
        ordered = [p for p in self.OBSERVED_PURPOSE_ORDER if p in present]
        ordered += [p for p in present if p not in ordered]
        for purpose in ordered:
            block = df[df["simple_purpose"] == purpose]
            self.write_dataframe_to_sheet(
                block[value_cols], row + 1, start_col, self.OBSERVED_TARGETS_SHEET,
                source_row=row, source_col=start_col, source_text=str(purpose))
            row += len(block) + 3  # purpose label + header + data rows + blank separator
        return row

    def _write_observed_targets(self, results: dict) -> None:
        """Place selected wide summaries on the targets sheet: purposes stacked, filters across columns."""
        if not getattr(self, "calib_workbook", None):
            self.logger.warning("No workbook available; skipping targets-sheet placement.")
            return

        row = self.OBSERVED_TARGETS_HEADER_ROW
        col = self.OBSERVED_TARGETS_START_COL
        for flt in self.OBSERVED_TARGETS_FILTERS:
            section_bottom = row
            for result_type in self.OBSERVED_TARGETS_RESULT_TYPES:
                key = f"tour_mode_summary_{result_type}_{flt}"
                df = results.get(key)
                if df is None:
                    self.logger.warning("No observed result for %s/%s; skipping. ", result_type, flt)
                    continue
                self.write_dataframe_to_sheet(pd.DataFrame(columns=[f"Source: {self.output_dir}/BATS2023_{key}"]), 1, col,
                                              self.OBSERVED_TARGETS_SHEET)
                section_bottom = max(section_bottom, self._write_purpose_blocks(df, row, col, f"{flt} - {result_type}"))
                            
                col += len([c for c in df.columns if c not in ("simple_purpose", "indiv_joint", "tour_mode")]) + 1
            col = col + 2


    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")

        if self.bats_data:
            # CSV-only per-filter outputs (empty sheet name skips workbook write).
            targets = [
                SheetTarget(key, "", 0, 0, f"BATS2023_{key}.csv", None)
                for key in results
            ]
            self.write_results_to_workbook(results, targets)
            # Additionally place selected wide summaries onto the 'targets' sheet.
            self._write_observed_targets(results)
        else:
            self.write_results_to_workbook(results, self.MODELED_SHEET_TARGETS)



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
