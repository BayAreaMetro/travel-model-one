import datetime, os, sys, argparse
import numpy, pandas as pd
from collections import OrderedDict, defaultdict
from dbfread import DBF
import math
import csv
pd.options.mode.chained_assignment = None  # default='warn'
INFLATION_FACTOR = 1.03
INFLATION_00_23 = (327.06 / 180.20) * INFLATION_FACTOR

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

    loaded_roadway_network = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period_vehclasses.csv")
    tm_loaded_network_df = pd.read_csv(loaded_roadway_network, 
                                       usecols=['a','b','tollclass','ft'],
                                       dtype={'a':numpy.int64, 'b':numpy.int64, 'tollclass':numpy.int64},
                                       na_values=[''])

    # read toll class groupings
    tollclass_df = pd.read_excel(NGFS_TOLLCLASS_FILE)
    # select NextGenFwy tollclasses where 'Grouping minor' exists
    tollclass_df = tollclass_df.loc[(tollclass_df.project == 'NextGenFwy') & pd.notna(tollclass_df['Grouping minor'])]

    # See TOLLCLASS_Designations.xlsx workbook, Readme - numbering convention
    if fwy_or_arterial == "fwy":
        tollclass_df = tollclass_df.loc[tollclass_df.tollclass > 900000]
    elif fwy_or_arterial == "arterial":
        tollclass_df = tollclass_df.loc[(tollclass_df.tollclass > 700000) & 
                                        (tollclass_df.tollclass < 900000)]

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

    # split 'Grouping minor' to 'grouping' (now without direction) and 'grouping_dir'
    grouping_df['grouping_dir'] = grouping_df['Grouping minor'].str[-2:]
    grouping_df['grouping']     = grouping_df['Grouping minor'].str[:-3]
    grouping_df.drop(columns=['Grouping minor','tollclass','ft'], inplace=True)
    return grouping_df

def calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, metric_id, metrics_dict):
    #function to compare two runs and enter difference as a metric in dictionary
    metrics_dict_series = pd.Series(metrics_dict)
    metrics_dict_df  = metrics_dict_series.to_frame().reset_index()
    metrics_dict_df.columns = ['modelrun_id','metric_id','intermediate/final','key','metric_desc','year','value']
    #     make a list of the metrics from the run of interest to iterate through and calculate a difference with
    metrics_list = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'].str.contains(tm_runid) == True)]
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

        val_run = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'] == tm_runid)].loc[(metrics_dict_df['metric_desc'] == metric)].iloc[0]['value']
        val_base = metrics_dict_df.copy().loc[(metrics_dict_df['modelrun_id'] == tm_runid_base)].loc[(metrics_dict_df['metric_desc'] == metric)].iloc[0]['value']
        metrics_dict[tm_runid, metric_id,'extra',key,'change_in_{}'.format(metric),year] = (val_run-val_base)
        metrics_dict[tm_runid, metric_id,'extra',key,'pct_change_in_{}'.format(metric),year] = ((val_run-val_base)/val_base)

def sum_grouping(network_df,period): #sum congested time across selected toll class groupings
    return network_df['ctim'+period].sum()

def calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid, year, tm_loaded_network_df, representative_links_df, metrics_dict):
  # Keeping essential columns of loaded highway network: node A and B, distance, free flow time, congested time
  metric_id = 'Reliable 1'

  tm_ab_ctim_df = tm_loaded_network_df.copy()
  # tm_ab_ctim_df = tm_ab_ctim_df.copy()[['Grouping minor_AMPM','a_b','ctimAM','ctimPM', 'distance','volEA_tot', 'volAM_tot', 'volMD_tot', 'volPM_tot', 'volEV_tot']]  
  tm_ab_ctim_df['Grouping minor_AMPM'] = tm_ab_ctim_df['grouping'] + '_' + tm_ab_ctim_df['grouping_dir']
  # create df for parallel arterials
  # keep this separate as there are duplicate rows
  tm_links_df = tm_loaded_network_df.copy().merge(representative_links_df, on='a_b', how='left')
  for i in minor_groups:
    # filter df for minor groupings (travel time)
    minor_group_am_df = tm_ab_ctim_df.copy().loc[tm_ab_ctim_df['Grouping minor_AMPM'] == i+'_AM']
    minor_group_am = sum_grouping(minor_group_am_df.loc[tm_loaded_network_df['USEAM'] == 1],'AM')
    metrics_dict[tm_runid,metric_id,'extra',i,'%s_AM_travel_time' % i, year] = minor_group_am

    # add vmt to metric dict
    minor_group_am_vmt =(minor_group_am_df['distance']*(minor_group_am_df['volAM_tot'])).sum()
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_AM_vmt',year] = minor_group_am_vmt

    # add toll per mile in 2023$
    minor_group_am_toll_per_mile =round(((minor_group_am_df['TOLLAM_DA']).sum()/100) / (minor_group_am_df['distance'] ).sum() * INFLATION_00_23, 2)
    metrics_dict[tm_runid,metric_id,'extra',i,'%s' % i + '_AM_toll_per_mile',year] = minor_group_am_toll_per_mile 

    # add trips (for freeways and arterials)
    tm_parallel_arterials_df = tm_links_df.copy().loc[tm_links_df['parallel_art_rep_link'] == i]
    tm_minor_groupings_df = tm_links_df.copy().loc[(tm_links_df['minor_group_rep_link'] == i)]

    parallel_arterials_trips = tm_parallel_arterials_df.copy().loc[:, 'volAM_tot'].sum()
    minor_groups_trips = tm_minor_groupings_df.copy().loc[:, 'volAM_tot'].sum()
    
    # add trips to metric dict
    metrics_dict[tm_runid,metric_id,'extra',i,'%s_AM_Parallel_Arterial_trips' % i,year] = parallel_arterials_trips
    metrics_dict[tm_runid,metric_id,'extra',i,'%s_AM_Freeway_trips' % i,year] = minor_groups_trips

