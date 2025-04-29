#!/usr/bin/env python3
"""
This script calculates key transit and vehicle miles traveled (VMT) metrics using dedicated computation functions.
It performs the following calculations:
  1. Total Transit Trips: Sums the frequency counts for trips in transit modes (mode numbers 9 through 18) from the TripDistance.csv file.
  2. Transit Mode Share: Determines mode share for both commute and non‐commute tours by processing individual and joint tour data (iteration 3 files), while adjusting for a 0.5 sample rate.
  3. VMT Metrics: Computes total passenger vehicle VMT and VMT per capita based on the VehicleMilesTraveled.csv data.

Input files used:
  - core_summaries/TripDistance.csv (Transit trip data)
  - main/indivTourData_3.csv and main/jointTourData_3.csv (Tour data for mode share calculation)
  - core_summaries/VehicleMilesTraveled.csv (VMT data)

The final output is a single CSV file named "{OUTPUT_Dir}/NPA_metrics_Goal_2.csv".
To make it suitable for Tableau, a reordered CSV file is generated as {OUTPUT_Dir}/NPA_metrics_Goal_2_reordered.csv, and an Excel file is created as {OUTPUT_Dir_Tableau}/NPA_metrics_Goal_2_{WORK_DIR.name}.xlsx.
"""

import os
import pathlib
import numpy as np
import pandas as pd

# ---------------------------
# Set working directory & options
# ---------------------------
WORK_DIR = pathlib.Path("../2035_TM161_FBP_NoProject_06")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())

os.makedirs(f"../data_output/{WORK_DIR.name}/NPA_Metrics_Goal_2", exist_ok=True)
OUTPUT_Dir = pathlib.Path(f"../data_output/{WORK_DIR.name}/NPA_Metrics_Goal_2")

os.makedirs(f"../data_output/Tableau_NPA_Metrics_Goal_2", exist_ok=True)
OUTPUT_Dir_Tableau = pathlib.Path(f"../data_output/Tableau_NPA_Metrics_Goal_2")

pd.set_option('display.width', 500)
pd.set_option('display.precision', 10)

# ---------------------------
# Part 1: Compute Transit Trips 
# ---------------------------
def compute_transit_trips():
    """
    Sum(freq) = trips
    """
    transit_modes = list(range(9, 19))  # transit mode numbers from 9 to 18 inclusive
    df = pd.read_csv(pathlib.Path(f"core_summaries/TripDistance.csv"))
    trips = df[df["trip_mode"].isin(transit_modes)]['freq'].sum()
    return trips

# ---------------------------
# Part 2: Compute Transit Mode Share for Commute and Non-Commute Tours
# ---------------------------
def compute_transit_mode_share():
    """
    Compute transit mode share metrics for commute and non‐commute tours using iteration 3 files.
    Returns a tuple:
      (transit_commute_tours, transit_noncommute_tours,
       total_commute_tours, total_noncommute_tours,
       transit_mode_share_commute, transit_mode_share_noncommute)
    """
    transit_modes = set(range(9, 19))
    commute_purposes = {'work_low', 'work_med', 'work_high', 'work_very high'}
    files = [pathlib.Path("main/indivTourData_3.csv"),
             pathlib.Path("main/jointTourData_3.csv")]
    
    total_commute = total_noncommute = 0
    transit_commute = transit_noncommute = 0
    
    for f in files:
        df = pd.read_csv(f)
        is_commute = df['tour_purpose'].isin(commute_purposes)
        total_commute += is_commute.sum()
        total_noncommute += (~is_commute).sum()
        transit_commute += df.loc[is_commute, 'tour_mode'].isin(transit_modes).sum()
        transit_noncommute += df.loc[~is_commute, 'tour_mode'].isin(transit_modes).sum()
    
    # Each tour counts as two trips because the sample rate is 0.5
    transit_commute_tours = transit_commute * 2
    total_commute_tours = total_commute * 2
    transit_noncommute_tours = transit_noncommute * 2
    total_noncommute_tours = total_noncommute * 2
    
    share_commute = (transit_commute_tours / total_commute_tours
                     if total_commute_tours else np.nan)
    share_noncommute = (transit_noncommute_tours / total_noncommute_tours
                        if total_noncommute_tours else np.nan)
    
    return (transit_commute_tours, transit_noncommute_tours,
            total_commute_tours, total_noncommute_tours,
            share_commute, share_noncommute)

