USAGE = """
  Asana task: https://app.asana.com/0/0/1204911549136921/f
"""
import os, sys
import pandas as pd
import numpy

# to read trips.rdata
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

import ngfs_metrics
print(ngfs_metrics.NGFS_OD_CITIES_OF_INTEREST_DF)

# https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes
# https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims
TRIP_MODE_TO_SIMPLE_SKIM_MODE = [
    # trip_mode, inbound, simple_skim_mode
    [1,  0, 'da'],          [1,  1, 'da'],
    [2,  0, 'daToll'],      [2,  1, 'daToll'],
    [3,  0, 's2'],          [3,  1, 's2'],
    [4,  0, 's2Toll'],      [4,  1, 's2Toll'],
    [5,  0, 's3'],          [5,  1, 's3'],
    [6,  0, 's3Toll'],      [6,  1, 's3Toll'],
    [9,  0, 'wTrnW'],       [9,  1, 'wTrnW'],  # walk to local bus
    [10, 0, 'wTrnW'],       [10, 1, 'wTrnW'],  # walk to lrt/ferry
    [11, 0, 'wTrnW'],       [11, 1, 'wTrnW'],  # walk to express bus
    [12, 0, 'wTrnW'],       [12, 1, 'wTrnW'],  # walk to heavy rail
    [13, 0, 'wTrnW'],       [13, 1, 'wTrnW'],  # walk to commuter rail
    [14, 0, 'dTrnW'],       [14, 1, 'wTrnD'],  # drive to local bus
    [15, 0, 'dTrnW'],       [15, 1, 'wTrnD'],  # drive to lrt/ferry
    [16, 0, 'dTrnW'],       [16, 1, 'wTrnD'],  # drive to express bus
    [17, 0, 'dTrnW'],       [17, 1, 'wTrnD'],  # drive to heavy rail
    [18, 0, 'dTrnW'],       [18, 1, 'wTrnD'],  # drive to commuter rail
]
TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF = pd.DataFrame(data=TRIP_MODE_TO_SIMPLE_SKIM_MODE, 
                                                columns=['trip_mode','inbound','simple_skim_mode'])
SIMPLE_SKIM_MODES = list(set(TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF.simple_skim_mode.tolist()))

# Step 1: calculate weight
# read mode runs
current_runs_df = pd.read_excel(
    ngfs_metrics.NGFS_MODEL_RUNS_FILE, 
    sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])

current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']

run_list = current_runs_df['directory'].to_list()
run_list.remove('2015_TM152_NGF_05')
run_list.remove('2035_TM152_FBP_Plus_24')
run_list.remove('2035_TM152_NGF_NP10')
run_list.remove('2035_TM152_NGF_NP10_Path2a_02')
run_list.remove('2035_TM152_NGF_NP10_Path2b_02')

# we need to read the trips directly because ODTravelTime_byModeTimeperiodIncome.csv does not distinguish between 
# inbound vs outbound for transit, so we can't distinguish between drive-transit-walk vs walk-transit-drive modes

# read trips.rdata from all run
trips_od_travel_time_df = pd.DataFrame()
robjects.r('library(dplyr)')
for runid in run_list:
    TRIPS_path = os.path.join(ngfs_metrics.NGFS_SCENARIOS, runid, 
        'OUTPUT', 'updated_output', 'trips.rdata')
    print("Reading {}".format(TRIPS_path))

    # read the trips.rdata - this is slow and memory-intensive. Uses up to 7.5GB RAM.
    robjects.r['load'](TRIPS_path)
    robjects.r('''
               trips <- select(trips, orig_taz, dest_taz, trip_mode, inbound, sampleRate, time, timeperiod_label)
               trips <- filter(trips, timeperiod_label=="AM Peak")
               ''')
    r_df = robjects.r['trips']
    # convert to pandas dataframe
    with (robjects.default_converter + pandas2ri.converter).context():
        trips_for_this_run_df = robjects.conversion.get_conversion().rpy2py(r_df)
    # delete R object
    robjects.r('remove(trips)')

    print("Read {:,} AM lines from {}".format(len(trips_for_this_run_df), TRIPS_path))
    print(trips_for_this_run_df.head())
    # print(trips_for_this_run_df.trip_mode.value_counts())

    # keep open MODES_PRIVATE_AUTO and MODES_TRANSIT
    trips_for_this_run_df = trips_for_this_run_df.loc[ 
        trips_for_this_run_df.trip_mode.isin(ngfs_metrics.MODES_PRIVATE_AUTO) |
        trips_for_this_run_df.trip_mode.isin(ngfs_metrics.MODES_TRANSIT) ]

    # pivot to orig,dest,trip_mode,inbound
    trips_for_this_run_df['num_trips'] = 1.0/trips_for_this_run_df['sampleRate']
    trips_for_this_run_df = pd.pivot_table(
        trips_for_this_run_df,
        index=['orig_taz','dest_taz','trip_mode','inbound'],
        values=['num_trips','time'],
        aggfunc={'num_trips':numpy.sum, 'time':numpy.sum}
    ).reset_index()
    trips_for_this_run_df.rename(columns={'num_trips':'num_trips', 'time':'total_trip_travel_time'}, inplace=True)
    print(trips_for_this_run_df.head())

    # note the runid
    trips_for_this_run_df["runid"] = runid
    # add to transit_assignment_df
    trips_od_travel_time_df = pd.concat([trips_od_travel_time_df, trips_for_this_run_df])

