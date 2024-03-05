USAGE = """

  python Efficient2_commute_mode_share.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Efficient2_commute_mode_share_XX.csv
  
  This file will have the following columns:
    'Freeway/Non-Freeway',
    'EPC/Non-EPC',
    'Tolled/Non-tolled Facilities',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final', 
    'Facility Type Definition',
    'Metric Description',
    'County',
    'value'
    
  Metrics are:
    1) Efficient 2: Transit, walk, bike and telecommute mode share of commute *tours*

"""

import os
import pandas as pd
import argparse
import logging
import numpy

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Efficient2_commute_mode_share.log" # in the cwd
LOGGER                  = None # will initialize in main     

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050
NGFS_EPC_TAZ_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_epc_crosswalk.csv")
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

# travel model tour and trip modes
# https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes
MODES_TRANSIT      = [9,10,11,12,13,14,15,16,17,18]
MODES_TAXI_TNC     = [19,20,21]
MODES_SOV          = [1,2]
MODES_HOV          = [3,4,5,6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV
MODES_WALK         = [7]
MODES_BIKE         = [8]

# travel model tour purpose
# https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour
PURPOSES_COMMUTE = ['work_low','work_med','work_high','work_very high']

# travel model time periods
# https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
TIME_PERIODS_PEAK    = ['AM','PM']

def trips_commute_mode_pkop(tm_run_id, metric_id):
    ################################### trips by peak/off-peak, commute/noncommute, auto/transit ###################################
    # key                       intermediate/final    metric_desc
    # [commute]_[mode]_[pkop]   top_level/E2b             trips
    # [commute]_[mode]_[pkop]   top_level/E2b             trips
    metrics_df = pd.DataFrame()
    trip_distance_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "TripDistance.csv")
    tm_trips_df = pd.read_csv(trip_distance_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_trips_df), trip_distance_file))
    LOGGER.debug("tm_trips_df.head():\n{}".format(tm_trips_df.head()))

    # simplify to auto versus transit versus active
    tm_trips_df['agg_trip_mode'] = 'active'
    tm_trips_df.loc[ tm_trips_df.trip_mode.isin(MODES_TRANSIT),      'agg_trip_mode' ] = 'transit'
    tm_trips_df.loc[ tm_trips_df.trip_mode.isin(MODES_PRIVATE_AUTO), 'agg_trip_mode' ] = 'auto'
    tm_trips_df.loc[ tm_trips_df.trip_mode.isin(MODES_TAXI_TNC),     'agg_trip_mode' ] = 'other'

    # simplify to commute versus noncommute
    tm_trips_df['commute_non'] = 'noncommute'
    tm_trips_df.loc[ tm_trips_df.tour_purpose.isin(PURPOSES_COMMUTE), 'commute_non' ] = 'commute'

    # simplify to peak versus nonpeak
    tm_trips_df['peak_non'] = 'offpeak'
    tm_trips_df.loc[ tm_trips_df.timeCode.isin(TIME_PERIODS_PEAK), 'peak_non' ] = 'peak'

    # roll it up
    tm_trips_df = tm_trips_df.groupby(by=['agg_trip_mode', 'commute_non', 'peak_non']).agg({'freq':'sum'}).reset_index()
    tm_trips_df.rename(columns={'freq':'trips'}, inplace=True)
    LOGGER.debug('Aggregated tm_trips_df:\n{}'.format(tm_trips_df))

    # metrics: total trips
    metrics_trip_df = tm_trips_df.copy()
    metrics_trip_df['intermediate/final'] = metric_id
    metrics_trip_df['metric_desc'] = 'trips'
    metrics_trip_df.rename(columns={'trips':'value', 'agg_trip_mode':'commute mode'}, inplace=True)
    LOGGER.debug('metrics_trip_df:\n{}'.format(metrics_trip_df))
    metrics_df = pd.concat([metrics_df, metrics_trip_df])

    metrics_df['shares'] = metrics_df['value'] / metrics_df.loc[:,'value'].sum()

    return metrics_df

