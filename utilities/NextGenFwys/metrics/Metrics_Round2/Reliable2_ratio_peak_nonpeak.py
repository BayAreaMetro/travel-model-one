USAGE = """

  python Reliable2_ratio_peak_nonpeak.py

  Run this from the model run dir.
  Processes model outputs and creates csvs for the relevant metric for every relevant scenario, called metrics\Reliable2_ratio_peak_nonpeak_XX.csv
  
  Inputs:
    taz_with_cities.csv: Lookup table linking Traffic Analysis Zones (TAZ) to groups of named cities for geographic analysis.
    taz1454_epcPBA50plus_2024_02_23.csv: Lookup file indicating Equity Priority Communitiy (EPC) designation for TAZs, used for classification.
    TOLLCLASS_Designations.xlsx: Excel file defining toll class designations used for categorizing toll facilities.
    ODTravelTime_byModeTimeperiodIncome.csv: OD travel time summarized by mode, time period and income group
    goods_routes_a_b.csv: Lookup file indicating goods routes designation for Roadway network, used for classification.
    avgload5period_vehclasses.csv: Roadway network information containing attributes like facility type, volume, and toll class designations.

  This file will have the following columns:
    'metric_desc',
    'value',
    'intermediate/final',
    'Origin and Destination',
    'modelrun_id',
    'year',
    'metric_id',
    'Goods Routes Y/N',
    'Peak/Non',
    'N/A',
    'Route'
    
  Metrics are:
    1) Reliable 2: Travel time during peak hours vs. off-peak hours on freeways for people and goods

"""

import os
import numpy
import pandas as pd
import argparse
import logging

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Reliable2_ratio_peak_nonpeak.log" # in the cwd
LOGGER                  = None # will initialize in main

# maps TAZs to a few selected cities for Origin/Destination analysis
NGFS_OD_CITIES_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_with_cities.csv")
NGFS_OD_CITIES_DF      = pd.read_csv(NGFS_OD_CITIES_FILE)

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050+
NGFS_EPC_TAZ_FILE    = "M:\\Application\\Model One\\RTP2025\\INPUT_DEVELOPMENT\\metrics\\metrics_01\\taz1454_epcPBA50plus_2024_02_23.csv"
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

# tollclass designations
TOLLCLASS_LOOKUP_DF     = pd.read_excel(NGFS_TOLLCLASS_FILE, sheet_name='Inputs_for_tollcalib', usecols=['project','facility_name','tollclass','s2toll_mandatory','THRESHOLD_SPEED','MAX_TOLL','MIN_TOLL','Grouping major','Grouping minor'])

# define origin destination pairs
NGFS_OD_CITIES_OF_INTEREST = [
    ['Central/West Oakland',                           'San Francisco Downtown Area'],
    ['Vallejo',                                        'San Francisco Downtown Area'],
    ['Danville, San Ramon, Dublin, and Pleasanton',    'San Francisco Downtown Area'],
    ['Antioch',                                        'Central/West Oakland'],
    ['Central San Jose',                               'San Francisco Downtown Area'],
    ['Central/West Oakland',                           'Palo Alto'],
    ['Central/West Oakland',                           'Central San Jose'],
    ['Livermore',                                      'Central San Jose'],
    ['Fairfield and Vacaville',                        'Richmond'],
    ['Santa Rosa',                                     'San Francisco Downtown Area']
]
NGFS_OD_CITIES_OF_INTEREST_DF = pd.DataFrame(
    data=NGFS_OD_CITIES_OF_INTEREST,
    columns=['orig_CITY', 'dest_CITY']
)
# define origin destination pairs to use for Reliable, Pathway 3 Travel Time calculation
NGFS_OD_CORDONS_OF_INTEREST = [
    ['Richmond',   'San Francisco Cordon'],
    ['Mission/Bayview',   'San Francisco Cordon'],
    ['Sunset',   'San Francisco Cordon'],
    ['Daly City',   'San Francisco Cordon'],
    ['Oakland/Alameda',   'San Francisco Cordon'],
    ['Oakland/Alameda',   'Oakland Cordon'],
    ['Berkeley',   'Oakland Cordon'],
    ['Hayward',   'Oakland Cordon'],
    ['Downtown San Jose',   'San Jose Cordon'],
    ['East San Jose',   'San Jose Cordon'],
    ['South San Jose',   'San Jose Cordon'],
    ['Sunnyvale',   'San Jose Cordon'],
    ['Cupertino',   'San Jose Cordon'],
]
NGFS_OD_CORDONS_OF_INTEREST_DF = pd.DataFrame(
    data=NGFS_OD_CORDONS_OF_INTEREST,
    columns=['orig_ZONE', 'dest_CORDON']
)

