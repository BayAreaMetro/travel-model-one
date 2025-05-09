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
import re
import logging

# Mode definitions
MODES_TRANSIT = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
MODES_TRANSIT_WALK = [9, 10, 11, 12, 13]
MODES_TRANSIT_DRIVE = [14, 15, 16, 17, 18]
MODES_TAXI_TNC = [19, 20, 21]
MODES_SOV = [1, 2]
MODES_HOV = [3, 4, 5, 6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV

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

def calculate_and_write_travel_time_metrics(logger, MODEL_DIR):
    """
    Calculatees and writes the following metrics:
    3A) Best AM peak and midday auto and transit travel times selected origin-destination pairs
    3B) Transit to auto AM peak period travel time ratio
    3C) Transit to auto midday travel time ratio
    3D) Best AM peak-to-midday transit travel time ratio

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
    skim_merge['wTrnW_ratio'] = (skim_merge.wTrnW_am_peak / skim_merge.wTrnW_midday).where(valid)
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

            # select row with lowest walk-transit=walk time
            ix = selected_od.loc[selected_od[trn_col] != -999, trn_col].idxmin()
            logger.info(f"{period} transit time idxmin() ix:{ix}; selected_od.loc[{ix}]:\n{selected_od.loc[ix]}")

            metrics["best_transit_travel_time"] = selected_od.loc[ix][trn_col]
            # note: this is the auto travel time for the same OD taz as best_transit_travel_time_
            metrics["auto_travel_time"] = selected_od.loc[ix][da_col]

            metrics_odper_key[(od_key,period)] = metrics
        
        # this metric is not period-specific
        metrics_odper_key[(od_key,'both')] = {
            'period':'both',
            'origin_city':','.join(origins),
            'destination_city':','.join(dests),
            'best_transit_ratio_am_peak_midday':selected_od.wTrnW_ratio.max()
        }

    logger.info(f"{metrics_odper_key=}")
    # --------------------------
    # 3B & 3C: Average Travel Time Ratio Processing
    # --------------------------
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

    metrics_dict_list = [metrics_odper_key[(od_key,period)] for od_key,period in metrics_odper_key.keys()]
    metrics_df = pd.DataFrame(metrics_dict_list)
    logger.info(f"metrics_df:\n{metrics_df}")
    # write it out
    output_file = MODEL_DIR / "metrics" / "NPA_metrics_Goal_3A_to_3D.csv"
    metrics_df.to_csv(output_file, index=False)
    logger.info(f"Wrote {len(metrics_df)} rows to {output_file}")

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

    logger.info(f'trn_date:\n{trn_data}')

    # Load roadway network BRT treatment data
    loaded_roadway_file = MODEL_DIR/"hwy"/"iter3"/"avgload5period_vehclasses.csv"
    loaded_roadway = pd.read_csv(loaded_roadway_file)
    loaded_roadway = loaded_roadway[['a','b','ft','lanes','brt']]
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

    # by mode
    trn_data_by_mode     = trn_data.groupby(['mode'         ]).agg({'service_miles':'sum'})
    trn_data_by_mode_brt = trn_data.groupby(['mode','is_brt']).agg({'service_miles':'sum'})
    logger.info(f"trn_data_by_mode:\n{trn_data_by_mode}")
    logger.info(f"trn_data_by_mode_brt:\n{trn_data_by_mode_brt}")

    metrics_dict_list = []
    for mode_num in trn_data_by_mode.index.to_list():
        metrics = {'mode':mode_num}
        metrics['transit_service_miles']     = trn_data_by_mode.loc[mode_num]['service_miles']
        metrics['transit_service_miles_brt'] = 0
        if (mode_num, True) in trn_data_by_mode_brt.index:
            metrics['transit_service_miles_brt'] = trn_data_by_mode_brt.loc[mode_num,True]['service_miles']

        metrics_dict_list.append(metrics)
    
    # all modes: use mode=0
    metrics = {'mode':'0'}
    metrics['transit_service_miles'    ] = trn_data.service_miles.sum()
    metrics['transit_service_miles_brt'] = trn_data.loc[trn_data.is_brt, 'service_miles'].sum()
    metrics_dict_list.append(metrics)

    metrics_df = pd.DataFrame(metrics_dict_list)
    metrics_df['transit_service_miles_brt_pct'] = metrics_df.transit_service_miles_brt / metrics_df.transit_service_miles
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
        usecols=['A','B','MODE','period','run_per_hr','AB_VOL','ivtt_hours','period_seatcap','period_standcap'] 
    )
    logger.info(f"trn_crowding_df:\n{trn_crowding_df}")

    # debug:
    logger.info(f"trn_crowding_df for mode=132:\n{trn_crowding_df.loc[trn_crowding_df.MODE==132]}")
    trn_crowding_df['passenger_hours'] = trn_crowding_df['AB_VOL'] * trn_crowding_df['ivtt_hours']

    trn_crowding_df['is_crowded'] = False
    # TODO: I think this is incorrect; these shouldn't be added
    # TODO: This should just one or the other
    trn_crowding_df.loc[ trn_crowding_df.AB_VOL > 0.85*(trn_crowding_df.period_seatcap + trn_crowding_df.period_standcap), 'is_crowded'] = True
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
    pd.set_option('display.width', None)
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
        left=metrics_brt_df,
        right=metrics_crowding_df,
        on='mode',
        how='outer',
        validate='one_to_one'
    )
    # write it out
    output_file = MODEL_DIR / "metrics" / "NPA_metrics_Goal_3E_3F.csv"
    metrics_df.to_csv(output_file, index=False)
    logger.info(f"Wrote {len(metrics_df)} rows to {output_file}")
