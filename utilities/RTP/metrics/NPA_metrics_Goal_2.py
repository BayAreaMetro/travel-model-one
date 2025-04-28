#!/usr/bin/env python3
"""
This script processes transit and vehicle miles traveled (VMT) metrics.
It computes:
(a) transit counts from individual and joint tour files,
(b) transit mode share metrics for commute and non‐commute tours, and
(c) VMT metrics.
All computed metrics are combined and written to a single CSV file named "Transit_and_VMT_metrics.csv" in the data_output directory.
The script reads the following input files:
  - main/indivTourData_{ITER}.csv (Individual tour data)
  - main/jointTourData_{ITER}.csv (Joint tour data)
  - core_summaries/VehicleMilesTraveled.csv (VMT data)
"""

import os
import pathlib
import numpy as np
import pandas as pd

# ---------------------------
# Set working directory & options
# ---------------------------
WORK_DIR = pathlib.Path("../2050_TM160_DBP_Plan_08b")
os.chdir(WORK_DIR)
print("Current working directory:", os.getcwd())
os.makedirs("../data_output", exist_ok=True)
OUTPUT_Dir = pathlib.Path("../data_output")

pd.set_option('display.width', 500)
pd.set_option('display.precision', 10)

# ---------------------------
# Part 1: Compute Transit Tours Counts
# ---------------------------
def compute_transit_counts():
    """
    Compute total transit counts from individual and joint tour data files.
    For each tour type and iteration, transit trips are counted (using transit mode codes 9–18).
    Returns a DataFrame with transit count metrics.
    """
    iterations = [3]
    transit_modes = list(range(9, 19))  # transit mode numbers from 9 to 18 inclusive

    totals = {"indiv": 0, "joint": 0}

    for tour_type in ["indiv", "joint"]:
        for ITER in iterations:
            input_file = pathlib.Path(f"main/{tour_type}TourData_{ITER}.csv")
            print(f"Reading file: {input_file}")
            df = pd.read_csv(input_file)
            transit_trips = df[df["tour_mode"].isin(transit_modes)]
            count = transit_trips.shape[0]
            totals[tour_type] += count
            print(f"Count for {tour_type} in iteration {ITER}: {count}")
    
    grand_total = totals["indiv"] + totals["joint"]
    print(f"Total Indiv Transit Tours:  {totals['indiv']}")
    print(f"Total Joint Transit Tours:  {totals['joint']}")
    print(f"Grand Total Transit Tours:  {grand_total}")

    # Prepare metrics list (each tuple: run_name, variable description, value, group code)
    run_name = os.path.split(os.getcwd())[1]
    metrics_list = [
        (run_name, "Total Indiv Transit Tours", totals["indiv"], "2A"),
        (run_name, "Total Joint Transit Tours", totals["joint"], "2A"),
        (run_name, "Grand Total Transit Tours", grand_total, "2A")
    ]
    df_metrics = pd.DataFrame(metrics_list, columns=["run_name", "variable_desc", "value", "group_code"])
    return df_metrics