# source: https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
INFLATION_FACTOR = 1.03
INFLATION_00_23 = (327.06 / 180.20) * INFLATION_FACTOR
INFLATION_00_20 = 300.08 / 180.20
INFLATION_00_18 = 285.55 / 180.20
INFLATION_18_20 = 300.08 / 285.55
REVENUE_DAYS_PER_YEAR = 260

# Average Annual Costs of Driving a Car in 2020$
# Source: AAA Driving Costs 2020; mid-size sedan
# \Box\NextGen Freeways Study\04 Engagement\02_Stakeholder Engagement\Advisory Group\Meeting 02 - Apr 2022 Existing Conditions\NGFS_Advisory Group Meeting 2_Apr2022.pptx
AUTO_OWNERSHIP_COST_2020D           = 3400
AUTO_MAINTENANCE_COST_2020D         = 1430 # use a model output instead
AUTO_INSURANCE_COST_2020D           = 1250
AUTO_FINANCE_COST_2020D             = 680
AUTO_REGISTRATION_TAXES_COST_2020D  = 730
AUTO_GAS_COST_2020D                 = 1250 # use a model output instead

# TODO: deprecate the use of these in Reliable (don't affect results, just need to clean up the code)
# sourced from USDOT Benefit-Cost Analysis Guidance  in 2020 dollars
# chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/https://www.transportation.gov/sites/dot.gov/files/2022-03/Benefit%20Cost%20Analysis%20Guidance%202022%20Update%20%28Final%29.pdf
# inflation adjustment CPI 2020, 2000 reference https://github.com/BayAreaMetro/modeling-website/wiki/InflationAssumptions
VOT_2023D_PERSONAL             = 17.8 / INFLATION_00_20 * INFLATION_00_23  # based on "All Purposes" in Table A-3
VOT_2023D_COMMERCIAL           = 32.0 / INFLATION_00_20 * INFLATION_00_23  # based on Commercial Vehicle Operators - Truck Drivers

A2_CONSTANTS = """

 - Avg hourly wage ($/hr)
    - source: ACS PUMS 2021, see M:\Data\Requests\Anup Tapase\ACS PUMS 2021 Mean Wage by Quartile.csv
 - Monetary Value of travel time (% of wage rate)
    - source: Table 5.2.11-1 https://www.vtpi.org/tca/tca0502.pdf
    - source: Table 1 (Revision - 2016 Update) https://www.transportation.gov/sites/dot.gov/files/docs/2016%20Revised%20Value%20of%20Travel%20Time%20Guidance.pdf
 - Monetary Value of travel time ($/hr)

"""

# for households and commercial
# updated 6/19/2023: https://app.asana.com/0/0/1204482774098821/1204820567114779/f
Q1_MEDIAN_HOURLY_WAGE_2023D = 15.33286
Q2_MEDIAN_HOURLY_WAGE_2023D = 30.05282
Q3_MEDIAN_HOURLY_WAGE_2023D = 53.90458
Q4_MEDIAN_HOURLY_WAGE_2023D = 114.96050

# BLS wage rates for the following categories
# source: https://www.bls.gov/oes/current/oes_41860.htm
HEAVY_TRUCK_OPERATORS_MEAN_HOURLY_WAGE_2023D = 30.83 * INFLATION_FACTOR
SALES_WORKERS_MEAN_HOURLY_WAGE_2023D = 35.04 * INFLATION_FACTOR
CONSTRUCTION_WORKERS_MEAN_HOURLY_WAGE_2023D = 39.35 * INFLATION_FACTOR