def calculate_map_data(tm_runid, year, tm_loaded_network_df, representative_links_df, metrics_dict):    
    # 5) Change in peak hour travel time on key freeway corridors and parallel arterials

    # borrowed from pba metrics calculate_Connected2_hwy_traveltimes()
    metric_id = 'Reliable 1'

    # calculate travel times on each cprridor for both runs
    this_run_metric = calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid, year, tm_loaded_network_df, representative_links_df, metrics_dict)
    base_run_metric = calculate_travel_time_and_return_weighted_sum_across_corridors(tm_runid_base, year, tm_loaded_network_df_base, representative_links_df, metrics_dict)
    # find the change in thravel time for each corridor
    calculate_change_between_run_and_base(tm_runid, tm_runid_base, year, 'Reliable 1', metrics_dict)

TM1_GIT_DIR             = "C:\\Users\\jalatorre\\Documents\\GitHub\\travel-model-one"
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")
# TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "NextGenFwys", "ModelRuns.xlsx")
# NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "NextGenFwys", "TOLLCLASS_Designations.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"
current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']
# only process metrics for 2035 model runs 
current_runs_df = current_runs_df.loc[ current_runs_df['year'] == 2035]
pathway1_runs = current_runs_df.loc[ current_runs_df['category'].str.startswith("Pathway 1")]
PATHWAY1_SCENARIO_RUN_ID = pathway1_runs['directory'].tolist()[-1] # take the last one
TOLLED_FWY_MINOR_GROUP_LINKS_DF = determine_tolled_minor_group_links(PATHWAY1_SCENARIO_RUN_ID, "fwy")

TOLLED_FWY_MINOR_GROUP_LINKS_DF

# # all current runs
# current_runs_location = "C:\\Users\\jalatorre\\Documents\\GitHub\\travel-model-one\\utilities\\NextGenFwys\\ModelRuns1.xlsx"
# current_runs_df = pd.read_excel(current_runs_location, sheet_name='all_runs')
# current_runs_list = current_runs_df.loc[current_runs_df['status'] == 'current', 'directory']
# # only process metrics for 2035 model runs 
# current_runs_df = current_runs_df.loc[ current_runs_df['year'] == 2035]
run1a = current_runs_df.loc[ current_runs_df['directory'].str.contains('Path1a') == True].iloc[-1]['directory']
run1b = current_runs_df.loc[ current_runs_df['directory'].str.contains('Path1b') == True].iloc[-1]['directory']
run2a = current_runs_df.loc[ current_runs_df['directory'].str.contains('Path2a') == True].iloc[-1]['directory']
run2b = current_runs_df.loc[ current_runs_df['directory'].str.contains('Path2b') == True].iloc[-1]['directory']
run4 = current_runs_df.loc[ current_runs_df['directory'].str.contains('Path4') == True].iloc[-1]['directory']
runs = [run1a, run1b, run2a, run2b, run4]

