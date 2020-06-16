USAGE = """

  python pba50_metrics.py

  Needs access to these box folders and M Drive
    Box/Modeling and Surveys/Urban Modeling/Bay Area UrbanSim 1.5/PBA50/Draft Blueprint runs/
    Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/

  Processes model outputs and creates a single csv with scenario metrics in this folder:
    Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/

  This csv file will have 6 columns:
    1) modelrun ID
    2) metric ID
    3) metric name
    4) year  (note: for metrics that depict change from 2015 to 2050, this value will be 2050)
    5) blueprint type
    6) metric value

"""

import datetime, os, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict


def calculate_tm_highlevelmetrics(runid, dbp, parcel_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall_TM"

    # TBD


def calculate_Affordable1_transportation_costs(runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, metrics_dict):

    metric_id = "A1"

    # Total number of households
    tm_tot_hh = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_households") == True), 'value'].sum()
    tm_tot_hh_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc1"),'value'].item()
    tm_tot_hh_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc2"),'value'].item()

    # Total household income (model outputs are in 2000$)
    tm_total_hh_inc = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_hh_inc") == True), 'value'].sum()
    tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()
    tm_total_hh_inc_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc2"),'value'].item()

    # Total transit fares (model outputs are in 2000$)
    tm_tot_transit_fares = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_fares") == True), 'value'].sum()
    tm_tot_transit_fares_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc1"),'value'].item()
    tm_tot_transit_fares_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc2"),'value'].item()

    # Total auto op cost (model outputs are in 2000$)
    tm_tot_auto_op_cost = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_cost") == True), 'value'].sum()
    tm_tot_auto_op_cost_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc1"),'value'].item()
    tm_tot_auto_op_cost_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc2"),'value'].item()

    # Calculating number of autos owned from autos_owned.csv
    tm_auto_owned_df['tot_autos'] = tm_auto_owned_df['autos'] * tm_auto_owned_df['households'] 
    tm_tot_autos_owned = tm_auto_owned_df['tot_autos'].sum()
    tm_tot_autos_owned_inc1 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 1), 'tot_autos'].sum()
    tm_tot_autos_owned_inc2 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 2), 'tot_autos'].sum()

    # Total auto ownership cost in 2000$
    tm_tot_auto_owner_cost = tm_tot_autos_owned * auto_ownership_cost * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc1 = tm_tot_autos_owned_inc1 * auto_ownership_cost_inc1 * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc2 = tm_tot_autos_owned_inc2 * auto_ownership_cost_inc2 * inflation_18_20 / inflation_00_20

    # Total Transportation Cost (in 2000$)
    tp_cost      = tm_tot_auto_op_cost      + tm_tot_transit_fares      + tm_tot_auto_owner_cost
    tp_cost_inc1 = tm_tot_auto_op_cost_inc1 + tm_tot_transit_fares_inc1 + tm_tot_auto_owner_cost_inc1
    tp_cost_inc2 = tm_tot_auto_op_cost_inc2 + tm_tot_transit_fares_inc2 + tm_tot_auto_owner_cost_inc2

    # Mean transportaiton cost per household in 2020$
    tp_cost_mean      = tp_cost / tm_tot_hh * inflation_00_20
    tp_cost_mean_inc1 = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    tp_cost_mean_inc2 = tp_cost_inc2 / tm_tot_hh_inc2 * inflation_00_20

    # Transportation cost % of income
    tp_cost_pct_inc = tp_cost / tm_total_hh_inc
    tp_cost_pct_inc_inc1 = tp_cost_inc1 / tm_total_hh_inc_inc1
    tp_cost_pct_inc_inc2 = tp_cost_inc2 / tm_total_hh_inc_inc2
    

        
    metrics_dict[runid,metric_id,'transportation_cost_pct_income',year,dbp] = tp_cost_pct_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1',year,dbp] = tp_cost_pct_inc_inc1
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc2',year,dbp] = tp_cost_pct_inc_inc2
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$',year,dbp] = tp_cost_mean
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp] = tp_cost_mean_inc1
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc2',year,dbp] = tp_cost_mean_inc2
    
    
    # Tolls & Fares
    
    # Reading auto times file
    tm_auto_times_df = tm_auto_times_df.sum(level='Income')

    # Calculating Total Tolls = bridge tolls + value tolls
    total_tolls = OrderedDict()
    for inc_level in range(1,5): 
        total_tolls['inc%d'  % inc_level] = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls', 'Value Tolls']].sum()/100  # cents -> dollars
    total_tolls_allHH = sum(total_tolls.values())
    total_tolls_LIHH = total_tolls['inc1'] + total_tolls['inc2']
    
    # Calculating Tolls per household
    metrics_dict[runid,metric_id,'tolls_per_HH',year,dbp] = total_tolls_allHH / tm_tot_hh / 100 * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_LIHH',year,dbp] = total_tolls_LIHH / (tm_tot_hh_inc1+tm_tot_hh_inc2) / 100 * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1HH',year,dbp] = total_tolls['inc1'] / tm_tot_hh_inc1 / 100 * inflation_00_20

    # Average Fares per Household
    metrics_dict[runid,metric_id,'fares_per_HH',year,dbp] = tm_tot_transit_fares / tm_tot_hh / 100 * inflation_00_20
    metrics_dict[runid,metric_id,'fares_per_LIHH',year,dbp] = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_hh_inc1+tm_tot_hh_inc2) / 100 * inflation_00_20
    metrics_dict[runid,metric_id,'fares_per_inc1HH',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 / 100 * inflation_00_20
    



def calculate_Connected1_accessibility(runid, year, dbp, tm_scen_metrics_df, metrics_dict):
    
    metric_id = "C1"

    # % of Jobs accessible by 30 min car/ 45 min transit
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 30 min car
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 45 min transit
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_noncoc"), 'value'].item()


def calculate_Connected1_proximity(runid, year, dbp, tm_scen_metrics_df, metrics_dict):
    
    metric_id = "C1"


def calculate_Connected2_crowding(runid, year, dbp, transit_operator_df, metrics_dict):
    
    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp

    transit_crowding_file = os.path.join(tm_run_location, runid, "OUTPUT", "metrics", "transit_crowding_complete.csv")
    if not os.path.exists(transit_crowding_file):
        print("Error: file {} not found".format(transit_crowding_file))
        raise

    tm_crowding_df = pd.read_csv(transit_crowding_file)
    tm_crowding_df = tm_crowding_df[['TIME','SYSTEM','ABNAMESEQ','period','load_standcap','AB_VOL']]
    tm_crowding_df = tm_crowding_df.loc[tm_crowding_df['period'] == "AM"]
    tm_crowding_df['time_overcapacity'] = tm_crowding_df.apply (lambda row: row['TIME'] if (row['load_standcap']>1) else 0, axis=1)
    tm_crowding_df['time_crowded'] = tm_crowding_df.apply (lambda row: row['TIME'] if (row['load_standcap']>0.85) else 0, axis=1)
    tm_crowding_df['person_hrs_total'] = tm_crowding_df['TIME'] * tm_crowding_df['AB_VOL']  
    tm_crowding_df['person_hrs_overcap'] = tm_crowding_df['time_overcapacity'] * tm_crowding_df['AB_VOL']  
    tm_crowding_df['person_hrs_crowded'] = tm_crowding_df['time_crowded'] * tm_crowding_df['AB_VOL']  


    tm_crowding_df = pd.merge(left=tm_crowding_df, right=transit_operator_df, left_on="SYSTEM", right_on="SYSTEM", how="left")

    system_crowding_df = tm_crowding_df[['person_hrs_total','person_hrs_overcap','person_hrs_crowded']].groupby(tm_crowding_df['operator']).sum().reset_index()
    system_crowding_df['pct_overcapacity'] = system_crowding_df['person_hrs_overcap'] / system_crowding_df['person_hrs_total'] 
    system_crowding_df['pct_crowded'] = system_crowding_df['person_hrs_crowded'] / system_crowding_df['person_hrs_total'] 

    for index,row in system_crowding_df.iterrows():
        if row['operator'] in ['AC Transit Local','AC Transit Transbay','SFMTA LRT','SFMTA Bus','VTA Bus Local','VTA LRT','BART','Caltrain','SamTrans Local','GGT Express','WETA']:
            metrics_dict[runid,metric_id,'crowded_pct_personhrs_AM_%s' % row['operator'],year,dbp] = row['pct_crowded'] 


def calculate_Connected2_hwy_traveltimes(runid, year, dbp, hwy_corridor_links_df, metrics_dict):

    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_loaded_network_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/avgload5period.csv')

    # Keeping essential columns of loaded highway network: node A and B, distance, free flow time, congested time
    tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
    tm_loaded_network_df = tm_loaded_network_df[['a','b','distance','fft','ctimAM']]
    tm_loaded_network_df['link'] = tm_loaded_network_df['a'].astype(str) + "_" + tm_loaded_network_df['b'].astype(str)

    # merging df that has the list of all
    hwy_corridor_links_df = pd.merge(left=hwy_corridor_links_df, right=tm_loaded_network_df, left_on="link", right_on="link", how="left")
    corridor_travel_times_df = hwy_corridor_links_df[['distance','fft','ctimAM']].groupby(hwy_corridor_links_df['route']).sum().reset_index()

    for index,row in corridor_travel_times_df.iterrows():
        metrics_dict[runid,metric_id,'travel_time_AM_%s' % row['route'],year,dbp] = row['ctimAM'] 

def calculate_Connected2_trn_traveltimes(runid, year, dbp, transit_operator_df, metrics_dict):

    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_trn_line_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/trn/trnline.csv')

    # It doesn't really matter which path ID we pick, as long as it is AM
    tm_trn_line_df = tm_trn_line_df.loc[tm_trn_line_df['path id'] == "am_wlk_loc_wlk"]
    tm_trn_line_df = pd.merge(left=tm_trn_line_df, right=transit_operator_df, left_on="mode", right_on="mode", how="left")

    # grouping by transit operator, and summing all line times and distances, to get metric of "time per unit distance", in minutes/mile
    trn_operator_travel_times_df = tm_trn_line_df[['line time','line dist']].groupby(tm_trn_line_df['operator']).sum().reset_index()
    trn_operator_travel_times_df['time_per_dist_AM'] = trn_operator_travel_times_df['line time'] / trn_operator_travel_times_df['line dist']

    # grouping by mode, and summing all line times and distances, to get metric of "time per unit distance", in minutes/mile
    trn_mode_travel_times_df = tm_trn_line_df[['line time','line dist']].groupby(tm_trn_line_df['mode_name']).sum().reset_index()
    trn_mode_travel_times_df['time_per_dist_AM'] = trn_mode_travel_times_df['line time'] / trn_mode_travel_times_df['line dist']

    for index,row in trn_operator_travel_times_df.iterrows():
        if row['operator'] in ['AC Transit Local','AC Transit Transbay','SFMTA LRT','SFMTA Bus','VTA Bus Local','VTA LRT','BART','Caltrain','SamTrans Local']:
            metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['operator'],year,dbp] = row['time_per_dist_AM'] 

    for index,row in trn_mode_travel_times_df.iterrows():
        metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['mode_name'],year,dbp] = row['time_per_dist_AM'] 