# merge with cities and only keep those ODs we need
trips_od_travel_time_df = pd.merge(
    left    = trips_od_travel_time_df,
    right   = ngfs_metrics.NGFS_OD_CITIES_DF.rename(columns={"taz1454":"orig_taz"}), 
    on      = ['orig_taz'],
    how     = 'left')
trips_od_travel_time_df.rename(columns={"CITY": "orig_CITY"}, inplace=True)

trips_od_travel_time_df = pd.merge(
    left    = trips_od_travel_time_df, 
    right   = ngfs_metrics.NGFS_OD_CITIES_DF.rename(columns={"taz1454":"dest_taz"}), 
    on      = 'dest_taz',
    how     = 'left')
trips_od_travel_time_df.rename(columns={"CITY": "dest_CITY"}, inplace=True)

trips_od_travel_time_df = pd.merge(
    left     = trips_od_travel_time_df,
    right    = ngfs_metrics.NGFS_OD_CITIES_OF_INTEREST_DF,
    how      = 'left',
    indicator= True
)
print(trips_od_travel_time_df['_merge'].value_counts())
trips_od_travel_time_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df._merge == 'both']
trips_od_travel_time_df.drop(columns=['_merge'], inplace=True)
print("Filtered to OD cities of interest, or {:,} rows; head:\n{}".format(
    len(trips_od_travel_time_df), trips_od_travel_time_df.head()))
# columns: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, runid, total_trip_travel_time, num_trips


# trips weights: max(num of trips across all pathways)
# https://app.asana.com/0/0/1204911549136921/1205043669589139/f
all_ODs_trip_times_df = pd.pivot_table(
    trips_od_travel_time_df,
    index=['orig_taz','orig_CITY','dest_taz','dest_CITY','trip_mode','inbound'],
    values=['num_trips'],
    aggfunc={'num_trips':numpy.nanmax})
all_ODs_trip_times_df.rename(columns={'num_trips':'max_num_trips'}, inplace=True)
all_ODs_trip_times_df.reset_index(inplace=True)

# join with TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF
all_ODs_trip_times_df = pd.merge(
    left        = all_ODs_trip_times_df,
    right       = TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF,
    on          = ['trip_mode','inbound'],
    how         = 'left',
    indicator   = True
)
# verify join is completely successful
assert(len(all_ODs_trip_times_df.loc[ all_ODs_trip_times_df._merge=='both']) == len(all_ODs_trip_times_df))
all_ODs_trip_times_df.drop(columns=['_merge'], inplace=True)
# columns: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, simple_skim_mode, max_num_trips
print("max trips across pathways head:\n{}".format(all_ODs_trip_times_df.head()))

# Step 2: join trips with skim time
TimeSkimsDatabaseAM_df = pd.DataFrame()
for runid in run_list:
    print("Adding skim information for runid {}".format(runid))
    
    TimeSkimsDatabaseAM_path = os.path.join(ngfs_metrics.NGFS_SCENARIOS, runid, 'OUTPUT', 'skimDB', 'TimeSkimsDatabaseAM.csv')
    # from https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims:
    # If travel between two points by the mode in question is not possible (or highly unlikely, 
    # e.g. a transit trip that would take 5 hours), the skim data contains a value of -999. 
    NA_SKIM_VAL = -999
    NA_VALS = {key: [NA_SKIM_VAL] for key in SIMPLE_SKIM_MODES}
    TimeSkimsDatabaseAM = pd.read_csv(TimeSkimsDatabaseAM_path,
                                      usecols=['orig','dest'] + SIMPLE_SKIM_MODES, 
                                      na_values=NA_VALS)
    
    # join to our max trip ODs
    all_ODs_trip_times_df = pd.merge(
        left     =all_ODs_trip_times_df,
        right    =TimeSkimsDatabaseAM.rename(columns={'orig':'orig_taz', 'dest':'dest_taz'}),
        on       =['orig_taz','dest_taz'],
        how      ='left',
        indicator=True
    )
    # verify join is completely successful
    assert(len(all_ODs_trip_times_df.loc[ all_ODs_trip_times_df._merge=='both']) == len(all_ODs_trip_times_df))
    all_ODs_trip_times_df.drop(columns=['_merge'], inplace=True)
    print(all_ODs_trip_times_df.head())

    # select travel time for the trip_mode's associated simple skim mode and save into column run_id
    all_ODs_trip_times_df[runid] = -999.0
    for simple_skim_mode in SIMPLE_SKIM_MODES:
        all_ODs_trip_times_df.loc[all_ODs_trip_times_df.simple_skim_mode == simple_skim_mode, runid] = \
            all_ODs_trip_times_df[simple_skim_mode]
    print(all_ODs_trip_times_df.head())

    unset_rows = all_ODs_trip_times_df.loc[ all_ODs_trip_times_df[runid] < 0]
    NA_rows    = all_ODs_trip_times_df.loc[ pd.isna(all_ODs_trip_times_df[runid]) ]
    print("unset_rows: {:,}\n{}".format(len(unset_rows), unset_rows))
    print("NA_rows:    {:,}\n{}".format(len(NA_rows), NA_rows))
    assert(len(NA_rows)==0)

    # drop skims columns
    all_ODs_trip_times_df.drop(columns=SIMPLE_SKIM_MODES, inplace=True)

