USAGE = """

  python Affordable2_ratio_time_cost.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Affordable2_ratio_time_cost_XX.csv
  
  This file will have the following columns:
    'Income Level',
    'Travel Mode',
    'value',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final', 
    'Metric Description',
    'Year'
    
  Metrics are:
    1) Affordable 2: Transportation costs as a share of household income, by different income groups

"""

import os
import numpy
import pandas as pd
import argparse
import logging
import simpledbf

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Affordable2_ratio_time_cost.log" # in the cwd
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
# define origin destination pairs to use for Affordable 2, Pathway 3 Travel Time calculation
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

# TODO: deprecate the use of these in Affordable 2 (don't affect results, just need to clean up the code)
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
    'Corridor',
    'Value Type',
    'Income Group/Occupation',
    'modelrun_id',
    'metric_id',
    'intermediate/final', # TODO: suggest renaming this to 'metric_level' since other options are used beyond intermediate and final
    'Household/Commercial',
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

def calculate_change_between_run_and_base(tm_run_id, BASE_SCENARIO_RUN_ID, year, metric_id, metrics_dict):
    #function to compare two runs and enter difference as a metric in dictionary
    LOGGER.debug("calculating change between run and base for metric: \n{} for runs \n{} and \n{}".format(metric_id, tm_run_id, BASE_SCENARIO_RUN_ID))
    grouping1 = ' '
    grouping2 = ' '
    grouping3 = ' '
    metrics_dict_series = pd.Series(metrics_dict)
    metrics_dict_df  = metrics_dict_series.to_frame().reset_index()
    metrics_dict_df.columns = ['Corridor', 'Value Type', 'Income Group/Occupation', 'modelrun_id','metric_id','intermediate/final','Household/Commercial','metric_desc','year','value']
    #     make a list of the metrics from the run of interest to iterate through and calculate a difference with
    LOGGER.debug("   metrics_dict_df:\n{}".format(metrics_dict_df))
    metrics_list = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'] == tm_run_id)]
    metrics_list = metrics_list.loc[(metrics_dict_df['metric_id'].str.contains(metric_id) == True)]['metric_desc']
    # iterate through the list
    # add in grouping field
    key = 'Change'
    for metric in metrics_list:
        if (('_AM' in metric)):
            temp = metric.split('_AM')[0]
            key = temp.split('travel_time_')[-1]
        elif ('across_key_corridors' in metric):
            key = 'Average Across Corridors'

        val_run = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'] == tm_run_id)].loc[(metrics_dict_df['metric_desc'] == metric)].iloc[0]['value']
        val_base = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'] == BASE_SCENARIO_RUN_ID)].loc[(metrics_dict_df['metric_desc'] == metric)].iloc[0]['value']
        LOGGER.debug("   run value:\n{}".format(val_run))
        LOGGER.debug("   base value:\n{}".format(val_base))
        metrics_dict[key, grouping2, grouping3, tm_run_id, metric_id,'debug step','By Corridor','change_in_{}'.format(metric),year] = (val_run-val_base)
        
def sum_grouping(network_df,period): #sum congested time across selected toll class groupings
    return network_df['CTIM'+period].sum()

def calculate_auto_travel_time(tm_run_id,metric_id, year,network,metrics_dict):
    grouping1 = ' '
    grouping2 = ' '
    grouping3 = ' '
    sum_of_weights = 0 #sum of weights (vmt of corridor) to be used for weighted average 
    total_weighted_travel_time = 0 #sum for numerator
    n = 0 #counter for simple average 
    total_travel_time = 0 #numerator for simple average 
    LOGGER.info("Calling function calculate_auto_travel_time() for {}".format(tm_run_id))
    
    # load base loaded nework for vmt weighting
    tm_loaded_network_file_base = os.path.join(NGFS_SCENARIOS, BASE_SCENARIO_RUN_ID, "OUTPUT", "avgload5period.csv")
    tm_loaded_network_df_base = pd.read_csv(tm_loaded_network_file_base)
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df_base), tm_loaded_network_file_base))
    tm_loaded_network_df_base = tm_loaded_network_df_base.rename(columns=lambda x: x.strip())
    tm_loaded_network_df_base['a_b'] = tm_loaded_network_df_base['a'].astype(str) + "_" + tm_loaded_network_df_base['b'].astype(str)

    for i in MINOR_GROUPS:
        #     add minor ampm ctim to metric dict
        minor_group_am_df = network.loc[network['Grouping minor_AMPM'] == i+'_AM']
        minor_group_am = sum_grouping(minor_group_am_df,'AM')
        
        # vmt to be used for weighted averages
        # create df to pull vmt from to use for weighted average
        # for simplicity of calculation, always using the base run VMT
        index_a_b = minor_group_am_df.copy()[['a_b']]
        network_for_vmt_df = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')
        vmt_minor_grouping_AM = (network_for_vmt_df['volAM_tot'] * network_for_vmt_df['distance']).sum()

        # check for length //can remove later
        length_of_grouping = (minor_group_am_df['DISTANCE']).sum()
        metrics_dict[i, grouping2, grouping3, BASE_SCENARIO_RUN_ID,metric_id,'debug step','By Corridor','%s' % i + '_AM_length',year] = length_of_grouping

        metrics_dict[i, grouping2, grouping3, BASE_SCENARIO_RUN_ID,metric_id,'debug step','By Corridor','%s' % i + '_AM_vmt',year] = vmt_minor_grouping_AM

        # add travel times to metric dict
        metrics_dict[i, 'Travel Time', grouping3, tm_run_id,metric_id,'extra','By Corridor','travel_time_%s' % i + '_AM',year] = minor_group_am
        # add average speed weighted by link distance
        try:
            metrics_dict[i, 'Travel Time', grouping3, tm_run_id,metric_id,'extra','By Corridor','average_speed_%s' % i + '_AM',year] = numpy.average(a = network_for_vmt_df['cspdAM'], weights = network_for_vmt_df['distance'])
        except:
            metrics_dict[i, 'Travel Time', grouping3, tm_run_id,metric_id,'extra','By Corridor','average_speed_%s' % i + '_AM',year] = 0

        # weighted AM,PM travel times (by vmt)
        weighted_AM_travel_time_by_vmt = minor_group_am * vmt_minor_grouping_AM

