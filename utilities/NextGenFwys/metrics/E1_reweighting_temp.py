USAGE = """
  Calculates auto vs transit travel times between OD cities for the NGFS pathways.

  Asana task: https://app.asana.com/0/0/1204911549136921/f
"""
import os, sys
import pandas as pd
import numpy
pd.options.display.width = 1000
pd.options.display.max_columns = 100


# to read trips.rdata
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

import ngfs_metrics
print(ngfs_metrics.NGFS_OD_CITIES_OF_INTEREST_DF)

NO_PRICING_RUNID = '2035_TM152_NGF_NP10_Path4_02'
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
# TEST - DO NOT COMMIT'
# run_list = ['2035_TM152_NGF_NP10_Path4_02','2035_TM152_NGF_NP10_Path1a_02']

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

# add aggregate trip_mode, agg_trip_mode
trips_od_travel_time_df['agg_trip_mode'] = 'unset'
trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(ngfs_metrics.MODES_PRIVATE_AUTO), 'agg_trip_mode'] = 'auto'
trips_od_travel_time_df.loc[ trips_od_travel_time_df.trip_mode.isin(ngfs_metrics.MODES_TRANSIT),      'agg_trip_mode'] = 'transit'
assert(len(trips_od_travel_time_df.loc[ trips_od_travel_time_df.agg_trip_mode =='unset'])==0)
print(trips_od_travel_time_df.head())
# columns: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, runid, agg_trip_mode, total_trip_travel_time, num_trips

# join with TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF to add simple_skim_mode
trips_od_travel_time_df = pd.merge(
    left        = trips_od_travel_time_df,
    right       = TRIP_MODE_TO_SIMPLE_SKIM_MODE_DF,
    on          = ['trip_mode','inbound'],
    how         = 'left',
    indicator   = True
)
# verify join is completely successful
assert(len(trips_od_travel_time_df.loc[ trips_od_travel_time_df._merge=='both']) == len(trips_od_travel_time_df))
trips_od_travel_time_df.drop(columns=['_merge'], inplace=True)
# columns: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, runid, agg_trip_mode, simple_skim_mode, 
#          total_trip_travel_time, num_trips

# taz_weight: NP_trips for o_taz/dtaz / trips for o_city/d_city
no_pricing_trips_df = trips_od_travel_time_df.loc[ trips_od_travel_time_df.runid == NO_PRICING_RUNID]

no_pricing_taz_trips_df = no_pricing_trips_df.groupby(
    by=['orig_taz','orig_CITY','dest_taz','dest_CITY']).agg(
        no_pricing_taz_trips  = pd.NamedAgg(column="num_trips",aggfunc="sum"))
no_pricing_taz_trips_df.reset_index(drop=False, inplace=True)
no_pricing_city_trips_df = no_pricing_trips_df.groupby(
    by=['orig_CITY','dest_CITY']).agg(
        no_pricing_city_trips = pd.NamedAgg(column="num_trips",aggfunc="sum"))
no_pricing_city_trips_df.reset_index(drop=False, inplace=True)
no_pricing_taz_trips_df = pd.merge(
    left    = no_pricing_taz_trips_df,
    right   = no_pricing_city_trips_df,
    how     = 'left',
    on      = ['orig_CITY','dest_CITY']
)
no_pricing_taz_trips_df['taz_weight'] = no_pricing_taz_trips_df['no_pricing_taz_trips']/no_pricing_taz_trips_df['no_pricing_city_trips']
print("no_pricing_taz_trips_df:\n{}".format(no_pricing_taz_trips_df))
print("no_pricing_taz_trips_df.columns:{}".format(list(no_pricing_taz_trips_df.columns)))
print("taz_weight sum: {}".format(no_pricing_taz_trips_df.taz_weight.sum()))
# columns: orig_taz, orig_CITY, dest_taz, dest_CITY, no_pricing_taz_trips, no_pricing_city_trips, taz_weight