Q1_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D = .5
Q2_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D = .5
Q3_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D = .5
Q4_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D = .5
# USDOT calculates value of travel time savings for commercial/business vehicles by expanding  the wage rate to total compensation using a factor of 1.54 (deduced from page 15 and 16)
# https://www.transportation.gov/sites/dot.gov/files/docs/2016%20Revised%20Value%20of%20Travel%20Time%20Guidance.pdf
# for simplicity the compensation factor is included below along with the Recommended Values of Travel Time Savings (per person-hour as a percentage of total earnings) 
HEAVY_TRUCK_OPERATORS_VOT_PCT_HOURLY_WAGE_2023D = 1 * 1.54
SALES_WORKERS_VOT_PCT_HOURLY_WAGE_2023D = 1 * 1.54
CONSTRUCTION_WORKERS_VOT_PCT_HOURLY_WAGE_2023D = 1 * 1.54

Q1_HOUSEHOLD_VOT_2023D = Q1_MEDIAN_HOURLY_WAGE_2023D * Q1_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
Q2_HOUSEHOLD_VOT_2023D = Q2_MEDIAN_HOURLY_WAGE_2023D * Q2_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
Q3_HOUSEHOLD_VOT_2023D = Q3_MEDIAN_HOURLY_WAGE_2023D * Q3_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
Q4_HOUSEHOLD_VOT_2023D = Q4_MEDIAN_HOURLY_WAGE_2023D * Q4_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
HEAVY_TRUCK_OPERATORS_VOT_2023D = HEAVY_TRUCK_OPERATORS_MEAN_HOURLY_WAGE_2023D * HEAVY_TRUCK_OPERATORS_VOT_PCT_HOURLY_WAGE_2023D
SALES_WORKERS_VOT_2023D = SALES_WORKERS_MEAN_HOURLY_WAGE_2023D * SALES_WORKERS_VOT_PCT_HOURLY_WAGE_2023D
CONSTRUCTION_WORKERS_VOT_2023D = CONSTRUCTION_WORKERS_MEAN_HOURLY_WAGE_2023D * CONSTRUCTION_WORKERS_VOT_PCT_HOURLY_WAGE_2023D

BASE_YEAR       = "2015"
FORECAST_YEAR   = "2035"