# ---------------------------
# Part 2: Compute Transit Mode Share for Commute and Non-Commute Tours
# ---------------------------
def compute_transit_mode_share():
    """
    Compute transit mode share metrics for commute and non‐commute tours.
    Uses iteration 3 from the indiv and joint tour files.
    Returns a DataFrame with a set of metrics (counts and ratios).
    """
    iterations = [3]
    transit_modes = list(range(9, 19))
    # For mode share we use the first (and only) iteration in the list.
    ITER = iterations[0]

    # Process Individual Tours
    input_file_indiv = pathlib.Path(f"main/indivTourData_{ITER}.csv")
    total_df_indiv = pd.read_csv(input_file_indiv)
    commute_purposes = ['work_low', 'work_med', 'work_high', 'work_very high']
    commute_df_indiv = total_df_indiv[total_df_indiv['tour_purpose'].isin(commute_purposes)]
    noncommute_df_indiv = total_df_indiv[~total_df_indiv['tour_purpose'].isin(commute_purposes)]
    transit_commute_df_indiv = commute_df_indiv[commute_df_indiv["tour_mode"].isin(transit_modes)]
    transit_noncommute_df_indiv = noncommute_df_indiv[noncommute_df_indiv["tour_mode"].isin(transit_modes)]

    # Process Joint Tours
    input_file_joint = pathlib.Path(f"main/jointTourData_{ITER}.csv")
    total_df_joint = pd.read_csv(input_file_joint)
    commute_df_joint = total_df_joint[total_df_joint['tour_purpose'].isin(commute_purposes)]
    noncommute_df_joint = total_df_joint[~total_df_joint['tour_purpose'].isin(commute_purposes)]
    transit_commute_df_joint = commute_df_joint[commute_df_joint["tour_mode"].isin(transit_modes)]
    transit_noncommute_df_joint = noncommute_df_joint[noncommute_df_joint["tour_mode"].isin(transit_modes)]

    # Compute totals for commute tours
    transit_commute_tours = transit_commute_df_indiv.shape[0] + transit_commute_df_joint.shape[0]
    total_commute_tours = commute_df_indiv.shape[0] + commute_df_joint.shape[0]

    # Compute totals for non‐commute tours
    transit_noncommute_tours = transit_noncommute_df_indiv.shape[0] + transit_noncommute_df_joint.shape[0]
    total_noncommute_tours = noncommute_df_indiv.shape[0] + noncommute_df_joint.shape[0]

    # Calculate mode share ratios (with a simple protection against division by zero)
    transit_mode_share_commute = (round((transit_commute_tours / total_commute_tours) * 100, 2) if total_commute_tours > 0 else np.nan)
    transit_mode_share_noncommute = (round((transit_noncommute_tours / total_noncommute_tours) * 100, 2) if total_noncommute_tours > 0 else np.nan)

    # Prepare metrics list
    run_name = os.path.split(os.getcwd())[1]
    metrics_list = [
        (run_name, "Commute Tours - Indiv", commute_df_indiv.shape[0], "2B"),
        (run_name, "Commute Tours - Joint", commute_df_joint.shape[0], "2B"),
        (run_name, "Transit Commute Tours - Indiv", transit_commute_df_indiv.shape[0], "2B"),
        (run_name, "Transit Commute Tours - Joint", transit_commute_df_joint.shape[0], "2B"),
        (run_name, "Total Commute Tours", total_commute_tours, "2B"),
        (run_name, "Total Transit Commute Tours", transit_commute_tours, "2B"),
        (run_name, "Transit Mode Share Commute (%)", transit_mode_share_commute, "2B"),
        (run_name, "Non-Commute Tours - Indiv", noncommute_df_indiv.shape[0], "2C"),
        (run_name, "Non-Commute Tours - Joint", noncommute_df_joint.shape[0], "2C"),
        (run_name, "Transit Non-Commute Tours - Indiv", transit_noncommute_df_indiv.shape[0], "2C"),
        (run_name, "Transit Non-Commute Tours - Joint", transit_noncommute_df_joint.shape[0], "2C"),
        (run_name, "Total Non-Commute Tours", total_noncommute_tours, "2C"),
        (run_name, "Total Transit Non-Commute Tours", transit_noncommute_tours, "2C"),
        (run_name, "Transit Mode Share Non-Commute (%)", transit_mode_share_noncommute, "2C")
    ]
    df_metrics = pd.DataFrame(metrics_list, columns=["run_name", "variable_desc", "value", "group_code"])
    return df_metrics

# ---------------------------
# Part 3: Compute Vehicle Miles Traveled (VMT) Metrics
# ---------------------------
def compute_vmt_metrics():
    """
    Compute VMT metrics from the VehicleMilesTraveled.csv file.
    Calculates total personal VMT (vmt*freq summed over all records) and VMT per capita.
    Returns a DataFrame with VMT metrics.
    """
    input_file = pathlib.Path("core_summaries/VehicleMilesTraveled.csv")
    df = pd.read_csv(input_file)
    vmt = (df['vmt'] * df['freq']).sum()
    total_freq = df['freq'].sum()
    vmt_per_capita = vmt / total_freq if total_freq > 0 else np.nan

    print(f"total personal VMT: {vmt}")
    print(f"VMT per capita: {vmt_per_capita}")

    run_name = os.path.split(os.getcwd())[1]
    metrics_list = [
        (run_name, "Total Personal VMT", vmt, "2D"),
        (run_name, "Total Number of Persons", total_freq, "2E"),
        (run_name, "VMT per Capita", vmt_per_capita, "2E")
    ]
    df_metrics = pd.DataFrame(metrics_list, columns=["run_name", "variable_desc", "value", "group_code"])
    return df_metrics

# ---------------------------
# Main routine
# ---------------------------
def main():
    # Compute transit counts metrics
    transit_counts_df = compute_transit_counts()
    
    # Compute transit mode share metrics
    transit_mode_share_df = compute_transit_mode_share()
    
    # Compute VMT metrics
    vmt_metrics_df = compute_vmt_metrics()
    
    # Combine all metrics into one DataFrame
    combined_df = pd.concat([transit_counts_df, transit_mode_share_df, vmt_metrics_df], ignore_index=True)
    
    # Write the combined metrics to a single CSV file
    output_filename = pathlib.Path(OUTPUT_Dir, "NPA_metrics_Goal_2.csv")
    combined_df.to_csv(output_filename, header=False, float_format='%.5f', index=False)
    print("Combined metrics written to", output_filename)
    
    # Print a summary of the computed metrics
    print("\nCombined Metrics:")
    print(combined_df)

if __name__ == '__main__':
    main()