# ---------------------------
# Part 3: Compute Vehicle Miles Traveled (VMT) Metrics
# ---------------------------
def compute_passenger_vehicle_vmt():
    """
    Compute VMT metrics from the VehicleMilesTraveled.csv file.
    Calculates total personal VMT (vmt*freq summed over all records) and VMT per capita.
    Returns a DataFrame with VMT metrics.
    """
    df = pd.read_csv(pathlib.Path("core_summaries/VehicleMilesTraveled.csv"))
    vmt = (df['vmt'] * df['freq']).sum()
    total_freq = df['freq'].sum()
    vmt_per_capita = vmt / total_freq if total_freq > 0 else np.nan

    return vmt, total_freq, vmt_per_capita

# ---------------------------
# Main routine
# ---------------------------
if __name__ == '__main__':
    run_name = os.path.split(os.getcwd())[1]
    metrics = []

    # Add transit trips metric
    metrics.append((run_name, "total_linked_transit_trips", compute_transit_trips(), "2A"))
    
    # Add transit mode share metrics
    tms = compute_transit_mode_share()
    metrics.extend([
        (run_name, "transit_commute_tours", tms[0], "2B"),
        (run_name, "total_commute_tours", tms[2], "2B"),
        (run_name, "transit_mode_share_commute", round(tms[4], 3), "2B"),
        (run_name, "transit_noncommute_tours", tms[1], "2C"),
        (run_name, "total_noncommute_tours", tms[3], "2C"),
        (run_name, "transit_mode_share_noncommute", round(tms[5], 3), "2C")
    ])
    
    # Add VMT metrics
    vmt = compute_passenger_vehicle_vmt()
    metrics.extend([
        (run_name, "total_passenger_vehicle_vmt", round(vmt[0], 0), "2D"),
        (run_name, "total_passenger", round(vmt[1], 0), "2E"),
        (run_name, "passenger_vehicle_vmt_per_capita", round(vmt[2], 2), "2E")
    ])
    
    # Create DataFrame, drop run_name column, and output the CSV
    combined_df = pd.DataFrame(metrics, columns=["run_name", "variable_desc", "current_value", "measure_names"])
    combined_df.drop(columns="run_name", inplace=True)
    output_filename = pathlib.Path(OUTPUT_Dir, "NPA_metrics_Goal_2.csv")
    combined_df.to_csv(output_filename, header=True, float_format='%.5f', index=False)
    
    print("Combined metrics written to", output_filename)
    print("\nCombined Metrics:")
    print(combined_df)

# ---------------------------
# Reorder the output
# ---------------------------
def reorder_metrics(row):
    desc = row['variable_desc']
    if row['measure_names'] in ['2D', '2E']:
        mode, tour_purpose = None, None
    else:
        mode = 'transit' if 'transit' in desc else 'all'
        tour_purpose = 'commute' if '_commute' in desc else 'noncommute' if '_noncommute' in desc else 'all'
    
    conditions = [
        ('total_linked_transit_trips', 'trips'),
        ('transit_commute_tours', 'tours'),
        ('total_commute_tours', 'tours'),
        ('transit_mode_share_commute', 'mode_share'),
        ('transit_noncommute_tours', 'tours'),
        ('total_noncommute_tours', 'tours'),
        ('transit_mode_share_noncommute', 'mode_share'),
        ('total_passenger_vehicle_vmt', 'total_passenger_vehicle_vmt'),
        ('total_passenger', 'total_number_of_persons'),
        ('passenger_vehicle_vmt_per_capita', 'vmt_per_capita')
    ]
    metric_name = next((name for key, name in conditions if key in desc), None)
    return pd.Series({'mode': mode, 'tour_purpose': tour_purpose, 'metric_name': metric_name})

combined_df[['mode', 'tour_purpose', 'metric_name']] = combined_df.apply(reorder_metrics, axis=1)

df_pivot = combined_df.pivot(
    index=['measure_names', 'variable_desc', 'mode', 'tour_purpose'],
    columns='metric_name',
    values='current_value'
).reset_index()

order = ['trips', 'tours', 'mode_share', 'total_passenger_vehicle_vmt', 'total_number_of_persons', 'vmt_per_capita']
final_columns = ['measure_names', 'variable_desc', 'mode', 'tour_purpose'] + [m for m in order if m in df_pivot.columns]
df_pivot = df_pivot[final_columns]

df_pivot.to_csv(pathlib.Path(OUTPUT_Dir, "NPA_metrics_Goal_2_reordered.csv"), index=False)
df_pivot.to_excel(pathlib.Path(OUTPUT_Dir_Tableau, f"NPA_metrics_Goal_2_{WORK_DIR.name}.xlsx"), index=False)
