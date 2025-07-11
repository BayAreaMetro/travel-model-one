#!/usr/bin/env python3
"""
This script calculates the following metrics for NPA Goal 3
https://app.asana.com/1/11860278793487/project/1205004773899709/task/1209227772187405?focus=true

calculate_and_write_travel_time_metrics()
  **Goal 3A:** Identifies the minimum transit travel times for each od city pair and time period, 
               and for the same od pair and time period, the auto travel time.
  **Goal 3D:** Calculate the maximum transit travel time ratio (AM Peak/Midday) for each od city pair.
  Inputs: database/TimeSkimsDatabase[AM,MD].csv (OD travel time data for AM Peak,Midday)

  **Goal 3B:** Calculate the average transit-to-auto travel time ratio for AM Peak periods using weighted 
               averages for each od city pair.
  **Goal 3C:** Calculate the average transit-to-auto travel time ratio for Midday periods using weighted
               averages for each od city pair.
  Inputs: core_summaries/ODTravelTime_byModeTimeperiodIncome.csv (trip summaries for origins/destinations)
    
These are written to metrics/NPA_metrics_Goal_3A_to_3D.csv

calculate_brt_service_miles()
   **Goal 3E:** Percent of total surface transit service miles on roads with transit priority treatments (BRT)
   Inputs: trn/trn[link,line].csv (transit link and line data)
           hwy/avgload5period_vehclasses.csv (loaded roadway network data including brt attribute for roaday links)

    This joins loaded transit output with roadway links (for transit that travels on roadway links) to assess
    what share of the service miles are on roadway links with transit priority (brt > 0).

calculate_crowded_passenger_hours()
   **Goal 3F:** Percent of person-hours in transit spent in crowded conditions
   - Inputs: metrics/transit_crowding_complete.csv (transit crowding data)
   
   This just summarizes transit passenger hours by mode based on if the transit vehicle is crowded or not.

These are written to metrics/NPA_metrics_Goal_3E_3F.csv

"""

import os
import pathlib
import pandas as pd
import geopandas
import numpy as np
import logging
import copy