simple_skim_mode_trips_df = trips_od_travel_time_df.groupby(
    by=['orig_CITY','dest_CITY','runid','agg_trip_mode','simple_skim_mode']).agg(
        simple_skim_trips = pd.NamedAgg(column="num_trips",aggfunc="sum"))
simple_skim_mode_trips_df.reset_index(drop=False, inplace=True)
agg_trip_mode_trips_df = trips_od_travel_time_df.groupby(
    by=['orig_CITY','dest_CITY','runid','agg_trip_mode']).agg(
        agg_trip_mode_trips = pd.NamedAgg(column="num_trips",aggfunc="sum"))
agg_trip_mode_trips_df.reset_index(drop=False, inplace=True)
simple_skim_mode_trips_df = pd.merge(
    left    = simple_skim_mode_trips_df,
    right   = agg_trip_mode_trips_df,
    how     = 'left',
    on      = ['orig_CITY','dest_CITY','runid','agg_trip_mode']
)
simple_skim_mode_trips_df['simple_mode_weight'] = simple_skim_mode_trips_df['simple_skim_trips']/simple_skim_mode_trips_df['agg_trip_mode_trips']
print("simple_skim_mode_trips_df:\n{}".format(simple_skim_mode_trips_df))
print("simple_skim_mode_trips_df.columns:\n{}".format(list(simple_skim_mode_trips_df.columns)))
print("simple_mode_weight sum: {}".format(simple_skim_mode_trips_df.simple_mode_weight.sum()))
# columns: orig_CITY, dest_CITY, runid, agg_trip_mode, simple_skim_trips, agg_trip_mode_trips, simple_mode_weight

weights_df = pd.merge(
    left    = no_pricing_taz_trips_df,
    right   = simple_skim_mode_trips_df,
    how     = 'outer',
    on      = ['orig_CITY','dest_CITY']
)
weights_df['taz_simple_mode_weight'] = weights_df['taz_weight']*weights_df['simple_mode_weight']
print("weights_df.taz_simple_mode_weight sum:{}".format(weights_df.taz_simple_mode_weight.sum()))
# save this
OUTPUT_FILE = "E1_Path1a_weights.csv"
weights_df.to_csv(OUTPUT_FILE, index=False)
print("Wrote {:,} rows to {}".format(len(weights_df), OUTPUT_FILE))

# drop unneeded columns
weights_df.drop(columns=[
    'no_pricing_taz_trips','no_pricing_city_trips','taz_weight',
    'simple_skim_trips','agg_trip_mode_trips','simple_mode_weight'
], inplace=True)
print(weights_df.head())
# columns: runid, orig_CITY, dest_CITY, orig_TAZ, dest_taz, simple_skim_mode, agg_trip_mode, taz_simple_mode_weight 