def calculate_auto_travel_time_for_pathway3(tm_run_id, origin_city_abbreviation):
    """ Calculates travel time by auto between representative origin-destination pairs
    overwrites the travel_time metric in the metric dictionary for pathway 3,
    the other function will still be called for simplicity of not editing all the code
    
    Args:
        tm_run_id (str): Travel model run ID

    Returns:
        pandas.DataFrame: with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Affordable 2'
          modelrun_id = tm_run_id
        Metrics returned:
          key                       intermediate/final  metric_desc
          [origCITY_destCITY]       extra               avg_travel_time_in_mins_auto
          [origCITY_destCITY]       extra               num_trips_auto

    Notes:
    * Representative origin-destination pairs are given by TAZs corresponding with 
      NGFS_OD_CITIES_FILE and NGFS_OD_CORDONS_OF_INTEREST
    * Auto modes includes taxi and tncs
    
      TODO: come back and change the code for all of Affordable 2 to improve readability
    """
    grouping1 = ' '
    grouping2 = ' '
    grouping3 = ' '
    METRIC_ID = 'Affordable 2'
    year = tm_run_id[:4]

    LOGGER.info("calculate_auto_travel_time_for_pathway3() for {}, metric: {}, city: {}".format(tm_run_id, METRIC_ID, origin_city_abbreviation))
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    # load tables that contain TAZs for trips originating within and outside of the cordons and headed to the cordons + the cordons itself
    NGFS_OD_ORIGINS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_with_origins.csv")
    NGFS_OD_ORIGINS_DF      = pd.read_csv(NGFS_OD_ORIGINS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(NGFS_OD_ORIGINS_DF), NGFS_OD_ORIGINS_FILE))

    NGFS_OD_CORDONS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_with_cordons.csv")
    NGFS_OD_CORDONS_DF      = pd.read_csv(NGFS_OD_CORDONS_FILE)
    LOGGER.info("  Read {:,} rows from {}".format(len(NGFS_OD_CORDONS_DF), NGFS_OD_CORDONS_FILE))

    # columns: orig_taz, dest_taz, trip_mode, timeperiod_label, incQ, incQ_label, num_trips, avg_travel_time_in_mins
    ODTravelTime_byModeTimeperiod_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "ODTravelTime_byModeTimeperiodIncome.csv") #changed "ODTravelTime_byModeTimeperiodIncome.csv" to a variable for better performance during debugging
    # this is large so join/subset it immediately
    trips_od_travel_time_df = pd.read_csv(ODTravelTime_byModeTimeperiod_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(trips_od_travel_time_df), ODTravelTime_byModeTimeperiod_file))

    trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df.timeperiod_label == 'AM Peak' ]
    LOGGER.info("  Filtered to AM only: {:,} rows".format(len(trips_od_travel_time_df)))

    # pivot out the income since we don't need it
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df,
                                             index=['orig_taz','dest_taz','trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'avg_travel_time_in_mins':numpy.mean})
    trips_od_travel_time_df.reset_index(inplace=True)
    LOGGER.info("  Aggregated income groups: {:,} rows".format(len(trips_od_travel_time_df)))

    # join to OD cities for origin
    origin_column_name = "ORIGIN_" + origin_city_abbreviation
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_ORIGINS_DF,
                                       left_on="orig_taz",
                                       right_on="taz1454")
    trips_od_travel_time_df.rename(columns={origin_column_name:"orig_ZONE"}, inplace=True)
    trips_od_travel_time_df.drop(columns=["taz1454"], inplace=True)
    # join to OD cities for destination
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_CORDONS_DF,
                                       left_on="dest_taz",
                                       right_on="taz1454")
    trips_od_travel_time_df.rename(columns={"CORDON":"dest_CORDON"}, inplace=True)
    trips_od_travel_time_df.drop(columns=["taz1454"], inplace=True)
    LOGGER.info("  Joined with {} for origin, destination: {:,} rows".format(NGFS_OD_CITIES_FILE, len(trips_od_travel_time_df)))
    LOGGER.debug("trips_od_travel_time_df.head():\n{}".format(trips_od_travel_time_df.head()))

    # filter again to only those of interest
    trips_od_travel_time_df = pd.merge(left=trips_od_travel_time_df,
                                       right=NGFS_OD_CORDONS_OF_INTEREST_DF,
                                       indicator=True)
    trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df._merge == 'both']
    LOGGER.info("  Filtered to only NGFS_OD_CORDONS_OF_INTEREST: {:,} rows".format(len(trips_od_travel_time_df)))

    # we're going to aggregate trip modes; auto includes TAXI and TNC
    trips_od_travel_time_df['agg_trip_mode'] = "N/A"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_PRIVATE_AUTO), 'agg_trip_mode' ] = "auto"
    trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(MODES_TAXI_TNC),     'agg_trip_mode' ] = "auto"

    # to get weighted average, transform to total travel time
    trips_od_travel_time_df['tot_travel_time_in_mins'] = \
        trips_od_travel_time_df['avg_travel_time_in_mins']*trips_od_travel_time_df['num_trips']

    # pivot down to orig_ZONE x dest_CORDON x agg_trip_mode
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_ZONE','dest_CORDON','agg_trip_mode'],
                                             values=['num_trips','tot_travel_time_in_mins'],
                                             aggfunc={'num_trips':numpy.sum, 'tot_travel_time_in_mins':numpy.sum})
    trips_od_travel_time_df.reset_index(inplace=True)
    trips_od_travel_time_df['avg_travel_time_in_mins'] = \
        trips_od_travel_time_df['tot_travel_time_in_mins']/trips_od_travel_time_df['num_trips']
    LOGGER.debug(trips_od_travel_time_df)

    # pivot again to move agg_mode to column
    # columns will now be: orig_ZONE_, dest_CORDON_, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, num_trips_auto, num_trips_transit
    trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df, 
                                             index=['orig_ZONE','dest_CORDON'],
                                             columns=['agg_trip_mode'],
                                             values=['num_trips','avg_travel_time_in_mins'])
    trips_od_travel_time_df.reset_index(inplace=True)
    # flatten resulting MultiIndex column names
    # rename from ('orig_ZONE',''), ('dest_CORDON',''), ('avg_travel_time_in_mins','auto'), ('avg_travel_time_in_mins', 'transit'), ...
    # to orig_ZONE, dest_CORDON, avg_travel_time_in_mins_auto, avg_travel_time_in_mins_transit, ...
    trips_od_travel_time_df.columns = ['_'.join(col) if len(col[1]) > 0 else col[0] for col in trips_od_travel_time_df.columns.values]

    # convert to metrics dataframe by pivoting one last time to just columns orig_ZONE, dest_CORDON
    trips_od_travel_time_df = pd.melt(trips_od_travel_time_df, 
                                      id_vars=['orig_ZONE','dest_CORDON'], 
                                      var_name='metric_desc',
                                      value_name='value')
    # travel times and num trips are extra
    trips_od_travel_time_df['intermediate/final']   = 'intermediate'
    
    # key is orig_ZONE, dest_CORDON
    trips_od_travel_time_df['Household/Commercial']  = trips_od_travel_time_df['orig_ZONE'] + "_into_" + trips_od_travel_time_df['dest_CORDON']
    trips_od_travel_time_df.drop(columns=['orig_ZONE','dest_CORDON'], inplace=True)

    trips_od_travel_time_df['modelrun_id'] = tm_run_id
    trips_od_travel_time_df['year'] = tm_run_id[:4]
    trips_od_travel_time_df['metric_id'] = METRIC_ID

    LOGGER.info(trips_od_travel_time_df)

    for OD in trips_od_travel_time_df['Household/Commercial']:
        # add travel times to metric dict
        OD_cordon_travel_time_df = trips_od_travel_time_df.loc[trips_od_travel_time_df['Household/Commercial'] == OD]
        LOGGER.info(OD_cordon_travel_time_df)
        OD_cordon_travel_time = OD_cordon_travel_time_df.loc[OD_cordon_travel_time_df['metric_desc'] == 'avg_travel_time_in_mins_auto'].iloc[0]['value']
        LOGGER.info(OD_cordon_travel_time)
        LOGGER.info(type(OD_cordon_travel_time))
        metrics_dict[OD + '_AM', 'Travel Time', grouping3, tm_run_id,METRIC_ID,'extra','By Corridor','travel_time_%s' % OD + '_AM',year] = OD_cordon_travel_time

