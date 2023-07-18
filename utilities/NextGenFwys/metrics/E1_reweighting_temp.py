USAGE = """
  Asana task: https://app.asana.com/0/0/1204911549136921/f
"""
import copy, os.path, re
import pandas as pd
import csv
import numpy as np
import numpy

# Step 1: calculate weight
# read mode runs
TM1_GIT_DIR             = 'C:/Users/llin/Documents/GitHub/travel-model-one'
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])

current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']

run_list = current_runs_df['directory'].to_list()
run_list.remove('2015_TM152_NGF_05')
run_list.remove('2035_TM152_FBP_Plus_24')
run_list.remove('2035_TM152_NGF_NP10')
run_list.remove('2035_TM152_NGF_NP10_Path2a_02')
run_list.remove('2035_TM152_NGF_NP10_Path2b_02')

# read TAZ and city file
NGFS_OD_CITIES_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_with_cities.csv")
NGFS_OD_CITIES_DF      = pd.read_csv(NGFS_OD_CITIES_FILE)

# read ODTravelTime_byModeTimeperiodIncome.csv from all run
ODTRAVELTIME_df = pd.DataFrame()
for runid in run_list:
    ODTRAVELTIME_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/core_summaries/ODTravelTime_byModeTimeperiodIncome.csv'
    ODTRAVELTIME      = pd.read_csv(ODTRAVELTIME_path)
    # note the runid
    ODTRAVELTIME["runid"] = runid
    # add to transit_assignment_df
    ODTRAVELTIME_df = pd.concat([ODTRAVELTIME_df, ODTRAVELTIME])

# process the ODTRAVELTIME_df
# only keep the AM
trips_od_travel_time_df = ODTRAVELTIME_df.loc[ ODTRAVELTIME_df.timeperiod_label == 'AM Peak']
# pivot out the income since we don't need it
trips_od_travel_time_df = pd.pivot_table(trips_od_travel_time_df,
                                         index=['orig_taz','dest_taz','trip_mode','runid'],
                                         values=['num_trips','avg_travel_time_in_mins'],
                                         aggfunc={'num_trips':numpy.nansum, 'avg_travel_time_in_mins':numpy.nanmean})
trips_od_travel_time_df.reset_index(inplace=True)

# trips weights: max(num of trips across all pathways)
# https://app.asana.com/0/0/1204911549136921/1205043669589139/f
trips_od_travel_time_df_num_of_trips = pd.pivot_table(trips_od_travel_time_df,
                                                      index=['orig_taz','dest_taz','trip_mode'],
                                                      values=['num_trips'],
                                                      aggfunc={'num_trips':numpy.nanmax})
trips_od_travel_time_df_num_of_trips.reset_index(inplace=True)
print(trips_od_travel_time_df_num_of_trips)