def calculate_Vibrant1_median_commute(runid, year, dbp, tm_commute_df, metrics_dict):
    
    metric_id = "V1"

    tm_commute_df['total_commute_miles'] = tm_commute_df['freq'] * tm_commute_df['distance']
   
    commute_dist_df = tm_commute_df[['incQ','freq','total_commute_miles']].groupby(['incQ']).sum()
        
    metrics_dict[runid,metric_id,'mean_commute_distance',year,dbp] = commute_dist_df['total_commute_miles'].sum() / commute_dist_df['freq'].sum()
    metrics_dict[runid,metric_id,'mean_commute_distance_inc1',year,dbp] = commute_dist_df['total_commute_miles'][1] / commute_dist_df['freq'][1] 
    metrics_dict[runid,metric_id,'mean_commute_distance_inc2',year,dbp] = commute_dist_df['total_commute_miles'][2] / commute_dist_df['freq'][2]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc3',year,dbp] = commute_dist_df['total_commute_miles'][3] / commute_dist_df['freq'][3]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc4',year,dbp] = commute_dist_df['total_commute_miles'][4] / commute_dist_df['freq'][4]


def calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict):

    for tm_runid in list_tm_runid_blueprintonly:

        year = tm_runid[:4]
        
        if "Basic" in tm_runid:
            dbp = "Basic"
        elif "Plus" in tm_runid:
            dbp = "Plus"
        #elif "PlusCrossing_01" in tm_runid:
        #    dbp = "Plus_01"  
        #elif  "PlusFixItFirst" in tm_runid:
        #    dbp = "PlusFixItFirst"
        else:
            dbp = "Unknown"


        metric_id = "A1"

        # Tolls
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'tolls_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'tolls_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'tolls_per_inc1HH',y2,"NoProject"] - 1
        # Transit Fares
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'fares_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'fares_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'fares_per_inc1HH',y2,"NoProject"] - 1


        metric_id = "C2"

        # Highway corridor travel times
        for route in ['Antioch_SF','Vallejo_SF','SanJose_SF','Oakland_SanJose','Oakland_SF']:
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2015_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'travel_time_AM_%s' % route,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2050noproject_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'travel_time_AM_%s' % route,y2,'NoProject']  - 1
        

        # Transit Crowding by operator
        for operator in ['AC Transit Local','AC Transit Transbay','SFMTA LRT','SFMTA Bus','VTA Bus Local','VTA LRT','BART','Caltrain','SamTrans Local','GGT Express','WETA']:
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y1,'2015']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = 0
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y2,'NoProject']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = 0
        

         # Transit travel times by operator
        for operator in ['AC Transit Local','AC Transit Transbay','SFMTA LRT','SFMTA Bus','VTA Bus Local','VTA LRT','BART','Caltrain','SamTrans Local']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % operator,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % operator,y2,'NoProject']  - 1

         # Transit travel times by mode
        for mode_name in ['Local','Express','Ferry','Light Rail','Heavy Rail','Commuter Rail']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2050_DBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y2,'NoProject']  - 1


