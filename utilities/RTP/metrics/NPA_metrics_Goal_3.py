#!/usr/bin/env python3
"""
The main tasks performed in the script include:
1. **Data Preparation**
    - Inputs:
     -- Loading TAZ-to-city mapping from GitHub
     -- Loading OD travel time data from local files
     -- Loading transit assignment data from local files
     -- Loading BRT treatment data from local files
     -- Loading transit crowding data from local files

2. **OD Travel Time Processing (Goal 3A & 3D)**
- **Goal 3A:** Identifies the minimum transit travel times for each route direction (od pair) and time period, and for the same od pair and time period, the minimum auto travel time.
- **Goal 3D:** Calculate the maximum transit travel time ratio (AM Peak/Midday) for each route direction (od pair).
    - Inputs:
     -- {WORK_DIR}/database/TimeSkimsDatabaseAM.csv (OD travel time data for AM Peak)
     -- {WORK_DIR}/database/TimeSkimsDatabaseMD.csv (OD travel time data for Midday)
    - This part of the script performs the following steps:
     1. Reads and filters the OD travel time data for AM Peak and Midday.
     2. Merges the AM Peak and Midday dataframes with appropriate suffixes.
     3. Creates a skim_merge dataframe with city information by merging with the TAZ-to-city mapping.
     4. Defines a function to filter, sort, and save travel time data for each od city pair, and calculates the minimum transit travel time for each od city pair and for AM Peak and Midday specifically (Goal 3A).
     5. Calculates the maximum transit travel time ratio (AM Peak/Midday) for each od city pair (Goal 3D).
     
3. **Transit Auto Travel Time Ratio Processing (Goal 3B & 3C)**
- **Goal 3B:** Calculate the average transit-to-auto travel time ratio for AM Peak periods using weighted averages for each od city pair.
- **Goal 3C:** Calculate the average transit-to-auto travel time ratio for Midday periods using weighted averages for each od city pair.

   - Inputs:
     -- {WORK_DIR}/core_summaries/ODTravelTime_byModeTimeperiodIncome.csv (OD travel time data)

   - This part of the script performs the following steps:
     1. Reads Origin-Destination (OD) travel time data from CSV files and filters out records with avg_travel_time_in_mins <= 0.
     2. Maps TAZs to city names by merging with the TAZ-to-city mapping.
     3. Defines a function to filter, sort, and save travel time data for each od city pair, separately for transit and auto modes, and for AM Peak and Midday.
     4. Calculates the average travel time by summing the travel time for all trips and dividing by the number of trips and calculates the transit-to-auto ratio for each od city pair and for AM Peak (Goal 3B) and Midday (Goal 3C).

4. **Transit Service Data Processing (Goal 3E)**
   - Inputs:
     -- {WORK_DIR}/trn/trnlink.csv (transit link data)
     -- {WORK_DIR}/trn/trnline.csv (transit line data)

   - This part of the script performs the following steps:
     1. Reads and consolidates transit link and line data.
     2. Filters out records where MODE is less than 10 and between 100 and 107 (inclusive).
     3. Drops duplicate records based on a set of unique columns: 'A', 'B', 'MODE', 'NAME', 'OWNER', 'time_period'.
     4. Maps the 'time_period' values to an 'hour_interval' using a predefined dictionary (e.g., 'am' maps to 4 hours).
     5. Calculates unique transit service miles using the formula: (60/FREQ) * hour_interval * DIST / 100.
     6. Merges with BRT treatment data to determine the proportion of transit service miles provided by BRT.
     7. Groups transit service miles by mode and calculates the ratio of BRT service miles to total transit service miles for each mode.

5. **Transit Capacity and Crowding Analysis (Goal 3F)**
   - Inputs:
     -- {WORK_DIR}/metrics/transit_crowding_complete.csv (transit crowding data)

   - This part of the script performs the following steps:
     1. Reads transit crowding data.
     2. Calculates passenger hours by multiplying AB_VOL by ivtt_hours.
     3. Identifies crowded conditions (when AB_VOL > 85% of the combined seated and standing capacity) and sums the corresponding passenger-hours.
     4. Computes the percentage of total passenger-hours in transit that occur under crowded conditions.

6. **Output Generation**
   - Combines all computed metrics (from Goals 3A, 3B, 3C, 3D, 3E, and 3F) into a summary CSV file:
     -- {OUTPUT_Dir}/NPA_metrics_Goal_3.csv (combined metrics)

7. **Reorder the output**
   - Reorders the output metrics into the wide format (can be deleted if not needed).
"""