# Step 2: grab skim data
TimeSkimsDatabaseAM_df = pd.DataFrame()
for runid in run_list:
    # select the analyzed pathway
    trips_od_travel_time_runid_df = trips_od_travel_time_df.loc[trips_od_travel_time_df.runid == runid]
    # drop the avg_travel_time_in_mins and num_trips columns
    trips_od_travel_time_runid_df = trips_od_travel_time_df.drop(columns=['avg_travel_time_in_mins', 'num_trips'])
    # join new num_of_trips from trips_od_travel_time_df_num_of_trips
    trips_od_travel_time_runid_df = pd.merge(trips_od_travel_time_runid_df, 
                                             trips_od_travel_time_df_num_of_trips,
                                             left_on=['orig_taz','dest_taz','trip_mode'],
                                             right_on = ['orig_taz','dest_taz','trip_mode'])
    
    # a list of OD that exists in the analyzd pathway
    od_list = trips_od_travel_time_runid_df.groupby(['orig_taz','dest_taz']).agg({'runid':'first'}).reset_index()
    
    # read skim data from modeling machine
    directory = runid
    if directory      == '2035_TM152_NGF_NP10_Path4_02':
        model_path = '//MODEL2-C/Model2C-Share/Projects/2035_TM152_NGF_NP10_Path4_02'
    elif directory    == '2035_TM152_NGF_NP10_Path3a_02':
        model_path =  '//MODEL3-C/Model3C-Share/Projects/2035_TM152_NGF_NP10_Path3a_02'
    elif directory    == '2035_TM152_NGF_NP10_Path3b_02':
        model_path =  '//MODEL3-D/Model3D-Share/Projects/2035_TM152_NGF_NP10_Path3b_02'
    elif directory    == '2035_TM152_NGF_NP10_Path1a_02':
        model_path =  '//MODEL3-A/Model3A-Share/Projects/2035_TM152_NGF_NP10_Path1a_02'
    elif directory    == '2035_TM152_NGF_NP10_Path1b_02':
        model_path =  '//MODEL3-B/Model3B-Share/Projects/2035_TM152_NGF_NP10_Path1b_02'
    elif directory    == '2035_TM152_NGF_NP10_Path2a_02_10pc':
        model_path =  '//MODEL2-D/Model2D-Share/Projects/2035_TM152_NGF_NP10_Path2a_02_10pc'
    elif directory    == '2035_TM152_NGF_NP10_Path2b_02_10pc':
        model_path =  '//MODEL3-D/Model3D-Share/Projects/2035_TM152_NGF_NP10_Path2b_02_10pc'
    print(model_path)
    
    TimeSkimsDatabaseAM_path = model_path + '/database/' + 'TimeSkimsDatabaseAM.csv'
    TimeSkimsDatabaseAM      = pd.read_csv(TimeSkimsDatabaseAM_path)
    
    # only keep the OD that exists in the analyzd pathway
    TimeSkimsDatabaseAM_od = pd.merge(od_list,
                                      TimeSkimsDatabaseAM,
                                      left_on=['orig_taz','dest_taz'], 
                                      right_on = ['orig','dest'])
    # categorize skim travel time
    TimeSkimsDatabaseAM_od['MODES_PRIVATE_AUTO'] = (TimeSkimsDatabaseAM_od['da'] + TimeSkimsDatabaseAM_od['daToll'] + TimeSkimsDatabaseAM_od['s2'] + TimeSkimsDatabaseAM_od['s2Toll'] + TimeSkimsDatabaseAM_od['s3'] + TimeSkimsDatabaseAM_od['s3Toll'])/6 
    TimeSkimsDatabaseAM_od.loc[TimeSkimsDatabaseAM_od['MODES_PRIVATE_AUTO'] < 0, 'MODES_PRIVATE_AUTO'] = 0
    
    TimeSkimsDatabaseAM_od['MODES_TRANSIT'] = (TimeSkimsDatabaseAM_od['wTrnW'] + TimeSkimsDatabaseAM_od['dTrnW'] + TimeSkimsDatabaseAM_od['wTrnD'])/3
    TimeSkimsDatabaseAM_od.loc[TimeSkimsDatabaseAM_od['MODES_TRANSIT'] < 0, 'MODES_TRANSIT'] = 0
    
    TimeSkimsDatabaseAM_od = TimeSkimsDatabaseAM_od[['orig_taz', 'dest_taz', 
                                                     'MODES_PRIVATE_AUTO',
                                                     'MODES_TRANSIT',
                                                     'walk',
                                                     'bike']]
    
    # from wide to long
    TimeSkimsDatabaseAM_od = pd.melt(TimeSkimsDatabaseAM_od, 
                                     id_vars=['orig_taz', 'dest_taz'], 
                                     value_vars=["MODES_PRIVATE_AUTO", "MODES_TRANSIT",'walk','bike'],
                                     var_name="trip_mode_category", 
                                     value_name="avg_travel_time_in_mins_skims")
    
    # note the run
    TimeSkimsDatabaseAM_od['runid'] = runid
    
    
    # concentate
    TimeSkimsDatabaseAM_df = pd.concat([TimeSkimsDatabaseAM_df, TimeSkimsDatabaseAM_od])
print(TimeSkimsDatabaseAM_df)

# Step 3: join skim travel time to each scenario's od
MODES_TRANSIT      = [9,10,11,12,13,14,15,16,17,18]
MODES_TAXI_TNC     = [19,20,21]
MODES_SOV          = [1,2]
MODES_HOV          = [3,4,5,6]
MODES_PRIVATE_AUTO = MODES_SOV + MODES_HOV
MODES_WALK         = [7]
MODES_BIKE         = [8]

