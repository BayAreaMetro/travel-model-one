"""Trip mode choice calibration submodel (submodel 15).

This script ports the legacy R workflow (15_trip_mode_choice_TM.R) to the shared
Python calibration framework. It supports:

- Model mode (bats_data = false):
  reads model trip outputs, applies ferry availability, and scales counts by
  sampleshare. Produces the full set of trip/transit-boarding/auto/ridehail
  summaries.
- BATS mode (bats_data = true):
  reads BATS-formatted trip files, weights by sampleRate, and produces
  weighted/unweighted trip mode summaries per configured county filter.

Model outputs:
- 15_trip_mode_choice_TM.csv
- 15_trip_mode_choice_trn_boards_TM.csv
- 15_trip_mode_choice_trn_odtaz_boards_TM.csv   (debug, CSV only)
- 15_trip_mode_choice_trn_ODdist_TM.csv
- 15_trip_mode_choice_auto_ODdist_TM.csv        (CSV only)
- 15_trip_mode_choice_ridehail_ODdist_TM.csv    (CSV only)
- 15_trip_mode_choice_ridehail_ODcounty_TM.csv
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calibration_framework import CalibrationBase, SheetTarget, add_county_info
from data_canon.codebook.ctramp import CTRAMPModeType

TIME_PERIODS = ["EA", "AM", "MD", "PM", "EV"]

# Legacy R simple_purpose mapping (trip version does NOT collapse joint by default).
SIMPLE_PURPOSE_MAP = {
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
    "work_high": "work",
    "work_low": "work",
    "work_med": "work",
    "work_very high": "work",
    "work_very_high": "work",
}


class TripModeChoiceCalibration(CalibrationBase):
    """Calibration processor for trip mode choice summaries."""

    # Declarative placement for modeled outputs (CSV + workbook cell).
    MODELED_SHEET_TARGETS = [
        SheetTarget("trip_mode_summary", "modeldata", 2, 1,
                    "15_trip_mode_choice_TM.csv", (1, 1)),
        SheetTarget("transit_od_summary", "modeldata", 2, 10,
                    "15_trip_mode_choice_trn_ODdist_TM.csv", (1, 10)),
        SheetTarget("transit_boards_summary", "modeldata", 2, 18,
                    "15_trip_mode_choice_trn_boards_TM.csv", (1, 18)),
        SheetTarget("ridehail_county_summary", "modeldata", 2, 32,
                    "15_trip_mode_choice_ridehail_ODcounty_TM.csv", (1, 32)),
        # CSV-only outputs (empty sheet name skips the workbook write).
        SheetTarget("transit_odtaz_boards_summary", "", 0, 0,
                    "15_trip_mode_choice_trn_odtaz_boards_TM.csv", None),
        SheetTarget("auto_od_summary", "", 0, 0,
                    "15_trip_mode_choice_auto_ODdist_TM.csv", None),
        SheetTarget("ridehail_od_summary", "", 0, 0,
                    "15_trip_mode_choice_ridehail_ODdist_TM.csv", None),
    ]

    # Observed (BATS): trips x tours cross summaries written to the 'targets' sheet,
    # split into a block per simple_purpose (stacked), filters across columns.
    OBSERVED_TARGETS_SHEET = "targets"
    OBSERVED_TARGETS_HEADER_ROW = 3
    OBSERVED_TARGETS_START_COL = 2
    OBSERVED_TARGETS_RESULT_TYPES = ["unweighted", "weighted"]
    OBSERVED_TARGETS_FILTERS = ["all", "solano_napa", "north_bay"]
    OBSERVED_PURPOSE_ORDER = ["work", "university", "school", "ind_maint", "ind_disc",
                             "atwork", "joint"]

    # Toll modes (DA toll, SR2 toll, SR3+ toll) to exclude from observed outputs.
    EXCLUDED_MODES = [2, 4, 6]

    def __init__(self, config_file: str | None = None):
        super().__init__("15", config_file)
        self._skim_dir = self.submodel_config.get(
            "ferry_skim_dir", f"{self.target_dir}/OUTPUT_00/skims")


    def _load_trips(self) -> pd.DataFrame:
        """Load and harmonize individual and joint trip tables."""
        cols = ["hh_id", "inbound", "tour_purpose", "tour_mode", "trip_mode",
                "depart_hour", "orig_taz", "dest_taz",
                ]
        if self.bats_data:
            cols.append("sampleRate")
        else:
            cols.extend(["taxiWait", "singleTNCWait", "sharedTNCWait"])

        indiv = pd.read_csv(self.submodel_config["indiv_trip_file"], usecols=cols)
        indiv["num_participants"] = 1
        indiv["indiv_joint"] = "indiv"

        joint = pd.read_csv(self.submodel_config["joint_trip_file"],
                            usecols=cols + ["num_participants"])
        joint["indiv_joint"] = "joint"

        trips = pd.concat([indiv, joint], ignore_index=True)
        trips["trip_mode"] = pd.to_numeric(trips["trip_mode"], errors="coerce")

        trips["timeperiod"] = np.select(
            [trips["depart_hour"] <= 5, trips["depart_hour"] <= 10,
             trips["depart_hour"] <= 15, trips["depart_hour"] <= 19],
            ["EA", "AM", "MD", "PM"], default="EV")
        trips["simple_purpose"] = self._map_simple_purpose(
            trips["tour_purpose"], trips["indiv_joint"], collapse_joint=True)
        return trips

    def _load_taz_sd(self) -> pd.DataFrame:
        taz_sd_file = self.submodel_config["taz_sd_file"]
        if not Path(taz_sd_file).exists():
            raise FileNotFoundError(f"TAZ superdistrict file not found: {taz_sd_file}")
        return pd.read_csv(taz_sd_file, usecols=["ZONE", "SD", "SD_NAME", "COUNTY"])

    def _attach_superdistrict(self, trips: pd.DataFrame) -> pd.DataFrame:
        taz_sd = self._load_taz_sd()
        for prefix in ("orig", "dest"):
            renamed = taz_sd.rename(columns={
                "ZONE": f"{prefix}_taz", "SD": f"{prefix}_SD",
                "SD_NAME": f"{prefix}_SD_NAME", "COUNTY": f"{prefix}_COUNTY"})
            trips = trips.merge(renamed, on=f"{prefix}_taz", how="left")
        return trips

    def _load_ferry_skims(self) -> pd.DataFrame:
        """Load ferry skim availability tables used to split LRF trips into LRT vs ferry."""
        rows: list[pd.DataFrame] = []
        for tp in TIME_PERIODS:
            for submode in ["wlk_lrf_wlk", "drv_lrf_wlk", "wlk_lrf_drv"]:
                path = Path(self._skim_dir) / f"trnskm{tp}_{submode}.csv"
                if not path.exists():
                    self.logger.warning("Ferry skim missing, skipping: %s", path)
                    continue
                tbl = pd.read_csv(path, usecols=["orig", "dest", "ivtFerry"])
                tbl = tbl.rename(columns={"orig": "OTAZ", "dest": "DTAZ"})
                tbl["timeperiod"] = tp
                tbl["submode"] = submode
                rows.append(tbl)
        if not rows:
            self.logger.warning("No ferry skims loaded; LRF trips remain as light rail.")
            return pd.DataFrame(columns=["OTAZ", "DTAZ", "timeperiod", "submode", "ivtFerry"])
        return pd.concat(rows, ignore_index=True)

    # Helper functions
    @staticmethod
    def _map_simple_purpose(purpose_series: pd.Series, indiv_joint_series: pd.Series,
                            collapse_joint: bool = False) -> pd.Series:
        """Map tour_purpose to a simple purpose; optionally collapse joint trips."""
        simple = purpose_series.astype(str).map(SIMPLE_PURPOSE_MAP)
        if collapse_joint:
            simple = simple.where(indiv_joint_series.astype(str) != "joint", "joint")
        return simple

    @staticmethod
    def _add_mode_label(df: pd.DataFrame, mode_col: str = "trip_mode",
                        label_col: str | None = None) -> pd.DataFrame:
        """Attach the human-readable CT-RAMP mode label next to the numeric mode."""
        mode_labels = {m.value: m.label for m in CTRAMPModeType}
        df = df.copy()
        df[label_col or f"{mode_col}_label"] = df[mode_col].map(mode_labels)
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

    def _aggregate_trips(self, df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        """Aggregate modeled trip totals for requested groups."""
        if df.empty:
            return pd.DataFrame(columns=group_cols + ["num_trips"])
        out = df.groupby(group_cols, dropna=False, as_index=False)["num_participants"].sum()
        out = out.rename(columns={"num_participants": "num_trips"})
        out["num_trips"] = out["num_trips"] / self.sampleshare
        return out

    def _aggregate_trips_bats(self, df: pd.DataFrame, group_cols: list[str],
                              categorical_col: str = "trip_mode",
                              categories: list | None = None) -> pd.DataFrame:
        """Aggregate BATS trips into weighted and unweighted totals, including all modes."""
        if df.empty:
            return pd.DataFrame(columns=group_cols + ["num_trips_unweighted", "num_trips_weighted"])
        grouped = df.copy()
        grouped["sample_rate"] = pd.to_numeric(grouped["sampleRate"], errors="coerce").fillna(0)
        grouped["num_trips_unweighted"] = grouped["num_participants"]
        grouped["num_trips_weighted"] = np.where(
            grouped["sample_rate"] > 0, grouped["num_participants"] / grouped["sample_rate"], 0.0)

        if categories is None:
            categories = [m.value for m in CTRAMPModeType]
        grouped[categorical_col] = pd.Categorical(grouped[categorical_col], categories=categories)
        out = grouped.groupby(group_cols, observed=False, dropna=False, as_index=False)[
            ["num_trips_unweighted", "num_trips_weighted"]].sum()
        out[["num_trips_unweighted", "num_trips_weighted"]] = out[
            ["num_trips_unweighted", "num_trips_weighted"]].fillna(0)
        return out

    # Adding ferry availability for modeled data
    def _apply_ferry_availability(self, trips: pd.DataFrame) -> pd.DataFrame:
        """Split LRF trips (mode 10/15) and negate trip_mode when ferry is available."""
        ferry = self._load_ferry_skims()
        non_lrf = trips[~trips["trip_mode"].isin([10, 15])].copy()
        non_lrf["ferryAvailable"] = 0

        def join_avail(df: pd.DataFrame, submode: str) -> pd.DataFrame:
            df = df.copy()
            if df.empty:
                df["ferryAvailable"] = 0
                return df
            skim = ferry[ferry["submode"] == submode][["OTAZ", "DTAZ", "timeperiod", "ivtFerry"]]
            out = df.merge(skim, left_on=["orig_taz", "dest_taz", "timeperiod"],
                           right_on=["OTAZ", "DTAZ", "timeperiod"], how="left")
            out["ferryAvailable"] = np.where(
                pd.to_numeric(out["ivtFerry"], errors="coerce").fillna(0) > 0, 1, 0)
            return out.drop(columns=["OTAZ", "DTAZ", "ivtFerry"])

        walk = join_avail(trips[trips["trip_mode"] == 10], "wlk_lrf_wlk")
        drv_out = join_avail(
            trips[(trips["trip_mode"] == 15) & (trips["inbound"] == 0)], "drv_lrf_wlk")
        drv_in = join_avail(
            trips[(trips["trip_mode"] == 15) & (trips["inbound"] == 1)], "wlk_lrf_drv")

        trips = pd.concat([non_lrf, walk, drv_out, drv_in], ignore_index=True)
        trips["ferryAvailable"] = trips["ferryAvailable"].fillna(0)
        trips["trip_mode"] = np.where(trips["ferryAvailable"] == 1,
                                      trips["trip_mode"] * -1, trips["trip_mode"])
        return trips

    # -------------------------------------------------------- transit boarding
    def _build_transit_table(self, trips: pd.DataFrame) -> pd.DataFrame:
        """Transit trips with submode label plus access/egress (mirrors the R logic)."""
        trn = trips[(trips["trip_mode"] < 0) |
                    ((trips["trip_mode"] >= 9) & (trips["trip_mode"] <= 18))].copy()
        submode_map = {-15: "Ferry", -10: "Ferry", 9: "Local", 10: "LRT", 11: "Express",
                       12: "HeavyRail", 13: "CommRail", 14: "Local", 15: "LRT",
                       16: "Express", 17: "HeavyRail", 18: "CommRail"}
        trn["trn_submode"] = trn["trip_mode"].map(submode_map)

        m = trn["trip_mode"]
        wlk_wlk = ((m >= 9) & (m <= 13)) | (m == -10)
        drv_wlk = ((trn["inbound"] == 0) & (m >= 14) & (m <= 18)) | \
                  ((trn["inbound"] == 0) & (m == -15))
        wlk_drv = ((trn["inbound"] == 1) & (m >= 14) & (m <= 18)) | \
                  ((trn["inbound"] == 1) & (m == -15))
        trn["acc"] = np.select([wlk_wlk, drv_wlk, wlk_drv], ["wlk", "drv", "wlk"], "Not Set")
        trn["egr"] = np.select([wlk_wlk, drv_wlk, wlk_drv], ["wlk", "wlk", "drv"], "Not Set")
        return trn

    def _attach_boards(self, trn: pd.DataFrame) -> pd.DataFrame:
        """Join boards + firstMode from per-submode transit skims and classify line haul."""
        trn = trn.copy()
        trn["num_boards"] = np.nan
        trn["first_trn_mode"] = np.nan

        submode_file = {"Local": "loc", "Express": "exp", "LRT": "lrf", "Ferry": "lrf",
                        "HeavyRail": "hvy", "CommRail": "com"}
        for tp in TIME_PERIODS:
            for trn_submode, submode in submode_file.items():
                for acc_egr in ["wlk_wlk", "drv_wlk", "wlk_drv"]:
                    acc, egr = acc_egr[:3], acc_egr[4:7]
                    path = Path(self._skim_dir) / f"trnskm{tp}_{acc}_{submode}_{egr}.csv"
                    if not path.exists():
                        continue
                    skim = pd.read_csv(path, usecols=["orig", "dest", "boards", "firstMode"])
                    skim = skim.rename(columns={"orig": "orig_taz", "dest": "dest_taz"})
                    skim["timeperiod"] = tp
                    skim["trn_submode"] = trn_submode
                    skim["acc"] = acc
                    skim["egr"] = egr
                    trn = trn.merge(
                        skim,
                        on=["orig_taz", "dest_taz", "timeperiod", "trn_submode", "acc", "egr"],
                        how="left")
                    trn["num_boards"] = trn["num_boards"].where(trn["boards"].isna(), trn["boards"])
                    trn["first_trn_mode"] = trn["first_trn_mode"].where(
                        trn["firstMode"].isna(), trn["firstMode"])
                    trn = trn.drop(columns=["boards", "firstMode"])

        trn["first_trn_mode_type"] = np.select(
            [trn["first_trn_mode"] < 80,
             (trn["first_trn_mode"] >= 80) & (trn["first_trn_mode"] < 100),
             (trn["first_trn_mode"] >= 100) & (trn["first_trn_mode"] < 110),
             (trn["first_trn_mode"] >= 110) & (trn["first_trn_mode"] < 120),
             (trn["first_trn_mode"] >= 120) & (trn["first_trn_mode"] < 130),
             (trn["first_trn_mode"] >= 130) & (trn["first_trn_mode"] < 140)],
            ["Local", "Express", "Ferry", "LRT", "HeavyRail", "CommRail"], default="Unknown")

        missing = int(trn["num_boards"].isna().sum())
        self.logger.info("Have %d transit rows without board counts of %d", missing, len(trn))
        return trn

    def _build_boards_summary(self, trn: pd.DataFrame) -> pd.DataFrame:
        """Spread board counts by submode for the workbook boards table."""
        have = trn[trn["num_boards"].notna()]
        summary = self._aggregate_trips(
            have, ["trn_submode", "acc", "egr", "first_trn_mode_type", "num_boards"])
        wide = summary.pivot_table(
            index=["acc", "egr", "first_trn_mode_type", "num_boards"],
            columns="trn_submode", values="num_trips", aggfunc="sum", fill_value=0).reset_index()
        wide.columns.name = None
        for col in ["Local", "Express", "Ferry", "LRT", "HeavyRail", "CommRail"]:
            if col not in wide.columns:
                wide[col] = 0.0
        return wide[["acc", "egr", "first_trn_mode_type", "num_boards",
                     "Local", "Express", "Ferry", "LRT", "HeavyRail", "CommRail"]]

    def _build_transit_od_summary(self, trn: pd.DataFrame) -> pd.DataFrame:
        """Summarize transit trips by purpose/access/submode and SD-to-SD pairs, with Totals."""
        trn = trn.copy()
        trn["trn_access_mode"] = np.where(
            (trn["acc"] == "wlk") & (trn["egr"] == "wlk"), "walk", "drive")
        expanded = pd.concat([
            trn,
            trn.assign(simple_purpose="Total"),
            trn.assign(trn_submode="Total"),
            trn.assign(trn_access_mode="Total"),
            trn.assign(simple_purpose="Total", trn_submode="Total"),
            trn.assign(simple_purpose="Total", trn_access_mode="Total"),
            trn.assign(trn_submode="Total", trn_access_mode="Total"),
            trn.assign(simple_purpose="Total", trn_submode="Total", trn_access_mode="Total"),
        ], ignore_index=True)
        summary = self._aggregate_trips(
            expanded, ["simple_purpose", "trn_access_mode", "trn_submode",
                       "orig_SD_NAME", "dest_SD_NAME"])
        summary["key"] = summary[["trn_access_mode", "trn_submode", "orig_SD_NAME",
                                  "dest_SD_NAME", "simple_purpose"]].astype(str).agg("-".join, axis=1)
        return summary[["key", "trn_access_mode", "trn_submode", "orig_SD_NAME",
                        "dest_SD_NAME", "simple_purpose", "num_trips"]]

    # ------------------------------------------------------------- auto / ride
    def _build_auto_od_summary(self, trips: pd.DataFrame) -> pd.DataFrame:
        """Summarize auto trips by SD-to-SD pairs and grouped purposes (CHTS codes)."""
        auto = trips[(trips["trip_mode"] >= 1) & (trips["trip_mode"] <= 6)].copy()
        auto["auto_submode"] = auto["trip_mode"].map({1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3})
        auto["simple_purpose2"] = np.select(
            [auto["simple_purpose"] == "atwork",
             (auto["simple_purpose"] == "ind_disc") & (auto["indiv_joint"] == "indiv"),
             (auto["simple_purpose"] == "ind_disc") & (auto["indiv_joint"] == "joint"),
             (auto["simple_purpose"] == "ind_maint") & (auto["indiv_joint"] == "indiv"),
             (auto["simple_purpose"] == "ind_maint") & (auto["indiv_joint"] == "joint"),
             auto["simple_purpose"] == "work",
             auto["simple_purpose"] == "university",
             auto["simple_purpose"] == "school"],
            ["ATWRK", "iDISC", "jDISC", "iMAIN", "jMAIN", "WORK", "UNIV", "SCHL"], default="OTHER")
        summary = self._aggregate_trips(
            auto, ["simple_purpose2", "auto_submode", "orig_SD_NAME", "dest_SD_NAME"])
        summary = summary.rename(columns={"simple_purpose2": "simple_purpose"})
        return summary[["auto_submode", "orig_SD_NAME", "dest_SD_NAME",
                        "simple_purpose", "num_trips"]]

    def _add_ridehail_mode(self, trips: pd.DataFrame) -> pd.DataFrame:
        trips = trips.copy()
        m = trips["trip_mode"]
        trips["ridehail_mode"] = np.select(
            [m < 0, (m > 0) & (m <= 6), (m == 7) | (m == 8),
             (m >= 9) & (m <= 18), m == 19, m == 20, m == 21],
            ["transit", "auto", "active", "transit", "Taxi", "TNC Single", "TNC Shared"],
            default=None)
        return trips

    def _ridehail_summary(self, trips: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
        """Trip flows plus average ride-hail wait times for the requested groups."""
        agg = trips.groupby(group_cols, dropna=False, as_index=False).agg(
            num_trips=("num_participants", "sum"),
            taxiWait=("taxiWait", "sum"),
            singleTNCWait=("singleTNCWait", "sum"),
            sharedTNCWait=("sharedTNCWait", "sum"))
        for col in ["taxiWait", "singleTNCWait", "sharedTNCWait"]:
            agg[col] = agg[col] / agg["num_trips"]
        agg["num_trips"] = agg["num_trips"] / self.sampleshare
        return agg

    def _copy_chts_file(self) -> None:
        chts = self.submodel_config.get("chts_file")
        if chts and Path(chts).exists():
            dest = f"{self.output_dir}/15_trip_mode_choice_auto_ODdist_CHTS.csv"
            shutil.copy(chts, dest)
            self.logger.info("Copied CHTS file to %s", dest)

    # ------------------------------------------------------------------ BATS
    def _build_bats_summaries(self, trips: pd.DataFrame) -> dict:
        """Cross-tab observed trips as tour mode x trip mode, segmented by tour purpose."""
        trips = self._add_mode_label(trips, mode_col="tour_mode", label_col="tour_mode_label")
        trip_mode_cols = [m.label for m in CTRAMPModeType if m.value not in self.EXCLUDED_MODES]

        group_cols = ["simple_purpose", "tour_mode", "tour_mode_label", "trip_mode"]
#        idx_cols = ["simple_purpose", "tour_mode", "tour_mode_label"]
        idx_cols = ["simple_purpose", "trip_mode", "trip_mode_label"]

        long_summary = self._aggregate_trips_bats(trips, group_cols)
        long_summary = self._add_mode_label(long_summary, mode_col="trip_mode",
                                            label_col="trip_mode_label")
        long_summary = long_summary[
            ~long_summary["trip_mode"].isin(self.EXCLUDED_MODES)
            & ~long_summary["tour_mode"].isin(self.EXCLUDED_MODES)]

        wide_unweighted = self.pivot_with_total(
            long_summary, idx_cols, "tour_mode_label", "num_trips_unweighted", trip_mode_cols)
        wide_weighted = self.pivot_with_total(
            long_summary, idx_cols, "tour_mode_label", "num_trips_weighted", trip_mode_cols)

        value_cols = trip_mode_cols + ["Total"]
        wide_unweighted = self._append_group_column_totals(
            wide_unweighted, "simple_purpose", "trip_mode_label", value_cols)
        wide_weighted = self._append_group_column_totals(
            wide_weighted, "simple_purpose", "trip_mode_label", value_cols)
        return {"long": long_summary,
                "wide_unweighted": wide_unweighted,
                "wide_weighted": wide_weighted}

    def process_data(self) -> dict:
        return self.process_observed() if self.bats_data else self.process_modeled()

    def process_observed(self) -> dict:
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS OBSERVED (BATS) DATA\n{sep}")

        trips = self._load_trips()
        taz_data = pd.read_csv(self.config.get("data_sources", "taz_data"),
                               usecols=["ZONE", "COUNTY"])
        trips = add_county_info(trips, taz_data, self.county_lookup, taz_col="orig_taz",
                                county_col_name="orig_county_id", county_name_col="orig_county")
        trips = add_county_info(trips, taz_data, self.county_lookup, taz_col="dest_taz",
                                county_col_name="dest_county_id", county_name_col="dest_county")

        results = {}
        for label, subset in self.iter_county_filters(trips):
            summ = self._build_bats_summaries(subset)
            results[f"tour_trip_mode_summary_long_{label}"] = summ["long"]
            results[f"tour_trip_mode_summary_wide_unweighted_{label}"] = summ["wide_unweighted"]
            results[f"tour_trip_mode_summary_wide_weighted_{label}"] = summ["wide_weighted"]
        return results

    def process_modeled(self) -> dict:
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nPROCESS MODELED DATA\n{sep}")

        trips = self._load_trips()
        trips = self._attach_superdistrict(trips)
        trips = self._apply_ferry_availability(trips)

        trip_mode_summary = self._aggregate_trips(
            trips, ["indiv_joint", "tour_purpose", "tour_mode", "trip_mode"])

        trn = self._build_transit_table(trips)
        trn = self._attach_boards(trn)
        boards_summary = self._build_boards_summary(trn)
        odtaz_boards_summary = self._aggregate_trips(
            trn, ["acc", "trn_submode", "egr", "first_trn_mode",
                  "orig_taz", "dest_taz", "num_boards"])
        transit_od_summary = self._build_transit_od_summary(trn)

        auto_od_summary = self._build_auto_od_summary(trips)

        trips = self._add_ridehail_mode(trips)
        ridehail_od_summary = self._ridehail_summary(
            trips, ["simple_purpose", "ridehail_mode", "orig_SD", "dest_SD"])
        ridehail_county_summary = self._ridehail_summary(
            trips, ["ridehail_mode", "orig_COUNTY", "dest_COUNTY"])

        self._copy_chts_file()

        return {
            "trip_mode_summary": trip_mode_summary,
            "transit_boards_summary": boards_summary,
            "transit_odtaz_boards_summary": odtaz_boards_summary,
            "transit_od_summary": transit_od_summary,
            "auto_od_summary": auto_od_summary,
            "ridehail_od_summary": ridehail_od_summary,
            "ridehail_county_summary": ridehail_county_summary,
        }

    def validate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nOUTPUT VALIDATION\n{sep}")
        self.logger.info("✓ Trip mode summaries validated")

    def _write_purpose_blocks(self, df: pd.DataFrame, start_row: int, start_col: int,
                              filter_label: str) -> int:
        """Write a wide summary to the targets sheet, one contiguous block per simple_purpose."""
        value_cols = [c for c in df.columns if c not in ["simple_purpose", "trip_mode"]]
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
        """Place trips x tours cross summaries on the targets sheet: purposes stacked, filters across columns."""
        if not getattr(self, "calib_workbook", None):
            self.logger.warning("No workbook available; skipping targets-sheet placement.")
            return

        row = self.OBSERVED_TARGETS_HEADER_ROW
        col = self.OBSERVED_TARGETS_START_COL
        for flt in self.OBSERVED_TARGETS_FILTERS:
            for result_type in self.OBSERVED_TARGETS_RESULT_TYPES:
                key = f"tour_trip_mode_summary_wide_{result_type}_{flt}"
                df = results.get(key)
                if df is None:
                    self.logger.warning("No observed result for %s/%s; skipping.", result_type, flt)
                    continue
                self.write_dataframe_to_sheet(
                    pd.DataFrame(columns=[f"Source: {self.output_dir}/BATS2023_{key}.csv"]),
                    1, col, self.OBSERVED_TARGETS_SHEET)
                self._write_purpose_blocks(df, row, col, f"{flt} - {result_type}")
                col += len([c for c in df.columns if c not in ("simple_purpose", "trip_mode")]) + 1
            col += 2

    def generate_outputs(self, results: dict):
        sep = "=" * 80
        self.logger.info(f"\n{sep}\nGENERATE OUTPUTS\n{sep}")
        if self.bats_data:
            # CSV-only per-filter outputs (empty sheet name skips workbook write).
            targets = [SheetTarget(key, "", 0, 0, f"BATS2023_{key}.csv", None)
                       for key in results]
            self.write_results_to_workbook(results, targets)
            # Additionally place the trips x tours cross summaries onto the 'targets' sheet.
            self._write_observed_targets(results)
        else:
            self.write_results_to_workbook(results, self.MODELED_SHEET_TARGETS)


def main():
    parser = argparse.ArgumentParser(description="Trip mode choice calibration")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to calibration_config.yaml (default: same directory as this script)",
    )
    args = parser.parse_args()

    calibration = TripModeChoiceCalibration(config_file=args.config)
    calibration.run()


if __name__ == "__main__":
    main()
