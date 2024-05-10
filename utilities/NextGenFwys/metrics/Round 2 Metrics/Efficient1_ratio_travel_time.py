USAGE = """

  python Efficient1_ratio_travel_time.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Efficient1_ratio_travel_time_XX.csv
  
  This file will have the following columns:
    'value',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final', 
    'Metric Description',
    'Year'
    
  Metrics are:
    1) Efficient 1: Travel time by transit vs. auto in the region and EPCs

"""

import os
import numpy
import pandas as pd
import argparse
import logging

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"
# line below for round 2 runs
NGFS_ROUND2_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Efficient1_ratio_travel_time.log" # in the cwd
LOGGER                  = None # will initialize in main

# maps TAZs to a few selected cities for Origin/Destination analysis
NGFS_OD_CITIES_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_with_cities.csv")
NGFS_OD_CITIES_DF      = pd.read_csv(NGFS_OD_CITIES_FILE)

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050
NGFS_EPC_TAZ_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_epc_crosswalk.csv")
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
# define origin destination pairs to use for Efficient 1, Pathway 3 Travel Time calculation
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

# TODO: deprecate the use of these in Efficient 1 (don't affect results, just need to clean up the code)
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
    'grouping1',
    'grouping2',
    'grouping3',
    'modelrun_id',
    'metric_id',
    'intermediate/final', # TODO: suggest renaming this to 'metric_level' since other options are used beyond intermediate and final
    'Origin and Destination',
    'metric_desc',
    'year',
    'value'
]

# TODO deprecate use of the file below
# load minor groupings, to be merged with loaded network
MINOR_LINKS_DF = pd.read_csv('L:\\Application\\Model_One\\NextGenFwys\\metrics\\Input Files\\a_b_with_minor_groupings.csv')
# list for iteration
MINOR_GROUPS = MINOR_LINKS_DF['Grouping minor'].unique()[1:] #exclude 'other' and NaN
MINOR_GROUPS = numpy.delete(MINOR_GROUPS, 2)

