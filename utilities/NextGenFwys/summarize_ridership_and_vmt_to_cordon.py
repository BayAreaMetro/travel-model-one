USAGE = """

  python summarize_ridership_and_vmt_to_cordon.py

  Asana task: https://app.asana.com/0/1201809392759895/1204875936483953/f

  Quick scripts to understand cordon effect (Pathway 2) on:
    1. VMT
        1.1  VMT on SF links
        1.2  VMT to-from SF vs. rest

    2. Mode share: this is not conducted by this script, but by https://app.asana.com/0/0/1204082986821822/f

    3. SF cordon effect on transit ridership: summarize transit ridership for routes ending in the cordons

    Outputs are saved in "L:\Application\Model_One\NextGenFwys\cordon_effect"
"""

import copy, os.path, re
import pandas as pd
import dbfread
import csv
import numpy as np
import geopandas as gpd


# read mode runs
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
current_runs_df = current_runs_df.loc[ current_runs_df['status'] == 'current']
run_list = current_runs_df['directory'].to_list()
print(run_list)

# 1. SF cordon effect on VMT
# 1.1 VMT on SF links
network_links_df = pd.DataFrame()
for runid in run_list:
    network_links_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/shapefile/network_links.shp'
    network_links      = gpd.read_file(network_links_path)
    # note the runid
    network_links["runid"] = runid
    # add to transit_assignment_df
    network_links_df = pd.concat([network_links_df, network_links])

# read TAZ and cordon files
TAZ_shp         = gpd.read_file('X:/travel-model-one-master/utilities/geographies/bayarea_rtaz1454_rev1_WGS84.shp').to_crs(network_links_df.crs)
TAZ_with_cordon = pd.read_csv('L:/Application/Model_One/NextGenFwys/INPUT_DEVELOPMENT/PopSyn_n_LandUse/2035_cordon/landuse/parking_strategy/tazData_parkingStrategy_v01_3cordons_LeaveOutTI.csv')

TAZ_shp         = TAZ_shp.merge(TAZ_with_cordon, left_on='TAZ1454', right_on='ZONE', how='left')

TAZ_sf_list = (TAZ_shp['TAZ1454'].loc[(TAZ_shp.CORDON == 10)]).to_list()
TAZ_ok_list = (TAZ_shp['TAZ1454'].loc[(TAZ_shp.CORDON == 11)]).to_list()
TAZ_sj_list = (TAZ_shp['TAZ1454'].loc[(TAZ_shp.CORDON == 12)]).to_list()

# Prep to summarize VMT on SF links
network_links_df['VOL_TOT'] = network_links_df['VOLEA_TOT'] + network_links_df['VOLAM_TOT'] + network_links_df['VOLMD_TOT'] + network_links_df['VOLPM_TOT'] + network_links_df['VOLEV_TOT']
network_links_df['VMT']     = network_links_df['VOL_TOT'] * network_links_df['DISTANCE']

# TAZ for three cordons
TAZ_sf = TAZ_shp.loc[TAZ_shp['TAZ1454'].isin(TAZ_sf_list)]
TAZ_ok = TAZ_shp.loc[TAZ_shp['TAZ1454'].isin(TAZ_ok_list)]
TAZ_sj = TAZ_shp.loc[TAZ_shp['TAZ1454'].isin(TAZ_sj_list)]

# spatial join: trn stops intersecting with cordon polygons
network_links_df["SF_cordon_links"] = network_links_df.intersects(TAZ_sf.unary_union) # SF cordon links
network_links_df["OK_cordon_links"] = network_links_df.intersects(TAZ_ok.unary_union) # OK cordon links
network_links_df["SJ_cordon_links"] = network_links_df.intersects(TAZ_sj.unary_union) # SJ cordon links

network_links_sf = network_links_df.loc[
    network_links_df.SF_cordon_links == True
]

network_links_ok = network_links_df.loc[
    network_links_df.OK_cordon_links == True
]

network_links_sj = network_links_df.loc[
    network_links_df.SJ_cordon_links == True
]