def calc_travelmodel_metrics():

    transit_operator_df         = pd.read_csv(transit_operator_file)
    hwy_corridor_links_df       = pd.read_csv(hwy_corridor_links_file)

    for tm_runid in list_tm_runid:

        year = tm_runid[:4]

        if "NoProject" in tm_runid:
            dbp = "NoProject"
        elif "Basic" in tm_runid:
            dbp = "Basic"
        elif "Plus" in tm_runid:
            dbp = "Plus"
        #elif "PlusCrossing_01" in tm_runid:
        #    dbp = "Plus_01"            
        #elif  "PlusFixItFirst" in tm_runid:
        #    dbp = "PlusFixItFirst"
        elif  "2015" in tm_runid:
            dbp = "2015"
        else:
            dbp = "Unknown"
        
        # Read relevant metrics files
        if "2015" in tm_runid: tm_run_location = tm_run_location_ipa
        else: tm_run_location = tm_run_location_bp
        tm_scen_metrics_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
        tm_auto_owned_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/autos_owned.csv')
        tm_auto_times_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/auto_times.csv',sep=",", index_col=[0,1])
        tm_commute_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv')

        calculate_Affordable1_transportation_costs(tm_runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, metrics_dict)
        print("@@@@@@@@@@@@@ A1 Done")
        calculate_Connected1_accessibility(tm_runid, year, dbp, tm_scen_metrics_df, metrics_dict)
        print("@@@@@@@@@@@@@ C1 Done")
        calculate_Connected2_hwy_traveltimes(tm_runid, year, dbp, hwy_corridor_links_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2hwy Done")
        calculate_Connected2_trn_traveltimes(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2trn Done")
        calculate_Connected2_crowding(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2crowding Done")
        calculate_Vibrant1_median_commute(tm_runid, year, dbp, tm_commute_df, metrics_dict)
        print("@@@@@@@@@@@@@ V1 Done")

        print("@@@@@@@@@@@@@%s Done"% dbp)
    
    calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict)


if __name__ == '__main__':

    #pd.set_option('display.width', 500)

    # Set Travel model inputs
    tm_run_location_bp  = 'M:/Application/Model One/RTP2021/Blueprint/'
    tm_run_location_ipa = 'M:/Application/Model One/RTP2021/IncrementalProgress/'

    # read ModelRuns.csv
    MODELRUNS_CSV       = '\\\\MainModel\\MainModelShare\\travel-model-one-master\\utilities\\RTP\\ModelRuns.csv'

    model_runs = pd.read_csv(MODELRUNS_CSV)

    # filter to RTP2021 and current
    model_runs = model_runs.loc[(model_runs['project']=='RTP2021')&(model_runs['status']=='current'), ]
    # filter to year = 2015 or Plus
    model_runs = model_runs.loc[(model_runs['year']==2015)|(model_runs['year']==2050), ]
    print(model_runs)

    # make sure we have one of each
    model_runs_2015           = model_runs.loc[model_runs['year']==2015,]
    model_runs_2050_noproject = model_runs.loc[(model_runs['year']==2050)&(model_runs['category']=='No Project'),]
    model_runs_2050_plus      = model_runs.loc[(model_runs['year']==2050)&(model_runs['category']=='Plus'      ),]

    assert(len(model_runs_2015          )==1)
    assert(len(model_runs_2050_noproject)==1)
    assert(len(model_runs_2050_plus     )==1)

    tm_2015_runid                     = model_runs_2015.iloc[0]['directory']
    tm_2050_DBP_NoProject_runid       = model_runs_2050_noproject.iloc[0]['directory']
    tm_2050_DBP_PlusCrossing_runid    = model_runs_2050_plus.iloc[0]['directory']
    print("tm_2015_runid                  = {}".format(tm_2015_runid))
    print("tm_2050_DBP_NoProject_runid    = {}".format(tm_2050_DBP_NoProject_runid))
    print("tm_2050_DBP_PlusCrossing_runid = {}".format(tm_2050_DBP_PlusCrossing_runid))
    list_tm_runid = [tm_2015_runid, tm_2050_DBP_NoProject_runid, tm_2050_DBP_PlusCrossing_runid]
    list_tm_runid_blueprintonly = [tm_2050_DBP_PlusCrossing_runid]

    # Set external inputs
    METRICS_BOX_DIR               = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics'.format(os.getenv('USERNAME'))
    metrics_source_folder         = os.path.join(METRICS_BOX_DIR, 'metrics_files')

    transit_operator_file         = os.path.join(metrics_source_folder, 'transit_system_lookup.csv')
    hwy_corridor_links_file       = os.path.join(metrics_source_folder, 'hwy_corridor_links.csv')
    


    # Global Inputs

    inflation_00_20 = 1.53
    inflation_18_20 = 1.04
    # Annual Auto ownership cost in 2018$
    # Source: Consumer Expenditure Survey 2018 (see Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Affordable\auto_ownership_costs.xlsx)
    # (includes depreciation, insurance, finance charges, license fees)
    auto_ownership_cost      = 5945
    auto_ownership_cost_inc1 = 2585
    auto_ownership_cost_inc2 = 4224


    metrics_dict = OrderedDict()
    y1        = "2015"
    y2        = "2050"
    y_diff    = "2050"

    # Calculate all metrics
    print("Starting metrics functions...")
    calc_travelmodel_metrics()
    print("*****************#####################Completed calc_travelmodel_metrics#####################*******************")

    # Write output
    idx             = pd.MultiIndex.from_tuples(metrics_dict.keys(), names=['modelrunID','metric','name','year','blueprint'])
    metrics         = pd.Series(metrics_dict, index=idx)
    metrics.name    = 'value'


    out_filename    = os.path.join(METRICS_BOX_DIR, 'metrics_travelmodel.csv')
    metrics.to_csv(out_filename, header=True, sep=',', float_format='%.9f')
    
    print("Wrote {}".format(out_filename))

    