def return_E1_DF(tm_run_id, od_df, All_or_EPC):
    # change orig_CITY to 'All TAZs

    od_df['orig_CITY'] = All_or_EPC + ' TAZs'

    # to get weighted average, transform to total travel time
    od_df['tot_travel_time_in_mins'] = \
        od_df['avg_travel_time_in_mins']*od_df['num_trips']

    # pivot down to orig_CITY x dest_CITY x agg_trip_mode
    od_df = pd.pivot_table(od_df, 
                                             index=['orig_CITY','dest_CITY','agg_trip_mode'],
                                             values=['num_trips','tot_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'tot_travel_time_in_mins':numpy.sum})
    od_df.reset_index(inplace=True)
    od_df['avg_travel_time_in_mins'] = \
        od_df['tot_travel_time_in_mins']/od_df['num_trips']
    # LOGGER.debug(od_df)

    # pivot again to move agg_mode to column
    # columns will now be: orig_CITY_, dest_CITY_, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, num_trips_auto, num_trips_transit
    od_df = pd.pivot_table(od_df, 
                                             index=['orig_CITY','dest_CITY'],
                                             columns=['agg_trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'])
    od_df.reset_index(inplace=True)
    # flatten resulting MultiIndex column names
    # rename from ('orig_CITY',''), ('dest_CITY',''), ('avg_travel_time_in_mins','auto'), ('avg_travel_time_in_mins', 'transit'), ...
    # to orig_CITY, dest_CITY, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, ...
    od_df.columns = ['_'.join(col) if len(col[1]) > 0 else col[0] for col in od_df.columns.values]

    # add ratio
    od_df['ratio_travel_time_transit_auto'] = \
        od_df['avg_travel_time_in_mins_transit']/od_df['avg_travel_time_in_mins_auto']
    
    # note that this does not include NaNs in either the numerator or the denominator, which I think is correct
    # TODO: in the previous implementation, NaN is converted to zero, which artificially lowers the average.
    # for example, if most ODs had NO transit paths, then the average ratio would be very low, making it seem like transit travel times
    # compare favorably to auto, which they do not
    average_ratio = od_df['ratio_travel_time_transit_auto'].mean()
    LOGGER.info("  => average_ratio={}".format(average_ratio))
    # LOGGER.debug(od_df)

    # convert to metrics dataframe by pivoting one last time to just columns orig_CITY, dest_CITY
    od_df = pd.melt(od_df, 
                                      id_vars=['orig_CITY','dest_CITY'], 
                                      var_name='metric_desc',
                                      value_name='value')
    # travel times and num trips are extra
    od_df['intermediate/final']   = 'extra'
    # ratios are intermediate
    od_df.loc[ od_df.metric_desc.str.startswith('ratio'), 'intermediate/final'] = 'intermediate'

    # Origin and Destination is orig_CITY, dest_CITY
    od_df['Origin and Destination']  = od_df['orig_CITY'] + "_" + od_df['dest_CITY']
    od_df.drop(columns=['orig_CITY','dest_CITY'], inplace=True)

    od_df['modelrun_id'] = tm_run_id
    od_df['year'] = tm_run_id[:4]
    od_df['metric_id'] = 'Efficient 1'
    # LOGGER.info(od_df)
    return od_df

def E1_aggregate_before_joining(tm_run_id):
    """

    have to aggregate before joining.  
    e.g. simplify the trip mode, aggregate all income quartiles, and then join — so we won't lose trips
    see asana task: https://app.asana.com/0/0/1204811778297277/f 
    
    """
    LOGGER.info("Efficient 1: Aggregating before joining for {}".format(tm_run_id)) 

    # columns: orig_taz, dest_taz, trip_mode, timeperiod_label, incQ, incQ_label, num_trips, avg_travel_time_in_mins
    ODTravelTime_byModeTimeperiod_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "ODTravelTime_byModeTimeperiodIncome.csv") #changed "ODTravelTime_byModeTimeperiodIncome.csv" to a variable for better performance during debugging
    # line below for round 2 runs
    ODTravelTime_byModeTimeperiod_file = os.path.join(NGFS_ROUND2_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "ODTravelTime_byModeTimeperiodIncome.csv") #changed "ODTravelTime_byModeTimeperiodIncome.csv" to a variable for better performance during debugging
    
    # TODO fix hardcoded solution below
    if tm_run_id == BASE_SCENARIO_RUN_ID:
        ODTravelTime_byModeTimeperiod_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "ODTravelTime_byModeTimeperiodIncome.csv") #changed "ODTravelTime_byModeTimeperiodIncome.csv" to a variable for better performance during debugging
    
    # this is large so join/subset it immediately
    trips_od_travel_time_df = pd.read_csv(ODTravelTime_byModeTimeperiod_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(trips_od_travel_time_df), ODTravelTime_byModeTimeperiod_file))

    trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df.timeperiod_label == 'AM Peak' ]
    LOGGER.info("  Filtered to AM only: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot out the income since we don't need it
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df,
                                             index=['orig_taz','dest_taz','trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'avg_travel_time_in_mins':numpy.mean})
    trips_od_travel_time_df.reset_index(inplace=True)
    LOGGER.info("  Aggregated income groups: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # we're going to aggregate trip modes; auto includes TAXI and TNC
    trips_od_travel_time_df['agg_trip_mode'] = "N/A"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_TRANSIT),      'agg_trip_mode' ] = "transit"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_PRIVATE_AUTO), 'agg_trip_mode' ] = "auto"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_TAXI_TNC),     'agg_trip_mode' ] = "auto"
    LOGGER.info("   Aggregated trip modes: {:,} rows".format(len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot down to orig_taz x dest_taz x agg_trip_mode
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_taz','dest_taz','agg_trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'avg_travel_time_in_mins':numpy.mean})
    trips_od_travel_time_df.reset_index(inplace=True)

    return trips_od_travel_time_df