# Summarize VMT on SF links
network_links_sf_summarize = network_links_sf.groupby(['runid']).agg({'VMT':'sum'}).reset_index()
network_links_sf_summarize['Cordon'] = 'San Francisco'
network_links_ok_summarize = network_links_ok.groupby(['runid']).agg({'VMT':'sum'}).reset_index()
network_links_ok_summarize['Cordon'] = 'Oakland'
network_links_sj_summarize = network_links_sj.groupby(['runid']).agg({'VMT':'sum'}).reset_index()
network_links_sj_summarize['Cordon'] = 'San Jose'

# append three cordon results to one table
network_links_vmt_summarize = pd.concat([network_links_sf_summarize, network_links_ok_summarize, network_links_sj_summarize])

# write out the output
print(network_links_vmt_summarize)
network_links_vmt_summarize.to_csv("L:/Application/Model_One/NextGenFwys/cordon_effect/network_links_vmt_summarize.csv",index=False)



# 1. SF cordon effect on VMT
# 1.2 VMT to-from SF vs. rest
AutoTripsVMT_df = pd.DataFrame()
for runid in run_list:
    AutoTripsVMT_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/core_summaries/AutoTripsVMT_perOrigDestHomeWork.csv'
    AutoTripsVMT      = pd.read_csv(AutoTripsVMT_path)
    # note the runid
    AutoTripsVMT["runid"] = runid
    # add to AutoTripsVMT_df
    AutoTripsVMT_df = pd.concat([AutoTripsVMT_df, AutoTripsVMT])

# Only select trips to and from SF cordon
AutoTripsVMT_from_sf = AutoTripsVMT_df.loc[AutoTripsVMT_df['orig_taz'].isin(TAZ_sf_list)]
AutoTripsVMT_to_sf = AutoTripsVMT_df.loc[AutoTripsVMT_df['dest_taz'].isin(TAZ_sf_list)]

AutoTripsVMT_sf = pd.concat([AutoTripsVMT_to_sf, AutoTripsVMT_from_sf])

# Only select trips to and from OK cordon
AutoTripsVMT_from_ok = AutoTripsVMT_df.loc[AutoTripsVMT_df['orig_taz'].isin(TAZ_ok_list)]
AutoTripsVMT_to_ok = AutoTripsVMT_df.loc[AutoTripsVMT_df['dest_taz'].isin(TAZ_ok_list)]

AutoTripsVMT_ok = pd.concat([AutoTripsVMT_to_ok, AutoTripsVMT_from_ok])

# Only select trips to and from SJ cordon
AutoTripsVMT_from_sj = AutoTripsVMT_df.loc[AutoTripsVMT_df['orig_taz'].isin(TAZ_sj_list)]
AutoTripsVMT_to_sj = AutoTripsVMT_df.loc[AutoTripsVMT_df['dest_taz'].isin(TAZ_sj_list)]

AutoTripsVMT_sj = pd.concat([AutoTripsVMT_to_sj, AutoTripsVMT_from_sj])

# Summarize VMT to and from SF cordon
AutoTripsVMT_sf_summarize = AutoTripsVMT_sf.groupby(['runid']).agg({'vmt':'sum'}).reset_index()
AutoTripsVMT_sf_summarize['Cordon'] = 'San Francisco'

# Summarize VMT to and from OK cordon
AutoTripsVMT_ok_summarize = AutoTripsVMT_ok.groupby(['runid']).agg({'vmt':'sum'}).reset_index()
AutoTripsVMT_ok_summarize['Cordon'] = 'Oakland'

# Summarize VMT to and from SJ cordon
AutoTripsVMT_sj_summarize = AutoTripsVMT_sj.groupby(['runid']).agg({'vmt':'sum'}).reset_index()
AutoTripsVMT_sj_summarize['Cordon'] = 'San Jose'

# append
AutoTripsVMT_summarize = pd.concat([AutoTripsVMT_sf_summarize, AutoTripsVMT_ok_summarize, AutoTripsVMT_sj_summarize])
# write out the output
print(AutoTripsVMT_summarize)
AutoTripsVMT_summarize.to_csv("L:/Application/Model_One/NextGenFwys/cordon_effect/AutoTripsVMT_summarize.csv",index=False)

# 2. Mode share
# Conducted in https://app.asana.com/0/0/1204082986821822/f