# travel model tour and trip modes
# https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes
MODES_TRANSIT      = [9,10,11,12,13,14,15,16,17,18]
MODES_TAXI_TNC     = [19,20,21]
MODES_SOV          = [1,2]
MODES_HOV          = [3,4,5,6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV
MODES_WALK         = [7]
MODES_BIKE         = [8]

# travel model time periods
# https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
TIME_PERIODS_PEAK    = ['AM','PM']
TIME_PERIOD_LABELS_PEAK    = ['AM Peak','PM Peak']
TIME_PERIOD_LABELS_NONPEAK = ['Midday']
METRICS_COLUMNS = [
    'Goods Routes Y/N',
    'Peak/Non',
    'N/A',
    'modelrun_id',
    'metric_id',
    'intermediate/final', # TODO: suggest renaming this to 'metric_level' since other options are used beyond intermediate and final
    'Route',
    'metric_desc',
    'year',
    'value'
]

def R2_aggregate_before_joining(tm_run_id):
    """

    have to aggregate before joining.  
    e.g. simplify the trip mode, aggregate all income quartiles, and then join — so we won't lose trips
    see asana task: https://app.asana.com/0/0/1204811778297277/f 
    
    """
    LOGGER.info("Reliable 2: Aggregating before joining for {}".format(tm_run_id)) 

    # columns: orig_taz, dest_taz, trip_mode, timeperiod_label, incQ, incQ_label, num_trips, avg_travel_time_in_mins
    ODTravelTime_byModeTimeperiod_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "ODTravelTime_byModeTimeperiodIncome.csv")
    # this is large so join/subset it immediately
    trips_od_travel_time_df = pd.read_csv(ODTravelTime_byModeTimeperiod_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(trips_od_travel_time_df), ODTravelTime_byModeTimeperiod_file))

    # filter for only driving modes
    # we're going to aggregate trip modes; auto includes TAXI and TNC
    trips_od_travel_time_df['agg_trip_mode'] = "N/A"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_PRIVATE_AUTO), 'agg_trip_mode' ] = "auto"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_TAXI_TNC),     'agg_trip_mode' ] = "auto"
    trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df.agg_trip_mode == 'auto' ]
    LOGGER.info("  Filtered to auto only: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot out the income and mode since we don't need it
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df,
                                             index=['orig_taz','dest_taz','timeperiod_label'],
                                             values=['num_trips','avg_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'avg_travel_time_in_mins':numpy.mean})
    trips_od_travel_time_df.reset_index(inplace=True)
    LOGGER.info("  Aggregated income groups and modes: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # we're going to aggregate trip time periods; auto includes TAXI and TNC
    trips_od_travel_time_df['agg_timeperiod_label'] = "N/A"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.timeperiod_label.isin(TIME_PERIOD_LABELS_PEAK),      'agg_timeperiod_label' ] = "peak"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.timeperiod_label.isin(TIME_PERIOD_LABELS_NONPEAK), 'agg_timeperiod_label' ] = "nonpeak"
    LOGGER.info("   Aggregated trip time periods: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot down to orig_taz x dest_taz x agg_timeperiod_label
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_taz','dest_taz','agg_timeperiod_label'],
                                             values=['num_trips','avg_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'avg_travel_time_in_mins':numpy.mean})
    trips_od_travel_time_df.reset_index(inplace=True)

    return trips_od_travel_time_df

def calculate_Reliable2_ratio_peak_nonpeak(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Reliable 2: Ratio of travel time during peak hours vs. non-peak hours between representative origin-destination pairs 
    
    Args:
        tm_run_id (str): Travel model run ID

    Returns:
        pandas.DataFrame: with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Reliable 2'
          modelrun_id = tm_run_id
        Metrics returned:
          key                       intermediate/final  metric_desc
          [origCITY_destCITY]       extra               avg_travel_time_in_mins_peak
          [origCITY_destCITY]       extra               avg_travel_time_in_mins_nonpeak
          [origCITY_destCITY]       extra               num_trips_peak
          [origCITY_destCITY]       extra               num_trips_nonpeak
          [origCITY_destCITY]       intermediate        ratio_travel_time_peak_nonpeak
          Average across OD pairs   final               ratio_travel_time_peak_nonpeak_across_pairs

    Notes:
    * Representative origin-destination pairs are given by TAZs corresponding with 
      NGFS_OD_CITIES_FILE and NGFS_OD_CITIES_OF_INTEREST
    * peak time includes AM and PM
    * Final calculation is the average of these ratios (not weighted) across all OD pairs,
      excluding those which have no trips and therefore lack a travel time
    
      TODO: Does this make sense?  If a market is very small, should it be considered equally
    """
    metric_id = 'Reliable 2'
    # metric dict input: year
    year = tm_run_id[:4]
    grouping1 = ' '
    grouping2 = ' '
    grouping3 = ' '
    LOGGER.info("Calculating {} for {}".format(metric_id, tm_run_id))

    trips_od_travel_time_df = R2_aggregate_before_joining(tm_run_id)
    # remove 'num_trips' column to use from base run instead
    trips_od_travel_time_df = trips_od_travel_time_df.drop('num_trips', axis = 1)
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # read a copy of the table for the base comparison run to pull the number of trips (for weighting)
    trips_od_travel_time_df_base = R2_aggregate_before_joining(BASE_SCENARIO_RUN_ID) 
    LOGGER.debug("trips_od_travel_time_df_base: \n{}".format(trips_od_travel_time_df_base))
    # reduce copied df to only relevant columns orig, dest, and num_trips
    # pivot down to orig_taz x dest_taz x agg_timeperiod_label
    # purpose is to use same number-of-trip weights by TAZ-TAZ pairs, for both peak and off-peak (and consistent across pathways)
    # https://app.asana.com/0/0/1204844161312298/1204858353452819/f
    trips_od_travel_time_df_base = pd.pivot_table(trips_od_travel_time_df_base, 
                                             index=['orig_taz','dest_taz'],
                                             values=['num_trips'],
                                             aggfunc={'num_trips':numpy.sum})
    trips_od_travel_time_df_base.reset_index(inplace=True)
    LOGGER.debug("pivot down trips_od_travel_time_df_base to only relevant columns orig, dest, and num_trips: \n{}".format(trips_od_travel_time_df_base))

    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=trips_od_travel_time_df_base, 
                                       how='left', 
                                       left_on=['orig_taz','dest_taz'], 
                                       right_on=['orig_taz','dest_taz'])
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # join to OD cities for origin
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_CITIES_DF,
                                       left_on="orig_taz",
                                       right_on="taz1454")
    trips_od_travel_time_df.rename(columns={"CITY":"orig_CITY"}, inplace=True)
    trips_od_travel_time_df.drop(columns=["taz1454"], inplace=True)
    # join to OD cities for destination
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_CITIES_DF,
                                       left_on="dest_taz",
                                       right_on="taz1454")
    trips_od_travel_time_df.rename(columns={"CITY":"dest_CITY"}, inplace=True)
    trips_od_travel_time_df.drop(columns=["taz1454"], inplace=True)
    LOGGER.info("  Joined with {} for origin, destination: {:,} rows".format(NGFS_OD_CITIES_FILE, len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # trips_od_travel_time_df.to_csv(os.path.join(os.getcwd(),"trips_od_travel_time_df({}).csv".format(tm_run_id)), float_format='%.5f', index=False)

    # filter again to only those of interest
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_CITIES_OF_INTEREST_DF,
                                       indicator=True)
    trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df._merge == 'both']
    LOGGER.info("  Filtered to only NGFS_OD_CITIES_OF_INTEREST: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # to get weighted average, transform to total travel time
    trips_od_travel_time_df['tot_travel_time_in_mins'] = \
        trips_od_travel_time_df['avg_travel_time_in_mins']*trips_od_travel_time_df['num_trips']

    # pivot down to orig_CITY x dest_CITY x agg_timeperiod_label
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_CITY','dest_CITY','agg_timeperiod_label'],
                                             values=['num_trips','tot_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'tot_travel_time_in_mins':numpy.sum})
    trips_od_travel_time_df.reset_index(inplace=True)
    trips_od_travel_time_df['avg_travel_time_in_mins'] = \
        trips_od_travel_time_df['tot_travel_time_in_mins']/trips_od_travel_time_df['num_trips']
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot again to move agg_timeperiod to column
    # columns will now be: orig_CITY_, dest_CITY_, avg_travel_time_in_mins_peak, avg_travel_time_in_mins_nonpeak, num_trips_peak, num_trips_nonpeak
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_CITY','dest_CITY'],
                                             columns=['agg_timeperiod_label'],
                                             values=['num_trips','avg_travel_time_in_mins'])
    trips_od_travel_time_df.reset_index(inplace=True)
    # flatten resulting MultiIndex column names
    # rename from ('orig_CITY',''), ('dest_CITY',''), ('avg_travel_time_in_mins','peak'), ('avg_travel_time_in_mins', 'nonpeak'), ...
    # to orig_CITY, dest_CITY, avg_travel_time_in_mins_peak, avg_travel_time_in_mins_nonpeak, ...
    trips_od_travel_time_df.columns = ['_'.join(col) if len(col[1]) > 0 else col[0] for col in trips_od_travel_time_df.columns.values]
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # add ratio
    trips_od_travel_time_df['ratio_travel_time_peak_nonpeak'] = \
        trips_od_travel_time_df['avg_travel_time_in_mins_peak']/trips_od_travel_time_df['avg_travel_time_in_mins_nonpeak']
    
    # note that this does not include NaNs in either the numerator or the denominator, which I think is correct
    # TODO: in the previous implementation, NaN is converted to zero, which artificially lowers the average.
    # for example, if most ODs had NO transit paths, then the average ratio would be very low, making it seem like transit travel times
    # compare favorably to auto, which they do not
    average_ratio = trips_od_travel_time_df['ratio_travel_time_peak_nonpeak'].mean()
    LOGGER.info("  => average_ratio={}".format(average_ratio))
    # LOGGER.debug(trips_od_travel_time_df)

    # convert to metrics dataframe by pivoting one last time to just columns orig_CITY, dest_CITY
    trips_od_travel_time_df = pd.melt(trips_od_travel_time_df, 
                                      id_vars=['orig_CITY','dest_CITY'], 
                                      var_name='metric_desc',
                                      value_name='value')
    # travel times and num trips are extra
    trips_od_travel_time_df['intermediate/final']   = 'extra'
    # ratios are intermediate
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.metric_desc.str.startswith('ratio'), 'intermediate/final'] = 'intermediate'

    # key is orig_CITY, dest_CITY
    trips_od_travel_time_df['Origin and Destination']  = trips_od_travel_time_df['orig_CITY'] + " to " + trips_od_travel_time_df['dest_CITY']
    trips_od_travel_time_df.drop(columns=['orig_CITY','dest_CITY'], inplace=True)

    trips_od_travel_time_df['modelrun_id'] = tm_run_id
    trips_od_travel_time_df['year'] = tm_run_id[:4]
    trips_od_travel_time_df['metric_id'] = metric_id
    # LOGGER.info(trips_od_travel_time_df)
    
    # finally, add the average_ratio
    final_row = pd.DataFrame.from_records([{
        'modelrun_id':          tm_run_id,
        'metric_id':            metric_id,
        'intermediate/final':   "final",
        'Origin and Destination':                  "Average across OD pairs",
        'metric_desc':          "ratio_travel_time_peak_nonpeak_across_pairs",
        'year':                 tm_run_id[:4], 
        'value':                average_ratio
     }])
    # LOGGER.debug(final_row)

    # add metric for goods routes: Calculate [Ratio of travel time during peak hours vs. non-peak hours] for 3 truck routes (using link-level)
    # load table with links for each goods route
    # columns: A, B, I580_I238_I880_PortOfOakland, I101_I880_PortOfOakland, I80_I880_PortOfOakland
    goods_routes_a_b_links_file = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "goods_routes_a_b.csv")
    # TODO: this is large so join/subset it immediately
    goods_routes_a_b_links_df = pd.read_csv(goods_routes_a_b_links_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(goods_routes_a_b_links_df), goods_routes_a_b_links_file))
    LOGGER.debug("goods_routes_a_b_links_df.head() =\n{}".format(goods_routes_a_b_links_df.head()))
    # merge loaded network with df containing route information
    # remove HOV lanes from the network
    # load loaded network
    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    tm_loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_with_goods_routes_df = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['useAM'] == 1)]
    loaded_network_with_goods_routes_df = loaded_network_with_goods_routes_df.copy()[['a','b','ctimAM','ctimMD','ctimPM']]
    loaded_network_with_goods_routes_df = pd.merge(left=loaded_network_with_goods_routes_df, right=goods_routes_a_b_links_df, how='left', left_on=['a','b'], right_on=['A','B'])
    LOGGER.debug("loaded_network_with_goods_routes_df.head() =\n{}".format(loaded_network_with_goods_routes_df.head()))

    # sum the travel time for the different time periods on the route that begins on I580
    travel_time_route_I580_summed_df = loaded_network_with_goods_routes_df.copy().groupby('I580_I238_I880_PortOfOakland').agg('sum')
    LOGGER.debug("travel_time_route_I580_summed_df.head() =\n{}".format(travel_time_route_I580_summed_df.head()))
    # Only use rows containing 'AM' since this is the direction toward the port of oakland
    AM_travel_time_route_I580 = travel_time_route_I580_summed_df.loc['AM', 'ctimAM']
    MD_travel_time_route_I580 = travel_time_route_I580_summed_df.loc['AM', 'ctimMD']
    PM_travel_time_route_I580 = travel_time_route_I580_summed_df.loc['AM', 'ctimPM']
    # calculate average travel time for peak period
    peak_average_travel_time_route_I580 = numpy.mean([AM_travel_time_route_I580,PM_travel_time_route_I580])
    # calculate ratio for peak/offpeak
    ratio_peak_offpeak_route_I580 = peak_average_travel_time_route_I580 / MD_travel_time_route_I580
    # enter into metrics_dict
    metrics_dict['Goods Routes', 'Peak Hours', grouping3, tm_run_id, metric_id,'intermediate','I580_I238_I880_PortOfOakland', 'average peak travel time', year] = peak_average_travel_time_route_I580
    metrics_dict['Goods Routes', 'NonPeak Hours', grouping3, tm_run_id, metric_id,'intermediate','I580_I238_I880_PortOfOakland', 'average nonpeak travel time', year] = MD_travel_time_route_I580
    metrics_dict['Goods Routes', 'Peak vs NonPeak', grouping3, tm_run_id, metric_id,'final','I580_I238_I880_PortOfOakland', 'Ratio', year] = ratio_peak_offpeak_route_I580
    
    # sum the travel time for the different time periods on the route that begins on I101
    travel_time_route_I101_summed_df = loaded_network_with_goods_routes_df.copy().groupby('I101_I880_PortOfOakland').agg('sum')
    # Only use rows containing 'AM' since this is the direction toward the port of oakland
    AM_travel_time_route_I101 = travel_time_route_I101_summed_df.loc['AM', 'ctimAM']
    MD_travel_time_route_I101 = travel_time_route_I101_summed_df.loc['AM', 'ctimMD']
    PM_travel_time_route_I101 = travel_time_route_I101_summed_df.loc['AM', 'ctimPM']
    # calculate average travel time for peak period
    peak_average_travel_time_route_I101 = numpy.mean([AM_travel_time_route_I101,PM_travel_time_route_I101])
    # calculate ratio for peak/offpeak
    ratio_peak_offpeak_route_I101 = peak_average_travel_time_route_I101 / MD_travel_time_route_I101
    # enter into metrics_dict
    metrics_dict['Goods Routes', 'Peak Hours', grouping3, tm_run_id, metric_id,'intermediate','I101_I880_PortOfOakland', 'average peak travel time', year] = peak_average_travel_time_route_I101
    metrics_dict['Goods Routes', 'NonPeak Hours', grouping3, tm_run_id, metric_id,'intermediate','I101_I880_PortOfOakland', 'average nonpeak travel time', year] = MD_travel_time_route_I101
    metrics_dict['Goods Routes', 'Peak vs NonPeak', grouping3, tm_run_id, metric_id,'final','I101_I880_PortOfOakland', 'Ratio', year] = ratio_peak_offpeak_route_I101
    
    # sum the travel time for the different time periods on the route that begins on I80
    travel_time_route_I80_summed_df = loaded_network_with_goods_routes_df.copy().groupby('I80_I880_PortOfOakland').agg('sum')
    # Only use rows containing 'AM' since this is the direction toward the port of oakland
    AM_travel_time_route_I80 = travel_time_route_I80_summed_df.loc['AM', 'ctimAM']
    MD_travel_time_route_I80 = travel_time_route_I80_summed_df.loc['AM', 'ctimMD']
    PM_travel_time_route_I80 = travel_time_route_I80_summed_df.loc['AM', 'ctimPM']
    # calculate average travel time for peak period
    peak_average_travel_time_route_I80 = numpy.mean([AM_travel_time_route_I80,PM_travel_time_route_I80])
    # calculate ratio for peak/offpeak
    ratio_peak_offpeak_route_I80 = peak_average_travel_time_route_I80 / MD_travel_time_route_I80
    # enter into metrics_dict
    metrics_dict['Goods Routes', 'Peak Hours', grouping3, tm_run_id, metric_id,'intermediate','I80_I880_PortOfOakland', 'average peak travel time', year] = peak_average_travel_time_route_I80
    metrics_dict['Goods Routes', 'NonPeak Hours', grouping3, tm_run_id, metric_id,'intermediate','I80_I880_PortOfOakland', 'average nonpeak travel time', year] = MD_travel_time_route_I80
    metrics_dict['Goods Routes', 'Peak vs NonPeak', grouping3, tm_run_id, metric_id,'final','I80_I880_PortOfOakland', 'Ratio', year] = ratio_peak_offpeak_route_I80

    # enter goods routes average
    goods_routes_average_ratio_peak_offpeak = numpy.mean([ratio_peak_offpeak_route_I580, ratio_peak_offpeak_route_I101,ratio_peak_offpeak_route_I80])
    metrics_dict['Goods Routes', 'Peak vs NonPeak', grouping3, tm_run_id, metric_id,'final','Average Across Routes', 'Ratio', year] = goods_routes_average_ratio_peak_offpeak

    # return df for reliable 2 excluding goods routes
    # TODO: add goods routes metric to DF returned
    trips_od_travel_time_df = pd.concat([trips_od_travel_time_df, final_row])
    LOGGER.debug("{} Result: \n{}".format(metric_id, trips_od_travel_time_df))
    return trips_od_travel_time_df

def metrics_dict_to_df(metrics_dict: dict) -> pd.DataFrame:
    """
    Temporary method to convert metrics_dict to metrics_df (pd.DataFrame) since the dictionary structure just makes this more confusing

    Returns DataFrame with columns: grouping1, grouping2, grouping3, modelrun_id, metric_id, metric_level, key, metric_desc, year, value
    """
    # key=grouping1, grouping2, grouping3, tm_run_id, metric_id, top_level|extra|intermediate|final, key, metric_desc, year
    row_dict_list = []
    for metric_key in metrics_dict.keys():
        # keys given by METRICS_COLUMNS
        row_dict = {METRICS_COLUMNS[idx]: metric_key[idx] for idx in range(len(metric_key))}
        # metric value
        row_dict['value'] = metrics_dict[metric_key]
        row_dict_list.append(row_dict)
    return pd.DataFrame.from_records(row_dict_list)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip_if_exists", action="store_true", help="Use this option to skip creating metrics files if one exists already")
    args = parser.parse_args()

    pd.options.display.width = 500 # redirect output to file so this will be readable
    pd.options.display.max_columns = 100
    pd.options.display.max_rows = 500
    pd.options.mode.chained_assignment = None  # default='warn'

    # set up logging
    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handler -- append if skip_if_exists is passed
    fh = logging.FileHandler(LOG_FILE, mode='a' if args.skip_if_exists else 'w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    LOGGER.debug("args = {}".format(args))

    current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
    current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']
    # only process metrics for 2035 model runs 
    current_runs_df = current_runs_df.loc[ current_runs_df['year'] == 2035]
    # # TODO: delete later after NP10 runs are completed
    # current_runs_df = current_runs_df.loc[ (current_runs_df['directory'].str.contains('NP10') == False)]

    LOGGER.info("current_runs_df: \n{}".format(current_runs_df))

    current_runs_list = current_runs_df['directory'].to_list()
    
    # define base run inputs
    # # base year run for comparisons = most recent Pathway 4 (No New Pricing) run
    pathway4_runs = current_runs_df.loc[ current_runs_df['category']=="Pathway 4" ]
    BASE_SCENARIO_RUN_ID = pathway4_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> BASE_SCENARIO_RUN_ID = {}".format(BASE_SCENARIO_RUN_ID))
    
    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Reliable2_ratio_peak_nonpeak_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))
        

        # results will be stored here
        # key=grouping1, grouping2, grouping3, tm_run_id, metric_id, top_level|extra|intermediate|final, key, metric_desc, year
        # TODO: convert to pandas.DataFrame with these column headings.  It's far more straightforward.
        metrics_dict = {}
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Reliable2_ratio_peak_nonpeak(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ R2 Done")

        # _________output table__________
        # TODO: deprecate when all metrics just come through via metrics_df
        metrics_df = pd.concat([metrics_df, metrics_dict_to_df(metrics_dict)])

        metrics_df.loc[(metrics_df['modelrun_id'] == tm_run_id)].to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()