USAGE = """

  python Metrics.py

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


def calculate_urbansim_highlevelmetrics(runid, dbp, parcel_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall"

    #################### Housing

    # all households
    metrics_dict[runid,metric_id,'TotHH_region',y2,dbp] = parcel_sum_df['tothh_2050'].sum()
    metrics_dict[runid,metric_id,'TotHH_region',y1,dbp] = parcel_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_growth_region',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_region',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_region',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] = parcel_sum_df['tothh_2050'].sum() - parcel_sum_df['tothh_2015'].sum()
    # HH growth by county
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'TotHH_county_growth_%s' % row['county'],y_diff,dbp] = row['tothh_growth'] 
        metrics_dict[runid,metric_id,'TotHH_county_shareofgrowth_%s' % row['county'],y_diff,dbp] = row['tothh_growth'] / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in all GGs
    metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('GG', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('GG', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_GG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_GG',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_GG',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in PDAs
    metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id'].str.contains('', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id'].str.contains('', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_PDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_PDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_PDA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_PDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in GGs that are not PDAs
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id'].str.contains('', na=False)==0), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id'].str.contains('', na=False)==0), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_GG_notPDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_GG_notPDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 


    # HH Growth in HRAs
    metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in TRAs
    metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_TRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_TRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_TRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 

    # HH Growth in areas that are both HRAs and TRAs
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) , 'tothh_2050'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) , 'tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRAandTRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRAandTRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',y_diff,dbp] 



    #################### Jobs


    # all jobs
    metrics_dict[runid,metric_id,'TotJobs_region',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'TotJobs_region',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'TotJobs_growth_region',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_region',y2,dbp]  / metrics_dict[runid,metric_id,'TotJobs_region',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] = parcel_sum_df['totemp_2050'].sum() - parcel_sum_df['totemp_2015'].sum()
    #Job growth by county
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'TotJobs_growth_%s' % row['county'],y_diff,dbp] = row['totemp_growth'] 
        metrics_dict[runid,metric_id,'TotJobs_county_shareofgrowth_%s' % row['county'],y_diff,dbp] = row['totemp_growth'] / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in all GGs
    metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('GG', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('GG', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_GG_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_GG',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_GG',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in PDAs
    metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id'].str.contains('', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pda_id'].str.contains('', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_PDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_PDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_PDA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_PDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in GGs that are not PDAs
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id'].str.contains('', na=False)==0), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('GG', na=False)) & \
                                                                (parcel_sum_df['pda_id'].str.contains('', na=False)==0), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_GG_notPDA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_GG_notPDA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in HRAs
    metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in TRAs
    metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_TRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_TRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_TRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 

    # Job Growth in areas that are both HRAs and TRAs
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) , 'totemp_2050'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) &\
                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) , 'totemp_2015'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRAandTRA_shareofgrowth',y_diff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRAandTRA',y1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',y_diff,dbp] 


    ############################
    # LIHH
    metrics_dict[runid,metric_id,'LIHH_share_2050',y2,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_share_2015',y1,dbp] = (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_growth_region',y_diff,dbp] = (parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / (parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2050'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'LIHH_growth_%s' % row["county"],y_diff,dbp] = row['LIHH_growth']
            
    # all jobs
    metrics_dict[runid,metric_id,'tot_jobs_2050',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'tot_jobs_2015',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_region',y_diff,dbp] = (parcel_sum_df['totemp_2050'].sum() / parcel_sum_df['totemp_2015'].sum())
    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'jobs_growth_%s' % row["county"],y_diff,dbp] = row['totemp_growth']

def calculate_tm_highlevelmetrics(runid, dbp, parcel_sum_df, county_sum_df, metrics_dict):

    metric_id = "Overall_TM"

    # TBD

def calculate_normalize_factor_Q1Q2(parcel_sum_df):
    return ((parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()) / parcel_sum_df['tothh_2050'].sum()) \
                        / ((parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()) /  parcel_sum_df['tothh_2015'].sum())

def calculate_normalize_factor_Q1(parcel_sum_df):
    return (parcel_sum_df['hhq1_2050'].sum() / parcel_sum_df['tothh_2050'].sum()) \
                        / (parcel_sum_df['hhq1_2015'].sum() /  parcel_sum_df['tothh_2015'].sum())


def calculate_Affordable1_transportation_costs(runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, metrics_dict):

    metric_id = "A1"

    days_per_year = 300

    # Total number of households
    tm_tot_hh      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_households_inc") == True), 'value'].sum()
    tm_tot_hh_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc1"),'value'].item()
    tm_tot_hh_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc2"),'value'].item()

    # Total household income (model outputs are in 2000$, annual)
    tm_total_hh_inc      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_hh_inc") == True), 'value'].sum()
    tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()
    tm_total_hh_inc_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc2"),'value'].item()

    # Total transit fares (model outputs are in 2000$, per day)
    tm_tot_transit_fares      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_fares") == True), 'value'].sum() * days_per_year
    tm_tot_transit_fares_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc1"),'value'].item() * days_per_year
    tm_tot_transit_fares_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc2"),'value'].item() * days_per_year

    # Total auto op cost (model outputs are in 2000$, per day)
    tm_tot_auto_op_cost      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_cost_inc") == True), 'value'].sum() * days_per_year
    tm_tot_auto_op_cost_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc1"),'value'].item() * days_per_year
    tm_tot_auto_op_cost_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc2"),'value'].item() * days_per_year

    # Total auto parking cost (model outputs are in 2000$, per day, in cents)
    #tm_travel_cost_df['park_cost'] = (tm_travel_cost_df['pcost_indiv']+tm_travel_cost_df['pcost_joint']) * tm_travel_cost_df['freq']
    tm_tot_auto_park_cost      = (tm_travel_cost_df.pcost_indiv.sum() + tm_travel_cost_df.pcost_joint.sum()) * days_per_year / 100
    tm_tot_auto_park_cost_inc1 = (tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'pcost_indiv'].sum() + tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'pcost_joint'].sum()) * days_per_year / 100
    tm_tot_auto_park_cost_inc2 = (tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'pcost_indiv'].sum() + tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'pcost_joint'].sum()) * days_per_year / 100

    # Calculating number of autos owned from autos_owned.csv
    tm_auto_owned_df['tot_autos'] = tm_auto_owned_df['autos'] * tm_auto_owned_df['households'] 
    tm_tot_autos_owned      = tm_auto_owned_df['tot_autos'].sum()
    tm_tot_autos_owned_inc1 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 1), 'tot_autos'].sum()
    tm_tot_autos_owned_inc2 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 2), 'tot_autos'].sum()

    # Total auto ownership cost in 2000$
    tm_tot_auto_owner_cost      = tm_tot_autos_owned      * auto_ownership_cost      * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc1 = tm_tot_autos_owned_inc1 * auto_ownership_cost_inc1 * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc2 = tm_tot_autos_owned_inc2 * auto_ownership_cost_inc2 * inflation_18_20 / inflation_00_20

    # Total Transportation Cost (in 2000$)
    tp_cost      = tm_tot_auto_op_cost      + tm_tot_transit_fares      + tm_tot_auto_owner_cost      + tm_tot_auto_park_cost
    tp_cost_inc1 = tm_tot_auto_op_cost_inc1 + tm_tot_transit_fares_inc1 + tm_tot_auto_owner_cost_inc1 + tm_tot_auto_park_cost_inc1
    tp_cost_inc2 = tm_tot_auto_op_cost_inc2 + tm_tot_transit_fares_inc2 + tm_tot_auto_owner_cost_inc2 + tm_tot_auto_park_cost_inc2

    # Mean transportation cost per household in 2020$
    tp_cost_mean      = tp_cost / tm_tot_hh * inflation_00_20
    tp_cost_mean_inc1 = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    tp_cost_mean_inc2 = tp_cost_inc2 / tm_tot_hh_inc2 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$',year,dbp]      = tp_cost_mean
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp] = tp_cost_mean_inc1
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc2',year,dbp] = tp_cost_mean_inc2
    
    # Transportation cost % of income
    tp_cost_pct_inc          = tp_cost      / tm_total_hh_inc
    tp_cost_pct_inc_inc1     = tp_cost_inc1 / tm_total_hh_inc_inc1
    tp_cost_pct_inc_inc2     = tp_cost_inc2 / tm_total_hh_inc_inc2
    tp_cost_pct_inc_inc1and2 = (tp_cost_inc1+tp_cost_inc2) / (tm_total_hh_inc_inc1+tm_total_hh_inc_inc2)


    # Transportation cost % of income metrics       
    metrics_dict[runid,metric_id,'transportation_cost_pct_income',year,dbp]      = tp_cost_pct_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1',year,dbp] = tp_cost_pct_inc_inc1
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc2',year,dbp] = tp_cost_pct_inc_inc2
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1and2',year,dbp] = tp_cost_pct_inc_inc1and2

    # Transportation cost % of income metrics; split by cost bucket
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autoop',year,dbp]        = tm_tot_auto_op_cost / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autopark',year,dbp]      = tm_tot_auto_park_cost / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_transitfare',year,dbp]   = tm_tot_transit_fares / tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_pct_income_autoown',year,dbp]       = tm_tot_auto_owner_cost / tm_total_hh_inc
 
    # Add housing costs from Shimon's outputs
    housing_costs_2050_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_files/2050 Share of Income Spent on Housing.csv')
    housing_costs_2015_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_files/2015 Share of Income Spent on Housing.csv')
    housing_costs_2015_df['totcosts'] = housing_costs_2015_df['share_income'] * housing_costs_2015_df['households']

    if year == "2050":
        metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]          = housing_costs_2050_df['w_all'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]     = housing_costs_2050_df['w_q1'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]     = housing_costs_2050_df['w_q2'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp] = housing_costs_2050_df['w_q1_q2'].sum()
    elif year == "2015":
        metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]          = housing_costs_2015_df.loc[(housing_costs_2015_df['tenure'].str.contains("Total")), 'totcosts'].sum() / \
                                                                                        housing_costs_2015_df.loc[(housing_costs_2015_df['tenure'].str.contains("Total")), 'households'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]     = housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'share_income'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]     = housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'share_income'].sum()
        metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp] = (housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'totcosts'].sum() + housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'totcosts'].sum()) / \
                                                                                        (housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q1t")), 'households'].sum() + housing_costs_2015_df.loc[(housing_costs_2015_df['short_name'].str.contains("q2t")), 'households'].sum())

    # Total H+T Costs pct of income
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income',year,dbp]          = metrics_dict[runid,metric_id,'transportation_cost_pct_income',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc1',year,dbp]     = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc2',year,dbp]     = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc2',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]  
    metrics_dict[runid,metric_id,'HplusT_cost_pct_income_inc1and2',year,dbp] = metrics_dict[runid,metric_id,'transportation_cost_pct_income_inc1and2',year,dbp] + \
                                                                                metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp]  
    
    


    # Tolls & Fares
    
    # Reading auto times file
    tm_auto_times_df = tm_auto_times_df.sum(level='Income')

    # Calculating Total Tolls per day = bridge tolls + value tolls  (2000$)
    total_tolls = OrderedDict()
    for inc_level in range(1,5): 
        total_tolls['inc%d'  % inc_level] = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls', 'Value Tolls']].sum()/100  # cents -> dollars
    total_tolls_allHH = sum(total_tolls.values())
    total_tolls_LIHH = total_tolls['inc1'] + total_tolls['inc2']
    
    # Average Daily Tolls per household
    metrics_dict[runid,metric_id,'tolls_per_HH',year,dbp]     = total_tolls_allHH / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_LIHH',year,dbp]   = total_tolls_LIHH / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1HH',year,dbp] = total_tolls['inc1'] / tm_tot_hh_inc1 * inflation_00_20

    # Average Daily Fares per Household   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'fares_per_HH',year,dbp]     = tm_tot_transit_fares / tm_tot_hh * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_LIHH',year,dbp]   = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1HH',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * inflation_00_20 / days_per_year

    
    # per trip

    # Total auto trips per day (model outputs are in trips, per day)
    tm_tot_auto_trips = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_trips") == True), 'value'].sum()
    tm_tot_auto_trips_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc1"),'value'].item() 
    tm_tot_auto_trips_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc2"),'value'].item() 
    # Total transit trips per day (model outputs are in trips, per day)
    tm_tot_transit_trips = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_trips") == True), 'value'].sum() 
    tm_tot_transit_trips_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc1"),'value'].item() 
    tm_tot_transit_trips_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc2"),'value'].item() 

    # Average Tolls per trip  (total_tolls_xx is calculated above as per day tolls in 2000 dollars)
    metrics_dict[runid,metric_id,'tolls_per_trip',year,dbp]          = total_tolls_allHH / tm_tot_auto_trips * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_trip_inc1and2',year,dbp] = total_tolls_LIHH / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_trip_inc1',year,dbp]     = total_tolls['inc1'] / tm_tot_auto_trips_inc1 * inflation_00_20
    # Total auto operating cost per trip (tm_tot_auto_op_cost and tm_tot_auto_park_cost are calculated above as annual costs in 2000 dollars)
    metrics_dict[runid,metric_id,'autocost_per_trip',year,dbp]           = (tm_tot_auto_op_cost + tm_tot_auto_park_cost) / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'autocost_per_trip_inc1and2',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_op_cost_inc2 + tm_tot_auto_park_cost_inc1 + tm_tot_auto_park_cost_inc2) / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20  / days_per_year
    metrics_dict[runid,metric_id,'autocost_per_trip_inc1',year,dbp]     = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_park_cost_inc1) / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year 

    # Average Fares per trip   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'fares_per_trip',year,dbp]          = tm_tot_transit_fares / tm_tot_transit_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_trip_inc1and2',year,dbp] = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_transit_trips_inc1+tm_tot_transit_trips_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_trip_inc1',year,dbp]     = tm_tot_transit_fares_inc1 / tm_tot_transit_trips_inc1 * inflation_00_20 / days_per_year
        

def calculate_Affordable2_deed_restricted_housing(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "A2"

    # totals for 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp] = parcel_sum_df['deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] = parcel_sum_df['deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] = parcel_sum_df['residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] = parcel_sum_df['residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'residential_units_2015'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'deed_restricted_units_2050'].sum()
    metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'deed_restricted_units_2015'].sum()
    metrics_dict[runid,metric_id,'residential_units_TRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'residential_units_2050'].sum()
    metrics_dict[runid,metric_id,'residential_units_TRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'residential_units_2015'].sum()

    # diff between 2050 and 2015
    metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_total',y2,dbp]  - metrics_dict[runid,metric_id,'deed_restricted_total',y1,dbp] 
    metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_total',y2,dbp] - metrics_dict[runid,metric_id,'residential_units_total',y1,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_HRA',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_HRA',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA',y1,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_TRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_TRA',y2,dbp] - metrics_dict[runid,metric_id,'deed_restricted_TRA',y1,dbp]
    metrics_dict[runid,metric_id,'residential_units_TRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_TRA',y2,dbp]  - metrics_dict[runid,metric_id,'residential_units_TRA',y1,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_nonHRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] - metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp] = metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp]  - metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]

    # metric: deed restricted % of total units: overall, HRA and non-HRA
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_diff',y_diff,dbp] / metrics_dict[runid,metric_id,'residential_units_diff',y_diff,dbp] 
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_HRA_diff',y_diff,dbp]/metrics_dict[runid,metric_id,'residential_units_HRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_TRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_TRA_diff',y_diff,dbp]/metrics_dict[runid,metric_id,'residential_units_TRA_diff',y_diff,dbp]
    metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp] = metrics_dict[runid,metric_id,'deed_restricted_nonHRA_diff',y_diff,dbp]/metrics_dict[runid,metric_id,'residential_units_nonHRA_diff',y_diff,dbp]

    print('********************A2 Affordable********************')
    print('DR pct of new units         %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units',y_diff,dbp] )
    print('DR pct of new units in HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_HRA',y_diff,dbp] )
    print('DR pct of new units in TRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_TRA',y_diff,dbp] )
    print('DR pct of new units outside of HRAs %s' % dbp,metrics_dict[runid,metric_id,'deed_restricted_pct_new_units_nonHRA',y_diff,dbp])


    # Forcing preservation metrics
    metrics_dict[runid,metric_id,'preservation_affordable_housing',y_diff,dbp] = 1


def calculate_Connected1_accessibility(runid, year, dbp, tm_scen_metrics_df, metrics_dict):
    
    metric_id = "C1"

    # % of Jobs accessible by 30 min car OR 45 min transit
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_allmodes_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 30 min car only
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_coc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_coc"), 'value'].item()
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_drv_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_drv_only_acc_accessible_job_share_noncoc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_noncoc"), 'value'].item()
                                
    # % of Jobs accessible by 45 min transit only 
    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_coc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_coc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_coc"), 'value'].item()

    metrics_dict[runid,metric_id,'pct_jobs_acc_by_trn_only_noncoc',year,dbp] = \
        tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_only_acc_accessible_job_share_noncoc"), 'value'].item() \
        + tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "jobacc_trn_drv_acc_accessible_job_share_noncoc"), 'value'].item()


def calculate_Connected1_proximity(runid, year, dbp, tm_scen_metrics_df, metrics_dict):
    
    metric_id = "C1"





def calculate_Connected2_crowding(runid, year, dbp, transit_operator_df, metrics_dict):
    
    metric_id = "C2"

    if "2015" in runid: tm_run_location = tm_run_location_ipa
    else: tm_run_location = tm_run_location_bp
    tm_crowding_df = pd.read_csv(tm_run_location+runid+'/OUTPUT/metrics/transit_crowding_complete.csv')

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



def calculate_Diverse1_LIHHinHRAs(runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict):

    metric_id = "D1"

    # Share of region's LIHH households that are in HRAs
    metrics_dict[runid,metric_id,'LIHH_total',y2,dbp] = parcel_sum_df['hhq1_2050'].sum() + parcel_sum_df['hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_total',y1,dbp] = parcel_sum_df['hhq1_2015'].sum() + parcel_sum_df['hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum() + parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() + parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq2_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y2,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y2,dbp]
    metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_inHRA',y1,dbp] / metrics_dict[runid,metric_id,'LIHH_total',y1,dbp]

    # normalizing for overall growth in LIHH
    metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] = metrics_dict[runid,metric_id,'LIHH_shareinHRA',y1,dbp] * normalize_factor_Q1Q2

    # Total number of Households
    # Total HHs in HRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2050'].sum()
    # Total HHs in TRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inTRA',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRA',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2050'].sum()
    # Total HHs in HRAs only, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRAonly',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRAonly',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False), 'tothh_2050'].sum()
    # Total HHs in TRAs only, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inTRAonly',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRAonly',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False), 'tothh_2050'].sum()
    # Total HHs in HRA/TRAs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inHRATRA',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inHRATRA',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & \
                                                                                (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)), 'tothh_2050'].sum()
     # Total HHs in DR Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tothh_2050'].sum()
    # Total HHs in CoC Tracts, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tothh_2050'].sum()
    # Total HHs in remainder of region (RoR); i.e. not HRA or TRA or CoC or DR
    metrics_dict[runid,metric_id,'TotHH_inRoR',y1,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('DR', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inRoR',y2,dbp] = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('DR', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'tothh_2050'].sum()
    # Total HHs in GGs, in 2015 and 2050
    metrics_dict[runid,metric_id,'TotHH_inGGs',y1,dbp] = GG_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inGGs',y2,dbp] = GG_sum_df['tothh_2050'].sum()
    # Total HHs in Transit Rich GGs, in 2015 and 2050
    GG_TRich_sum_df = GG_sum_df[GG_sum_df['Designation']=="Transit-Rich"]
    metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y1,dbp] = GG_TRich_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y2,dbp] = GG_TRich_sum_df['tothh_2050'].sum()



    ########### Tracking movement of Q1 households: Q1 share of Households
    # Share of Households that are Q1, within each geography type in this order:
    # Overall Region; HRAs; TRAs, DR Tracts; CoCs; Rest of Region; and also GGs and TRichGGs

    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y1,dbp]            = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum() 
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion_normalized',y1,dbp] = parcel_sum_df['hhq1_2015'].sum()  / parcel_sum_df['tothh_2015'].sum()  * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofRegion',y2,dbp]            = parcel_sum_df['hhq1_2050'].sum()  / parcel_sum_df['tothh_2050'].sum() 

    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inTRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRAonly',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRAonly',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRAonly',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRAonly',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRAonly',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('tra', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inTRAonly',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inHRATRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofHRATRA',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False)) & (parcel_sum_df['pba50chcat'].str.contains('tra', na=False)), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inHRATRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRA',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRA',y2,dbp]               = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'hhq1_2050'].sum()  / metrics_dict[runid,metric_id,'TotHH_inTRA',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts_normalized',y1,dbp]     = metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofDRTracts',y2,dbp]                = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inDRTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofCoCTracts',y2,dbp]               = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inCoCTracts',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y1,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('DR', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'hhq1_2015'].sum()      / metrics_dict[runid,metric_id,'TotHH_inRoR',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofRoR_normalized',y1,dbp]    = metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofRoR',y2,dbp]               = parcel_sum_df.loc[(parcel_sum_df['pba50chcat'].str.contains('HRA', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('tra', na=False) == False) & \
                                                                                 (parcel_sum_df['pba50chcat'].str.contains('DR', na=False) == False) & \
                                                                                 (parcel_sum_df['coc_flag_pba2050'] == 0), 'hhq1_2050'].sum()     / metrics_dict[runid,metric_id,'TotHH_inRoR',y2,dbp]


    metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y1,dbp]                     = GG_sum_df['hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inGGs',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofGGs_normalized',y1,dbp]          = metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofGGs',y2,dbp]                     = GG_sum_df['hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inGGs',y2,dbp]

    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y1,dbp]                = GG_TRich_sum_df['hhq1_2015'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y1,dbp]
    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs_normalized',y1,dbp]     = metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y1,dbp] * normalize_factor_Q1
    metrics_dict[runid,metric_id,'Q1HH_shareofTRichGGs',y2,dbp]                = GG_TRich_sum_df['hhq1_2050'].sum() / metrics_dict[runid,metric_id,'TotHH_inTRichGGs',y2,dbp]



    '''
    print('********************D1 Diverse********************')
    print('Growth of LIHH share of population (normalize factor))',normalize_factor_Q1Q2 )
    print('LIHH Share in HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA',y2,dbp] )
    print('LIHH Share in HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareinHRA_normalized',y1,dbp] )
    print('LIHH Share of HRA 2050 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareofHRA',y2,dbp])
    print('LIHH Share of HRA 2015 %s' % dbp,metrics_dict[runid,metric_id,'LIHH_shareofHRA_normalized',y1,dbp] )
    '''



def calculate_Diverse2_LIHH_Displacement(runid, dbp, parcel_sum_df, tract_sum_df, TRA_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict):

    metric_id = "D2"

    # For reference: total number of LIHH in tracts
    metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2050'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2015'].sum()
    metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('DR', na=False), 'hhq1_2015'].sum() * normalize_factor_Q1

    print('********************D2 Diverse********************')
    print('Total Number of LIHH in DR tracts in 2050',metrics_dict[runid,metric_id,'LIHH_inDR',y2,dbp] )
    print('Number of LIHH in DR tracts in 2015',metrics_dict[runid,metric_id,'LIHH_inDR',y1,dbp] )
    print('Number of LIHH in DR tracts in normalized',metrics_dict[runid,metric_id,'LIHH_inDR_normalized',y1,dbp] )


    ###### Displacement at Tract Level (for Displacement Risk Tracts and CoC Tracts and HRA Tracts)

    # Total number of DR, CoC, HRA Tracts
    metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] = tract_sum_df.loc[(tract_sum_df['DispRisk'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] = tract_sum_df.loc[(tract_sum_df['coc_flag_pba2050'] == 1), 'tract_id'].nunique()
    metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp] = tract_sum_df.loc[(tract_sum_df['hra'] == 1), 'tract_id'].nunique()


    # Calculating share of Q1 households at tract level / we are not going to normalize this since we want to check impacts at neighborhood level
    #tract_sum_df['hhq1_pct_2015_normalized'] = tract_sum_df['hhq1_2015'] / tract_sum_df['tothh_2015'] * normalize_factor_Q1
    tract_sum_df['hhq1_pct_2050'] = tract_sum_df['hhq1_2050'] / tract_sum_df['tothh_2050']
    tract_sum_df['hhq1_pct_2015'] = tract_sum_df['hhq1_2015'] / tract_sum_df['tothh_2015']

    
    # Creating functions to check if rows of a dataframe lost hhq1 share or absolute; applied to tract_summary_df and TRA_summary_df

    def check_losthhq1_share(row,j):
        if (row['hhq1_pct_2015'] == 0): return 0
        elif ((row['hhq1_pct_2050']/row['hhq1_pct_2015'])<j): return 1
        else: return 0

    def check_losthhq1_abs(row,j):
        if (row['hhq1_2015'] == 0): return 0
        elif ((row['hhq1_2050']/row['hhq1_2015'])<j): return 1
        else: return 0


    # Calculating number of Tracts that Lost LIHH, with "lost" defined as any loss, or 10% loss

    for i in [0, 10]:

        if i == 0:
            j = 1
        else:
            j = 0.9

        # Calculating change in share of LIHH at tract level to check gentrification            
        tract_sum_df['lost_hhq1_%dpct' % i] = tract_sum_df.apply (lambda row: check_losthhq1_share(row,j), axis=1)
                    #(lambda row: 1 if ((row['hhq1_pct_2050']/row['hhq1_pct_2015_normalized'])<j) else 0, axis=1)
                    #(lambda row: 1 if (row['hhq1_pct_2050'] < (row['hhq1_pct_2015']*j)) else 0, axis=1)


        # Calculating absolute change in LIHH at tract level to check true displacement
        tract_sum_df['lost_hhq1_abs_%dpct' % i] = tract_sum_df.apply (lambda row: check_losthhq1_abs(row,j), axis=1)
                    #(lambda row: 1 if (row['hhq1_2050'] < (row['hhq1_2015']*j)) else 0, axis=1)



        ###############################  Gentrification
                        
        ######## Gentrification in Displacement Risk Tracts
        # Number or percent of DR tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] )
        print('Number of DR Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of DR Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in Communities of Concern
        # Number or percent of CoC tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] )
        print('Number of CoC Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Gentrification in HRAs
        # Number or percent of HRA tracts that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['lost_hhq1_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp] )
        print('Number of HRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA Tracts that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_%dpct' % i,y_diff,dbp] )



        ###############################  Displacement
                        
        ######## Displacement in Displacement Risk Tracts
        # Number or percent of DR tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_DRtracts_total',y1,dbp] )
        print('Number of DR Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of DR Tracts that lost LIHH from (in absolute numbers) 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_DRtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in Communities of Concern
        # Number or percent of CoC tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['coc_flag_pba2050'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_CoCtracts_total',y1,dbp] )
        print('Number of CoC Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of CoC Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_CoCtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

        ######## Displacement in HRAs
        # Number or percent of HRA tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = tract_sum_df.loc[((tract_sum_df['hra'] == 1) & (tract_sum_df['lost_hhq1_abs_%dpct' % i] == 1)), 'tract_id'].nunique()
        metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_HRAtracts_total',y1,dbp] )
        print('Number of HRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of HRA Tracts that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_HRAtracts_lostLIHH_abs_%dpct' % i,y_diff,dbp] )


    ##### Calculating displacement risk using the PBA2040 methodology
    # The analysis estimated which zones (i.e., TAZs) gained or lost lower-income households; those zones
    # that lost lower-income households over the time period would be flagged as being “at risk of displacement.”
    # The share of lower-income households at risk of displacement would be calculated by
    # dividing the number of lower-income households living in TAZs flagged as PDAs, TPAs, or
    # highopportunity areas with an increased risk of displacement by the total number of lower-income
    # households living in TAZs flagged as PDAs, TPAs, or high-opportunity areas in 2040

    # Calculating this first for all DR Risk/CoC/HRA tracts; and next for TRA areas  

    ######## PBA40 Displacement risk in DR Risk/CoC/HRA tracts

    # Q1 only
    #metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y1,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
    #                                                                                    (tract_sum_df['hra'] == 1)), 'hhq1_2015'].nunique()
    metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y2,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq1_2050'].sum()
    # Total number of LIHH in HRA/CoC/DR tracts that lost hhq1
    metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts_disp',y_diff,dbp] = tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq1_2050'].sum()

    metrics_dict[runid,metric_id,'DispRisk_PBA40_DRCoCHRAtracts',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_LIHH_inDRCoCHRAtracts',y2,dbp]   


    #For both Q1, Q2 - because this is how it was done in PBA40
    metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts',y2,dbp] = tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq1_2050'].sum() + \
                                                                         tract_sum_df.loc[((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)), 'hhq2_2050'].sum() 

    metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts_disp',y_diff,dbp] = tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq1_2050'].sum() + \
                                                                                  tract_sum_df.loc[(((tract_sum_df['DispRisk'] == 1)|(tract_sum_df['coc_flag_pba2050'] == 1)|\
                                                                                        (tract_sum_df['hra'] == 1)) & (tract_sum_df['lost_hhq1_abs_0pct'] == 1)), 'hhq2_2050'].sum()

    metrics_dict[runid,metric_id,'DispRisk_PBA40_Q1Q2_DRCoCHRAtracts',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_Q1Q2HH_inDRCoCHRAtracts',y2,dbp]   


    ########### Repeating all above analysis for TRAs

    # Calculating share of Q1 households at TRA level using TRA summary dataframe
    TRA_sum_df['hhq1_pct_2015'] = TRA_sum_df['hhq1_2015'] / TRA_sum_df['tothh_2015'] 
    #TRA_sum_df['hhq1_pct_2015_normalized'] = TRA_sum_df['hhq1_pct_2015'] * normalize_factor_Q1
    TRA_sum_df['hhq1_pct_2050'] = TRA_sum_df['hhq1_2050'] / TRA_sum_df['tothh_2050']

    # Total number of TRAs
    metrics_dict[runid,metric_id,'Num_TRAs_total',y1,dbp] = TRA_sum_df['juris_tra'].nunique()


    # Calculating number of TRAs that Lost LIHH as a share of total HH, with "lost" defined as any loss, or 10% loss

    for i in [0, 10]:
        if i == 0:
            j = 1
        else:
            j = 0.9

        # Calculating change in share of LIHH at TRA level to check gentrification
        TRA_sum_df['lost_hhq1_%dpct' % i] = TRA_sum_df.apply (lambda row: check_losthhq1_share(row,j), axis=1)

        # Calculating absolute change in LIHH at TRA level to check true displacement
        TRA_sum_df['lost_hhq1_abs_%dpct' % i] = TRA_sum_df.apply (lambda row: check_losthhq1_abs(row,j), axis=1)

        ######## Gentrification in TRAs
        # Number or percent of TRAs that lost Q1 households as a share of total HH
        metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_%dpct' % i,y_diff,dbp] = TRA_sum_df.loc[(TRA_sum_df['lost_hhq1_%dpct' % i] == 1), 'juris_tra'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAs_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAs_total',y1,dbp])
        print('Number of TRAs that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of TRAs that lost LIHH (as a share) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAs_lostLIHH_%dpct' % i,y_diff,dbp] )

        ######## Displacement in TRAs
        # Number or percent of DR tracts that lost Q1 households in absolute numbers
        metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_abs_%dpct' % i,y_diff,dbp] = TRA_sum_df.loc[(TRA_sum_df['lost_hhq1_abs_%dpct' % i] == 1), 'juris_tra'].nunique()
        metrics_dict[runid,metric_id,'Pct_TRAs_lostLIHH_abs_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_abs_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_TRAs_total',y1,dbp])
        print('Number of TRAs that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_TRAs_lostLIHH_abs_%dpct' % i,y_diff,dbp] )
        print('Pct of TRAs that lost LIHH (in absolute numbers) from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_TRAs_lostLIHH_abs_%dpct' % i,y_diff,dbp] )

    ######## PBA40 Displacement Risk metric in TRAs
    metrics_dict[runid,metric_id,'Num_LIHH_inTRAs',y2,dbp] = TRA_sum_df['hhq1_2050'].sum()
    metrics_dict[runid,metric_id,'Num_LIHH_inTRAs_disp',y_diff,dbp] = TRA_sum_df.loc[(TRA_sum_df['lost_hhq1_abs_0pct'] == 1), 'hhq1_2050'].sum()
    metrics_dict[runid,metric_id,'DispRisk_PBA40_TRAs',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_LIHH_inTRAs_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_LIHH_inTRAs',y2,dbp]   

    metrics_dict[runid,metric_id,'Num_Q1Q2HH_inTRAs',y2,dbp] = TRA_sum_df['hhq1_2050'].sum() + TRA_sum_df['hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'Num_Q1Q2_inTRAs_disp',y_diff,dbp] = TRA_sum_df.loc[(TRA_sum_df['lost_hhq1_abs_0pct'] == 1), 'hhq1_2050'].sum() + TRA_sum_df.loc[(TRA_sum_df['lost_hhq1_abs_0pct'] == 1), 'hhq2_2050'].sum()
    metrics_dict[runid,metric_id,'DispRisk_PBA40_Q1Q2_TRAs',y_diff,dbp] = metrics_dict[runid,metric_id,'Num_Q1Q2_inTRAs_disp',y_diff,dbp] / \
                                                                                metrics_dict[runid,metric_id,'Num_Q1Q2HH_inTRAs',y2,dbp]   



    ######## Displacement from Growth Geographies

    # Calculating GG rows that lost inc1 Households
    GG_sum_df['hhq1_pct_2015'] = GG_sum_df['hhq1_2015'] / GG_sum_df['tothh_2015'] 
    #GG_sum_df['hhq1_pct_2015_normalized'] = GG_sum_df['hhq1_pct_2015'] * normalize_factor_Q1
    GG_sum_df['hhq1_pct_2050'] = GG_sum_df['hhq1_2050'] / GG_sum_df['tothh_2050']

    # Total number of GGs
    metrics_dict[runid,metric_id,'Num_GGs_total',y1,dbp] = GG_sum_df['PDA_ID'].nunique()
    # Total number of Transit Rich GGs
    GG_TRich_sum_df = GG_sum_df[GG_sum_df['Designation']=="Transit-Rich"]
    metrics_dict[runid,metric_id,'Num_GGs_TRich_total',y1,dbp] = GG_TRich_sum_df['PDA_ID'].nunique()


    # Calculating number of GGs that Lost LIHH as a share of total HH, with "lost" defined as any loss, or 10% loss

    for i in [0, 10]:
        if i == 0:
            j = 1
        else:
            j = 0.9
        GG_sum_df['lost_hhq1_%dpct' % i] = GG_sum_df.apply (lambda row: check_losthhq1_share(row,j), axis=1)
        GG_TRich_sum_df['lost_hhq1_%dpct' % i] = GG_TRich_sum_df.apply (lambda row: check_losthhq1_share(row,j), axis=1)

        # Number or percent of GGs that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp] = GG_sum_df.loc[(GG_sum_df['lost_hhq1_%dpct' % i] == 1), 'PDA_ID'].nunique()
        metrics_dict[runid,metric_id,'Pct_GG_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGs_total',y1,dbp])
        print('Number of GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GG_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GG_lostLIHH_%dpct' % i,y_diff,dbp] )

        # Number or percent of Transit Rich GGs that lost Q1 households as a proportion of total HH
        metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] = GG_TRich_sum_df.loc[(GG_TRich_sum_df['lost_hhq1_%dpct' % i] == 1), 'PDA_ID'].nunique()
        metrics_dict[runid,metric_id,'Pct_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] = float(metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp]) / float(metrics_dict[runid,metric_id,'Num_GGs_TRich_total',y1,dbp])
        print('Number of Transit Rich GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Num_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] )
        print('Pct of Transit Rich GGs that lost LIHH from 2015 to 2050: ',metrics_dict[runid,metric_id,'Pct_GG_TRich_lostLIHH_%dpct' % i,y_diff,dbp] )



def calculate_Healthy1_HHs_SLRprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H1"

    # Renaming Parcels as "Protected", "Unprotected", and "Unaffected"
    '''
    #Basic
    def label_SLR(row):
        if (row['SLR'] == 12): return 'Unprotected'
        elif (row['SLR'] == 24): return 'Unprotected'
        elif (row['SLR'] == 36): return 'Unprotected'
        elif (row['SLR'] == 100): return 'Protected'
        else: return 'Unaffected'
    parcel_sum_df['SLR_protection'] = parcel_sum_df.apply (lambda row: label_SLR(row), axis=1)
    '''
    def label_SLR(row):
        if ((row['SLR'] == 12) or (row['SLR'] == 24)  or (row['SLR'] == 36)): return 'Unprotected'
        elif row['SLR'] == 100: return 'Protected'
        else: return 'Unaffected'
    parcel_sum_df['SLR_protection'] = parcel_sum_df.apply (lambda row: label_SLR(row), axis=1)

    # Calculating protected households

    # All households
    tothh_2050_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'tothh_2050'].sum()
    tothh_2050_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'tothh_2050'].sum()
    tothh_2015_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'tothh_2015'].sum()
    tothh_2015_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'tothh_2015'].sum()

    # Q1 Households
    hhq1_2050_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'hhq1_2050'].sum()
    hhq1_2050_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'hhq1_2050'].sum()
    hhq1_2015_affected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("rotected") == True), 'hhq1_2015'].sum()
    hhq1_2015_protected = parcel_sum_df.loc[(parcel_sum_df['SLR_protection'].str.contains("Protected") == True), 'hhq1_2015'].sum()

    # CoC Households

    CoChh_2050_affected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("rotected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2050'].sum()
    CoChh_2050_protected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("Protected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2050'].sum()
    CoChh_2015_affected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("rotected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2015'].sum()
    CoChh_2015_protected = parcel_sum_df.loc[((parcel_sum_df['SLR_protection'].str.contains("Protected") == True) & \
                                             parcel_sum_df['coc_flag_pba2050']==1), 'tothh_2015'].sum()

    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_tothh',y2,dbp] = tothh_2050_protected / tothh_2050_affected
    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_hhq1',y2,dbp] = hhq1_2050_protected / hhq1_2050_affected
    metrics_dict[runid,metric_id,'SLR_protected_pct_affected_CoChh',y2,dbp] = CoChh_2050_protected / CoChh_2050_affected

    print('********************H1 Healthy********************')
    print('Pct of HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_tothh',y2,dbp])
    print('Pct of Q1 HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_hhq1',y2,dbp])
    print('Pct of CoC HHs affected by 3ft SLR that are protected in 2050 in %s' % dbp,metrics_dict[runid,metric_id,'SLR_protected_pct_affected_CoChh',y2,dbp])


def calculate_Healthy1_HHs_EQprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H1"

    '''
    # Reading building codes file, which has info at building level, on which parcels are inundated and protected

    buildings_code = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Healthy/buildings_with_eq_code.csv')
    buildings_eq = pd.merge(left=buildings_code[['building_id', 'parcel_id', 'residential_units', 'year_built', 'earthquake_code']], right=parcel_sum_df[['parcel_id','zone_id','tract_id','coc_flag_pba2050','pba50chcat','hhq1_2015','hhq1_2050','tothh_2015','tothh_2050']], left_on="parcel_id", right_on="parcel_id", how="left")
    buildings_eq = pd.merge(left=buildings_eq, right=coc_flag[['tract_id_coc','county_fips']], left_on="tract_id", right_on="tract_id_coc", how="left")
    buildings_cat = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Healthy/building_eq_categories.csv')
    buildings_eq = pd.merge(left=buildings_eq, right=buildings_cat, left_on="earthquake_code", right_on="building_eq_code", how="inner")
    buildings_eq.drop(['building_eq_code', 'tract_id_coc'], axis=1, inplace=True)
    buildings_eq['cost_retrofit_total'] = buildings_eq['residential_units'] * buildings_eq['cost_retrofit']

    # Calculated protected households in PLus

    # Number of Units retrofitted
    metrics_dict['H2_eq_num_units_retrofit'] = buildings_eq['residential_units'].sum()
    metrics_dict['H2_eq_num_CoC_units_retrofit'] = buildings_eq.loc[(buildings_eq['coc_flag_pba2050']== 1), 'residential_units'].sum()

    metrics_dict['H2_eq_total_cost_retrofit'] = buildings_eq['cost_retrofit_total'].sum()
    metrics_dict['H2_eq_CoC_cost_retrofit'] = buildings_eq.loc[(buildings_eq['coc_flag_pba2050']== 1), 'cost_retrofit_total'].sum()

    print('Total number of units retrofited',metrics_dict['H2_eq_num_units_retrofit'])
    print('CoC number of units retrofited',metrics_dict['H2_eq_num_CoC_units_retrofit'])

    print('Total cost of retrofit',metrics_dict['H2_eq_total_cost_retrofit'])
    print('CoC cost of retrofit',metrics_dict['H2_eq_CoC_cost_retrofit'])
    '''


def calculate_Healthy1_HHs_WFprotected(runid, dbp, parcel_sum_df, metrics_dict):

    metric_id = "H1"

    '''
    # 
    '''


def calculate_Healthy1_safety(runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict):

    metric_id = "H1"
    population = tm_taz_input_df.TOTPOP.sum()
    per_x_people = 1000000
    print('population %d' % population)

    fatalities   = safety_df.loc[(safety_df['index']=="N_total_fatalities")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_m = safety_df.loc[(safety_df['index']=="N_motorist_fatalities")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_b = safety_df.loc[(safety_df['index']=="N_bike_fatalities")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    fatalities_p = safety_df.loc[(safety_df['index']=="N_ped_fatalities")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    injuries     = safety_df.loc[(safety_df['index']=="N_injuries")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
                                                                               
    metrics_dict[runid,metric_id,'fatalities_annual_per_MNppl',year,dbp]         = fatalities   / population * per_x_people
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_MNppl',year,dbp]    = fatalities_m / population * per_x_people
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_MNppl',year,dbp]    = fatalities_b / population * per_x_people 
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_MNppl',year,dbp]     = fatalities_p / population * per_x_people 
    metrics_dict[runid,metric_id,'injuries_annual_per_MNppl',year,dbp]           = injuries     / population * per_x_people 

    metrics_dict[runid,metric_id,'fatalities_annual_per_100MVMT',year,dbp]         = safety_df.loc[(safety_df['index']=="N_total_fatalities_per_100M_VMT")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_motorist_fatalities_per_100M_VMT")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_bike_fatalities_per_100M_VMT")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100MVMT',year,dbp]     = safety_df.loc[(safety_df['index']=="N_ped_fatalities_per_100M_VMT")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'injuries_annual_per_100MVMT',year,dbp]           = safety_df.loc[(safety_df['index']=="N_injuries_per_100M_VMT")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()



def calculate_Healthy2_emissions(runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict):

    metric_id = "H2"
    population = tm_taz_input_df.TOTPOP.sum()

    tm_auto_times_df = tm_auto_times_df.sum(level='Mode')
    dailyVMT = tm_auto_times_df['Vehicle Miles'].sum() - tm_auto_times_df.loc['truck', ['Vehicle Miles']].sum()

    metrics_dict[runid,metric_id,'daily_vmt_per_capita',year,dbp] = dailyVMT / population 

    metrics_dict[runid,metric_id,'daily_vmt_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'VMT per capita'].sum() 
    metrics_dict[runid,metric_id,'daily_vmt_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'VMT per capita'].sum() 

    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2015","2015"] = emfac_df.loc[(emfac_df['dbp']==2015), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_lbs_per_capita',"2050","Plus"] = 0

    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2005","2005"] = emfac_df.loc[(emfac_df['dbp']==2005), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2015","2015"] = emfac_df.loc[(emfac_df['dbp']==2015), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2035","2035"] = emfac_df.loc[(emfac_df['dbp']==2035), 'Total CO2 Emissions Per Capita (lbs)'].sum() 
    metrics_dict["emfac_hardcode",metric_id,'ghg_emissions_nonSB375_lbs_per_capita',"2050","Plus"] = 0


def calculate_Vibrant1_JobsHousing(runid, dbp, county_sum_df, metrics_dict):
    
    metric_id = "V1"
    
    metrics_dict[runid,metric_id,'jobs_housing_ratio_region',y1,dbp] = county_sum_df['totemp_2015'].sum() / county_sum_df['tothh_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_housing_ratio_region',y2,dbp] = county_sum_df['totemp_2050'].sum() / county_sum_df['tothh_2050'].sum()

    for index,row in county_sum_df.iterrows():
        metrics_dict[runid,metric_id,'jobs_housing_ratio_%s' % row['county'],y1,dbp] = row['totemp_2015'] / row['tothh_2015'] 
        metrics_dict[runid,metric_id,'jobs_housing_ratio_%s' % row['county'],y2,dbp] = row['totemp_2050'] / row['tothh_2050'] 


def calculate_Vibrant1_median_commute(runid, year, dbp, tm_commute_df, metrics_dict):
    
    metric_id = "V1"

    tm_commute_df['total_commute_miles'] = tm_commute_df['freq'] * tm_commute_df['distance']
   
    commute_dist_df = tm_commute_df[['incQ','freq','total_commute_miles']].groupby(['incQ']).sum()
        
    metrics_dict[runid,metric_id,'mean_commute_distance',year,dbp] = commute_dist_df['total_commute_miles'].sum() / commute_dist_df['freq'].sum()
    metrics_dict[runid,metric_id,'mean_commute_distance_inc1',year,dbp] = commute_dist_df['total_commute_miles'][1] / commute_dist_df['freq'][1] 
    metrics_dict[runid,metric_id,'mean_commute_distance_inc2',year,dbp] = commute_dist_df['total_commute_miles'][2] / commute_dist_df['freq'][2]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc3',year,dbp] = commute_dist_df['total_commute_miles'][3] / commute_dist_df['freq'][3]
    metrics_dict[runid,metric_id,'mean_commute_distance_inc4',year,dbp] = commute_dist_df['total_commute_miles'][4] / commute_dist_df['freq'][4]


def calculate_Vibrant2_Jobs(runid, dbp, parcel_sum_df, metrics_dict):


    metric_id = 'V2'
    print('********************V2 Vibrant********************')

    # Total Jobs Growth

    metrics_dict[runid,metric_id,'Total_jobs',y2,dbp] = parcel_sum_df['totemp_2050'].sum()
    metrics_dict[runid,metric_id,'Total_jobs',y1,dbp] = parcel_sum_df['totemp_2015'].sum()
    metrics_dict[runid,metric_id,'Total_jobs_growth',y_diff,dbp] = metrics_dict[runid,metric_id,'Total_jobs',y2,dbp]/metrics_dict[runid,metric_id,'Total_jobs',y1,dbp] - 1
    print('Number of Jobs in 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs',y2,dbp])
    print('Number of Jobs in 2015 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs',y1,dbp])
    print('Job Growth from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs_growth',y_diff,dbp])

    # MWTEMPN jobs
    metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp] = parcel_sum_df['MWTEMPN_2050'].sum()
    metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp] = parcel_sum_df['MWTEMPN_2015'].sum()
    metrics_dict[runid,metric_id,'Total_jobs_growth_MWTEMPN',y_diff,dbp] = metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp]/metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp] - 1
    print('Number of Total MWTEMPN Jobs 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y2,dbp])
    print('Number of Total MWTEMPN Jobs 2015 %s' % dbp,metrics_dict[runid,metric_id,'Total_MWTEMPN_jobs',y1,dbp])
    print('Job Growth Total MWTEMPN from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'Total_jobs_growth_MWTEMPN',y_diff,dbp])


    # Jobs Growth in PPAs

    metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'totemp_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'totemp_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_PPA',y_diff,dbp] = metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp]/metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp] - 1
    print('Number of Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y2,dbp])
    print('Number of Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_jobs',y1,dbp])
    print('Job Growth in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobs_growth_PPA',y_diff,dbp])

    '''
    AGREMPN = Agriculture & Natural Resources 
    MWTEMPN = Manufacturing & Wholesale, Transportation & Utilities 
    RETEMPN = Retail 
    FPSEMPN = Financial & Leasing, Professional & Managerial Services 
    HEREMPN = Health & Educational Services 
    OTHEMPN = Construction, Government, Information 
    totemp = total employment
    '''
    # Jobs Growth MWTEMPN in PPAs (Manufacturing & Wholesale, Transportation & Utilities)

    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'MWTEMPN_2050'].sum()
    metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('ppa', na=False), 'MWTEMPN_2015'].sum()
    metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp] = metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp]/metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp] - 1
    print('Number of MWTEMPN Jobs in PPAs 2050 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y2,dbp])
    print('Number of MWTEMPN Jobs in PPAs 2015 %s' % dbp,metrics_dict[runid,metric_id,'PPA_MWTEMPN_jobs',y1,dbp])
    print('Job Growth MWTEMPN in PPAs from 2015 to 2050 %s' % dbp,metrics_dict[runid,metric_id,'jobs_growth_MWTEMPN_PPA',y_diff,dbp])


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


def parcel_building_output_sum(urbansim_runid):

    #################### creating parcel level df from buildings output

    building_output_2050 = pd.read_csv((urbansim_runid+'_building_data_2050.csv'))
    building_output_2015 = pd.read_csv((urbansim_runid+'_building_data_2015.csv'))

    parcel_building_output_2050 = building_output_2050[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2015 = building_output_2015[['parcel_id','residential_units','deed_restricted_units']].groupby(['parcel_id']).sum()
    parcel_building_output_2050 = parcel_building_output_2050.add_suffix('_2050')
    parcel_building_output_2015 = parcel_building_output_2015.add_suffix('_2015')
    return pd.merge(left=parcel_building_output_2050, right=parcel_building_output_2015, left_on="parcel_id", right_on="parcel_id", how="left")
    


def calc_pba40urbansim():


    urbansim_runid = 'C:/Users/{}/Box/Modeling and Surveys/Share Data/plan-bay-area-2040/RTP17 UrbanSim Output/r7224c/run7224'.format(os.getenv('USERNAME'))
    runid          = "plan-bay-area-2040/RTP17 UrbanSim Output/r7224c/run7224"
    dbp            = "PBA40"

    metric_id = "Overall"
    year2     = "2040"
    year1     = "2010"
    yeardiff  = "2040"

    parcel_geo_df  = pd.read_csv(parcel_geography_file)


    ################## Creating parcel summary

    hhq_list = ['hhq1','hhq2','hhq3','hhq4']
    emp_list = ['AGREMPN','MWTEMPN','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN']
    
    parcel_output_2040_df = pd.read_csv((urbansim_runid+'_parcel_data_2040.csv'))
    parcel_output_2040_df['tothh'] = parcel_output_2040_df[hhq_list].sum(axis=1, skipna=True)
    parcel_output_2040_df['totemp'] = parcel_output_2040_df[emp_list].sum(axis=1, skipna=True)


    parcel_output_2010_df = pd.read_csv((urbansim_runid+'_parcel_data_2010.csv'))
    parcel_output_2010_df['tothh'] = parcel_output_2010_df[hhq_list].sum(axis=1, skipna=True)
    parcel_output_2010_df['totemp'] = parcel_output_2010_df[emp_list].sum(axis=1, skipna=True)

    # keeping essential columns / renaming columns
    parcel_output_2040_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type_id'], axis=1, inplace=True)
    parcel_output_2010_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type_id'], axis=1, inplace=True)
    parcel_output_2040_df = parcel_output_2040_df.add_suffix('_2040')
    parcel_output_2010_df = parcel_output_2010_df.add_suffix('_2010')

    # creating parcel summaries with 2040 and 2010 outputs, and parcel geographic categories 
    parcel_sum_df = pd.merge(left=parcel_output_2040_df, right=parcel_output_2010_df, left_on="parcel_id_2040", right_on="parcel_id_2010", how="left")
    parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_geo_df[['pba50chcat','PARCEL_ID']], left_on="parcel_id_2040", right_on="PARCEL_ID", how="left")
    parcel_sum_df.drop(['PARCEL_ID', 'parcel_id_2010'], axis=1, inplace=True)
    parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2040': 'parcel_id'})


    #################### Housing

    # all households
    metrics_dict[runid,metric_id,'TotHH_region',year2,dbp] = parcel_sum_df['tothh_2040'].sum()
    metrics_dict[runid,metric_id,'TotHH_region',year1,dbp] = parcel_sum_df['tothh_2010'].sum()
    metrics_dict[runid,metric_id,'TotHH_growth_region',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_region',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_region',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] = parcel_sum_df['tothh_2040'].sum() - parcel_sum_df['tothh_2010'].sum()

    # HH Growth in HRAs
    metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2040'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'tothh_2010'].sum() 
    metrics_dict[runid,metric_id,'TotHH_HRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_HRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotHH_HRA',year2,dbp] - metrics_dict[runid,metric_id,'TotHH_HRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] 

    # HH Growth in TRAs
    metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2040'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'tothh_2010'].sum() 
    metrics_dict[runid,metric_id,'TotHH_TRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] / metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotHH_TRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotHH_TRA',year2,dbp] - metrics_dict[runid,metric_id,'TotHH_TRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotHH_growth_region_number',yeardiff,dbp] 


    #################### Jobs

    # all jobs
    metrics_dict[runid,metric_id,'TotJobs_region',year2,dbp] = parcel_sum_df['totemp_2040'].sum()
    metrics_dict[runid,metric_id,'TotJobs_region',year1,dbp] = parcel_sum_df['totemp_2010'].sum()
    metrics_dict[runid,metric_id,'TotJobs_growth_region',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_region',year2,dbp]  / metrics_dict[runid,metric_id,'TotJobs_region',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] = parcel_sum_df['totemp_2040'].sum() - parcel_sum_df['totemp_2010'].sum()

    # Job Growth in HRAs
    metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'totemp_2040'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('HRA', na=False), 'totemp_2010'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_HRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] / metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_HRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_HRA',year2,dbp] - metrics_dict[runid,metric_id,'TotJobs_HRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] 

    # Job Growth in TRAs
    metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'totemp_2040'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp] = parcel_sum_df.loc[parcel_sum_df['pba50chcat'].str.contains('tra', na=False), 'totemp_2010'].sum() 
    metrics_dict[runid,metric_id,'TotJobs_TRA_growth',yeardiff,dbp] = metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] / metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp] - 1
    metrics_dict[runid,metric_id,'TotJobs_TRA_shareofgrowth',yeardiff,dbp] = (metrics_dict[runid,metric_id,'TotJobs_TRA',year2,dbp] - metrics_dict[runid,metric_id,'TotJobs_TRA',year1,dbp]) / metrics_dict[runid,metric_id,'TotJobs_growth_region_number',yeardiff,dbp] 



def calc_urbansim_metrics():

    parcel_geo_df               = pd.read_csv(parcel_geography_file)
    parcel_tract_crosswalk_df   = pd.read_csv(parcel_tract_crosswalk_file)
    parcel_PDA_xwalk_df         = pd.read_csv(parcel_PDA_xwalk_file)
    parcel_TRA_xwalk_df         = pd.read_csv(parcel_TRA_xwalk_file)
    parcel_HRA_xwalk_df         = pd.read_csv(parcel_HRA_xwalk_file)
    parcel_GG_xwalk_df          = pd.read_csv(parcel_GG_crosswalk_file)
    tract_HRA_xwalk_df          = pd.read_csv(tract_HRA_xwalk_file)
    udp_DR_df                   = pd.read_csv(udp_file)
    coc_flag_df                 = pd.read_csv(coc_flag_file)
    #slr_basic                   = pd.read_csv(slr_basic_file)
    slr_plus                    = pd.read_csv(slr_plus_file)

    for us_runid in list_us_runid:

        urbansim_runid = urbansim_run_location + us_runid

        if "s20" in urbansim_runid:
            dbp = "NoProject"
        elif "s21" in urbansim_runid:
            dbp = "Basic"
        elif "s22" in urbansim_runid:
            dbp = "Plus"
        elif  "s23" in urbansim_runid:
            dbp = "Plus"
        else:
            dbp = "Unknown"

        # Temporary forcing until we have a Plus run
        #urbansim_runid     = urbansim_run_location + 'Blueprint Basic (s21)/v1.5/run939'
        
        #################### creating parcel level df from buildings output

        parcel_building_output_sum_df = parcel_building_output_sum(urbansim_runid)


        #################### Creating parcel summary

        parcel_output_2050_df = pd.read_csv((urbansim_runid+'_parcel_data_2050.csv'))
        parcel_output_2015_df = pd.read_csv((urbansim_runid+'_parcel_data_2015.csv'))
        # keeping essential columns / renaming columns
        parcel_output_2050_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2015_df.drop(['x','y','zoned_du','zoned_du_underbuild', 'zoned_du_underbuild_nodev', 'first_building_type'], axis=1, inplace=True)
        parcel_output_2050_df = parcel_output_2050_df.add_suffix('_2050')
        parcel_output_2015_df = parcel_output_2015_df.add_suffix('_2015')

        # creating parcel summaries with 2050 and 2015 outputs, and parcel geographic categories 
        parcel_sum_df = pd.merge(left=parcel_output_2050_df, right=parcel_output_2015_df, left_on="parcel_id_2050", right_on="parcel_id_2015", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_building_output_sum_df, left_on="parcel_id_2050", right_on="parcel_id", how="left")
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_geo_df[['pba50chcat','PARCEL_ID']], left_on="parcel_id_2050", right_on="PARCEL_ID", how="left")
        parcel_sum_df.drop(['PARCEL_ID', 'parcel_id_2015'], axis=1, inplace=True)
        parcel_sum_df = parcel_sum_df.rename(columns={'parcel_id_2050': 'parcel_id'})

        # merging with PDA crosswalk; because pba50chcat indicates whether the parcel is a GG, TRA, HRA, DR, but not whether it is a jurisdiction nominated PDA
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_PDA_xwalk_df, left_on="parcel_id", right_on="parcel_id", how="left")


        ################### Create tract summary
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_tract_crosswalk_df[['parcel_id','zone_id','tract_id','county']], left_on="parcel_id", right_on="parcel_id", how="left")
        tract_sum_df = parcel_sum_df.groupby(["tract_id"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()

        #### Adding flags at tract level for DR, CoC and HRA

        # Adding displacement risk by tract from UDP
        tract_sum_df = pd.merge(left=tract_sum_df, right=udp_DR_df[['Tract','DispRisk']], left_on="tract_id", right_on="Tract", how="left")

        # Adding CoC flag to tract_sum_df
        tract_sum_df = pd.merge(left=tract_sum_df, right=coc_flag_df[['tract_id','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id", how="left")
 
        # Adding HRA by tract
        tract_sum_df = pd.merge(left=tract_sum_df, right=tract_HRA_xwalk_df[['tract_id','hra']], left_on="tract_id", right_on="tract_id", how="left")


        # Adding CoC flag to parcel_sum_df as well, cuz, why not
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=coc_flag_df[['tract_id','coc_flag_pba2050']], left_on="tract_id", right_on="tract_id", how="left")


        ################### Create county summary
        county_sum_df = parcel_sum_df.groupby(["county"])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015","totemp_2050","totemp_2015"].sum().reset_index()
        county_sum_df["tothh_growth"] = county_sum_df['tothh_2050'] / county_sum_df['tothh_2015']
        county_sum_df["totemp_growth"] = county_sum_df['totemp_2050'] / county_sum_df['totemp_2015']
        county_sum_df["LIHH_share_2050"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / county_sum_df['tothh_2050']
        county_sum_df["LIHH_share_2015"] = (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015']) / county_sum_df['tothh_2015']
        county_sum_df["LIHH_growth"] = (county_sum_df['hhq1_2050'] + county_sum_df['hhq2_2050']) / (county_sum_df['hhq1_2015'] + county_sum_df['hhq2_2015'])

      
        ################### Create Growth Geography summary
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_GG_xwalk_df[['PARCEL_ID','PDA_ID','Designation']], left_on="parcel_id", right_on="PARCEL_ID", how="left")
        parcel_sum_df.drop(['PARCEL_ID',], axis=1, inplace=True)
        GG_sum_df = parcel_sum_df.groupby(['Designation','PDA_ID'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()
        GG_sum_df = GG_sum_df[(GG_sum_df['PDA_ID']!="na") & (GG_sum_df['Designation']!="Removed")]
        GG_type_sum_df = GG_sum_df.groupby(['Designation'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015"].sum().reset_index()


        ################### Create TRA summary
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=parcel_TRA_xwalk_df, left_on="parcel_id", right_on="parcel_id", how="left")
        TRA_sum_df = parcel_sum_df.groupby(['juris_tra'])["tothh_2050","tothh_2015","hhq1_2050", "hhq1_2015","hhq2_2050", "hhq2_2015"].sum().reset_index()

        '''
        ################### Merging SLR data with parcel summary file
        #if "Basic" in dbp:
        #    parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_basic, left_on="parcel_id", right_on="ParcelID", how="left")
        #    parcel_sum_df = parcel_sum_df.rename(columns={'Basic': 'SLR'})
        #else:
        parcel_sum_df = pd.merge(left=parcel_sum_df, right=slr_plus, left_on="parcel_id", right_on="ParcelID", how="left")
        parcel_sum_df = parcel_sum_df.rename(columns={'SLR_basic': 'SLR'})
        parcel_sum_df.drop(['ParcelID'], axis=1, inplace=True)
        '''

        normalize_factor_Q1Q2  = calculate_normalize_factor_Q1Q2(parcel_sum_df)
        normalize_factor_Q1    = calculate_normalize_factor_Q1(parcel_sum_df)


        print("Starting urbansim metrics functions...")
        calculate_urbansim_highlevelmetrics(us_runid, dbp, parcel_sum_df, county_sum_df, metrics_dict)
        calculate_Affordable2_deed_restricted_housing(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Diverse1_LIHHinHRAs(us_runid, dbp, parcel_sum_df, tract_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict)
        calculate_Diverse2_LIHH_Displacement(us_runid, dbp, parcel_sum_df, tract_sum_df, TRA_sum_df, GG_sum_df, normalize_factor_Q1Q2, normalize_factor_Q1, metrics_dict)
        #calculate_Healthy1_HHs_SLRprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_EQprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        #calculate_Healthy1_HHs_WFprotected(us_runid, dbp, parcel_sum_df, metrics_dict)
        calculate_Vibrant1_JobsHousing(us_runid, dbp, county_sum_df, metrics_dict)
        calculate_Vibrant2_Jobs(us_runid, dbp, parcel_sum_df, metrics_dict)


def calc_travelmodel_metrics():

    coc_flag_df                 = pd.read_csv(coc_flag_file)
    transit_operator_df         = pd.read_csv(transit_operator_file)
    hwy_corridor_links_df       = pd.read_csv(hwy_corridor_links_file)
    safety_df                   = pd.read_csv(safety_file)
    emfac_df                    = pd.read_csv(emfac_file)

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
        tm_travel_cost_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/TravelCost.csv')
        tm_commute_df = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv')
        tm_taz_input_df = pd.read_csv(tm_run_location+tm_runid+'/INPUT/landuse/tazData.csv')


        calculate_Affordable1_transportation_costs(tm_runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, metrics_dict)
        print("@@@@@@@@@@@@@ A1 Done")
        calculate_Connected1_accessibility(tm_runid, year, dbp, tm_scen_metrics_df, metrics_dict)
        print("@@@@@@@@@@@@@ C1 Done")
        calculate_Connected2_hwy_traveltimes(tm_runid, year, dbp, hwy_corridor_links_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2hwy Done")
        calculate_Connected2_trn_traveltimes(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2trn Done")
        calculate_Connected2_crowding(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2crowding Done")
        calculate_Healthy1_safety(tm_runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict)
        print("@@@@@@@@@@@@@ H1 Done")
        calculate_Healthy2_emissions(tm_runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict)
        print("@@@@@@@@@@@@@ H2 Done")
        calculate_Vibrant1_median_commute(tm_runid, year, dbp, tm_commute_df, metrics_dict)
        print("@@@@@@@@@@@@@ V1 Done")

        print("@@@@@@@@@@@@@%s Done"% dbp)
    
    calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict)



if __name__ == '__main__':

    #pd.set_option('display.width', 500)


    # Set UrbanSim inputs
    urbansim_run_location           = 'C:/Users/{}/Box/Modeling and Surveys/Urban Modeling/Bay Area UrbanSim 1.5/PBA50/Draft Blueprint runs/'.format(os.getenv('USERNAME'))
    #us_2050_DBP_NoProject_runid    = 'Blueprint Basic (s21)/v1.5/run939'
    #us_2050_DBP_Basic_runid        = 'Blueprint Basic (s21)/v1.5/run939'
    us_2050_DBP_Plus_runid          = 'Blueprint Plus Crossing (s23)/v1.7.1- FINAL DRAFT BLUEPRINT/run98'
    #us_2050_DBP_Plus_runid         = 'Blueprint Basic (s21)/v1.5/run939'
    list_us_runid = [us_2050_DBP_Plus_runid]
    #urbansim_runid = urbansim_run_location + runid

    # Set Travel model inputs
    tm_run_location_bp = 'M:/Application/Model One/RTP2021/Blueprint/'
    tm_run_location_ipa = 'M:/Application/Model One/RTP2021/IncrementalProgress/'
    tm_2015_runid                     = '2015_TM152_IPA_16'
    tm_2050_DBP_NoProject_runid       = '2050_TM152_DBP_NoProject_08'
    #tm_2050_DBP_Basic_runid           = '2050_TM152_DBP_Basic_01_AV25'
    tm_2050_DBP_PlusCrossing_runid    = '2050_TM152_DBP_PlusCrossing_08'
    #tm_2050_DBP_PlusFixItFirst_runid = '2050_TM152_DBP_PlusCrossing_01'
    list_tm_runid = [tm_2015_runid, tm_2050_DBP_NoProject_runid, tm_2050_DBP_PlusCrossing_runid]
    list_tm_runid_blueprintonly = [tm_2050_DBP_PlusCrossing_runid]

    # Set external inputs
    metrics_source_folder         = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_files/'.format(os.getenv('USERNAME'))
    parcel_geography_file         = metrics_source_folder + '2020_04_17_parcels_geography.csv'
    parcel_tract_crosswalk_file   = metrics_source_folder + 'parcel_tract_crosswalk.csv'
    parcel_PDA_xwalk_file         = 'M:/Data/GIS layers/Blueprint Land Use Strategies/ID_idx/pda_id_2020.csv'
    parcel_TRA_xwalk_file         = 'M:/Data/GIS layers/Blueprint Land Use Strategies/ID_idx/tra_id_2020_s23.csv'
    parcel_HRA_xwalk_file         = 'M:/Data/GIS layers/Blueprint Land Use Strategies/ID_idx/hra_id_2020.csv'
    parcel_GG_crosswalk_file      = metrics_source_folder + 'parcel_GG_xwalk.csv'
    tract_HRA_xwalk_file          = metrics_source_folder + 'tract_hra_xwalk.csv'
    udp_file                      = metrics_source_folder + 'udp_2017results.csv'
    coc_flag_file                 = metrics_source_folder + 'COCs_ACS2018_tbl_TEMP.csv'
    # These are SLR input files into Urbansim, which has info at parcel ID level, on which parcels are inundated and protected
    slr_basic_file                = metrics_source_folder + 'slr_parcel_inundation_basic.csv'
    slr_plus_file                 = metrics_source_folder + 'slr_parcel_inundation_plus.csv'
    transit_operator_file         = metrics_source_folder + 'transit_system_lookup.csv'
    hwy_corridor_links_file       = metrics_source_folder + 'maj_corridors_hwy_links.csv'
    safety_file                   = metrics_source_folder + 'fatalities_injuries_export.csv'
    emfac_file                    = metrics_source_folder + 'emfac.csv'

    '''
        # Script to create parcel_GG_crosswalk_file that is used above

        # Creating parcel / Growth Geography crosswalk file
        parcel_GG_crosswalk_file = 'M:/Data/GIS layers/Blueprint Land Use Strategies/p10_gg_idxed.csv'
        parcel_GG_crosswalk_df = pd.read_csv(parcel_GG_crosswalk_file)

        parcel_GG_crosswalk_df['PDA_ID'] = parcel_growthgeo_crosswalk_df.apply \
        (lambda row: str(row['County_ID']) + "_" + row['Jurisdiction'][0:5] + "_" + str(int(row['idx'])) \
         if (row['idx']>0) else "na", axis=1)

        parcel_GG_crosswalk_df.drop(['geom_id_s', 'ACRES', 'PDA_Change', 'County', 'County_ID','Jurisdiction', 'idx',], axis=1, inplace=True)

        parcel_GG_crosswalk_df.to_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Diverse/parcel_GG_xwalk.csv', sep=',', index=False)
    '''

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
    #calc_pba40urbansim()
    calc_urbansim_metrics()
    print("*****************#####################Completed urbansim_metrics#####################*******************")
    calc_travelmodel_metrics()
    print("*****************#####################Completed calc_travelmodel_metrics#####################*******************")

    # Write output
    idx = pd.MultiIndex.from_tuples(metrics_dict.keys(), names=['modelrunID','metric','name','year','blueprint'])
    metrics = pd.Series(metrics_dict, index=idx)
    metrics.name = 'value'
    out_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics.csv'.format(os.getenv('USERNAME'))
    metrics.to_csv(out_filename, header=True, sep=',')
    
    print("Wrote metrics.csv output")

    