def Affordable2_ratio_time_cost(tm_run_id):
    # 2) Ratio of value of auto travel time savings to incremental toll costs

    # borrow from pba metrics calculate_Connected2_hwy_traveltimes(), but only for corridor disaggregation (and maybe commercial vs private vehicle. need to investigate income cat further)
    # make sure to run after the comparison functions have been run, as this takes them as inputs from the metrics dict
    # will need to compute a new average across corridors, since we are only interested in the AM period
    metric_id = 'Affordable 2'
    # metric dict input: year
    year = tm_run_id[:4]
    grouping1 = ' '
    grouping2 = ' '
    grouping3 = ' '
    LOGGER.info("Calculating {} for {}".format(metric_id, tm_run_id))
    
    # load scenario loaded network for analysis
    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links.DBF") 
    tm_loaded_network_dbf = simpledbf.Dbf5(loaded_roadway_network)
    tm_loaded_network_df = tm_loaded_network_dbf.to_dataframe()
    tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
    tm_loaded_network_df['a_b'] = tm_loaded_network_df['A'].astype(str) + "_" + tm_loaded_network_df['B'].astype(str)
    
    # merge MINOR_GROUPS_DF
    tm_loaded_network_df = tm_loaded_network_df.merge(MINOR_LINKS_DF, on='a_b', how='left')
    
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df), loaded_roadway_network))
    LOGGER.debug("  Head:\n{}".format(tm_loaded_network_df.head()))

    # load base scenario loaded network for comparison
    base_loaded_roadway_network = os.path.join(NGFS_SCENARIOS, BASE_SCENARIO_RUN_ID, "OUTPUT", "shapefile", "network_links.DBF")
    tm_base_loaded_network_dbf = simpledbf.Dbf5(base_loaded_roadway_network)
    tm_loaded_network_df_base = tm_base_loaded_network_dbf.to_dataframe()
    tm_loaded_network_df_base = tm_loaded_network_df_base.rename(columns=lambda x: x.strip())
    tm_loaded_network_df_base['a_b'] = tm_loaded_network_df_base['A'].astype(str) + "_" + tm_loaded_network_df_base['B'].astype(str)
    
    # merge MINOR_GROUPS_DF
    tm_loaded_network_df_base = tm_loaded_network_df_base.merge(MINOR_LINKS_DF, on='a_b', how='left')
    
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_loaded_network_df_base), base_loaded_roadway_network))
    LOGGER.debug("  Head:\n{}".format(tm_loaded_network_df_base.head()))
    
    network_with_nonzero_tolls = tm_loaded_network_df.copy().loc[(tm_loaded_network_df['TOLLCLASS'] > 1000) | (tm_loaded_network_df['TOLLCLASS'] == 99) |(tm_loaded_network_df['TOLLCLASS'] == 10)|(tm_loaded_network_df['TOLLCLASS'] == 11)|(tm_loaded_network_df['TOLLCLASS'] == 12)]
    network_with_nonzero_tolls = network_with_nonzero_tolls.copy().loc[(network_with_nonzero_tolls['USEAM'] == 1)&(network_with_nonzero_tolls['FT'] != 6)]
    network_with_nonzero_tolls['sum of tolls'] = network_with_nonzero_tolls['TOLLAM_DA'] + network_with_nonzero_tolls['TOLLAM_LRG'] + network_with_nonzero_tolls['TOLLAM_S3']
    # check if run has all lane tolling, if not return 0 for this metric 
    if (network_with_nonzero_tolls['sum of tolls'].sum() == 0):
        metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'final','Private Auto: All Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc1_weighted_by_vmt',year] = 0
        metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'final','Private Auto: Very Low Income Households','average_ratio_auto_time_savings_to_toll_costs_across_corridors_inc2_weighted_by_vmt',year] = 0
        metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'final','Commercial Vehicle','average_ratio_truck_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'final','High Occupancy Vehicle','average_ratio_hov_time_savings_to_toll_costs_across_corridors_weighted_by_vmt',year] = 0
        return
    network_with_nonzero_tolls = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['sum of tolls'] > 1)]
    index_a_b = network_with_nonzero_tolls.copy()[['a_b']]
    network_with_nonzero_tolls_base = tm_loaded_network_df_base.copy().merge(index_a_b, on='a_b', how='right')

    # add in the minor groupings for the cordon (they're not included in the source file, might be able to make it work with function that calls TOLLCLASS_Designations.xlsx)   
    network_with_nonzero_tolls.loc[network_with_nonzero_tolls['TOLLCLASS'] == 10, 'Grouping minor_AMPM' ] = "San Francisco Cordon_AM"
    network_with_nonzero_tolls.loc[network_with_nonzero_tolls['TOLLCLASS'] == 11, 'Grouping minor_AMPM' ] = "Oakland Cordon_AM"
    network_with_nonzero_tolls.loc[network_with_nonzero_tolls['TOLLCLASS'] == 12, 'Grouping minor_AMPM' ] = "San Jose Cordon_AM"
    network_with_nonzero_tolls_base.loc[network_with_nonzero_tolls_base['TOLLCLASS'] == 10, 'Grouping minor_AMPM' ] = "San Francisco Cordon_AM"
    network_with_nonzero_tolls_base.loc[network_with_nonzero_tolls_base['TOLLCLASS'] == 11, 'Grouping minor_AMPM' ] = "Oakland Cordon_AM"
    network_with_nonzero_tolls_base.loc[network_with_nonzero_tolls_base['TOLLCLASS'] == 12, 'Grouping minor_AMPM' ] = "San Jose Cordon_AM"

    LOGGER.debug('network_with_nonzero_tolls (sent to calculate_auto_travel_time()):\n{}'.format(network_with_nonzero_tolls))
    calculate_auto_travel_time(tm_run_id,metric_id, year,network_with_nonzero_tolls,metrics_dict)
    calculate_auto_travel_time(BASE_SCENARIO_RUN_ID,metric_id, year,network_with_nonzero_tolls_base,metrics_dict)
    if 'Path3' in tm_run_id:
        calculate_auto_travel_time_for_pathway3(tm_run_id, 'SF')
        calculate_auto_travel_time_for_pathway3(BASE_SCENARIO_RUN_ID, 'SF')
        calculate_auto_travel_time_for_pathway3(tm_run_id, 'OAK')
        calculate_auto_travel_time_for_pathway3(BASE_SCENARIO_RUN_ID, 'OAK')
        calculate_auto_travel_time_for_pathway3(tm_run_id, 'SJ')
        calculate_auto_travel_time_for_pathway3(BASE_SCENARIO_RUN_ID, 'SJ')
    # ----calculate difference between runs----
    # run comparisons
    calculate_change_between_run_and_base(tm_run_id, BASE_SCENARIO_RUN_ID, year, 'Affordable 2', metrics_dict)

    metrics_dict_series = pd.Series(metrics_dict)
    metrics_dict_df  = metrics_dict_series.to_frame().reset_index()
    LOGGER.debug('metrics_dict_df:\n{}'.format(metrics_dict_df))
    metrics_dict_df.columns = ['Corridor', 'Value Type', 'Income Group/Occupation', 'modelrun_id','metric_id','intermediate/final','Household/Commercial','metric_desc','year','value']
    corridor_vmt_df = metrics_dict_df.copy().loc[(metrics_dict_df['metric_desc'].str.contains('_AM_vmt') == True)&(metrics_dict_df['metric_desc'].str.contains('change') == False)]
    LOGGER.debug('corridor_vmt_df:\n{}'.format(corridor_vmt_df))
    # simplify df to relevant model run
    metrics_dict_df = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_run_id) == True)]
    #make a list of the metrics from the run of interest to iterate through and calculate numerator of ratio with
    if 'Path3' in tm_run_id:
        metrics_dict_df = metrics_dict_df.copy().loc[(metrics_dict_df['metric_desc'].str.contains('Cordon') == True)]
    metrics_list = metrics_dict_df.loc[(metrics_dict_df['metric_desc'].str.startswith('change_in_travel_time_') == True)&(metrics_dict_df['metric_desc'].str.contains('_AM') == True)&(metrics_dict_df['metric_desc'].str.contains('vmt') == False)]['metric_desc'] 
    LOGGER.debug('metrics_list:\n{}'.format(metrics_list))

    # the list of metrics should have the name of the corridor. split on 'change_in_avg' and pick the end part. if empty, will be final ratio, use this for other disaggregations
    # total tolls and time savings variables to be used for average
    # for weighted average
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_truck_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_hov_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc3 = 0
    sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc4 = 0
    sum_of_weighted_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_SALES_WORKERS_time_savings_to_toll_costs = 0
    sum_of_weighted_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs = 0

    # for simple average
    sum_of_ratio_auto_time_savings_to_toll_costs = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc1 = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc2 = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc3 = 0
    sum_of_ratio_auto_time_savings_to_toll_costs_inc4 = 0
    sum_of_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs = 0
    sum_of_ratio_SALES_WORKERS_time_savings_to_toll_costs = 0
    sum_of_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs = 0
    sum_of_ratio_hov_time_savings_to_toll_costs = 0

    sum_of_weights = 0 #sum of weights (length of corridor) to be used for weighted average 
    n = 0 #counter to serve as denominator 
    # iterate through list
    for metric in metrics_list:
        minor_grouping_corridor = metric.split('travel_time_')[1]

        if 'Path3' in tm_run_id: # can not calculate a weighted average for pathway 3 using TAZ level data because it doesn't contain a distance field
            minor_grouping_vmt = 0
        else:
            # calculate average vmt
            minor_grouping_vmt = corridor_vmt_df.loc[corridor_vmt_df['metric_desc'] == (minor_grouping_corridor + '_vmt')].iloc[0]['value']
        # simplify df to relevant metric
        metric_row = metrics_dict_df.loc[(metrics_dict_df['metric_desc'].str.contains(metric) == True)]
        if (minor_grouping_vmt == 0) & ('Path3' not in tm_run_id): #check to make sure there is traffic on the link
            time_savings_minutes = 0
            time_savings_in_hours = 0
        else:
            time_savings_minutes = (metric_row.iloc[0]['value']) * (-1) #make time savings reflected as a positive value when there is a decrease in travel time (and vice versa)
            time_savings_in_hours = time_savings_minutes/60
        # ____will need to restructure this whole section to include all the calculations here 
        # ____as done for denominator because there is a need to filter the df by toll class and tolls paid
        # ____consider including a call to change_in function here. first define the metrics needed

        # define key for grouping field, consistent with section above
        if 'Path3' in tm_run_id:
            key = minor_grouping_corridor
        else:
            key = minor_grouping_corridor.split('_AM')[0]

        priv_auto_travel_time_savings_minor_grouping = time_savings_in_hours * VOT_2023D_PERSONAL
        commercial_vehicle_travel_time_savings_minor_grouping = time_savings_in_hours * VOT_2023D_COMMERCIAL

        # Q1 HH numerator: travel time savings
        q1_household_travel_time_savings_minor_grouping = time_savings_in_hours * Q1_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'extra','Household','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'extra','Household','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'intermediate','Household','Avg hourly wage ($/hr)',year] = Q1_MEDIAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time (% of wage rate)',year] = Q1_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time ($/hr)',year] = Q1_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc1', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time savings',year] = q1_household_travel_time_savings_minor_grouping

        # Q2 HH numerator: travel time savings
        q2_household_travel_time_savings_minor_grouping = time_savings_in_hours * Q2_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'extra','Household','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'extra','Household','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'intermediate','Household','Avg hourly wage ($/hr)',year] = Q2_MEDIAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time (% of wage rate)',year] = Q2_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time ($/hr)',year] = Q2_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc2', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time savings',year] = q2_household_travel_time_savings_minor_grouping

        # Q3 HH numerator: travel time savings
        q3_household_travel_time_savings_minor_grouping = time_savings_in_hours * Q3_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'extra','Household','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'extra','Household','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'intermediate','Household','Avg hourly wage ($/hr)',year] = Q3_MEDIAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time (% of wage rate)',year] = Q3_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time ($/hr)',year] = Q3_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc3', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time savings',year] = q3_household_travel_time_savings_minor_grouping

        # Q4 HH numerator: travel time savings
        q4_household_travel_time_savings_minor_grouping = time_savings_in_hours * Q4_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'extra','Household','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'extra','Household','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'intermediate','Household','Avg hourly wage ($/hr)',year] = Q4_MEDIAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time (% of wage rate)',year] = Q4_HOUSEHOLD_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time ($/hr)',year] = Q4_HOUSEHOLD_VOT_2023D
        metrics_dict[key, 'Travel Time', 'inc4', tm_run_id, metric_id,'intermediate','Household','Monetary Value of travel time savings',year] = q4_household_travel_time_savings_minor_grouping

        # Heavy Truck Operators numerator: travel time savings
        HEAVY_TRUCK_OPERATORS_travel_time_savings_minor_grouping = time_savings_in_hours * HEAVY_TRUCK_OPERATORS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'intermediate','Business/Commercial','Avg hourly wage ($/hr)',year] = HEAVY_TRUCK_OPERATORS_MEAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time (% of wage rate)',year] = HEAVY_TRUCK_OPERATORS_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time ($/hr)',year] = HEAVY_TRUCK_OPERATORS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Heavy Truck Operators', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time savings',year] = HEAVY_TRUCK_OPERATORS_travel_time_savings_minor_grouping

        # Sales Workers numerator: travel time savings
        SALES_WORKERS_travel_time_savings_minor_grouping = time_savings_in_hours * SALES_WORKERS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Avg hourly wage ($/hr)',year] = SALES_WORKERS_MEAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time (% of wage rate)',year] = SALES_WORKERS_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time ($/hr)',year] = SALES_WORKERS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Sales Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time savings',year] = SALES_WORKERS_travel_time_savings_minor_grouping

        # Construction Workers numerator: travel time savings
        CONSTRUCTION_WORKERS_travel_time_savings_minor_grouping = time_savings_in_hours * CONSTRUCTION_WORKERS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (minutes)',year] = time_savings_minutes 
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'extra','Business/Commercial','Travel Time Savings (hours)',year] = time_savings_in_hours
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Avg hourly wage ($/hr)',year] = CONSTRUCTION_WORKERS_MEAN_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time (% of wage rate)',year] = CONSTRUCTION_WORKERS_VOT_PCT_HOURLY_WAGE_2023D
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time ($/hr)',year] = CONSTRUCTION_WORKERS_VOT_2023D
        metrics_dict[key, 'Travel Time', 'Construction Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','Monetary Value of travel time savings',year] = CONSTRUCTION_WORKERS_travel_time_savings_minor_grouping

        # calculate the denominator: incremental toll costs (for PA CV and HOV) 
        # by filtering for the links on the corridor and summing across them
        if 'Path3' in tm_run_id:
            minor_grouping_corridor = minor_grouping_corridor.split('_into_')[-1]
        DA_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_DA'].sum()/100 * INFLATION_00_23
        LRG_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_LRG'].sum()/100 * INFLATION_00_23
        S3_incremental_toll_costs_minor_grouping = network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True), 'TOLLAM_S3'].sum()/100 * INFLATION_00_23
        if 'Path3' in tm_run_id:
            number_of_links = len(network_with_nonzero_tolls.loc[(network_with_nonzero_tolls['Grouping minor_AMPM'].str.contains(minor_grouping_corridor) == True)])
            LOGGER.debug('number_of_links:\n{}'.format(number_of_links))
            DA_incremental_toll_costs_minor_grouping = DA_incremental_toll_costs_minor_grouping / number_of_links
            LRG_incremental_toll_costs_minor_grouping = LRG_incremental_toll_costs_minor_grouping / number_of_links
            S3_incremental_toll_costs_minor_grouping = S3_incremental_toll_costs_minor_grouping / number_of_links
        DA_incremental_toll_costs_inc1_minor_grouping = (DA_incremental_toll_costs_minor_grouping * Q1_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS)
        DA_incremental_toll_costs_inc2_minor_grouping = (DA_incremental_toll_costs_minor_grouping * Q2_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS)
        DA_incremental_toll_costs_inc3_minor_grouping = (DA_incremental_toll_costs_minor_grouping * Q3_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS)
        DA_incremental_toll_costs_inc4_minor_grouping = (DA_incremental_toll_costs_minor_grouping * Q4_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS)
        # assuming no inc quantile discounts for business/commercial drivers
        HEAVY_TRUCK_OPERATORS_incremental_toll_costs_minor_grouping = (LRG_incremental_toll_costs_minor_grouping)
        SALES_WORKERS_incremental_toll_costs_minor_grouping = (LRG_incremental_toll_costs_minor_grouping)
        CONSTRUCTION_WORKERS_incremental_toll_costs_minor_grouping = (LRG_incremental_toll_costs_minor_grouping)

        metrics_dict[key, 'Toll Costs (2023$)', 'inc1', tm_run_id, metric_id,'intermediate','Household','auto_toll_costs',year] = DA_incremental_toll_costs_inc1_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'inc2', tm_run_id, metric_id,'intermediate','Household','auto_toll_costs',year] = DA_incremental_toll_costs_inc2_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'inc3', tm_run_id, metric_id,'intermediate','Household','auto_toll_costs',year] = DA_incremental_toll_costs_inc3_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'inc4', tm_run_id, metric_id,'intermediate','Household','auto_toll_costs',year] = DA_incremental_toll_costs_inc4_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'Heavy Truck Operators', tm_run_id, metric_id,'intermediate','Business/Commercial','truck_toll_costs',year] = HEAVY_TRUCK_OPERATORS_incremental_toll_costs_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'Sales Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','truck_toll_costs',year] = SALES_WORKERS_incremental_toll_costs_minor_grouping
        metrics_dict[key, 'Toll Costs (2023$)', 'Construction Workers', tm_run_id, metric_id,'intermediate','Business/Commercial','truck_toll_costs',year] = CONSTRUCTION_WORKERS_incremental_toll_costs_minor_grouping

        metrics_dict[key, 'Toll Costs (2023$)', 'hov', tm_run_id, metric_id,'debug step','Household','hov_toll_costs',year] = S3_incremental_toll_costs_minor_grouping

        if (DA_incremental_toll_costs_minor_grouping == 0):
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc3 = 0
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc4 = 0

            HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping = 0
            SALES_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping = 0
            CONSTRUCTION_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping = 0
            hov_ratio_time_savings_to_toll_costs_minor_grouping = 0
        else:
            # calculate ratios for overall + inc groups and enter into metrics dict 
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping = priv_auto_travel_time_savings_minor_grouping/DA_incremental_toll_costs_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 = q1_household_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc1_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 = q2_household_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc2_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc3 = q3_household_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc3_minor_grouping
            priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc4 = q4_household_travel_time_savings_minor_grouping/DA_incremental_toll_costs_inc4_minor_grouping

            HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping = HEAVY_TRUCK_OPERATORS_travel_time_savings_minor_grouping/HEAVY_TRUCK_OPERATORS_incremental_toll_costs_minor_grouping
            SALES_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping = SALES_WORKERS_travel_time_savings_minor_grouping/SALES_WORKERS_incremental_toll_costs_minor_grouping
            CONSTRUCTION_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping = CONSTRUCTION_WORKERS_travel_time_savings_minor_grouping/CONSTRUCTION_WORKERS_incremental_toll_costs_minor_grouping

            hov_ratio_time_savings_to_toll_costs_minor_grouping = priv_auto_travel_time_savings_minor_grouping/S3_incremental_toll_costs_minor_grouping

        if S3_incremental_toll_costs_minor_grouping == 0: #make the ratio 0 if there is no cost to drive
            hov_ratio_time_savings_to_toll_costs_minor_grouping = 0
 

        metrics_dict[key, 'Ratio', 'inc1', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1
        metrics_dict[key, 'Ratio', 'inc2', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2
        metrics_dict[key, 'Ratio', 'inc3', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc3
        metrics_dict[key, 'Ratio', 'inc4', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc4

        metrics_dict[key, 'Ratio', 'Heavy Truck Operators', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping
        metrics_dict[key, 'Ratio', 'Sales Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = SALES_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping
        metrics_dict[key, 'Ratio', 'Construction Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = CONSTRUCTION_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping
        
        # add in metric as $ per minute saved
        metrics_dict[key, 'Ratio', 'inc1', tm_run_id, metric_id,'final','Household','Ratio of toll$ (2023$) to minutes saved',year] = DA_incremental_toll_costs_inc1_minor_grouping / time_savings_minutes
        metrics_dict[key, 'Ratio', 'inc2', tm_run_id, metric_id,'final','Household','Ratio of toll$ (2023$) to minutes saved',year] = DA_incremental_toll_costs_inc2_minor_grouping / time_savings_minutes
        metrics_dict[key, 'Ratio', 'inc3', tm_run_id, metric_id,'final','Household','Ratio of toll$ (2023$) to minutes saved',year] = DA_incremental_toll_costs_inc3_minor_grouping / time_savings_minutes
        metrics_dict[key, 'Ratio', 'inc4', tm_run_id, metric_id,'final','Household','Ratio of toll$ (2023$) to minutes saved',year] = DA_incremental_toll_costs_inc4_minor_grouping / time_savings_minutes

        metrics_dict[key, 'Ratio', 'Heavy Truck Operators', tm_run_id, metric_id,'final','Business/Commercial','Ratio of toll$ (2023$) to minutes saved',year] = HEAVY_TRUCK_OPERATORS_incremental_toll_costs_minor_grouping / time_savings_minutes
        metrics_dict[key, 'Ratio', 'Sales Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of toll$ (2023$) to minutes saved',year] = SALES_WORKERS_incremental_toll_costs_minor_grouping / time_savings_minutes
        metrics_dict[key, 'Ratio', 'Construction Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of toll$ (2023$) to minutes saved',year] = CONSTRUCTION_WORKERS_incremental_toll_costs_minor_grouping / time_savings_minutes


        metrics_dict[key, 'Ratio', grouping3, tm_run_id, metric_id,'final','By Corridor','commercial vehicle',year] = HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping

        # ----sum up the ratio of tolls and time savings across the corridors for weighted average

        # ----calculate average vmt, multiply time savings by it?

        sum_of_weighted_ratio_auto_time_savings_to_toll_costs = sum_of_weighted_ratio_auto_time_savings_to_toll_costs + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_truck_time_savings_to_toll_costs = sum_of_weighted_ratio_truck_time_savings_to_toll_costs + HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_hov_time_savings_to_toll_costs = sum_of_weighted_ratio_hov_time_savings_to_toll_costs + hov_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1 * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2 * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc3 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc3 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc3 * minor_grouping_vmt
        sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc4 = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc4 + priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc4 * minor_grouping_vmt
        sum_of_weighted_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs = sum_of_weighted_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs + HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_SALES_WORKERS_time_savings_to_toll_costs = sum_of_weighted_ratio_SALES_WORKERS_time_savings_to_toll_costs + SALES_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt
        sum_of_weighted_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs = sum_of_weighted_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs + CONSTRUCTION_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping * minor_grouping_vmt

        sum_of_ratio_auto_time_savings_to_toll_costs += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_auto_time_savings_to_toll_costs_inc1 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc1
        sum_of_ratio_auto_time_savings_to_toll_costs_inc2 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc2
        sum_of_ratio_auto_time_savings_to_toll_costs_inc3 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc3
        sum_of_ratio_auto_time_savings_to_toll_costs_inc4 += priv_auto_ratio_time_savings_to_toll_costs_minor_grouping_inc4
        sum_of_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs += HEAVY_TRUCK_OPERATORS_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_SALES_WORKERS_time_savings_to_toll_costs += SALES_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs += CONSTRUCTION_WORKERS_ratio_time_savings_to_toll_costs_minor_grouping
        sum_of_ratio_hov_time_savings_to_toll_costs += hov_ratio_time_savings_to_toll_costs_minor_grouping

        #----sum of weights (vmt of corridor) to be used for weighted average
        sum_of_weights = sum_of_weights + minor_grouping_vmt
        # for corrdior simple average calc
        n = n+1

    # ----commented out to clear clutter. use for debugging
    # metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs
    # metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_inc1_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1
    # metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'intermediate','Private Auto','sum_of_ratio_auto_time_savings_to_toll_costs_inc2_weighted_by_vmt',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2
    # metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'intermediate','Commercial Vehicle','sum_of_ratio_truck_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_truck_time_savings_to_toll_costs
    # metrics_dict[grouping1, grouping2, grouping3, tm_run_id, metric_id,'intermediate','High Occupancy Vehicle','sum_of_ratio_hov_time_savings_to_toll_costs_weighted_by_vmt',year] = sum_of_weighted_ratio_hov_time_savings_to_toll_costs

    # weighted averages
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'inc1', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc1/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'inc2', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc2/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'inc3', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc3/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'inc4', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_auto_time_savings_to_toll_costs_inc4/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'Heavy Truck Operators', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'Sales Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_SALES_WORKERS_time_savings_to_toll_costs/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', 'Construction Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs/sum_of_weights
    metrics_dict['Weighted Average Across Tolled Corridors', 'Ratio', grouping3, tm_run_id, metric_id,'debug step','High Occupancy Vehicle','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_weighted_ratio_hov_time_savings_to_toll_costs/sum_of_weights

    # simple averages
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'inc1', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc1/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'inc2', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc2/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'inc3', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc3/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'inc4', tm_run_id, metric_id,'final','Household','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_auto_time_savings_to_toll_costs_inc4/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'Heavy Truck Operators', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_HEAVY_TRUCK_OPERATORS_time_savings_to_toll_costs/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'Sales Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_SALES_WORKERS_time_savings_to_toll_costs/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', 'Construction Workers', tm_run_id, metric_id,'final','Business/Commercial','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_CONSTRUCTION_WORKERS_time_savings_to_toll_costs/n
    metrics_dict['Simple Average Across Tolled Corridors', 'Ratio', grouping3, tm_run_id, metric_id,'debug step','High Occupancy Vehicle','Ratio of Monetary value of travel time savings to toll costs',year] = sum_of_ratio_hov_time_savings_to_toll_costs/n

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

    # find the last pathway 1 run, since we'll use that to determine which links are in the fwy minor groupings
    pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("Pathway 1")]
    PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
    LOGGER.info("=> PATHWAY1_SCENARIO_RUN_ID = {}".format(PATHWAY1_SCENARIO_RUN_ID))
    TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")
    # TOLLED_FWY_MINOR_GROUP_LINKS_DF.to_csv("TOLLED_FWY_MINOR_GROUP_LINKS.csv", index=False)
    
    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Affordable2_ratio_time_cost_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))
        
        # manually calculated sums for discounts, credits, and rebates
        # adjust later
        # TODO: What are these?
        if ('1b' in tm_run_id) | ('2b' in tm_run_id) | ('3b' in tm_run_id): #how to include discounts for persons with disabilities?
          Q1_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0.5
          Q2_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0
          Q3_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0
          Q4_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0

        else:
          Q1_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0
          Q2_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0
          Q3_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0
          Q4_TOLL_DISCOUNTS_HIGHWAYS_ARTERIALS = 1 - 0

        # results will be stored here
        # key=grouping1, grouping2, grouping3, tm_run_id, metric_id, top_level|extra|intermediate|final, key, metric_desc, year
        # TODO: convert to pandas.DataFrame with these column headings.  It's far more straightforward.
        metrics_dict = {}
        metrics_df = pd.DataFrame()

        Affordable2_ratio_time_cost(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ A2 Done")
        
        # _________output table__________
        # TODO: deprecate when all metrics just come through via metrics_df
        metrics_df = pd.concat([metrics_df, metrics_dict_to_df(metrics_dict)])

        metrics_df.loc[(metrics_df['modelrun_id'] == tm_run_id)].to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()