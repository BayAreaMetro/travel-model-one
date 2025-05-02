#!/usr/bin/env python3
"""
This script calculates key transit and vehicle miles traveled (VMT) metrics using dedicated computation functions.
It performs the following calculations:
  1. Total Transit Trips: Sums the frequency counts for trips in transit modes 
     (mode numbers 9 through 18) from core_summaries/TripDistance.csv
  2. Transit Mode Share: Determines mode share for both commute and non‐commute
     tours from core_summaries/TimeOfDay.csv
  3. VMT Metrics: Computes total passenger vehicle VMT and VMT per capita from 
     core_summaries/VehicleMilesTraveled.csv

Input files used:
  - core_summaries/TripDistance.csv (Transit trip data)
  - core_summaries/TimeOfDay.csv (Tour data for mode share calculation)
  - core_summaries/VehicleMilesTraveled.csv (VMT data)

The final output is a single CSV file, metrics/NPA_metrics_Goal_2.csv with columns:

"""

import os
import pathlib
import pandas as pd

# ---------------------------
# Part 1: Compute Daily Transit Trips; returns int
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
def compute_transit_mode_share(metrics_dict):
    """
    Compute transit mode share metrics for commute and non‐commute tours using iteration 3 files.
    Updates metrics_dict by adding values for the following keys:
    * transit_commute_tours
    * transit_noncommute_tours,
    * total_commute_tours
    * total_noncommute_tours,
    * transit_mode_share_commute
    * transit_mode_share_noncommute
    """
    TRANSIT_MODES = set(range(9, 19))
    tod_file = pathlib.Path("core_summaries") / "TimeOfDay.csv"
    tod_df = pd.read_csv(tod_file)
    print(f"Read {tod_file}; head:\n{tod_df}")
    # print(tod_df['tour_mode'].value_counts())
    # print(tod_df['simple_purpose'].value_counts())

    # TODO: I think this should be num_participants rather than freq
    # TODO: But leaving as freq to be consistent with original implementation
    metrics_dict["transit_commute_tours"] = tod_df.loc[(tod_df.simple_purpose == 'work') & tod_df.tour_mode.isin(TRANSIT_MODES), 'freq'].sum()
    metrics_dict["total_commute_tours"]   = tod_df.loc[ tod_df.simple_purpose == 'work', 'freq'].sum()
    metrics_dict["transit_mode_share_commute"] = metrics_dict["transit_commute_tours"] / metrics_dict["total_commute_tours"]

    metrics_dict["transit_noncommute_tours"] = tod_df.loc[(tod_df.simple_purpose != 'work') & tod_df.tour_mode.isin(TRANSIT_MODES), 'freq'].sum()
    metrics_dict["total_noncommute_tours"]   = tod_df.loc[ tod_df.simple_purpose != 'work', 'freq'].sum()
    metrics_dict["transit_mode_share_noncommute"] = metrics_dict["transit_noncommute_tours"] / metrics_dict["total_noncommute_tours"]
    
# ---------------------------
# Part 3: Compute Vehicle Miles Traveled (VMT) Metrics
# ---------------------------
def compute_passenger_vehicle_vmt(metrics_dict):
    """
    Compute VMT metrics from the VehicleMilesTraveled.csv file.
    Calculates total personal VMT (vmt*freq summed over all records) and VMT per capita.
    Returns a DataFrame with VMT metrics.
    """
    df = pd.read_csv(pathlib.Path("core_summaries/VehicleMilesTraveled.csv"))
    metrics_dict['total_passenger_vehicle_vmt'] = (df['vmt'] * df['freq']).sum()
    metrics_dict['total_passenger'] = df['freq'].sum()
    metrics_dict['passenger_vehicle_vmt_per_capita'] = metrics_dict['total_passenger_vehicle_vmt'] / metrics_dict['total_passenger'] 

# ---------------------------
# Main routine
# ---------------------------
if __name__ == '__main__':
    pd.set_option('display.width', 800)
    pd.set_option('display.precision', 10)
    pd.set_option('display.max_columns', None)

    # Add transit trips metric
    metrics = {}
    metrics["total_linked_transit_trips"] = compute_transit_trips()
    
    # Add transit mode share metrics
    compute_transit_mode_share(metrics)
    
    # Add VMT metrics
    compute_passenger_vehicle_vmt(metrics)

    print(f"{metrics=}")
    metrics_df = pd.DataFrame([metrics])
    print(metrics_df)

    output_filename = pathlib.Path("metrics") / "NPA_metrics_Goal_2.csv"
    metrics_df.to_csv(output_filename, header=True, index=False)
    
    print("metrics written to", output_filename)