def calculate_Efficient2_commute_mode_share(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Efficient 2: Transit, walk, bike and telecommute mode share of commute *tours*

    Args:
        tm_run_id (str): Travel model run ID

    Returns:
        pandas.DataFrame: Dataframe with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Efficient 2'
          modelrun_id = tm_run_id
        Metrics returned:
          key             intermediate/final  metric_desc
          [commute mode]  intermediate        commute_tours
          [commute mode]  final               commute_tours_share

        where commute mode is one of:
         SOV, HOV, transit, walk, bike, telecommute, taxi/TNC
    """
    # from model-files\scripts\preprocess\updateTelecommuteConstants.py
    # see EN7 Telecommuting.xlsx (https://mtcdrive.box.com/s/uw3n8wyervle6r2cgoz1j6k4i5lmv253)
    # for 2015 and before
    P_notworking_if_noworktour_FT = 0.560554289
    P_notworking_if_noworktour_PT = 0.553307383
    # future
    P_notworking_FT = 0.107904288
    P_notworking_PT = 0.205942146

    METRIC_ID = 'Efficient 2'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    journey_to_work_modes_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "JourneyToWork_modes.csv")
    tm_journey_to_work_df = pd.read_csv(journey_to_work_modes_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_journey_to_work_df), journey_to_work_modes_file))
    LOGGER.debug("tm_journey_to_work_df.head() =\n{}".format(tm_journey_to_work_df.head()))

    # create aggregate mode
    tm_journey_to_work_df['commute mode'] = 'Unknown'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_SOV),      'commute mode'] = 'SOV'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_HOV),      'commute mode'] = 'HOV'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_TRANSIT),  'commute mode'] = 'transit'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_TAXI_TNC), 'commute mode'] = 'taxi/TNC'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_WALK),     'commute mode'] = 'walk'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode.isin(MODES_BIKE),     'commute mode'] = 'bike'
    tm_journey_to_work_df.loc[ tm_journey_to_work_df.tour_mode == 0,                 'commute mode'] = 'did not go to work'

    # aggregate to person types and move person types to columns
    tm_journey_to_work_df = tm_journey_to_work_df.groupby(['ptype_label', 'commute mode']).agg(
        {"freq": "sum"}).reset_index()
    tm_journey_to_work_df = tm_journey_to_work_df.pivot(index=['commute mode'],
                                                        columns=['ptype_label'])
    # reset multiindex columns to just a single level, ptype_label
    tm_journey_to_work_df.columns = tm_journey_to_work_df.columns.get_level_values(1)
    # reorder to match tableau convention
    tm_journey_to_work_df = tm_journey_to_work_df[[
        'Full-time worker',
        'Part-time worker',
        'College student',
        'Driving-age student']]
    # add row for total workers
    tm_journey_to_work_df.loc['all_modes incl time off'] = tm_journey_to_work_df.sum(axis=0)

    # add row for telecommute, not-working, start with 0 for the four person types
    LOGGER.debug("tm_journey_to_work_df:\n{}".format(tm_journey_to_work_df))
    tm_journey_to_work_df.loc['telecommute'] = [0,0,0,0]
    tm_journey_to_work_df.loc['time off'] = [0,0,0,0]

    # calculate non-workers consistently with model-files\scripts\preprocess\updateTelecommuteConstants.py
    model_year = int(tm_run_id[:4])
    # note: Full-time worker and Part-time worker columns will be float now
    if model_year <= 2020:
        tm_journey_to_work_df.at['time off', 'Full-time worker'] = P_notworking_if_noworktour_FT*tm_journey_to_work_df.at['did not go to work', 'Full-time worker']
        tm_journey_to_work_df.at['time off', 'Part-time worker'] = P_notworking_if_noworktour_PT*tm_journey_to_work_df.at['did not go to work', 'Part-time worker']
    else:
        tm_journey_to_work_df.at['time off', 'Full-time worker'] = P_notworking_FT*tm_journey_to_work_df.at['all_modes incl time off', 'Full-time worker']
        tm_journey_to_work_df.at['time off', 'Part-time worker'] = P_notworking_PT*tm_journey_to_work_df.at['all_modes incl time off', 'Part-time worker']
    # assume no telecommute for driving-age students and college students
    tm_journey_to_work_df.at['time off', 'Driving-age student'] = tm_journey_to_work_df.at['did not go to work' , 'Driving-age student']
    tm_journey_to_work_df.at['time off', 'College student']     = tm_journey_to_work_df.at['did not go to work' , 'College student']
    # subtract for telecommute
    tm_journey_to_work_df.loc['telecommute'] = tm_journey_to_work_df.loc['did not go to work'] - tm_journey_to_work_df.loc['time off']

    # create all_modes excl time off
    tm_journey_to_work_df.loc['all_modes excl time off'] = tm_journey_to_work_df.loc['all_modes incl time off'] - tm_journey_to_work_df.loc['time off']

    # add column for all person types
    tm_journey_to_work_df['All workers'] = tm_journey_to_work_df.sum(axis=1)
    LOGGER.debug("tm_journey_to_work_df:\n{}".format(tm_journey_to_work_df))
    LOGGER.debug(tm_journey_to_work_df.columns)
    LOGGER.debug(tm_journey_to_work_df.index)
    # drop did not go to work since it's covered by telecommute + time off
    tm_journey_to_work_df = tm_journey_to_work_df.loc[ tm_journey_to_work_df.index != 'did not go to work']
    # drop time off and all modes incl time off since the mode share won't include those
    tm_journey_to_work_df = tm_journey_to_work_df.loc[ tm_journey_to_work_df.index != 'time off']
    tm_journey_to_work_df = tm_journey_to_work_df.loc[ tm_journey_to_work_df.index != 'all_modes incl time off']

    # convert to shares
    tm_journey_to_work_shares_df = tm_journey_to_work_df/tm_journey_to_work_df.loc['all_modes excl time off']
    LOGGER.debug("tm_journey_to_work_shares_df:\n{}".format(tm_journey_to_work_shares_df))

    # reformat to metrics
    # we only care about the All Workers column
    tm_journey_to_work_df = tm_journey_to_work_df[['All workers']].reset_index(drop=False)
    tm_journey_to_work_df['metric_desc'] = 'commute tours'
    tm_journey_to_work_df.rename(columns={'All workers':'value'}, inplace=True)
    # LOGGER.debug("tm_journey_to_work_df:\n{}".format(tm_journey_to_work_df))
    # columns: commute mode, All workers, intermediate/final, metric_desc

    tm_journey_to_work_shares_df = tm_journey_to_work_shares_df[['All workers']].reset_index(drop=False)
    tm_journey_to_work_shares_df['metric_desc'] = 'commute_tours_share'
    tm_journey_to_work_shares_df.rename(columns={'All workers':'shares'}, inplace=True)
    # LOGGER.debug("tm_journey_to_work_shares_df:\n{}".format(tm_journey_to_work_shares_df))
    # columns: commute mode, All workers, intermediate/final, metric_desc
    
    tm_journey_to_work_df['shares'] = tm_journey_to_work_shares_df['shares']
    tm_journey_to_work_df['commute_non'] = 'commute'

    metrics_df = tm_journey_to_work_df
    # metrics_df.rename(columns={'All workers':'value', 'commute mode':'key'}, inplace=True)
    # add 2b metric for modeshare by trips for non commute trips
    metrics_df = pd.concat([metrics_df, trips_commute_mode_pkop(tm_run_id, 'Efficient 2b')])
    metrics_df['Model Run ID'] = tm_run_id
    metrics_df['Metric ID'] = METRIC_ID
    metrics_df['Year'] = tm_run_id[:4]
    metrics_df.columns.name = None # it was named ptype_label
    LOGGER.debug("metrics_df:\n{}".format(metrics_df))
    return metrics_df

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

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Efficient2_commute_mode_share_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Efficient2_commute_mode_share(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ E2 Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()