def calculate_Efficient1_ratio_travel_time(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Efficient1: Ratio of travel time by transit over that of auto between representative origin-destination pairs
    
    Args:
        tm_run_id (str): Travel model run ID

    Returns:
        pandas.DataFrame: with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Efficient 1'
          modelrun_id = tm_run_id
        Metrics returned:
          Origin and Destination                       intermediate/final  metric_desc
          [origCITY_destCITY]       extra               avg_travel_time_in_mins_auto
          [origCITY_destCITY]       extra               avg_travel_time_in_mins_transit
          [origCITY_destCITY]       extra               num_trips_auto
          [origCITY_destCITY]       extra               num_trips_transit
          [origCITY_destCITY]       intermediate        ratio_travel_time_transit_auto
          Average across OD pairs   final               ratio_travel_time_transit_auto_across_pairs

    Notes:
    * Representative origin-destination pairs are given by TAZs corresponding with 
      NGFS_OD_CITIES_FILE and NGFS_OD_CITIES_OF_INTEREST
    * Auto modes includes taxi and tncs
    * Final calculation is the average of these ratios (not weighted) across all OD pairs,
      excluding those which have no transit trips and therefore lack a transit travel time
    
      TODO: Does this make sense?  If a market is very small, should it be considered equally
    """
    METRIC_ID = 'Efficient 1'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id)) 

    trips_od_travel_time_df = E1_aggregate_before_joining(tm_run_id)
    # remove 'num_trips' column to use from base run instead
    trips_od_travel_time_df = trips_od_travel_time_df.drop('num_trips', axis = 1)
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # read a copy of the table for the base comparison run to pull the number of trips (for weighting)
    trips_od_travel_time_df_base = E1_aggregate_before_joining(BASE_SCENARIO_RUN_ID) 
    # reduce copied df to only relevant columns orig, dest, and num_trips
    # columns: orig_taz, dest_taz, agg_trip_mode, num_trips
    trips_od_travel_time_df_base = trips_od_travel_time_df_base[['orig_taz','dest_taz','agg_trip_mode','num_trips']]
    LOGGER.debug("trips_od_travel_time_df_base: \n{}".format(trips_od_travel_time_df_base))

    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=trips_od_travel_time_df_base, 
                                       how='left', 
                                       left_on=['orig_taz','dest_taz','agg_trip_mode'], 
                                       right_on=['orig_taz','dest_taz','agg_trip_mode'])
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

    # filter a copy to only those ending in cities of interest
    trips_ending_in_city_dt_od_travel_time_df = trips_od_travel_time_df.copy().loc[(trips_od_travel_time_df['dest_CITY'] == 'San Francisco Downtown Area')|
                                                                                    (trips_od_travel_time_df['dest_CITY'] == 'Central/West Oakland')|
                                                                                    (trips_od_travel_time_df['dest_CITY'] == 'Central San Jose')]
    # join to epc lookup table
    trips_ending_in_city_dt_od_travel_time_df = pd.merge(left=trips_ending_in_city_dt_od_travel_time_df,
                                                        right=NGFS_EPC_TAZ_DF,
                                                        left_on="orig_taz",
                                                        right_on="TAZ1454")
    # filter a copy to only those starting in EPCs
    trips_starting_EPC_ending_in_city_dt_od_travel_time_df = trips_ending_in_city_dt_od_travel_time_df.copy().loc[(trips_ending_in_city_dt_od_travel_time_df['taz_epc'] == 1)]

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

    # pivot down to orig_CITY x dest_CITY x agg_trip_mode
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_CITY','dest_CITY','agg_trip_mode'],
                                             values=['num_trips','tot_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'tot_travel_time_in_mins':numpy.sum})
    trips_od_travel_time_df.reset_index(inplace=True)
    trips_od_travel_time_df['avg_travel_time_in_mins'] = \
        trips_od_travel_time_df['tot_travel_time_in_mins']/trips_od_travel_time_df['num_trips']
    LOGGER.debug("trips_od_travel_time_df: \n{}".format(trips_od_travel_time_df))

    # pivot again to move agg_mode to column
    # columns will now be: orig_CITY_, dest_CITY_, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, num_trips_auto, num_trips_transit
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_CITY','dest_CITY'],
                                             columns=['agg_trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'])
    trips_od_travel_time_df.reset_index(inplace=True)
    # flatten resulting MultiIndex column names
    # rename from ('orig_CITY',''), ('dest_CITY',''), ('avg_travel_time_in_mins','auto'), ('avg_travel_time_in_mins', 'transit'), ...
    # to orig_CITY, dest_CITY, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, ...
    trips_od_travel_time_df.columns = ['_'.join(col) if len(col[1]) > 0 else col[0] for col in trips_od_travel_time_df.columns.values]

    # add ratio
    trips_od_travel_time_df['ratio_travel_time_transit_auto'] = \
        trips_od_travel_time_df['avg_travel_time_in_mins_transit']/trips_od_travel_time_df['avg_travel_time_in_mins_auto']
    
    # note that this does not include NaNs in either the numerator or the denominator, which I think is correct
    # TODO: in the previous implementation, NaN is converted to zero, which artificially lowers the average.
    # for example, if most ODs had NO transit paths, then the average ratio would be very low, making it seem like transit travel times
    # compare favorably to auto, which they do not
    average_ratio = trips_od_travel_time_df['ratio_travel_time_transit_auto'].mean()
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

    # Origin and Destination is orig_CITY, dest_CITY
    trips_od_travel_time_df['Origin and Destination']  = trips_od_travel_time_df['orig_CITY'] + " to " + trips_od_travel_time_df['dest_CITY']
    trips_od_travel_time_df.drop(columns=['orig_CITY','dest_CITY'], inplace=True)

    trips_od_travel_time_df['modelrun_id'] = tm_run_id
    trips_od_travel_time_df['year'] = tm_run_id[:4]
    trips_od_travel_time_df['metric_id'] = METRIC_ID
    # LOGGER.info(trips_od_travel_time_df)
    
    # finally, add the average_ratio
    final_row = pd.DataFrame.from_records([{
        'modelrun_id':          tm_run_id,
        'metric_id':            METRIC_ID,
        'intermediate/final':   "final",
        'Origin and Destination':                  "Average across OD pairs",
        'metric_desc':          "ratio_travel_time_transit_auto_across_pairs",
        'year':                 tm_run_id[:4], 
        'value':                average_ratio
     }])
    # LOGGER.debug(final_row)

    # all TAZ rows
    all_taz_rows = return_E1_DF(tm_run_id, trips_ending_in_city_dt_od_travel_time_df, 'All')
    epc_taz_rows = return_E1_DF(tm_run_id, trips_starting_EPC_ending_in_city_dt_od_travel_time_df, 'EPC')
     
    trips_od_travel_time_df = pd.concat([trips_od_travel_time_df, final_row, all_taz_rows, epc_taz_rows])
    LOGGER.debug("{} Result: \n{}".format(METRIC_ID, trips_od_travel_time_df))
    return trips_od_travel_time_df

def determine_tolled_minor_group_links(tm_run_id: str, fwy_or_arterial: str) -> pd.DataFrame:
    """ Given a travel model run ID, reads the loaded network and the tollclass designations,
    and returns a table that will be used to define which links belong to which tollclass minor grouping.

    If fwy_or_arterial == "fwy",      tm_run_id should be a Pathway 1 model run, and this will return tolled freeway links
    If fwy_or_arterial == "arterial", tm_run_id should be a Pathway 2 model run, and this will return arterial freeway links

    This replaces 'Input Files\\a_b_with_minor_groupings.csv' because this uses the model network information directly

    Args:
        tm_run_id (str):      travel model run ID (should be Pathway 1 or 2)
        fwy_or_arterial(str): one of "fwy" or "arterial"

    Returns:
        pd.DataFrame: mapping from links to tollclass minor groupings.  Columns:
        a (int):              link A node
        b (int):              link B node
        grouping (str):       minor grouping without direction, e.g. EastBay_68024980, EastBay_880680, etc.
        grouping_dir (str):   either AM or PM for the grouping
    """
    if fwy_or_arterial not in ["fwy","arterial"]: raise ValueError

    LOGGER.info("=== determine_tolled_minor_group_links({}, {}) ===".format(tm_run_id, fwy_or_arterial))
    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    
    tm_loaded_network_df = pd.read_csv(loaded_roadway_network, 
                                       usecols=['a','b','tollclass','ft'],
                                       dtype={'a':numpy.int64, 'b':numpy.int64, 'tollclass':numpy.int64},
                                       na_values=[''])
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df), loaded_roadway_network))

    # read toll class groupings
    tollclass_df = pd.read_excel(NGFS_TOLLCLASS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(tollclass_df), NGFS_TOLLCLASS_FILE))
    # select NextGenFwy tollclasses where 'Grouping minor' exists
    tollclass_df = tollclass_df.loc[(tollclass_df.project == 'NextGenFwy') & pd.notna(tollclass_df['Grouping minor'])]

    # See TOLLCLASS_Designations.xlsx workbook, Readme - numbering convention
    if fwy_or_arterial == "fwy":
        tollclass_df = tollclass_df.loc[tollclass_df.tollclass > 900000]
    elif fwy_or_arterial == "arterial":
        tollclass_df = tollclass_df.loc[(tollclass_df.tollclass > 700000) & 
                                        (tollclass_df.tollclass < 900000)]

    LOGGER.info("  Filtered to {:,} rows for project=='NextGenFwy' with notna 'Grouping minor' and tollclass appropriate to {}".format(
        len(tollclass_df), fwy_or_arterial))
    # LOGGER.info("  Grouping minor: {}".format(sorted(tollclass_df['Grouping minor'].to_list())))

    # add to loaded roadway network -- INNER JOIN
    grouping_df = pd.merge(
        left=tm_loaded_network_df,
        right=tollclass_df[['tollclass','Grouping minor']],
        on=['tollclass'],
        how='inner'
    )
    # remove rows with 'Minor grouping' that doesn't end in AM or PM
    grouping_df = grouping_df.loc[
        grouping_df['Grouping minor'].str.endswith('_AM') |
        grouping_df['Grouping minor'].str.endswith('_PM')
    ]

    # log the facility type summary
    LOGGER.debug("  Tolled {} facility types:\n{}".format(fwy_or_arterial, grouping_df['ft'].value_counts()))

    # split 'Grouping minor' to 'grouping' (now without direction) and 'grouping_dir'
    grouping_df['grouping_dir'] = grouping_df['Grouping minor'].str[-2:]
    grouping_df['grouping']     = grouping_df['Grouping minor'].str[:-3]
    grouping_df.drop(columns=['Grouping minor','tollclass','ft'], inplace=True)
    LOGGER.debug("  Returning {:,} links:\n{}".format(len(grouping_df), grouping_df))
    return grouping_df

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
    
    # line below for round 2 runs
    current_runs_list = ['2035_TM160_NGF_r2_NoProject_01', '2035_TM160_NGF_r2_NoProject_01_AOCx1.25_v2', '2035_TM160_NGF_r2_NoProject_03_pretollcalib', '2035_TM160_NGFr2_NP04_Path1_02']

    # define base run inputs
    # # base year run for comparisons = most recent Pathway 4 (No New Pricing) run
    pathway4_runs = current_runs_df.loc[ current_runs_df['category']=="Pathway 4" ]
    BASE_SCENARIO_RUN_ID = pathway4_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> BASE_SCENARIO_RUN_ID = {}".format(BASE_SCENARIO_RUN_ID))

    # find the last pathway 1 run, since we'll use that to determine which links are in the fwy minor groupings
    pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("Pathway 1")]
    PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> PATHWAY1_SCENARIO_RUN_ID = {}".format(PATHWAY1_SCENARIO_RUN_ID))
    TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")
    # TOLLED_FWY_MINOR_GROUP_LINKS_DF.to_csv("TOLLED_FWY_MINOR_GROUP_LINKS.csv", index=False)
    
    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Efficient1_ratio_travel_time_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))
        

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Efficient1_ratio_travel_time(tm_run_id)

        LOGGER.info("@@@@@@@@@@@@@ E1 Done")


        metrics_df.loc[(metrics_df['modelrun_id'] == tm_run_id)].to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()