# load minor groupings, to be merged with loaded network
# minor_links_df = pd.read_csv('C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\202302 Metrics Scripting\\Input Files\\a_b_with_minor_groupings.csv')
minor_links_df = TOLLED_FWY_MINOR_GROUP_LINKS_DF
representative_links_lookup = "C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\Corridor Level Visualization\\NGFS_CorridorMaps_SketchData_v3.xlsx"
# representative_links_lookup = os.path.join(TM1_GIT_DIR, "NextGenFwys", "metrics", "Input Files", "NGFS_CorridorMaps_SketchData_v3.xlsx")
representative_links_df = pd.read_excel(representative_links_lookup, sheet_name='am_links')
# list for iteration
# minor_groups = minor_links_df['Grouping minor'].dropna().unique()[1:] #exclude 'other' and NaN
minor_groups = TOLLED_FWY_MINOR_GROUP_LINKS_DF['grouping'].unique()
# load lookup file for parallel arterial links

# define base run inputs
# # base year run for comparisons (no project)
# ______load no project network to use for speed comparisons in vmt corrections______
tm_run_location_base = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\2035_TM152_NGF_NP10_Path4_02"
tm_runid_base = tm_run_location_base.split('\\')[-1]
# tm_run_location_base = os.path.join(NGFS_SCENARIOS, run4)
# tm_runid_base = run4
# ______define the base run inputs for "change in" comparisons______
tm_loaded_network_df_base = pd.read_csv(tm_run_location_base+'/OUTPUT/avgload5period.csv')
tm_loaded_network_df_base = tm_loaded_network_df_base.rename(columns=lambda x: x.strip())
# merging df that has the list of minor segments with loaded network - for corridor analysis
tm_loaded_network_df_base['a_b'] = tm_loaded_network_df_base['a'].astype(str) + "_" + tm_loaded_network_df_base['b'].astype(str)
network_links_dbf_base = pd.read_csv(tm_run_location_base + '\\OUTPUT\\shapefile\\network_links_reduced_file.csv')
tm_loaded_network_df_base = tm_loaded_network_df_base.copy().merge(network_links_dbf_base.copy(), on='a_b', how='left')
tm_loaded_network_df_base = pd.merge(left=tm_loaded_network_df_base.copy(), right=minor_links_df, how='left', left_on=['a','b'], right_on=['a','b'])

# load transit data
transit_vol_AM = "C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\Corridor Level Visualization\\10 csvs for the 10 maps with final data\\transit_vols_AM.csv"
# transit_vol_AM = os.path.join(TM1_GIT_DIR, "NextGenFwys", "metrics", "Input Files", "transit_vols_AM.csv")
transit_vol_df = pd.read_csv(transit_vol_AM).fillna(0)
# parallel and express bus
transit_vol_df['m2_LRT_Bus'] = transit_vol_df.iloc[:,5] + transit_vol_df.iloc[:,7] + transit_vol_df.iloc[:,9]
# rail
transit_vol_df['m2_Rail'] = transit_vol_df.iloc[:,11] + transit_vol_df.iloc[:,13]
transit_vol_df = transit_vol_df[['Corridor','Model Run ID', 'm2_LRT_Bus', 'm2_Rail']]