import os
from pathlib import Path
import pandas as pd
import re
import logging

# Setup directories and global constants
WORK_DIR = Path("../2050_TM160_DBP_Plan_08b")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())

OUTPUT_DIR = Path(f"../data_output/{WORK_DIR.name}/NPA_Metrics_Goal_3_v2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR_TABLEAU = Path(f"../data_output/Tableau_NPA_Metrics_Goal_3")
OUTPUT_DIR_TABLEAU.mkdir(parents=True, exist_ok=True)

# Set up logging
log_file = os.path.join(OUTPUT_DIR, 'NPA_metrics_Goal_3_v2.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Script execution started")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Output directory: {OUTPUT_DIR}")

# Mode definitions
MODES_TRANSIT = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
MODES_TRANSIT_WALK = [9, 10, 11, 12, 13]
MODES_TRANSIT_DRIVE = [14, 15, 16, 17, 18]
MODES_TAXI_TNC = [19, 20, 21]
MODES_SOV = [1, 2]
MODES_HOV = [3, 4, 5, 6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV

EFFECTIVE_TRANSIT_SERVICE_HOURS = {'ea': 3, 'am': 4, 'md': 5, 'pm': 4, 'ev': 8} # based on the effective service hours of the transit system

TIMEPERIOD_LABELS = ['AM Peak', 'Midday']

# Define OD city pairs with IDs and city lists
OD_PAIRS = [
    ("richmond_to_oakland",                 ["Richmond"],                  ["Oakland"]),
    ("oakland_to_richmond",                 ["Oakland"],                   ["Richmond"]),
    ("oakland_to_san_francisco",            ["Oakland"],                   ["San Francisco"]),
    ("san_francisco_to_oakland",            ["San Francisco"],             ["Oakland"]),
    ("fremont&union_city_to_san_jose",      ["Fremont","Union City"],      ["San Jose"]),
    ("san_jose_to_fremont&union_city",      ["San Jose"],                  ["Fremont","Union City"]),
    ("mountain_view&palo_alto_to_san_jose", ["Mountain View","Palo Alto"], ["San Jose"]),
    ("san_jose_to_mountain_view&palo_alto", ["San Jose"],                  ["Mountain View","Palo Alto"])
]

# Load TAZ→city mapping
logger.info("Loading TAZ-to-city mapping")
od_cities_map = (
    pd.read_csv(
        "https://raw.githubusercontent.com/BayAreaMetro/travel-model-one/"
        "refs/heads/v1.6.1_develop/utilities/AttachShapeToNetwork/TAZ1454_city.csv",
        usecols=['TAZ1454','city']
    )
    .set_index('TAZ1454')['city']
)

# --------------------------
# 3A & 3D: Best Transit Travel Time and Ratio Processing
# --------------------------

# Load and merge AM/Midday skims
logger.info("Loading AM and Midday skims")
skim_paths = {
    'am_peak': WORK_DIR/"database"/"TimeSkimsDatabaseAM.csv",
    'midday': WORK_DIR/"database"/"TimeSkimsDatabaseMD.csv"
}
skim = {tp: pd.read_csv(fp, usecols=['orig','dest','da','wTrnW']) 
        for tp, fp in skim_paths.items()}
skim_merge = skim['am_peak'].merge(skim['midday'], on=['orig','dest'], suffixes=('_am_peak','_midday')).rename(columns={'orig':'orig_taz','dest':'dest_taz'})
skim_merge['orig_CITY'] = skim_merge.orig_taz.map(od_cities_map)
skim_merge['dest_CITY'] = skim_merge.dest_taz.map(od_cities_map)
valid = (skim_merge[['wTrnW_am_peak','wTrnW_midday']] != -999).all(axis=1)
skim_merge['wTrnW_ratio'] = (skim_merge.wTrnW_am_peak / skim_merge.wTrnW_midday).where(valid)

# Compute best travel times (3A) and best ratio (3D)
metrics_3A, metrics_3D = {}, {}
for od_key, origins, dests in OD_PAIRS:
    selected_od = skim_merge[skim_merge.orig_CITY.isin(origins) & skim_merge.dest_CITY.isin(dests)]
    for period, trn_col, da_col in [
        ('am_peak', 'wTrnW_am_peak', 'da_am_peak'),
        ('midday', 'wTrnW_midday', 'da_midday')
    ]:
        mask = selected_od[trn_col] != -999
        if not mask.any():
            metrics_3A[f"best_transit_travel_time_{od_key}_{period}"] = None
            metrics_3A[f"best_auto_travel_time_{od_key}_{period}"] = None
        else:
            ix = selected_od.loc[mask, trn_col].idxmin()
            best = selected_od.loc[ix]
            metrics_3A[f"best_transit_travel_time_{od_key}_{period}"] = best[trn_col]
            metrics_3A[f"best_auto_travel_time_{od_key}_{period}"] = (
                selected_od.loc[
                    (selected_od.orig_taz == best.orig_taz) & (selected_od.dest_taz == best.dest_taz),
                    da_col
                ].iloc[0]
            )
    ratio = selected_od.wTrnW_ratio.dropna()
    metrics_3D[f"best_transit_ratio_{od_key}_am_peak_midday"] = (
        round(ratio.max(),2) if not ratio.empty else None
    )

# --------------------------
# 3B & 3C: Average Travel Time Ratio Processing
# --------------------------
logger.info("Loading avg OD travel time data")
od_tt_avg = pd.read_csv(WORK_DIR/"core_summaries"/"ODTravelTime_byModeTimeperiodIncome.csv")
od_tt_avg = od_tt_avg[od_tt_avg.avg_travel_time_in_mins > 0]
od_tt_avg['orig_CITY'] = od_tt_avg.orig_taz.map(od_cities_map)
od_tt_avg['dest_CITY'] = od_tt_avg.dest_taz.map(od_cities_map)

# Weighted average helper
def w_avg(df, modes):
    subset = df[df.trip_mode.isin(modes)]
    count = subset.num_trips.sum()
    return (subset.avg_travel_time_in_mins * subset.num_trips).sum()/count if count else None

metrics_3B, metrics_3C = {}, {}
for tp in TIMEPERIOD_LABELS:
    label = tp.lower().replace(" ","_")
    od_tt_avg_tp = (od_tt_avg[od_tt_avg.timeperiod_label==tp]
             .drop(columns=['incQ','incQ_label'], errors='ignore')
             .drop_duplicates())
    for od_key, origins, dests in OD_PAIRS:
        selected_od = od_tt_avg_tp[od_tt_avg_tp.orig_CITY.isin(origins) & od_tt_avg_tp.dest_CITY.isin(dests)]
        ratio = None
        if not selected_od.empty:
            t_avg = w_avg(selected_od, MODES_TRANSIT)
            a_avg = w_avg(selected_od, MODES_PRIVATE_AUTO + MODES_TAXI_TNC)
            ratio = (t_avg/a_avg) if (t_avg is not None and a_avg) else None
        key = f"transit_auto_travel_time_ratio_{od_key}_{label}"
        (metrics_3B if label=='am_peak' else metrics_3C)[key] = (
            round(ratio,2) if ratio is not None else None
        )

# --------------------------
# 3E: Transit Service Data Processing
# --------------------------
logger.info("Starting Transit Service Data Processing (Goal 3E)")

# Load and filter transit link/line data
link = pd.read_csv(WORK_DIR/"trn"/"trnlink.csv")
line = pd.read_csv(WORK_DIR/"trn"/"trnline.csv")

# Build a boolean mask for valid rows
mask_link = (link["mode"] >= 10) & (~link["mode"].isin(range(100, 108)))
mask_line = (line["mode"] >= 10) & (~line["mode"].isin(range(100, 108)))

# Filter
link = link.loc[mask_link]
line = line.loc[mask_line].drop(columns=["mode", "owner"])

link = link.drop_duplicates(['A','B','mode','name','owner','timeperiod'])
link['short_source'] = link.source.str.replace(r'^trnlink|\.csv$','', regex=True)

# Merge and compute service miles
trn_data = (
    link
    .merge(line, left_on=['name','short_source'], right_on=['name','path id'], how='left')
    .assign(
        hour_interval=lambda df: df.timeperiod.map(EFFECTIVE_TRANSIT_SERVICE_HOURS),
        service_miles=lambda df: (60 / df.frequency) * df.hour_interval * df.distance / 100
    )
)

# Load BRT treatment data
brt = pd.read_csv(WORK_DIR/"hwy"/"iter3"/"avgload5period_vehclasses.csv").query("brt > 0")

# Calculate totals and mode‐level BRT share
total_sm = trn_data.service_miles.sum()
brt_sm = trn_data.merge(brt, left_on=['A','B'], right_on=['a','b']).service_miles.sum()

# Compute BRT share by mode
ratio_by_mode = (
    trn_data
      .merge(brt, left_on=['A','B'], right_on=['a','b'])
      .groupby('mode').service_miles.sum()
    / trn_data.groupby('mode').service_miles.sum()
).fillna(0).loc[lambda s: s > 0].round(3)

# Base metrics
metrics_3E = {
    "transit_service_miles": int(round(total_sm)),
    "transit_service_miles_brt": int(round(brt_sm)),
    "transit_service_miles_brt_pct": round(brt_sm/total_sm, 3)
}

# Append per-mode BRT share into metrics_3E
for mode, share in ratio_by_mode.items():
    metrics_3E[f"transit_service_miles_brt_pct_mode_{mode}"] = share

logger.info(
    "Goal 3E metrics\n total transit service miles: %d, BRT service miles: %d, BRT share: %.1f%%; \n by mode BRT share: %s",
    metrics_3E["transit_service_miles"],
    metrics_3E["transit_service_miles_brt"],
    metrics_3E["transit_service_miles_brt_pct"] * 100, 
    "\n".join([f"{mode}: {share * 100 :.1f}%" for mode, share in ratio_by_mode.items()])
)

# --------------------------
# 3F: Transit Capacity and Crowding Analysis
# --------------------------
logger.info("Calculating transit capacity and crowding metrics")
trn_crowding_df = pd.read_csv(WORK_DIR / "metrics" / "transit_crowding_complete.csv")
trn_crowding_df['passenger_hours'] = trn_crowding_df['AB_VOL'] * trn_crowding_df['ivtt_hours']
crowded_mask = trn_crowding_df["AB_VOL"] > 0.85 * (trn_crowding_df["period_seatcap"] + trn_crowding_df["period_standcap"])
crowded_hours = trn_crowding_df.loc[crowded_mask, "passenger_hours"].sum()
total_hours = trn_crowding_df["passenger_hours"].sum()
metrics_3F = {
    "crowded_person_hours": int(round(crowded_hours)),
    "total_person_hours": int(round(total_hours)),
    "ratio_crowded": round(crowded_hours / total_hours, 2)
}
logger.info(f"Goal 3F metrics calculated: {metrics_3F}")

# --------------------------
# Metrics Output
# --------------------------
logger.info("Combining all metrics for final output")
metrics_sets = [
    (metrics_3A, '3A'),
    (metrics_3B, '3B'),
    (metrics_3C, '3C'),
    (metrics_3D, '3D'),
    (metrics_3E, '3E'),
    (metrics_3F, '3F')
]

run_name = Path(os.getcwd()).parts[-1]
logger.info(f"Run name: {run_name}")

dfs = []
for metrics, measure_name in metrics_sets:
    logger.info(f"Processing metrics for Goal {measure_name}, count: {len(metrics)}")
    df = pd.DataFrame(list(metrics.items()), columns=['variable_desc', 'current_value'])
    df.insert(0, 'run_name', run_name)
    df.insert(3, 'measure_names', measure_name)
    dfs.append(df)

out_frame = pd.concat(dfs, ignore_index=True)
metrics_file = OUTPUT_DIR / "NPA_metrics_Goal_3.csv"
out_frame.to_csv(metrics_file, index=False)
logger.info(f"Saved combined metrics to: {metrics_file}, total metrics: {len(out_frame)}")

# --------------------------
# Reorder the output
# --------------------------
logger.info("Reordering the output for better readability")

def extract_direction(row):
    measure = row['measure_names']
    var_desc = row['variable_desc']
    # Set defaults for regionwide (or when pattern matching fails)
    orig_city = "regionwide"
    dest_city = "regionwide"
    metric_name = var_desc

    if measure == '3A':
        # Expected format: best_transit_travel_time_{origin}_to_{destination}_{period}
        m = re.search(r'^(.*?)_time_(.+)_to_(.+)_(am_peak|midday)$', var_desc)
        if m:
            prefix, orig, dest, period = m.groups()
            orig_city = orig
            dest_city = dest
            metric_name = f"{prefix}_time_{period}"
    elif measure in ('3B', '3C'):
        # Expected format: transit_auto_travel_time_ratio_{origin}_to_{destination}_{period}
        m = re.search(r'^(.*?)_ratio_(.+)_to_(.+)_(am_peak|midday)$', var_desc)
        if m:
            prefix, orig, dest, period = m.groups()
            orig_city = orig
            dest_city = dest
            metric_name = f"{prefix}_ratio_{period}"
    elif measure == '3D':
        # Expected format: best_transit_ratio_{origin}_to_{destination}_am_peak_midday
        m = re.search(r'^(.*?)_ratio_(.+)_to_(.+)_am_peak_midday', var_desc)
        if m:
            prefix, orig, dest = m.groups()
            orig_city = orig
            dest_city = dest
            metric_name = f"{prefix}_ratio_am_peak_midday"

    return pd.Series({'orig_city': orig_city, 'dest_city': dest_city, 'metric_name': metric_name})

# Apply the function and create new columns in out_frame
logger.info("Extracting origin, destination, and metric names from variable descriptions")
out_frame[['orig_city', 'dest_city', 'metric_name']] = out_frame.apply(extract_direction, axis=1)

# Pivot the DataFrame: index by orig_city and dest_city and use the metric_name as column headers.
logger.info("Pivoting the data frame to wide format")
out_frame_new = out_frame.pivot(index=['orig_city', 'dest_city'], columns='metric_name', values='current_value')
logger.info(f"Pivoted data frame, shape: {out_frame_new.shape}")

# Move the row with both orig_city and dest_city equal to "regionwide" to the bottom.
logger.info("Reordering rows to move regionwide metrics to the bottom")
regionwide_mask = (out_frame_new.index.get_level_values('orig_city') == "regionwide") & \
                  (out_frame_new.index.get_level_values('dest_city') == "regionwide")
if regionwide_mask.any():
    non_regionwide = out_frame_new[~regionwide_mask]
    regionwide_row = out_frame_new[regionwide_mask]
    out_frame_new = pd.concat([non_regionwide, regionwide_row])
    logger.info("Moved regionwide metrics to the bottom")

# Reorder columns: move any columns that came from regionwide rows to the end.
logger.info("Reordering columns to move regionwide metrics to the end")
regionwide_metrics = out_frame.loc[
    (out_frame['orig_city'] == "regionwide") & 
    (out_frame['dest_city'] == "regionwide"),
    'metric_name'
].unique()

if len(regionwide_metrics) > 0:
    logger.info(f"Found {len(regionwide_metrics)} regionwide metrics to move to the end")
    non_regionwide_cols = [col for col in out_frame_new.columns if col not in regionwide_metrics]
    new_column_order = non_regionwide_cols + list(regionwide_metrics)
    out_frame_new = out_frame_new[new_column_order]

# Reorder columns so that the first four columns are as specified (if they exist).
logger.info("Reordering columns to prioritize key metrics")
desired_first = [
    "best_transit_travel_time_am_peak",
    "best_auto_travel_time_am_peak",
    "best_transit_travel_time_midday",
    "best_auto_travel_time_midday"
]
existing_desired = [col for col in desired_first if col in out_frame_new.columns]
logger.info(f"Found {len(existing_desired)} key metrics to prioritize")
remaining_cols = [col for col in out_frame_new.columns if col not in existing_desired]
out_frame_new = out_frame_new[existing_desired + remaining_cols]

# Save the final, reformatted output.
reordered_file = OUTPUT_DIR_TABLEAU / f"NPA_metrics_Goal_3_{run_name}.xlsx"
# Write the Excel file 
out_frame_new.to_excel(reordered_file, index=True, merge_cells=False)
logger.info(f"Saved reordered metrics to: {reordered_file}")
logger.info("Script execution completed successfully")