trips_od_travel_time_weighting_df = pd.DataFrame()
for runid in run_list:
    # select the analyzed pathway
    trips_od_travel_time_runid_df = trips_od_travel_time_df.loc[trips_od_travel_time_df.runid == runid]
    # drop runid to avoid having two runid columns in the output
    trips_od_travel_time_runid_df = trips_od_travel_time_runid_df.drop(['runid'], axis=1)
    TimeSkimsDatabaseAM_runid_df  = TimeSkimsDatabaseAM_df.loc[TimeSkimsDatabaseAM_df.runid == runid]
                                                                
    # drop the avg_travel_time_in_mins and num_trips columns
    trips_od_travel_time_runid_df = trips_od_travel_time_runid_df.drop(columns=['avg_travel_time_in_mins', 'num_trips'])
    # join new num_of_trips from trips_od_travel_time_df_num_of_trips
    trips_od_travel_time_runid_df = pd.merge(trips_od_travel_time_runid_df, 
                                             trips_od_travel_time_df_num_of_trips,
                                             left_on=['orig_taz','dest_taz','trip_mode'],
                                             right_on = ['orig_taz','dest_taz','trip_mode'])
    
    # join skim travel time to each scenario's od
    trips_od_travel_time_runid_df.loc[trips_od_travel_time_runid_df['trip_mode'].isin(MODES_TRANSIT),'trip_mode_category'] = 'MODES_TRANSIT'
    trips_od_travel_time_runid_df.loc[trips_od_travel_time_runid_df['trip_mode'].isin(MODES_PRIVATE_AUTO),'trip_mode_category'] = 'MODES_PRIVATE_AUTO'  
    trips_od_travel_time_runid_df.loc[trips_od_travel_time_runid_df['trip_mode'].isin(MODES_WALK),'trip_mode_category'] = 'walk'
    trips_od_travel_time_runid_df.loc[trips_od_travel_time_runid_df['trip_mode'].isin(MODES_BIKE),'trip_mode_category'] = 'bike'    
    
    
    trips_od_travel_time_runid_df = pd.merge(trips_od_travel_time_runid_df, 
                                             TimeSkimsDatabaseAM_runid_df,
                                             left_on=['orig_taz','dest_taz','trip_mode_category'],
                                             right_on = ['orig_taz','dest_taz','trip_mode_category'])
    
    # concentate
    trips_od_travel_time_weighting_df = pd.concat([trips_od_travel_time_weighting_df, trips_od_travel_time_runid_df])
print(trips_od_travel_time_weighting_df)

# Step 4: Summarize by Cities
trips_od_travel_time_weighting_orig_df = pd.merge(trips_od_travel_time_weighting_df, 
                                                  NGFS_OD_CITIES_DF, 
                                                  left_on=['orig_taz'],
                                                  right_on=['taz1454'])

trips_od_travel_time_weighting_orig_df = trips_od_travel_time_weighting_orig_df.rename(columns={"CITY": "CITY_orig",
                                                                                               "taz1454": "taz1454_orig"})

trips_od_travel_time_weighting_origdest_df = pd.merge(trips_od_travel_time_weighting_orig_df, 
                                                      NGFS_OD_CITIES_DF, 
                                                      left_on=['dest_taz'],
                                                      right_on=['taz1454'])

trips_od_travel_time_weighting_origdest_df = trips_od_travel_time_weighting_origdest_df.rename(columns={"CITY": "CITY_dest",
                                                                                                        "taz1454": "taz1454_dest"})
print(trips_od_travel_time_weighting_origdest_df)

# Step 5: group by cities
trips_od_travel_time_E1_df = trips_od_travel_time_weighting_origdest_df.groupby(['CITY_orig', 'CITY_dest','trip_mode_category','runid']).agg({'num_trips':'sum','avg_travel_time_in_mins_skims':'mean'}).reset_index()

print(trips_od_travel_time_E1_df)
trips_od_travel_time_E1_df.to_csv("L:/Application/Model_One/NextGenFwys/metrics/E1_reweighting/trips_od_travel_time_E1_df.csv")
