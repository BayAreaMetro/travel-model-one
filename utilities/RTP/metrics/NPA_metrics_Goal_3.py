#!/usr/bin/env python3
"""
The main tasks performed in the script include:
1. **Data Preparation**
    - Inputs:
     -- {WORK_DIR}/hwy/iter3/avgload5period_vehclasses.csv (auxiliary dataset)
    - Creates a trips_od dataframe with city information by merging with the auxiliary dataset. 
    - Outputs (Intermediate files):
     -- {OUTPUT_Dir}/duplicated_taz_od_cities_df.csv (duplicated TAZ mappings)

2. **OD Travel Time Processing (Goal 3A & 3D)**
- **Goal 3A:** Identifies the minimum transit travel times for each route direction (od pair) and time period, and for the same od pair and time period, the minimum auto travel time.
- **Goal 3D:** Calculate the maximum transit travel time ratio (AM Peak/Midday) for each route direction (od pair).
    - Inputs:
     -- {WORK_DIR}/database/TimeSkimsDatabaseAM.csv (OD travel time data for AM Peak)
     -- {WORK_DIR}/database/TimeSkimsDatabaseMD.csv (OD travel time data for Midday)
    - This part of the script performs the following steps:
     1. Reads and filters the OD travel time data for AM Peak and Midday.
     2. Merges the AM Peak and Midday dataframes with appropriate suffixes.
     3. Creates a trips_od dataframe with city information by merging with the auxiliary dataset.
     4. Defines a function to filter, sort, and save travel time data for each route direction, and calculates the minimum transit travel time for each od pair and for AM Peak and Midday specifically (Goal 3A).
     5. Calculates the maximum transit travel time ratio (AM Peak/Midday) for each od pair (Goal 3D).

   - Outputs (Intermediate files):
     -- {OUTPUT_Dir}/trips_od_travel_time_df_cities.csv (filtered and merged OD travel time data)
     -- {OUTPUT_Dir}/{origin}_to_{destination}/od_travel_time_df.csv 
     

3. **Transit Auto Travel Time Ratio Processing (Goal 3B & 3C)**
- **Goal 3B:** Calculate the average transit-to-auto travel time ratio for AM Peak periods using weighted averages for each route direction (od pair).
- **Goal 3C:** Calculate the average transit-to-auto travel time ratio for Midday periods using weighted averages for each route direction (od pair).

   - Inputs:
     -- {WORK_DIR}/core_summaries/ODTravelTime_byModeTimeperiodIncome.csv (OD travel time data)

   - This part of the script performs the following steps:
     1. Reads Origin-Destination (OD) travel time data from CSV files and filters out records with avg_travel_time_in_mins <= 0.
     2. Maps TAZs to city names by merging with an auxiliary dataset to create a comprehensive dataset for analysis.
     3. Defines a function to filter, sort, and save travel time data for each route direction, separately for transit and auto modes, and for AM Peak and Midday.
     4. Calculates the average travel time by summing the travel time for all trips and dividing by the number of trips and calculates the transit-to-auto ratio for each od pair and for AM Peak (Goal 3B) and Midday (Goal 3C).

   - Outputs (Intermediate files):
     -- {OUTPUT_Dir}/trips_od_travel_time_df_cities_trips.csv (filtered and merged OD travel time data)
     -- {OUTPUT_Dir}/{origin}_to_{destination}/od_travel_time_{am_peak, midday}_{transit, auto}.csv (filtered and merged OD travel time data for AM Peak or Midday and for transit, auto)

4. **Transit Service Data Processing (Goal 3E)**
   - Inputs:
     -- {WORK_DIR}/trn/TransitAssignment.iter3/*.dbf (transit assignment data)

   - This part of the script performs the following steps:
     1. Reads and consolidates transit link data from multiple DBF files, filtering and combining the records.
     2. Filters out records where MODE is less than 10.
     3. Adds a new column 'time_period' by extracting the two letters after "trnlink" and before the next "_" in 'source_file'
     4. Drops duplicate records based on a set of unique columns: 'A', 'B', 'MODE', 'NAME', 'OWNER', 'time_period'.
     5. Maps the 'time_period' values to an 'hour_interval' using a predefined dictionary (e.g., 'am' maps to 4 hours).
     6. Calculates unique transit service miles using the formula: (60/FREQ) * hour_interval * DIST / 100.
     7. Merges with BRT treatment data to determine the proportion of transit service miles provided by BRT.

   - Outputs (Intermediate files):
     -- {OUTPUT_Dir}/transit_data_unique_3E.csv (transit link data with unique records)

5. **Transit Capacity and Crowding Analysis (Goal 3F)**
   - Inputs:
     -- {WORK_DIR}/CTRAMP/scripts/metrics/transitSeatCap.csv (transit seat capacity data)
     -- {WORK_DIR}/trn/trnlink{timeperiod}_ALLMSA.dbf (transit link data) for time periods in AM, EA, EV, MD, PM

   - This part of the script performs the following steps:
     1. Reads transit seat capacity data from a CSV file, and reads transit link data from DBF files for multiple time periods (AM, EA, EV, MD, PM) and combines them.
     2. Applies vehicle type overrides based on transit system and route identifiers.
     3. Merges the transit data with seat capacity data to compute period-specific seating and standing capacities.
     4. Calculates in-vehicle transit time (IVTT) in hours based on the number of trips and trip time.
     5. Identifies crowded conditions (when AB_VOL > 85% of the combined seated and standing capacity) and sums the corresponding person-hours.
     6. Computes the percentage of total person-hours in transit that occur under crowded conditions.

   - Outputs (Intermediate files):
     -- {OUTPUT_Dir}/all_trn_df_3F.csv (transit link data with updated vehicle type and seat capacity)
     -- {OUTPUT_Dir}/aggregated_ivtt_hours_3F.csv (aggregated IVTT by mode, system, and vehicle type)
     -- {OUTPUT_Dir}/veh_type_updated_before_after_comparison_3F.csv (comparison of original and updated vehicle types)

6. **Output Generation**
   - Combines all computed metrics (from Goals 3A, 3B, 3C, 3D, 3E, and 3F) into a summary CSV file:
     -- {OUTPUT_Dir}/NPA_metrics_Goal_3.csv (combined metrics)

7. **Reorder the output**
   - Reorders the output metrics into the wide format (can be deleted if not needed).
"""

