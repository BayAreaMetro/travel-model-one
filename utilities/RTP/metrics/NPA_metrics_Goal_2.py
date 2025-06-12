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

import pathlib
import pandas as pd
import pyreadr

# ---------------------------
# Part 1: Compute Daily Transit Trips; returns int
# ---------------------------
def compute_transit_trips():
    """
    Returns dataframe with columns: is_transit, county_name (of residence), num_trips
    """
    print("compute_transit_trips():")
    transit_modes = list(range(9, 19))  # transit mode numbers from 9 to 18 inclusive
    df = pd.read_csv(pathlib.Path(f"core_summaries/TripDistance.csv"))
    trips = df[df["trip_mode"].isin(transit_modes)]['freq'].sum()
    print(f"trips: {trips}")

    # read taz -> county mapping for home_taz
    taz_county_df = pd.read_csv(
        pathlib.Path(__file__).parent.parent.parent / "geographies" / "taz-superdistrict-county.csv",
        usecols=['ZONE','COUNTY_NAME']
    )
    taz_county_df.rename(columns={'ZONE':'home_taz', 'COUNTY_NAME':'county_name'}, inplace=True)

    print("Reading trips.rdata")
    trips_df = pyreadr.read_r(pathlib.Path("updated_output/trips.rdata"))['trips']
    trips_df = trips_df[['hh_id','person_id','home_taz','trip_mode','sampleRate']]
    # select only transit trips
    transit_trips_df = trips_df.loc[trips_df.trip_mode.isin(transit_modes)]

    # join to home_taz for home county
    transit_trips_df = pd.merge(left=transit_trips_df, right=taz_county_df, how="left", validate='many_to_one')

    print(f"transit_trips_df:\n{transit_trips_df.head()}")

    transit_trips_df['num_transit_trips'] = 1.0/transit_trips_df['sampleRate']
    summary_df = transit_trips_df.groupby(['county_name']).agg(
        num_transit_trips = pd.NamedAgg(column='num_transit_trips', aggfunc='sum'),
    ).reset_index(drop=False)
    print(f"transit_trips_df summary_df:\n{summary_df}")
    return summary_df

# ---------------------------
# Part 2: Compute Transit Mode Share for Commute and Non-Commute Tours
# ---------------------------
def compute_transit_mode_share():
    """
    Compute transit mode share metrics for commute and non‐commute tours using core_summaries/TimeOfDay.csv.
    Returns summary dataframe with columns: county_name (of residence), num_tours, num_commute_tours, num_transit_tours, num_transit_commute_tours
    """
    TRANSIT_MODES = set(range(9, 19))
    tod_file = pathlib.Path("core_summaries") / "TimeOfDay.csv"
    tod_df = pd.read_csv(tod_file)
    # print(f"Read {tod_file}:\n{tod_df}")

    tod_df['commute_tour'] = 0
    tod_df.loc[tod_df.simple_purpose == 'work', 'commute_tour'] = tod_df.num_participants

    tod_df['transit_tour'] = 0
    tod_df.loc[tod_df.tour_mode.isin(TRANSIT_MODES), 'transit_tour'] = tod_df.num_participants

    tod_df['transit_commute_tour'] = 0
    tod_df.loc[(tod_df.simple_purpose == 'work') & tod_df.tour_mode.isin(TRANSIT_MODES), 
               'transit_commute_tour'] = tod_df.num_participants

    summary_df = tod_df.groupby(['county_name']).agg(
        num_tours                 = pd.NamedAgg(column='num_participants',     aggfunc='sum'),
        num_commute_tours         = pd.NamedAgg(column='commute_tour',         aggfunc='sum'),
        num_transit_tours         = pd.NamedAgg(column='transit_tour',         aggfunc='sum'),
        num_transit_commute_tours = pd.NamedAgg(column='transit_commute_tour', aggfunc='sum')
    ).reset_index(drop=False)
    return summary_df
    
    
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

    df['total_passenger_vehicle_vmt'] = df['vmt'] * df['freq']
    summary_df = df.groupby(['county_name']).agg(
        total_passenger_vehicle_vmt = pd.NamedAgg(column='total_passenger_vehicle_vmt', aggfunc='sum'),
        total_passenger = pd.NamedAgg(column='freq', aggfunc='sum')
    ).reset_index(drop=False)
    
    summary_df['passenger_vehicle_vmt_per_capita'] = summary_df['total_passenger_vehicle_vmt'] / summary_df['total_passenger'] 
    return summary_df

# ---------------------------
# Main routine
# ---------------------------
if __name__ == '__main__':
    pd.set_option('display.width', 800)
    pd.set_option('display.precision', 10)
    pd.set_option('display.max_columns', None)

    # Add transit trips metric
    metrics_df = compute_transit_trips()

    # Add VMT metrics by county
    vmt_df = compute_passenger_vehicle_vmt()
    metrics_df = pd.merge(
        left=metrics_df,
        right=vmt_df,
        on='county_name',
        validate='one_to_one'
    )

    # Add mode share metrics by county
    mode_share_df = compute_transit_mode_share()
    metrics_df = pd.merge(
        left=metrics_df,
        right=mode_share_df,
        on='county_name',
        validate='one_to_one'
    )
    print(f"metrics_df=\n{metrics_df}")

    output_filename = pathlib.Path("metrics") / "NPA_metrics_Goal_2.csv"
    metrics_df.to_csv(output_filename, header=True, index=False)
    
    print("metrics written to", output_filename)