for runid in run_list:
    # columns are: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, max_num_trips, [runid1], [runid2], ...
    # convert [runid] to total travel time : max_num_trips x travel time
    all_ODs_trip_times_df[runid] = all_ODs_trip_times_df[runid]*all_ODs_trip_times_df.max_num_trips

# convert to long - move runid to a single column
all_ODs_trip_times_df = all_ODs_trip_times_df.melt(
    id_vars=['orig_taz','orig_CITY','dest_taz','dest_CITY','trip_mode','inbound','max_num_trips'],
    value_vars = run_list,
    var_name='runid',
    value_name='total_skim_travel_time')
print("all_ODs_trip_times_df long:\n{}".format(all_ODs_trip_times_df))

# and add back in original num_trips and avg_travel_time_in_mins from trips
all_ODs_trip_times_df = pd.merge(
    left    = all_ODs_trip_times_df,
    right   = trips_od_travel_time_df,
    on      = ['runid','orig_taz','orig_CITY','dest_taz','dest_CITY','trip_mode','inbound'],
    how     = 'left'
)
print("after joining with trip columns:\n{}".format(all_ODs_trip_times_df.head()))

# aggregate trip_mode
all_ODs_trip_times_df['agg_trip_mode'] = 'unset'
all_ODs_trip_times_df.loc[ all_ODs_trip_times_df.trip_mode.isin(ngfs_metrics.MODES_PRIVATE_AUTO), 'agg_trip_mode'] = 'auto'
all_ODs_trip_times_df.loc[ all_ODs_trip_times_df.trip_mode.isin(ngfs_metrics.MODES_TRANSIT),      'agg_trip_mode'] = 'transit'
assert(len(all_ODs_trip_times_df.loc[ all_ODs_trip_times_df.agg_trip_mode =='unset'])==0)
print(all_ODs_trip_times_df.head())

# for understanding NaNs
# max_num_trips_for_NaN_num_trips = trips that would have been dropped
# so num_trips, total_trip_travel_time are missing
all_ODs_trip_times_df['max_num_trips_for_NaN_num_trips'] = 0
all_ODs_trip_times_df.loc[ pd.isna(all_ODs_trip_times_df.num_trips), 'max_num_trips_for_NaN_num_trips'] = \
    all_ODs_trip_times_df['max_num_trips']
all_ODs_trip_times_df['max_num_trips_for_NaN_skim_time'] = 0
all_ODs_trip_times_df.loc[ pd.isna(all_ODs_trip_times_df.total_skim_travel_time), 'max_num_trips_for_NaN_skim_time'] = \
    all_ODs_trip_times_df['max_num_trips']

# summarize to orig_CITY, dest_CITY, mode
OD_city_df = all_ODs_trip_times_df.groupby(
    by = ['orig_CITY','dest_CITY', 'runid', 'agg_trip_mode']
).agg(
    max_num_trips    = pd.NamedAgg(column="max_num_trips",          aggfunc="sum"),
    skim_travel_time = pd.NamedAgg(column="total_skim_travel_time", aggfunc="sum"),
    run_num_trips    = pd.NamedAgg(column="num_trips",              aggfunc=numpy.nansum),
    trip_travel_time = pd.NamedAgg(column="total_trip_travel_time", aggfunc=numpy.nansum),
    # checks
    max_num_trips_for_NaN_num_trips = pd.NamedAgg(column="max_num_trips_for_NaN_num_trips", aggfunc="sum"),
    max_num_trips_for_NaN_skim_time = pd.NamedAgg(column="max_num_trips_for_NaN_skim_time", aggfunc="sum"),

).reset_index(drop=False)
OD_city_df['avg_skim_travel_time'] = OD_city_df['skim_travel_time']/OD_city_df['max_num_trips']
OD_city_df['avg_trip_travel_time'] = OD_city_df['trip_travel_time']/OD_city_df['run_num_trips']
print(OD_city_df.head())

OUTPUT_FILE = "OD_city_travel_times_E1.csv"
OD_city_df.to_csv(OUTPUT_FILE, index=False)
print("Wrote {:,} rows to {}".format(len(OD_city_df), OUTPUT_FILE))