import os
from pathlib import Path
import pandas as pd
import simpledbf
import re

# Setup directories and global constants
WORK_DIR = Path("../2050_TM160_DBP_Plan_08b")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())

OUTPUT_DIR = Path(f"../data_output/{WORK_DIR.name}/NPA_Metrics_Goal_3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mode definitions
MODES_TRANSIT = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
MODES_TRANSIT_WALK = [9, 10, 11, 12, 13]
MODES_TRANSIT_DRIVE = [14, 15, 16, 17, 18]
MODES_TAXI_TNC = [19, 20, 21]
MODES_SOV = [1, 2]
MODES_HOV = [3, 4, 5, 6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV

TIMEPERIOD_LABELS = ['AM Peak', 'Midday']
ROUTE_PAIRS = [
    ("Richmond", "Oakland"),
    ("Oakland", "Richmond"),
    ("Oakland", "San Francisco"),
    ("San Francisco", "Oakland"),
    (["Fremont", "Union City"], "San Jose"),
    ("San Jose", ["Fremont", "Union City"]),
    (["Mountain View", "Palo Alto"], "San Jose"),
    ("San Jose", ["Mountain View", "Palo Alto"])
]
OD_DIRECTIONS = [
    "richmond_to_oakland", "oakland_to_richmond", "oakland_to_san_francisco", "san_francisco_to_oakland",
    "fremont&union_city_to_san_jose", "san_jose_to_fremont&union_city", "mountain_view&palo_alto_to_san_jose", "san_jose_to_mountain_view&palo_alto"
]

# Map TAZs to cities for OD analysis
od_cities_df = pd.read_csv(WORK_DIR / "hwy" / "iter3" / "avgload5period_vehclasses.csv")[['a', 'b', 'cityname']]
od_cities_df = (od_cities_df[od_cities_df['a'] <= 1454]
                .rename(columns={'a': 'taz_id'})
                .drop_duplicates(subset=['taz_id', 'cityname']))

# Save duplicated TAZ mappings and merge city information
dup_taz = od_cities_df[od_cities_df.duplicated(subset='taz_id', keep=False)]
dup_taz.to_csv(OUTPUT_DIR / "duplicated_taz_od_cities_df.csv", index=False)

def format_city(city):
    """Format city name(s) for folder naming."""
    if isinstance(city, list):
        return "&".join(c.lower().replace(" ", "_") for c in city)
    return city.lower().replace(" ", "_")

# --------------------------
# 3A & 3D: OD Travel Time Processing
# --------------------------
# Read and filter the OD travel time data
trips_od_df_am_peak = pd.read_csv(WORK_DIR / "database" / "TimeSkimsDatabaseAM.csv")
trips_od_df_midday = pd.read_csv(WORK_DIR / "database" / "TimeSkimsDatabaseMD.csv")

# Join AM Peak and Midday dataframes with appropriate suffixes
trips_od_df = pd.merge(
    trips_od_df_am_peak,
    trips_od_df_midday,
    on=['orig', 'dest'],
    suffixes=('_am_peak', '_midday')
).rename(columns = {'orig': 'orig_taz', 'dest': 'dest_taz'})

# Create trips_od dataframe with city information
trips_od = (pd.merge(trips_od_df, od_cities_df, left_on="orig_taz", right_on="taz_id")
               .rename(columns={"cityname": "orig_CITY"})
               .drop(columns=["taz_id", "b"]))
trips_od = (pd.merge(trips_od, od_cities_df, left_on="dest_taz", right_on="taz_id")
               .rename(columns={"cityname": "dest_CITY"})
               .drop(columns=["taz_id", "b"]))
trips_od.to_csv(OUTPUT_DIR / "trips_od_travel_time_df_cities.csv", index=False)

def process_direction(df, origin, destination, out_folder):
    """Filter, sort, and save OD travel time data by route direction."""
    origin_list = origin if isinstance(origin, list) else [origin]
    destination_list = destination if isinstance(destination, list) else [destination]
    
    route = df[df['orig_CITY'].isin(origin_list) & df['dest_CITY'].isin(destination_list)].copy()
    # Calculate ratios for rows where values are not -999
    route.loc[(route['wTrnW_am_peak'] != -999) & (route['wTrnW_midday'] != -999), 'wTrnW_ratio'] = route['wTrnW_am_peak'] / route['wTrnW_midday']

    out_folder.mkdir(parents=True, exist_ok=True)
    route.to_csv(out_folder / f"od_travel_time_df.csv", index=False)
    print(f"Wrote {out_folder / 'od_travel_time_df.csv'}")

# Process route direction
for origin, destination in ROUTE_PAIRS:
    folder_name = f"{format_city(origin)}_to_{format_city(destination)}"
    process_direction(trips_od, origin, destination, OUTPUT_DIR / folder_name)

metrics_3A = {}
for direction in OD_DIRECTIONS:
    df = pd.read_csv(OUTPUT_DIR / direction / "od_travel_time_df.csv")
    for period in ["am_peak", "midday"]:
        min_transit_row = df.loc[df[f'wTrnW_{period}'] != -999]
        min_transit_row = min_transit_row.loc[min_transit_row[f'wTrnW_{period}'] == min_transit_row[f'wTrnW_{period}'].min()]
        min_transit_time = min_transit_row[f'wTrnW_{period}'] 

        print(f"min_transit_row for {direction} {period}\n:{min_transit_row}")
        
        # Find the minimum auto travel time for the same od pair
        orig_taz = min_transit_row['orig_taz'].values[0]
        dest_taz = min_transit_row['dest_taz'].values[0]
        condition = ((df['orig_taz'] == orig_taz) & (df['dest_taz'] == dest_taz))
        print(f"df.loc[condition]:\n{df.loc[condition]}")
        # this should be a single row, right?
        # then, how is this the minimum or the best?  isn't it just the travel time?
        min_auto_time = df.loc[condition, f'da_{period}'].min()
        metrics_3A[f"best_transit_origin_{direction}_{period}"] = orig_taz
        metrics_3A[f"best_transit_destination_{direction}_{period}"] = dest_taz
        metrics_3A[f"best_transit_travel_time_{direction}_{period}"] = min_transit_time.values[0]
        metrics_3A[f"best_auto_travel_time_{direction}_{period}"] = min_auto_time

metrics_3D = {}
for direction in OD_DIRECTIONS:
    df_ratio = pd.read_csv(OUTPUT_DIR / direction / "od_travel_time_df.csv")
    max_ratio = round(df_ratio['wTrnW_ratio'].max(), 2) if not df_ratio.empty else None
    metrics_3D[f"best_transit_ratio_{direction}_am_peak_midday"] = max_ratio

# --------------------------
# 3B & 3C: Transit Auto Travel Time Ratio Processing
# --------------------------
trips_od_df_trips = pd.read_csv(WORK_DIR / "core_summaries" / "ODTravelTime_byModeTimeperiodIncome.csv")
trips_od_df_trips = trips_od_df_trips[trips_od_df_trips['avg_travel_time_in_mins'] > 0]

# Create trips_od dataframe with city information
trips_od_trips = (pd.merge(trips_od_df_trips, od_cities_df, left_on="orig_taz", right_on="taz_id")
               .rename(columns={"cityname": "orig_CITY"})
               .drop(columns=["taz_id", "b"]))
trips_od_trips = (pd.merge(trips_od_trips, od_cities_df, left_on="dest_taz", right_on="taz_id")
               .rename(columns={"cityname": "dest_CITY"})
               .drop(columns=["taz_id", "b"]))
trips_od_trips.to_csv(OUTPUT_DIR / "trips_od_travel_time_df_cities_trips.csv", index=False)

def process_direction_2(df, origin, destination, out_folder, period_label):
    """Filter, sort, and save OD travel time data by route direction."""
    origin_list = origin if isinstance(origin, list) else [origin]
    destination_list = destination if isinstance(destination, list) else [destination]
    
    route = df[df['orig_CITY'].isin(origin_list) & df['dest_CITY'].isin(destination_list)].copy()
    route.sort_values('avg_travel_time_in_mins', inplace=True)
    transit = route[route['trip_mode'].isin(MODES_TRANSIT)].copy().sort_values('avg_travel_time_in_mins')
    auto = route[route['trip_mode'].isin(MODES_PRIVATE_AUTO + MODES_TAXI_TNC)].copy().sort_values('avg_travel_time_in_mins')
    out_folder.mkdir(parents=True, exist_ok=True)
    transit.to_csv(out_folder / f"od_travel_time_{period_label}_transit.csv", index=False)
    auto.to_csv(out_folder / f"od_travel_time_{period_label}_auto.csv", index=False)

def compute_transit_auto_travel_time_ratio(direction, period):
    folder = OUTPUT_DIR / direction
    df_transit = pd.read_csv(folder / f"od_travel_time_{period}_transit.csv").drop(columns=['timeperiod_label'])
    df_auto = pd.read_csv(folder / f"od_travel_time_{period}_auto.csv").drop(columns=['timeperiod_label'])
    df_transit['total_travel_time'] = df_transit['avg_travel_time_in_mins'] * df_transit['num_trips']
    df_auto['total_travel_time'] = df_auto['avg_travel_time_in_mins'] * df_auto['num_trips']
    avg_transit = df_transit['total_travel_time'].sum() / df_transit['num_trips'].sum()
    avg_auto = df_auto['total_travel_time'].sum() / df_auto['num_trips'].sum()
    return avg_transit / avg_auto

# Process each time period and route direction
for time_period in TIMEPERIOD_LABELS:
    period_label = time_period.lower().replace(" ", "_")
    df_tp = trips_od_trips[trips_od_trips['timeperiod_label'] == time_period].drop(columns=['incQ', 'incQ_label']).drop_duplicates()
    
    for origin, destination in ROUTE_PAIRS:
        folder_name = f"{format_city(origin)}_to_{format_city(destination)}"
        process_direction_2(df_tp, origin, destination, OUTPUT_DIR / folder_name, period_label)

metrics_3B = {}
for direction in OD_DIRECTIONS:
    ratio = compute_transit_auto_travel_time_ratio(direction, "am_peak")
    metrics_3B[f"transit_auto_travel_time_ratio_{direction}_am_peak"] = round(ratio, 2)

metrics_3C = {}
for direction in OD_DIRECTIONS:
    ratio = compute_transit_auto_travel_time_ratio(direction, "midday")
    metrics_3C[f"transit_auto_travel_time_ratio_{direction}_midday"] = round(ratio, 2)

# --------------------------
# 3E: Transit Service Data Processing
# --------------------------
transit_assignment_dir = WORK_DIR / "trn" / "TransitAssignment.iter3"
dbf_files = [f for f in os.listdir(transit_assignment_dir) if f.lower().endswith('.dbf') and not f.lower().endswith('_links.dbf')]

transit_data = pd.DataFrame()
for dbf_file in dbf_files:
    file_path = transit_assignment_dir / dbf_file
    dbf = simpledbf.Dbf5(str(file_path))
    df_temp = dbf.to_dataframe()
    df_temp['source_file'] = dbf_file
    # # Filter out records where MODE is less than 10
    df_temp = df_temp[df_temp['MODE'] >= 10]
    transit_data = pd.concat([transit_data, df_temp], ignore_index=True)

transit_data['time_period'] = transit_data['source_file'].str.extract(r'trnlink([A-Za-z]{2})_')
unique_cols = ['A', 'B', 'MODE', 'NAME', 'OWNER', 'time_period']
transit_data_unique = transit_data.drop_duplicates(subset=unique_cols, keep='first')
hour_interval_map = {'ea': 3, 'am': 4, 'md': 5, 'pm': 4, 'ev': 8}
transit_data_unique['hour_interval'] = transit_data_unique['time_period'].map(hour_interval_map)
transit_data_unique.to_csv(OUTPUT_DIR / "transit_data_unique_3E.csv", index=False)

brt_treatment_df = pd.read_csv(WORK_DIR / "hwy" / "iter3" / "avgload5period_vehclasses.csv")
brt_treatment_df = brt_treatment_df[brt_treatment_df['brt'] > 0]

metrics_3E = {}
transit_data_unique['service_miles'] = (60 / transit_data_unique['FREQ']) * transit_data_unique['hour_interval'] * transit_data_unique['DIST'] / 100
transit_service_miles = transit_data_unique['service_miles'].sum()
merged_brt = transit_data_unique.merge(brt_treatment_df, left_on=["A", "B"], right_on=["a", "b"], how="inner")
transit_service_miles_brt = merged_brt["service_miles"].sum()

metrics_3E["transit_service_miles"] = int(round(transit_service_miles))
metrics_3E["transit_service_miles_brt"] = int(round(transit_service_miles_brt))
metrics_3E["transit_service_miles_brt_pct"] = round(transit_service_miles_brt / transit_service_miles, 3)

# --------------------------
# 3F: Transit Capacity and Crowding Analysis
# --------------------------
transit_seatcap_df = pd.read_csv(WORK_DIR / "CTRAMP" / "scripts" / "metrics" / "transitSeatCap.csv")
transit_seatcap_df.columns = transit_seatcap_df.columns.str.replace('%','pct')
transit_seatcap_df.rename(columns={"VEHTYPE":"veh_type_updated", "100pctCapacity":"standcap"}, inplace=True)

all_trn_df = pd.DataFrame()
for tp in ['AM', 'EA', 'EV', 'MD', 'PM']:
    trn_file = WORK_DIR / "trn" / f"trnlink{tp}_ALLMSA.dbf"
    dbf = simpledbf.Dbf5(str(trn_file))
    trn_df = dbf.to_dataframe()
    trn_df["period"] = tp
    all_trn_df = pd.concat([all_trn_df, trn_df], ignore_index=True)

cols_to_drop = ["AB_XITA","AB_BRDB","BA_VOL","BA_BRDA","BA_XITA","BA_BRDB","BA_XITB"]
all_trn_df.drop(columns=cols_to_drop, inplace=True)
all_trn_df.sort_values(by=["MODE","NAME","period","SEQ"], inplace=True)
all_trn_df["veh_type_updated"] = all_trn_df["VEHTYPE"]

# Vehicle type overrides
## AC Transit Transbay
all_trn_df.loc[all_trn_df["SYSTEM"]=="AC Transit", "veh_type_updated"] = "AC Plus Bus"
all_trn_df.loc[all_trn_df["SYSTEM"]=="AC Transit Transbay", "veh_type_updated"] = "AC Plus Bus"

override_patterns = ["84_LA", "84_NL", "84_O", "84_NX", "84_SB", "84_F", "84_J", "84_CFLA", "84_CFNL", "84_CFO", "84_CFNX", "84_CFSB", "84_CFF", "84_CFJ"]
for pattern in override_patterns:
    all_trn_df.loc[all_trn_df["NAME"].str.contains(pattern), "veh_type_updated"] = "Motor Articulated Bus"

## Other express buses
all_trn_df.loc[ all_trn_df["SYSTEM"]=="WestCAT Express", "veh_type_updated"] = "AC Plus Bus"   # note this is transbay buses
all_trn_df.loc[ all_trn_df["SYSTEM"]=="Golden Gate Transit Express", "veh_type_updated"] = "AC Plus Bus"   # note this is transbay buses

## AC Transit Local
local_patterns = {
    "Motor Articulated Bus": ["30_1AC", "30_BRT", "30_6AC", "30_72R", "30_97R"],
    "Motor Bus Mix of Standard and Artics": ["30_40", "30_52", "30_57", "30_60", "30_97", "30_99", "30_217"]
}
for veh_type, patterns in local_patterns.items():
    for pat in patterns:
        all_trn_df.loc[all_trn_df["NAME"].str.contains(pat), "veh_type_updated"] = veh_type

## VTA bus
vta_patterns = {
    "Motor Articulated Bus": ["522VTA", "523VTA", "22VTA"],
    "Motor Bus Mix of Standard and Artics": ["40VTA", "55VTA"]
}
for veh_type, patterns in vta_patterns.items():
    for pat in patterns:
        all_trn_df.loc[all_trn_df["NAME"].str.contains(pat), "veh_type_updated"] = veh_type

## Samtrans 
samtrans_patterns = ["24_ECR", "24_292", "24_398"]
for pat in samtrans_patterns:
    all_trn_df.loc[all_trn_df["NAME"].str.contains(pat), "veh_type_updated"] = "Motor Articulated Bus"

all_trn_df.loc[all_trn_df["NAME"].str.contains("120_EBART"), "veh_type_updated"] = "eBart 1 car"
all_trn_df.loc[(all_trn_df["NAME"].str.contains("120_EBART")) & (all_trn_df["period"]=="AM"), "veh_type_updated"] = "eBart 2 car"
all_trn_df.loc[(all_trn_df["NAME"].str.contains("120_EBART")) & (all_trn_df["period"]=="PM"), "veh_type_updated"] = "eBart 2 car"

## for crossings projects   
all_trn_df.loc[(all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"].isin(["EA","MD","EV"])), "veh_type_updated"] = "5 Car BART RENOVATED"
all_trn_df.loc[(all_trn_df["veh_type_updated"]=='8 Car BART') & (all_trn_df["period"].isin(["AM","PM"])), "veh_type_updated"] = "10 Car BART RENOVATED"
all_trn_df.loc[all_trn_df["NAME"].str.contains("130_RR"), "veh_type_updated"] = "Caltrain PCBB 10 car"

veh_comparison_df = all_trn_df.loc[all_trn_df["VEHTYPE"] != all_trn_df["veh_type_updated"]]
veh_comparison_df.to_csv(OUTPUT_DIR / "veh_type_updated_before_after_comparison_3F.csv", index=False)

all_trn_df = pd.merge(all_trn_df,
                      transit_seatcap_df[["veh_type_updated","seatcap","standcap"]],
                      on="veh_type_updated", how="left")
all_trn_df["period_seatcap"] = all_trn_df["PERIODCAP"] / all_trn_df["VEHCAP"] * all_trn_df["seatcap"]
all_trn_df["period_standcap"] = all_trn_df["PERIODCAP"] / all_trn_df["VEHCAP"] * all_trn_df["standcap"]
all_trn_df["load_seatcap"] = all_trn_df["AB_VOL"] / all_trn_df["period_seatcap"]
all_trn_df["load_standcap"] = all_trn_df["AB_VOL"] / all_trn_df["period_standcap"]
all_trn_df["ivtt_hours"] = all_trn_df["AB_VOL"] * (all_trn_df["TIME"]/100) / 60
all_trn_df.to_csv(OUTPUT_DIR / "all_trn_df_3F.csv", index=False)

grouped_ivtt = all_trn_df.groupby(["MODE", "SYSTEM", "veh_type_updated"], as_index=False)["ivtt_hours"].sum()
grouped_ivtt.to_csv(OUTPUT_DIR / "aggregated_ivtt_hours_3F.csv", index=False)

crowded_condition = all_trn_df["AB_VOL"] > 0.85 * (all_trn_df["period_seatcap"] + all_trn_df["period_standcap"])
crowded_person_hours = all_trn_df.loc[crowded_condition, "ivtt_hours"].sum()
total_person_hours = all_trn_df["ivtt_hours"].sum()
ratio_crowded = crowded_person_hours / total_person_hours

metrics_3F = {
    "crowded_person_hours": int(round(crowded_person_hours)),
    "total_person_hours": int(round(total_person_hours)),
    "ratio_crowded": round(ratio_crowded, 2)
}

# --------------------------
# Metrics Calculation 
# --------------------------
metrics_sets = [
    (metrics_3A, '3A'),
    (metrics_3B, '3B'),
    (metrics_3C, '3C'),
    (metrics_3D, '3D'),
    (metrics_3E, '3E'),
    (metrics_3F, '3F')
]

run_name = Path(os.getcwd()).parts[-1]
dfs = []
for metrics, measure_name in metrics_sets:
    df = pd.DataFrame(list(metrics.items()), columns=['variable_desc', 'current_value'])
    df.insert(0, 'run_name', run_name)
    df.insert(3, 'measure_names', measure_name)
    dfs.append(df)

out_frame = pd.concat(dfs, ignore_index=True)
out_frame.to_csv(OUTPUT_DIR / "NPA_metrics_Goal_3.csv", index=False)

# --------------------------
# Reorder the output
# --------------------------

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
out_frame[['orig_city', 'dest_city', 'metric_name']] = out_frame.apply(extract_direction, axis=1)

# Pivot the DataFrame: index by orig_city and dest_city and use the metric_name as column headers.
out_frame_new = out_frame.pivot(index=['orig_city', 'dest_city'], columns='metric_name', values='current_value')

# Move the row with both orig_city and dest_city equal to "regionwide" to the bottom.
regionwide_mask = (out_frame_new.index.get_level_values('orig_city') == "regionwide") & \
                  (out_frame_new.index.get_level_values('dest_city') == "regionwide")
if regionwide_mask.any():
    non_regionwide = out_frame_new[~regionwide_mask]
    regionwide_row = out_frame_new[regionwide_mask]
    out_frame_new = pd.concat([non_regionwide, regionwide_row])

# Reorder columns: move any columns that came from regionwide rows to the end.
regionwide_metrics = out_frame.loc[
    (out_frame['orig_city'] == "regionwide") & 
    (out_frame['dest_city'] == "regionwide"),
    'metric_name'
].unique()

if len(regionwide_metrics) > 0:
    non_regionwide_cols = [col for col in out_frame_new.columns if col not in regionwide_metrics]
    new_column_order = non_regionwide_cols + list(regionwide_metrics)
    out_frame_new = out_frame_new[new_column_order]

# Reorder columns so that the first four columns are as specified (if they exist).
desired_first = [
    "best_transit_travel_time_am_peak",
    "best_auto_travel_time_am_peak",
    "best_transit_travel_time_midday",
    "best_auto_travel_time_midday"
]
existing_desired = [col for col in desired_first if col in out_frame_new.columns]
remaining_cols = [col for col in out_frame_new.columns if col not in existing_desired]
out_frame_new = out_frame_new[existing_desired + remaining_cols]

# Save the final, reformatted output.
out_frame_new.to_csv(OUTPUT_DIR / "NPA_metrics_Goal_3_reordered.csv", index=True)