# 3. SF cordon effect on transit ridership
# https://app.asana.com/0/0/1204875936483961/f
# SF cordon effect on transit ridership (also OK and SJ)
transit_assignment_summarized = pd.DataFrame()

for runid in ['2035_TM152_NGF_NP10_Path3a_02', '2035_TM152_NGF_NP10_Path3b_02','2035_TM152_NGF_NP10_Path4_02']:
    # read the AM transit ridreship data by runid
    transit_assignment_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/trn/trnlinkam_withSupport.dbf'
    transit_assignment_df   = pd.DataFrame(dbfread.DBF(transit_assignment_path))
    # note the runid
    transit_assignment_df["runid"] = runid
    # add to transit_assignment_df
    # transit_assignment_df = pd.concat([transit_assignment_df, transit_assignment])
    print(runid)
    
    # read the transit link file by runid
    print("read network_trn_links")    
    network_trn_links_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/shapefile/network_trn_links.shp'
    network_trn_links = gpd.read_file(network_trn_links_path)
    
    # spatial join the transit links and the cordons
    print("select links")  
    network_trn_links["SF_cordon_links"] = network_trn_links.within(TAZ_sf.unary_union)
    network_trn_links["OK_cordon_links"] = network_trn_links.within(TAZ_ok.unary_union)
    network_trn_links["SJ_cordon_links"] = network_trn_links.within(TAZ_sj.unary_union) # this won't capture Caltrains for SJ

    
    network_trn_links["SJ_cordon_intersect_links"] = network_trn_links.intersects(TAZ_sj.unary_union) # this can capture Caltrains for SJ
    network_trn_links_sj_cordon_Caltrain = network_trn_links.loc[
        (network_trn_links.SJ_cordon_intersect_links == True) &
        (network_trn_links.MODE == 130)
    ][['A', 'B', 'NAME','geometry']] #capture caltrains for SJ cordon

    # filter out transit links in cordons
    network_trn_links_sf_cordon = network_trn_links.loc[
        (network_trn_links.SF_cordon_links == True) 
    ][['A', 'B', 'NAME','geometry']]

    network_trn_links_ok_cordon = network_trn_links.loc[
        network_trn_links.OK_cordon_links == True
    ][['A', 'B', 'NAME','geometry']]

    network_trn_links_sj_cordon = network_trn_links.loc[
        network_trn_links.SJ_cordon_links == True
    ][['A', 'B', 'NAME','geometry']]

    network_trn_links_sj_cordon = pd.concat([network_trn_links_sj_cordon, network_trn_links_sj_cordon_Caltrain])
    
    
    
    # join the transit ridership to selected links
    print('join the transit ridership to selected links')
    transit_assignment_sf_cordon = network_trn_links_sf_cordon.merge(transit_assignment_df, how = 'left', on=['A','B','NAME'])
    transit_assignment_ok_cordon = network_trn_links_ok_cordon.merge(transit_assignment_df, how = 'left', on=['A','B','NAME'])
    transit_assignment_sj_cordon = network_trn_links_sj_cordon.merge(transit_assignment_df, how = 'left', on=['A','B','NAME'])
    
    # sum the exit
    transit_assignment_sf_summarized = transit_assignment_sf_cordon.groupby(['runid']).agg({'AB_XITA':'sum'}).reset_index()
    transit_assignment_sf_summarized['cordon'] = "SF"
    transit_assignment_ok_summarized = transit_assignment_ok_cordon.groupby(['runid']).agg({'AB_XITA':'sum'}).reset_index()
    transit_assignment_ok_summarized['cordon'] = "OK"
    transit_assignment_sj_summarized = transit_assignment_sj_cordon.groupby(['runid']).agg({'AB_XITA':'sum'}).reset_index()
    transit_assignment_sj_summarized['cordon'] = "SJ"
    
    # results by runid
    results_by_runid = pd.concat([transit_assignment_sf_summarized, 
                                  transit_assignment_ok_summarized,
                                  transit_assignment_sj_summarized])
    results_by_runid['runid'] = runid
    print(results_by_runid)
    
    # combine the results
    transit_assignment_summarized = pd.concat([transit_assignment_summarized, results_by_runid])
transit_assignment_summarized.to_csv("L:/Application/Model_One/NextGenFwys/cordon_effect/transit_assignment_summarized.csv",index=False)