# Step 2: join trips with skim time
all_ODs_trip_times_df = pd.DataFrame()
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
    # Pathway 2 has some da/s2/s3 > 1,000,000 => convert to NA
    TimeSkimsDatabaseAM.loc[ TimeSkimsDatabaseAM.da > 1000, 'da'] = pd.NA
    TimeSkimsDatabaseAM.loc[ TimeSkimsDatabaseAM.s2 > 1000, 's2'] = pd.NA
    TimeSkimsDatabaseAM.loc[ TimeSkimsDatabaseAM.s3 > 1000, 's3'] = pd.NA
    
    # get the weights for this runid
    ODs_trip_times_df = weights_df.loc[ weights_df.runid == runid ]
    # join to skims
    ODs_trip_times_df = pd.merge(
        left     =ODs_trip_times_df,
        right    =TimeSkimsDatabaseAM.rename(columns={'orig':'orig_taz', 'dest':'dest_taz'}),
        on       =['orig_taz','dest_taz'],
        how      ='left',
        indicator=True
    )
    # verify join is completely successful
    assert(len(ODs_trip_times_df.loc[ ODs_trip_times_df._merge=='both']) == len(ODs_trip_times_df))
    ODs_trip_times_df.drop(columns=['_merge'], inplace=True)
    print(ODs_trip_times_df.head())

    # select travel time for the trip_mode's associated simple skim mode and save into column travel_time
    ODs_trip_times_df['travel_time'] = -999.0
    for simple_skim_mode in SIMPLE_SKIM_MODES:
        ODs_trip_times_df.loc[ODs_trip_times_df.simple_skim_mode == simple_skim_mode, 'travel_time'] = \
            ODs_trip_times_df[simple_skim_mode]
    print(ODs_trip_times_df.head())

    unset_rows = ODs_trip_times_df.loc[ ODs_trip_times_df['travel_time'] < 0]
    NA_rows    = ODs_trip_times_df.loc[ pd.isna(ODs_trip_times_df['travel_time']) ]
    print("unset_rows: {:,}\n{}".format(len(unset_rows), unset_rows))
    print("NA_rows:    {:,}\n{}".format(len(NA_rows), NA_rows))
    # assert(len(NA_rows)==0)

    # drop skims columns
    ODs_trip_times_df.drop(columns=SIMPLE_SKIM_MODES, inplace=True)

    all_ODs_trip_times_df = pd.concat([all_ODs_trip_times_df, ODs_trip_times_df])

# columns are: orig_taz, orig_CITY, dest_taz, dest_CITY, trip_mode, inbound, mean_num_trips, [runid1], [runid2], ...
# where [runid1],[runid2],... is the skim travel time from the orig_taz to the dest_taz for the trip_mode/inbound for that run
# convert [runid1] to total travel time = mean_num_trips x travel time
for runid in run_list:
    all_ODs_trip_times_df['weighted_travel_time'] = all_ODs_trip_times_df.travel_time * all_ODs_trip_times_df.taz_simple_mode_weight

all_ODs_trip_times_df.reset_index(drop=True, inplace=True)
print("all_ODs_trip_times_df:\n{}".format(all_ODs_trip_times_df))
print("all_ODs_trip_times_df.columns:{}".format(list(all_ODs_trip_times_df.columns)))

# for understanding NaNs
# mean_num_trips_for_NaN_num_trips = trips that would have been dropped
# so num_trips, total_trip_travel_time are missing
all_ODs_trip_times_df['weight_for_NaN_travel_time'] = 0
all_ODs_trip_times_df.loc[ pd.isna(all_ODs_trip_times_df.travel_time), 
                          'weight_for_NaN_travel_time'] = all_ODs_trip_times_df.taz_simple_mode_weight

# save this TAZ-based aggregate version
OUTPUT_FILE = "OD_taz_travel_times_E1_double_weighted.csv"
all_ODs_trip_times_df.to_csv(OUTPUT_FILE, index=False)
print("Wrote {:,} rows to {}".format(len(all_ODs_trip_times_df), OUTPUT_FILE))

# summarize to orig_CITY, dest_CITY, mode
OD_city_df = all_ODs_trip_times_df.groupby(
    by = ['orig_CITY','dest_CITY', 'runid', 'agg_trip_mode']
).agg(
    weighted_travel_time   = pd.NamedAgg(column="weighted_travel_time",   aggfunc=numpy.nansum),
    taz_simple_mode_weight = pd.NamedAgg(column="taz_simple_mode_weight", aggfunc=numpy.nansum),
    # checks
    weight_for_NaN_travel_time = pd.NamedAgg(column="weight_for_NaN_travel_time", aggfunc="sum"),

).reset_index(drop=False)
OD_city_df['avg_skim_travel_time'] = OD_city_df['weighted_travel_time']/OD_city_df['taz_simple_mode_weight']
print(OD_city_df.head())

OUTPUT_FILE = "OD_city_travel_times_E1_double_weighted.csv"
OD_city_df.to_csv(OUTPUT_FILE, index=False)
print("Wrote {:,} rows to {}".format(len(OD_city_df), OUTPUT_FILE))