# Mode definitions
MODES_TRANSIT = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
MODES_TRANSIT_WALK = [9, 10, 11, 12, 13]
MODES_TRANSIT_DRIVE = [14, 15, 16, 17, 18]
MODES_TAXI_TNC = [19, 20, 21]
MODES_SOV = [1, 2]
MODES_HOV = [3, 4, 5, 6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV
# the following is mainly for debugging
MODES_BUS = [9, 11, 14, 16]
MODES_FERRY_LIGHT_RAIL = [10, 15]
MODES_COMMUTER_RAIL = [13, 18] # commuter rail modes
MODES_HEAVY_RAIL = [12, 17] # heavy rail mod


EFFECTIVE_TRANSIT_SERVICE_HOURS = {'ea': 3, 'am': 4, 'md': 5, 'pm': 4, 'ev': 8} # based on the effective service hours of the transit system

TIMEPERIOD_LABELS = ['AM Peak','Midday']

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

# Weighted average helper
def weighted_average_travel_time(df, modes):
    """
    Calculates weighted travel time of trips with trip_mode given by list modes
    from a datafram with columns: trip_mode, avg_travel_time_in_mins, num_trips.

    Returns None if no trips, otherwise the avg_travel_time_in_mins weighted by num_trips
    """
    subset = df[df.trip_mode.isin(modes)]
    if subset.num_trips.sum() == 0:
        return None
    return (subset.avg_travel_time_in_mins * subset.num_trips).sum()/subset.num_trips.sum()

# number of trips helper
def number_of_trips(df, modes):
    """
    Calculates number of trips with trip_mode given by list modes
    from a datafram with columns: trip_mode, avg_travel_time_in_mins, num_trips.

    Returns None if no trips, otherwise the avg_travel_time_in_mins weighted by num_trips
    """
    subset = df[df.trip_mode.isin(modes)]
    if subset.num_trips.sum() == 0:
        return None
    return subset.num_trips.sum()

# min/max travel time helper
def min_max_travel_time(df, modes):
    """
    Calculates min / max of TAZ-level avg travel time with trip_mode given by list modes
    from a datafram with columns: trip_mode, avg_travel_time_in_mins, num_trips.

    Returns None if no trips, otherwise the avg_travel_time_in_mins weighted by num_trips
    """
    subset = df[df.trip_mode.isin(modes)]
    if subset.num_trips.sum() == 0:
        return None
    
    min_max_avg_travel_time_metrics = {}
 
    ixmin = subset['avg_travel_time_in_mins'].idxmin()
    ixmax = subset['avg_travel_time_in_mins'].idxmax()

    min_max_avg_travel_time_metrics['min_time_orig_taz'] = subset.loc[ixmin]['orig_taz']
    min_max_avg_travel_time_metrics['min_time_dest_taz'] = subset.loc[ixmin]['dest_taz']
    min_max_avg_travel_time_metrics['min_avg_time'] = subset.loc[ixmin]['avg_travel_time_in_mins']

    min_max_avg_travel_time_metrics['max_time_orig_taz'] = subset.loc[ixmax]['orig_taz']
    min_max_avg_travel_time_metrics['max_time_dest_taz'] = subset.loc[ixmax]['dest_taz']
    min_max_avg_travel_time_metrics['max_avg_time'] = subset.loc[ixmax]['avg_travel_time_in_mins']

    return min_max_avg_travel_time_metrics

def calculate_and_write_travel_time_metrics(logger, MODEL_DIR):
    """
    Calculatees and writes the following metrics:
    3A) Best AM peak and midday auto and transit travel times selected origin-destination pairs
    3B) Transit to auto AM peak period travel time ratio
    3C) Transit to auto midday travel time ratio
    3D) midday / AM peak transit travel time ratio for OD with best midday and best AM transit travel time

    The result is written to metrics/NPA_metrics_Goal_3A_to_3D.csv
    """
    # Load TAZ→city mapping - this will be copied to the INPUT/metrics folder
    taz_city_file = MODEL_DIR / "INPUT" / "metrics" / "TAZ1454_city.csv"
    logger.info(f"Loading TAZ-to-city mapping from {taz_city_file}")
    od_cities_map = pd.read_csv(taz_city_file, usecols=['TAZ1454','city']).set_index('TAZ1454')['city']
    logger.info(f"\n{od_cities_map.head()}")

    # --------------------------
    # 3A & 3D: Best Transit Travel Time and Ratio Processing
    # --------------------------

    # Load and merge AM/Midday skims
    logger.info("Loading AM and Midday skims")
    skim_paths = {
        'am_peak': MODEL_DIR/"database"/"TimeSkimsDatabaseAM.csv",
        'midday': MODEL_DIR/"database"/"TimeSkimsDatabaseMD.csv"
    }
    skim = {tp: pd.read_csv(fp, usecols=['orig','dest','da','wTrnW']) 
            for tp, fp in skim_paths.items()}
    skim_merge = skim['am_peak'].merge(skim['midday'], on=['orig','dest'], suffixes=('_am_peak','_midday')).rename(columns={'orig':'orig_taz','dest':'dest_taz'})
    skim_merge['orig_CITY'] = skim_merge.orig_taz.map(od_cities_map)
    skim_merge['dest_CITY'] = skim_merge.dest_taz.map(od_cities_map)
    valid = (skim_merge[['wTrnW_am_peak','wTrnW_midday']] != -999).all(axis=1)
    skim_merge['wTrnW_ratio'] = (skim_merge.wTrnW_midday / skim_merge.wTrnW_am_peak).where(valid)
    logger.info(f"skim_merge:\n{skim_merge}")

    # Compute best travel times (3A) and best ratio (3D)
    metrics_odper_key = {} # key: [od_key, period]
    for od_key, origins, dests in OD_PAIRS:
        selected_od = skim_merge[skim_merge.orig_CITY.isin(origins) & skim_merge.dest_CITY.isin(dests)]
        logger.info(f"Processing {od_key} with origins={origins} and dests={dests}")
        logger.info(f"selected_od:\n{selected_od}")
        
        for period in ['am_peak','midday']:
            metrics = {}
            metrics['origin_city'] = ','.join(origins)
            metrics['destination_city'] = ','.join(dests)
            metrics['period'] = period
        
            trn_col = f"wTrnW_{period}"
            da_col = f"da_{period}"

            # select row with lowest walk-transit-walk time
            ix = selected_od.loc[selected_od[trn_col] != -999, trn_col].idxmin()
            logger.info(f"{period} transit time idxmin() ix:{ix}; selected_od.loc[{ix}]:\n{selected_od.loc[ix]}")

            # retain these
            metrics["orig_taz"] = selected_od.loc[ix]['orig_taz']
            metrics["dest_taz"] = selected_od.loc[ix]['dest_taz']

            metrics["best_transit_travel_time"] = selected_od.loc[ix][trn_col]
            # note: this is the auto travel time for the same OD taz as best_transit_travel_time_
            metrics["auto_travel_time"] = selected_od.loc[ix][da_col]

            # note the ratio_midday_over_am for this TAZ / period as well
            metrics["transit_ratio_midday_over_am"] = selected_od.loc[ix]["wTrnW_ratio"]

            metrics_odper_key[(od_key,period)] = metrics

    logger.info(f"{metrics_odper_key=}")
    # --------------------------
    # 3B & 3C: Average Travel Time Ratio Processing
    # --------------------------
    metrics_odper_debug_key = copy.deepcopy(metrics_odper_key) # key: [od_key, period]
    logger.info(f"{metrics_odper_debug_key=}")
    logger.info("Loading avg OD trips & travel time data")
    od_tt_avg = pd.read_csv(MODEL_DIR/"core_summaries"/"ODTravelTime_byModeTimeperiodIncome.csv")
    od_tt_avg = od_tt_avg[od_tt_avg.avg_travel_time_in_mins > 0]
    od_tt_avg['orig_CITY'] = od_tt_avg.orig_taz.map(od_cities_map)
    od_tt_avg['dest_CITY'] = od_tt_avg.dest_taz.map(od_cities_map)
    logger.info(f"od_tt_avg:\n{od_tt_avg}")

    for od_key, origins, dests in OD_PAIRS:
        for timeperiod in TIMEPERIOD_LABELS:
            period = timeperiod.lower().replace(" ","_")
            # select the trips/travel time for the given time period and origin/destination city pair
            logger.info(f"Processing {od_key} in {timeperiod}")
            selected_od = od_tt_avg.loc[(od_tt_avg.timeperiod_label==timeperiod) & 
                                         od_tt_avg.orig_CITY.isin(origins) & 
                                         od_tt_avg.dest_CITY.isin(dests)]
            logger.info(f"selected_od has {len(selected_od)} rows:\n{selected_od}")

            metrics_odper_key[(od_key,period)]["weighted_avg_transit_travel_time"] = \
                weighted_average_travel_time(selected_od, MODES_TRANSIT)
            metrics_odper_key[(od_key,period)]["weighted_avg_auto_travel_time"] = \
                weighted_average_travel_time(selected_od, MODES_PRIVATE_AUTO + MODES_TAXI_TNC)

            # transit / auto
            metrics_odper_key[(od_key,period)]["weighted_avg_transit_over_auto_travel_time"] = \
                metrics_odper_key[(od_key,period)]["weighted_avg_transit_travel_time"] / \
                metrics_odper_key[(od_key,period)]["weighted_avg_auto_travel_time"]
            
            # debug: calculate number of trips by mode group, and best/worse transit travel time
            metrics_odper_debug_key[(od_key,period)]["weighted_avg_transit_travel_time"] = \
                weighted_average_travel_time(selected_od, MODES_TRANSIT)
            metrics_odper_debug_key[(od_key,period)]["num_trips_TRANSIT"] = \
                number_of_trips(selected_od, MODES_TRANSIT)            
            metrics_odper_debug_key[(od_key,period)]["num_trips_BUS"] = \
                number_of_trips(selected_od, MODES_BUS)            
            metrics_odper_debug_key[(od_key,period)]["num_trips_FERRY_LIGHTRAIL"] = \
                number_of_trips(selected_od, MODES_FERRY_LIGHT_RAIL)
            metrics_odper_debug_key[(od_key,period)]["num_trips_COMMUTER_RAIL"] = \
                number_of_trips(selected_od, MODES_COMMUTER_RAIL)
            metrics_odper_debug_key[(od_key,period)]["num_trips_HEAVY_RAIL"] = \
                number_of_trips(selected_od, MODES_HEAVY_RAIL)
            metrics_odper_debug_key[(od_key,period)]["weighted_avg_auto_travel_time"] = \
                weighted_average_travel_time(selected_od, MODES_PRIVATE_AUTO + MODES_TAXI_TNC)
            metrics_odper_debug_key[(od_key,period)]["num_trips_AUTO"] = \
                number_of_trips(selected_od, MODES_PRIVATE_AUTO + MODES_TAXI_TNC)

            min_max_average_transit_travel_time = min_max_travel_time(selected_od, MODES_TRANSIT)
            for key, value in min_max_average_transit_travel_time.items():
                metrics_odper_debug_key[(od_key,period)][f"{key}_TRANSIT"] = value

    metrics_dict_list = [metrics_odper_key[(od_key,period)] for od_key,period in metrics_odper_key.keys()]
    metrics_df = pd.DataFrame(metrics_dict_list)
    logger.info(f"metrics_df:\n{metrics_df}")
    # write it out
    output_file = MODEL_DIR / "metrics" / "NPA_metrics_Goal_3A_to_3D.csv"
    metrics_df.to_csv(output_file, index=False)
    logger.info(f"Wrote {len(metrics_df)} rows to {output_file}")

    # modify and write out debugging data
    metrics_debug_dict_list = [metrics_odper_debug_key[(od_key,period)] for od_key,period in metrics_odper_debug_key.keys()]
    metrics_debug_df = pd.DataFrame(metrics_debug_dict_list)
    metrics_debug_df.drop(columns=['orig_taz', 'dest_taz', 'best_transit_travel_time', 'auto_travel_time', 'transit_ratio_midday_over_am'], inplace=True)  # drop TAZ columns
    logger.info(f"metrics_df:\n{metrics_debug_df}")

    # write it out
    output_file = MODEL_DIR / "metrics" / "NPA_metrics_Goal_3A_to_3D_debug.csv"
    metrics_debug_df.to_csv(output_file, index=False)
    logger.info(f"Wrote {len(metrics_debug_df)} rows to {output_file}")

def calculate_brt_service_miles(logger, MODEL_DIR):
    """
    Calculates service miles, BRT and non-BRT, by mode and overall.
    returns DataFrame with columns:
    * mode
    * transit_service_miles
    * transit_service_miles_brt
    * transit_service_miles_brt_pct
    """
    logger.info("Starting Transit Service Miles (Goal 3E)")

    # Load and filter transit link/line data
    link = pd.read_csv(MODEL_DIR/"trn"/"trnlink.csv")
    line = pd.read_csv(MODEL_DIR/"trn"/"trnline.csv")
    logger.info(f"Read trnlink from trnlink.csv:\n{link}")
    logger.info(f"Read trnline from trnline.csv:\n{line}")

    # https://github.com/BayAreaMetro/modeling-website/wiki/TransitModes
    # filter out support acess/egress/transfer links
    link = link.loc[ link['mode'] >= 10]
    line = line.loc[ line['mode'] >= 10]
    logger.info(f"Filtered to {len(link):,} links and {len(line):,} lines after dropping support mode")

    # filter out ferry links
    FERRY_MODES = list(range(100, 108))
    link = link.loc[ ~link['mode'].isin(FERRY_MODES)]
    line = line.loc[ ~line['mode'].isin(FERRY_MODES)]
    logger.info(f"Filtered to {len(link):,} links and {len(line):,} lines after dropping FERRY mode")

    # link columns: A, B, time, mode, plot, stopA, stopB, distance, name, owner, AB_VOL, AB_BRDA, AB_XITA, AB_BRDB, AB_XITB, BA_VOL  BA_BRDA, BA_XITA, BA_BRDB, BA_XITB, prn, timeperiod, source, short_source
    link = link[['A','B','name','mode','timeperiod','distance','AB_VOL']]
    link.drop_duplicates(inplace=True)
    logger.info(f"links:\n{link}")

    # line columns: name, mode, owner, frequency, line time, limne dist, total boardings, passenger miles, passenger hours, path id (e.g. am_wlk_loc_wlk)
    # select to just supply
    line['timeperiod'] = line['path id'].str[:2]
    line = line[['name','mode','timeperiod','frequency']].drop_duplicates()
    logger.info(f"lines:\n{line}")

    # Merge and compute service miles
    trn_data = pd.merge(
        left=link,
        right=line,
        on=['name','mode','timeperiod'],
        validate='many_to_one'
    )
    trn_data['timeperiod_interval'] = trn_data.timeperiod.map(EFFECTIVE_TRANSIT_SERVICE_HOURS)
    # transit runs per period = hours * 60 / frequency
    trn_data['service_miles'] = (trn_data.timeperiod_interval * 60.0 / trn_data.frequency) * trn_data.distance

    logger.info(f'trn_data:\n{trn_data}')
    logger.info(f'\n{trn_data.describe()}')
    # columns: A, B, name, mode, timeperiod, distance, AB_VOL, timeperiod_interval, frequency, service_miles

    #### Read shapefiles for the shape for A, B
    trn_links_gdf = geopandas.read_file(MODEL_DIR / "shapefile" / "network_trn_links.shp", columns=['A','B','MODE','geometry'])
    logger.info("Read network_trn_links.shp")
    trn_links_gdf = trn_links_gdf.loc[trn_links_gdf.MODE >= 10]  # filter out support modes
    trn_links_gdf.rename(columns={'MODE':'mode'}, inplace=True)
    trn_links_gdf.drop_duplicates(inplace=True)
    logger.info(f"trn_links_gdf:\n{trn_links_gdf}")
    logger.info(f'\n{trn_links_gdf.describe()}')

    COUNTIES_SHAPEFILE = pathlib.Path("M:\\Data\\GIS layers\\Counties\\bay_counties.shp")
    counties_gdf = geopandas.read_file(COUNTIES_SHAPEFILE, columns=['NAME','geometry'])
    counties_gdf.rename(columns={'NAME':'county_name'}, inplace=True)
    logger.info(f"counties_gdf:\n{counties_gdf}")

    # Ensure same CRS
    counties_gdf = counties_gdf.to_crs(trn_links_gdf.crs)
    trn_links_counties_gdf = geopandas.overlay(trn_links_gdf, counties_gdf, how='intersection')
    # Calculate segment length (in CRS units, e.g., meters if projected)
    trn_links_counties_gdf['segment_length'] = trn_links_counties_gdf.geometry.length

    # For each original link, find the polygon with the longest segment
    idx = trn_links_counties_gdf.groupby(['A','B'])['segment_length'].idxmax()
    longest_segments = trn_links_counties_gdf.loc[idx]
    # Merge 'county_name' back to trn_links_gdf
    trn_links_gdf = trn_links_gdf.merge(
        longest_segments[['A', 'B', 'county_name']],
        on=['A', 'B'],
        how='left'
    )
    logger.info(f"trn_links_gdf with county_name:\n{trn_links_gdf}")
    # merge county name back into trn_data
    trn_data = pd.merge(
        left=trn_data,
        right=trn_links_gdf[['A', 'B', 'mode','county_name']],
        how='left',
        validate='many_to_one',
    )
    logger.info(f'trn_data:\n{trn_data}')
    logger.info(f'\n{trn_data.describe()}')

    # Load roadway network BRT treatment and HOV data
    loaded_roadway_file = MODEL_DIR/"hwy"/"iter3"/"avgload5period_vehclasses.csv"
    loaded_roadway = pd.read_csv(loaded_roadway_file)
    loaded_roadway = loaded_roadway[['a','b','ft','lanes','brt', 'useEA','useAM', 'useMD', 'usePM', 'useEV']]
    logger.info(f"Read loaded_roadway_file:{loaded_roadway_file}; dataframe=\n{loaded_roadway}")

    # Calculate totals and mode‐level BRT share
    trn_data = pd.merge(
        left=trn_data,
        right=loaded_roadway,
        how='left',
        left_on=['A','B'],
        right_on=['a','b'],
        validate='many_to_one'
    )
    logger.info(f"trn_data:\n{trn_data}")
    # sanity check - join failures should be non-bus
    pd.set_option('display.max_rows', None)
    logger.info(f"value_counts:\n{trn_data[['mode','brt']].value_counts(dropna=False)}")
    pd.set_option('display.max_rows', 20)

    # make brt always a number
    trn_data.fillna({'brt':0}, inplace=True)
    trn_data['is_brt'] = trn_data['brt'] > 0

    # Determine use based on time period (useEA, useAM, useMD, usePM, useEV)
    def useType(row):
        if row['timeperiod'] == 'ea':
            return row['useEA']
        elif row['timeperiod'] == 'am':
            return row['useAM']
        elif row['timeperiod'] == 'md':
            return row['useMD']
        elif row['timeperiod'] == 'pm':
            return row['usePM']
        elif row['timeperiod'] == 'ev':
            return row['useEV']
        else:
            return 0

    trn_data['use'] = trn_data.apply(lambda x: useType(x), axis=1)
    # make use always a number
    trn_data.fillna({'use':0}, inplace=True)
    trn_data['is_hov'] = trn_data['use'] > 1
    

    metrics_dict_list = []
    # by mode or county
    for groupby_col in ['mode','county_name']:
        trn_data_grouped     = trn_data.groupby([groupby_col        ]).agg({'service_miles':'sum'})
        trn_data_grouped_brt = trn_data.groupby([groupby_col,'is_brt']).agg({'service_miles':'sum'})
        trn_data_grouped_hov = trn_data.groupby([groupby_col, 'is_hov']).agg({'service_miles':'sum'})
        trn_data_grouped_brt_hov = trn_data.groupby([groupby_col,'is_brt', 'is_hov']).agg({'service_miles':'sum'})
        logger.info(f"trn_data_grouped:\n{trn_data_grouped}")
        logger.info(f"trn_data_grouped_brt:\n{trn_data_grouped_brt}")
        logger.info(f"trn_data_grouped_hov:\n{trn_data_grouped_hov}")
        logger.info(f"trn_data_grouped_brt_hov:\n{trn_data_grouped_brt_hov}")

        # for county-based metric, leave mode = None
        # for mode-based metric, leave county_name = None
        for grouped_val in trn_data_grouped.index.to_list():
            if groupby_col == "mode":
                metrics = {'mode':grouped_val}
            else:
                metrics = {'county_name':grouped_val}
            metrics['transit_service_miles']     = trn_data_grouped.loc[grouped_val]['service_miles']
            metrics['transit_service_miles_brt'] = 0
            metrics['transit_service_miles_hov'] = 0
            # Variable to count service miles that are both brt and hov
            metrics['transit_service_miles_brt_hov'] = 0
            if (grouped_val, True) in trn_data_grouped_brt.index:
                metrics['transit_service_miles_brt'] = trn_data_grouped_brt.loc[grouped_val,True]['service_miles']
            if (grouped_val, True) in trn_data_grouped_hov.index:
                metrics['transit_service_miles_hov'] = trn_data_grouped_hov.loc[grouped_val,True]['service_miles']
            if (grouped_val, True, True) in trn_data_grouped_brt_hov.index:
                metrics['transit_service_miles_brt_hov'] = trn_data_grouped_brt_hov.loc[grouped_val,True,True]['service_miles']


            metrics_dict_list.append(metrics)
    
    # all modes/counties: use mode=0
    metrics = {'mode':'0', 'county_name':'All Counties'}
    metrics['transit_service_miles'    ] = trn_data.service_miles.sum()
    metrics['transit_service_miles_brt'] = trn_data.loc[trn_data.is_brt, 'service_miles'].sum()
    metrics['transit_service_miles_hov'] = trn_data.loc[trn_data.is_hov, 'service_miles'].sum()
    metrics['transit_service_miles_brt_hov'] = trn_data.loc[trn_data.is_brt & trn_data.is_hov,'service_miles'].sum()
    metrics_dict_list.append(metrics)

    metrics_df = pd.DataFrame(metrics_dict_list)
    metrics_df['transit_service_miles_brt_pct'] = metrics_df.transit_service_miles_brt / metrics_df.transit_service_miles
    metrics_df['transit_service_miles_hov_pct'] = metrics_df.transit_service_miles_hov / metrics_df.transit_service_miles
    metrics_df['transit_service_miles_transit_priority_pct'] = (metrics_df.transit_service_miles_brt + metrics_df.transit_service_miles_hov - metrics_df.transit_service_miles_brt_hov) / metrics_df.transit_service_miles
    logger.info(f"metrics_df:\n{metrics_df}")
    return metrics_df

def calculate_crowded_passenger_hours(logger, MODEL_DIR):
    """
    Calculates 3F: transit passenger hours by crowded vs not crowded.
    Returns pandas.DataFrame with columns:
    * mode
    * passenger_hours
    * crowded_passenger_hours
    * ratio_crowded
    """
    # --------------------------
    # 3F: Transit Capacity and Crowding Analysis
    # --------------------------
    logger.info("Calculating transit capacity and crowding metrics")
    trn_crowding_df = pd.read_csv(
        MODEL_DIR / "metrics" / "transit_crowding_complete.csv",
        usecols=['A','B','MODE','period','run_per_hr','AB_VOL','ivtt_hours','load_standcap','period_standcap'] 
    )
    logger.info(f"trn_crowding_df:\n{trn_crowding_df}")

    # debug:
    logger.info(f"trn_crowding_df for mode=132:\n{trn_crowding_df.loc[trn_crowding_df.MODE==132]}")
    trn_crowding_df['passenger_hours'] = trn_crowding_df['AB_VOL'] * trn_crowding_df['ivtt_hours']

    trn_crowding_df['is_crowded'] = False
    # Consistent with utilities\RTP\metrics\travel_model_performance_equity_metrics.py::calculate_Connected2_crowding()
    trn_crowding_df.loc[ trn_crowding_df.load_standcap > 0.85, 'is_crowded'] = True
    logger.info(f"trn_crowding_df:\n{trn_crowding_df}")

    trn_crowding_by_mode_df       = trn_crowding_df.groupby(['MODE']).agg({'passenger_hours':'sum'})
    trn_crowding_by_mode_crowd_df = trn_crowding_df.groupby(['MODE','is_crowded']).agg({'passenger_hours':'sum'})
    logger.info(f"trn_crowding_by_mode_df:\n{trn_crowding_by_mode_df}")
    logger.info(f"trn_crowding_by_mode_crowd_df:\n{trn_crowding_by_mode_crowd_df}")

    metrics_dict_list = []
    for mode_num in trn_crowding_by_mode_df.index.to_list():
        metrics = {'mode':mode_num}
        metrics['passenger_hours']         = trn_crowding_by_mode_df.loc[mode_num]['passenger_hours']
        metrics['crowded_passenger_hours'] = 0
        if (mode_num, True) in trn_crowding_by_mode_crowd_df.index:
            metrics['crowded_passenger_hours'] = trn_crowding_by_mode_crowd_df.loc[mode_num,True]['passenger_hours']

        metrics_dict_list.append(metrics)
    
    # all modes: use mode=0
    metrics = {'mode':'0'}
    metrics['passenger_hours']         = trn_crowding_df.passenger_hours.sum()
    metrics['crowded_passenger_hours'] = trn_crowding_df.loc[trn_crowding_df.is_crowded, 'passenger_hours'].sum()
    metrics_dict_list.append(metrics)

    metrics_df = pd.DataFrame(metrics_dict_list)
    metrics_df['ratio_crowded'] = metrics_df.crowded_passenger_hours / metrics_df.passenger_hours
    metrics_df.fillna({'ratio_crowded':0}, inplace=True)
    logger.info(f"metrics_df:\n{metrics_df}")

    return metrics_df

if __name__ == '__main__':
    pd.set_option('display.width', 800)
    pd.set_option('display.max_columns', None)

    MODEL_DIR = pathlib.Path(".")

    # Set up logging
    log_file = MODEL_DIR / "metrics" / 'NPA_metrics_Goal_3.log'
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__file__)
    logger.info("Script execution started")
    logger.info(f"Working directory: {os.getcwd()}")

    calculate_and_write_travel_time_metrics(logger, MODEL_DIR)

    metrics_brt_df = calculate_brt_service_miles(logger, MODEL_DIR)

    metrics_crowding_df = calculate_crowded_passenger_hours(logger, MODEL_DIR)

    # these both have a mode column; join
    metrics_df = pd.merge(
        left=metrics_brt_df.loc[pd.notnull(metrics_brt_df['mode'])],
        right=metrics_crowding_df,
        on='mode',
        how='outer',
        validate='one_to_one'
    )
    # concatenate with county summaries of brt
    metrics_df = pd.concat([metrics_df, metrics_brt_df.loc[pd.isnull(metrics_brt_df['mode'])]], ignore_index=True)
    # write it out
    output_file = MODEL_DIR / "metrics" / "NPA_metrics_Goal_3E_3F.csv"
    metrics_df.to_csv(output_file, index=False)
    logger.info(f"Wrote {len(metrics_df)} rows to {output_file}")