for run in runs:
  USAGE = """

    python ngfs_corridor_map_data.py

    Run this from the model run dir.
    Processes model outputs and creates a single csv with scenario metrics, called metrics\scenario_metrics.csv
    
    This file will have _ columns:
      1) County
      2) #
      3) Corridor
      4) Model Run
      
    Metrics are:
      1) VMT Change
      2) Time Savings (mins)
      3) Toll per mile
      4) Change in Trips
        a) Freeway absolute Change
        b) Freeway Pct Change
        c) Parallel Arterial
      
    Specifics:
      Map 1: Region map with three icons for each of 19 corridors showing VMT change (%), Travel Time savings (%), Toll Value (per mile, 2023$)
      Map 2: Region map with four icons for each of 19 corridors showing Trips change (absolute number) on: freeways, parallel arterials, parallel and express bus, rail
      Five maps for each map shown for (total 10 maps; no maps for cordon pathways):
        Pathway 4 (no pricing)
        Pathway 1a
        Pathway 1b
        Pathway 2a
        Pathway 2b 

      """

  # ______run______
  # add the run name... use the current dir
  # tm_run_location = os.getcwd()
  # tm_runid = os.path.split(os.getcwd())[1]

  # #temporary run location for testing purposes
  tm_run_location = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\" + run
  tm_runid = tm_run_location.split('\\')[-1]

  # metric dict input: year
  year = tm_runid[:4]

  # ______define the inputs_______
  tm_loaded_network_df = pd.read_csv(tm_run_location+'/OUTPUT/avgload5period.csv')
  tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
  # ----merging df that has the list of minor segments with loaded network - for corridor analysis
  tm_loaded_network_df['a_b'] = tm_loaded_network_df['a'].astype(str) + "_" + tm_loaded_network_df['b'].astype(str)
  tm_loaded_network_df = pd.merge(left=tm_loaded_network_df, right=minor_links_df, how='left', left_on=['a','b'], right_on=['a','b'])

  # ----import network links file from reduced dbf as a dataframe to merge with loaded network and get toll rates
  network_links_dbf = pd.read_csv(tm_run_location + '\\OUTPUT\\shapefile\\network_links_reduced_file.csv')
  tm_loaded_network_df = tm_loaded_network_df.copy().merge(network_links_dbf.copy(), on='a_b', how='left')

  metrics_dict = {} 
  calculate_map_data(tm_runid, year, tm_loaded_network_df, representative_links_df, metrics_dict)

  # _________output table__________
  out_series = pd.Series(metrics_dict)
  out_frame  = out_series.to_frame().reset_index()
  out_frame.columns = ['modelrun_id','metric_id','intermediate/final','key','metric_desc','year','value']
  # print out table
  out_frame = out_frame.loc[out_frame['modelrun_id'] == tm_runid]
  final_df = pd.DataFrame()
  final_df['Corridor'] = minor_groups
  # final_df['VMT'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('change') == False)&(out_frame['metric_desc'].str.contains('vmt') == True)].reset_index(drop=True)['value']
  # map 1 VMT change (%)
  final_df['m1_VMT_pct'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('pct') == True)&(out_frame['metric_desc'].str.contains('vmt') == True)].reset_index(drop=True)['value']
  # final_df['Travel Time (mins)'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('change') == False)&(out_frame['metric_desc'].str.contains('time') == True)].reset_index(drop=True)['value']
  # map 1 Travel Time savings (%)
  final_df['m1_TTS_pct'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('pct') == True)&(out_frame['metric_desc'].str.contains('time') == True)].reset_index(drop=True)['value']
  # map 1 Toll Value (per mile, 2023$)
  final_df['m1_TollVal'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('change') == False)&(out_frame['metric_desc'].str.contains('toll') == True)].reset_index(drop=True)['value']
  # final_df['Freeway Trips'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('change') == False)&(out_frame['metric_desc'].str.contains('Freeway_trips') == True)].reset_index(drop=True)['value']
  # map 2 Trips change (absolute number) on: freeways
  final_df['m2_fwytrip'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('pct') == False)&(out_frame['metric_desc'].str.contains('change') == True)&(out_frame['metric_desc'].str.contains('Freeway_trips') == True)].reset_index(drop=True)['value']
  # final_df['Freeway Trips Pct Change'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('pct') == True)&(out_frame['metric_desc'].str.contains('change') == True)&(out_frame['metric_desc'].str.contains('Freeway_trips') == True)].reset_index(drop=True)['value']
  # final_df['Parallel Arterial Trips'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('change') == False)&(out_frame['metric_desc'].str.contains('Parallel_Arterial_trips') == True)].reset_index(drop=True)['value']
  # map 2 Trips change (absolute number) on: parallel arterials
  final_df['m2_arttrip'] = out_frame.copy().loc[(out_frame['metric_desc'].str.contains('pct') == False)&(out_frame['metric_desc'].str.contains('change') == True)&(out_frame['metric_desc'].str.contains('Parallel_Arterial_trips') == True)].reset_index(drop=True)['value']
  final_df['Model Run ID'] = tm_runid
  final_df = pd.merge(left=final_df, right=transit_vol_df, how='left', left_on=['Corridor','Model Run ID'], right_on=['Corridor','Model Run ID'])
  final_df['freeway'] = round(final_df['m2_fwytrip'], -2)
  final_df['arterial'] = round(final_df['m2_arttrip'], -2)
  final_df['transit'] = round(final_df['m2_LRT_Bus'] + final_df['m2_Rail'], -2)
  new_directory = "C:\\Users\\jalatorre\\Box\\NextGen Freeways Study\\07 Tasks\\07_AnalysisRound1\\Corridor Level Visualization\\10 csvs for the 10 maps with final data\\{} (Compared to {})".format(tm_runid,tm_runid_base)
  # new_directory = os.path.join(os.getcwd(),"{} (Compared to {})".format(tm_runid,tm_runid_base))
  out_filename = new_directory + "\\NGFS_CorridorMaps_SketchData.csv"
  try:
    # skip if it exists already
    if os.path.exists(new_directory):
        print("    Destination folder {} exists ".format(new_directory))
    else:
      os.mkdir(new_directory)
    # couldn't get the code below to work right
    # final_df.style.format({'m1_VMT_pct': '{:,.2f}%',
    #                        'm1_TTS_pct': '{:,.2f}%',
    #                        'm1_TollVal': '${:,.2f}'}).to_excel(out_filename, engine='openpyxl')
    final_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
    print("Wrote {}".format(out_filename))
  except:
    print('[Errno 2] No such file or directory: {}'.format(out_filename))