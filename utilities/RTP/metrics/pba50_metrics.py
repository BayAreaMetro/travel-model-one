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

import datetime, os, pathlib, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict


def calculate_Affordable1_HplusT_costs(runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, tm_parking_cost_df, housing_costs_df, metrics_dict):

    metric_id = "A1"

    days_per_year = 300
    UBI_annual = 6000

    # Total number of households
    tm_tot_hh      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_households_inc") == True), 'value'].sum()
    tm_tot_hh_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc1"),'value'].item()
    tm_tot_hh_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_households_inc2"),'value'].item()

    # Total household income (model outputs are in 2000$, annual), adjusting for UBI for Q1 households
    tm_total_hh_inc      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_hh_inc") == True), 'value'].sum()
    tm_total_hh_inc_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc2"),'value'].item()

    if dbp in ["Plus","Alt1","Alt2"] :
        tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item() + (UBI_annual * tm_tot_hh_inc1 / inflation_00_20)
    else:
        tm_total_hh_inc_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()
    
    tm_total_hh_inc_inc1_noubi = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_hh_inc_inc1"),'value'].item()


    # Total transit fares (model outputs are in 2000$, per day)
    tm_tot_transit_fares      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_fares") == True), 'value'].sum() * days_per_year
    tm_tot_transit_fares_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc1"),'value'].item() * days_per_year
    tm_tot_transit_fares_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_fares_inc2"),'value'].item() * days_per_year

    # Total auto op cost (model outputs are in 2000$, per day)
    tm_tot_auto_op_cost      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_cost_inc") == True), 'value'].sum() * days_per_year
    tm_tot_auto_op_cost_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc1"),'value'].item() * days_per_year
    tm_tot_auto_op_cost_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_cost_inc2"),'value'].item() * days_per_year

    '''
    if year=="2015":
        # Total auto parking cost (model outputs are in 2000$, per day, in cents)
        tm_travel_cost_df['parking_cost'] = (tm_travel_cost_df.pcost_indiv + tm_travel_cost_df.pcost_joint) *  tm_travel_cost_df.freq
        tm_tot_auto_park_cost      = tm_travel_cost_df.parking_cost.sum() * days_per_year / 100
        tm_tot_auto_park_cost_inc1 = tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 1),'parking_cost'].sum() * days_per_year / 100
        tm_tot_auto_park_cost_inc2 = tm_travel_cost_df.loc[(tm_travel_cost_df['incQ'] == 2),'parking_cost'].sum() * days_per_year / 100
    else:
    '''
    # Total auto parking cost (model outputs are in 2000$, per day, in dollars)
    tm_tot_auto_park_cost      = tm_parking_cost_df.parking_cost.sum() * days_per_year
    tm_tot_auto_park_cost_inc1 = tm_parking_cost_df.loc[(tm_parking_cost_df['incQ'] == 1),'parking_cost'].sum() * days_per_year
    tm_tot_auto_park_cost_inc2 = tm_parking_cost_df.loc[(tm_parking_cost_df['incQ'] == 2),'parking_cost'].sum() * days_per_year


    # Calculating number of autos owned from autos_owned.csv
    tm_auto_owned_df['tot_autos'] = tm_auto_owned_df['autos'] * tm_auto_owned_df['households'] 
    tm_tot_autos_owned      = tm_auto_owned_df['tot_autos'].sum()
    tm_tot_autos_owned_inc1 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 1), 'tot_autos'].sum()
    tm_tot_autos_owned_inc2 = tm_auto_owned_df.loc[(tm_auto_owned_df['incQ'] == 2), 'tot_autos'].sum()

    # Total auto ownership cost in 2000$   (total annual cost for all households)
    tm_tot_auto_owner_cost      = tm_tot_autos_owned      * auto_ownership_cost      * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc1 = tm_tot_autos_owned_inc1 * auto_ownership_cost_inc1 * inflation_18_20 / inflation_00_20
    tm_tot_auto_owner_cost_inc2 = tm_tot_autos_owned_inc2 * auto_ownership_cost_inc2 * inflation_18_20 / inflation_00_20

    # Total Transportation Cost (in 2000$) (total annual cost for all households)
    tp_cost      = tm_tot_auto_op_cost      + tm_tot_transit_fares      + tm_tot_auto_owner_cost      + tm_tot_auto_park_cost
    tp_cost_inc1 = tm_tot_auto_op_cost_inc1 + tm_tot_transit_fares_inc1 + tm_tot_auto_owner_cost_inc1 + tm_tot_auto_park_cost_inc1
    tp_cost_inc2 = tm_tot_auto_op_cost_inc2 + tm_tot_transit_fares_inc2 + tm_tot_auto_owner_cost_inc2 + tm_tot_auto_park_cost_inc2

    # Transportation cost % of income
    tp_cost_pct_inc          = tp_cost      / tm_total_hh_inc
    tp_cost_pct_inc_inc1     = tp_cost_inc1 / tm_total_hh_inc_inc1
    tp_cost_pct_inc_inc2     = tp_cost_inc2 / tm_total_hh_inc_inc2
    tp_cost_pct_inc_inc1and2 = (tp_cost_inc1+tp_cost_inc2) / (tm_total_hh_inc_inc1+tm_total_hh_inc_inc2)

    tp_cost_pct_inc_inc1_noubi = tp_cost_inc1 / tm_total_hh_inc_inc1_noubi

    # Transportation costs annual, in 2000$, for all households together
    metrics_dict[runid,metric_id,'transportation_cost_totalHHincome',year,dbp] = tm_total_hh_inc
    metrics_dict[runid,metric_id,'transportation_cost_autoop',year,dbp]        = tm_tot_auto_op_cost
    metrics_dict[runid,metric_id,'transportation_cost_autopark',year,dbp]      = tm_tot_auto_park_cost
    metrics_dict[runid,metric_id,'transportation_cost_transitfare',year,dbp]   = tm_tot_transit_fares
    metrics_dict[runid,metric_id,'transportation_cost_autoown',year,dbp]       = tm_tot_auto_owner_cost
 
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
    #housing_costs_2050_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_input_files/2050 Share of Income Spent on Housing.csv')
    #housing_costs_2015_df = pd.read_csv('C:/Users/ATapase/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/metrics_input_files/2015 Share of Income Spent on Housing.csv')
    #housing_costs_2015_df['totcosts'] = housing_costs_2015_df['share_income'] * housing_costs_2015_df['households']
    '''
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
    '''
    metrics_dict[runid,metric_id,'housing_cost_pct_income',year,dbp]       =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_all'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q1'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc2',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q2'].sum()
    metrics_dict[runid,metric_id,'housing_cost_pct_income_inc1and2',year,dbp]  =  housing_costs_df.loc[((housing_costs_df['year']==int(year)) & (housing_costs_df['blueprint'].str.contains(dbp) == True)), 'w_q1_q2'].sum()


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
    total_tolls       = OrderedDict()
    total_opcost      = OrderedDict()
    total_valuetolls  = OrderedDict()
    total_bridgetolls = OrderedDict()
    for inc_level in range(1,5): 
        total_tolls['inc%d'  % inc_level]        = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls', 'Value Tolls']].sum()/100  # cents -> dollars
        total_opcost['inc%d'  % inc_level]       = tm_auto_times_df.loc['inc%d' % inc_level, ['Total Cost']].sum()/100  # cents -> dollars
        total_valuetolls['inc%d'  % inc_level]   = tm_auto_times_df.loc['inc%d' % inc_level, ['Value Tolls']].sum()/100  # cents -> dollars
        total_bridgetolls['inc%d'  % inc_level]  = tm_auto_times_df.loc['inc%d' % inc_level, ['Bridge Tolls']].sum()/100  # cents -> dollars

    total_tolls_allHH        = sum(total_tolls.values())
    total_tolls_inc1and2     = total_tolls['inc1'] + total_tolls['inc2']

    tm_tot_auto_op_cost_fuel_maint   = sum(total_opcost.values())       * days_per_year
    tm_tot_auto_op_cost_valuetolls   = sum(total_valuetolls.values())   * days_per_year
    tm_tot_auto_op_cost_bridgetolls  = sum(total_bridgetolls.values())  * days_per_year
    # this is to make sure the op costs sourced by this script is equal to the op costs calcuated in scenario_metrics.csv
    tm_tot_auto_op_cost_check        = tm_tot_auto_op_cost_fuel_maint + tm_tot_auto_op_cost_valuetolls + tm_tot_auto_op_cost_bridgetolls

    tm_tot_auto_op_cost_fuel_maint_inc1   = total_opcost['inc1']       * days_per_year
    tm_tot_auto_op_cost_valuetolls_inc1   = total_valuetolls['inc1']   * days_per_year
    tm_tot_auto_op_cost_bridgetolls_inc1  = total_bridgetolls['inc1']  * days_per_year
    # this is to make sure the op costs sourced by this script is equal to the op costs calcuated in scenario_metrics.csv
    tm_tot_auto_op_cost_check_inc1        = tm_tot_auto_op_cost_fuel_maint_inc1 + tm_tot_auto_op_cost_valuetolls_inc1 + tm_tot_auto_op_cost_bridgetolls_inc1
    

    # Mean annual transportation cost per household in 2020$

    '''
    # Breakdown of op costs in 2000$   (output is in cents in 2000$)
    tm_tot_auto_op_cost_fuel_maint  = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Total Cost'].sum()   / 100  * days_per_year
    tm_tot_auto_op_cost_valuetolls  = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Value Tolls'].sum()  / 100  * days_per_year
    tm_tot_auto_op_cost_bridgetolls = tm_auto_times_df.loc[(tm_auto_times_df['Income'].str.contains("inc") == True), 'Bridge Tolls'].sum() / 100  * days_per_year
    tm_tot_auto_op_cost_check       = tm_tot_auto_op_cost_fuel_maint + tm_tot_auto_op_cost_valuetolls + tm_tot_auto_op_cost_bridgetolls
    '''
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_numHH',year,dbp]       = tm_tot_hh * inflation_00_20

    # All households
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$',year,dbp]             = tp_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown',year,dbp]     = tm_tot_auto_owner_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop',year,dbp]      = tm_tot_auto_op_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark',year,dbp]    = tm_tot_auto_park_cost / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare',year,dbp] = tm_tot_transit_fares / tm_tot_hh * inflation_00_20

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check',year,dbp]         = tm_tot_auto_op_cost_check / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint  / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls  / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls / tm_tot_hh * inflation_00_20   
    
    # Q1 HHs
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp]             = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown_inc1',year,dbp]     = tm_tot_auto_owner_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_inc1',year,dbp]      = tm_tot_auto_op_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark_inc1',year,dbp]    = tm_tot_auto_park_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare_inc1',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * inflation_00_20

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check_inc1',year,dbp]         = tm_tot_auto_op_cost_check_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint_inc1',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls_inc1',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls_inc1',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_hh_inc1 * inflation_00_20   

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp] = tp_cost_inc1 / tm_tot_hh_inc1 * inflation_00_20
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc2',year,dbp] = tp_cost_inc2 / tm_tot_hh_inc2 * inflation_00_20

    
    
    # Average Daily Tolls per household
    metrics_dict[runid,metric_id,'tolls_per_HH',year,dbp]           = total_tolls_allHH / tm_tot_hh * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1and2HH',year,dbp]   = total_tolls_inc1and2 / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'tolls_per_inc1HH',year,dbp]       = total_tolls['inc1'] / tm_tot_hh_inc1 * inflation_00_20

    # Average Daily Fares per Household   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'fares_per_HH',year,dbp]     = tm_tot_transit_fares / tm_tot_hh * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1and2HH',year,dbp]   = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_hh_inc1+tm_tot_hh_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1HH',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * inflation_00_20 / days_per_year

    

    ####### per trip auto

    # Total auto trips per day (model outputs are in trips, per day)
    tm_tot_auto_trips      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_trips") == True), 'value'].sum()
    tm_tot_auto_trips_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc1"),'value'].item() 
    tm_tot_auto_trips_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_auto_perday',year,dbp]          = tm_tot_auto_trips
    metrics_dict[runid,metric_id,'trips_total_auto_perday_inc1',year,dbp]     = tm_tot_auto_trips_inc1

    # Average Tolls per trip  (total_tolls_xx is calculated above as per day tolls in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_tolls',year,dbp]          = total_tolls_allHH / tm_tot_auto_trips * inflation_00_20
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1and2',year,dbp] = total_tolls_inc1and2 / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1',year,dbp]     = total_tolls['inc1'] / tm_tot_auto_trips_inc1 * inflation_00_20

    # Total auto operating cost per trip (tm_tot_auto_op_cost and tm_tot_auto_park_cost are calculated above as annual costs in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_autocost',year,dbp]           = (tm_tot_auto_op_cost + tm_tot_auto_park_cost) / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_park',year,dbp]      = tm_tot_auto_park_cost / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op',year,dbp]        = tm_tot_auto_op_cost / tm_tot_auto_trips * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_op_check',year,dbp]             = tm_tot_auto_op_cost_check / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_fuel_maint',year,dbp]        = tm_tot_auto_op_cost_fuel_maint / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_valuetolls',year,dbp]        = tm_tot_auto_op_cost_valuetolls / tm_tot_auto_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_bridgetolls',year,dbp]       = tm_tot_auto_op_cost_bridgetolls / tm_tot_auto_trips * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_park_cost_inc1) / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year 
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op',year,dbp]               = tm_tot_auto_op_cost_inc1             / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_check',year,dbp]         = tm_tot_auto_op_cost_check_inc1       / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_park',year,dbp]             = tm_tot_auto_park_cost_inc1           / tm_tot_auto_trips_inc1 * inflation_00_20 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1and2',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_op_cost_inc2 + tm_tot_auto_park_cost_inc1 + tm_tot_auto_park_cost_inc2) / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * inflation_00_20  / days_per_year


    ####### per trip transit

    # Total transit trips per day (model outputs are in trips, per day)
    tm_tot_transit_trips            = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_trips") == True), 'value'].sum() 
    tm_tot_transit_trips_inc1       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc1"),'value'].item() 
    tm_tot_transit_trips_inc2       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_transit_perday',year,dbp]          = tm_tot_transit_trips
    metrics_dict[runid,metric_id,'trips_total_transit_perday_inc1',year,dbp]     = tm_tot_transit_trips_inc1

    # Average Fares per trip   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'per_trip_fare',year,dbp]          = tm_tot_transit_fares / tm_tot_transit_trips * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1and2',year,dbp] = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_transit_trips_inc1+tm_tot_transit_trips_inc2) * inflation_00_20 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1',year,dbp]     = tm_tot_transit_fares_inc1 / tm_tot_transit_trips_inc1 * inflation_00_20 / days_per_year

def calculate_Connected1_proximity(runid, year, dbp, transitproximity_df, metrics_dict):
    
    metric_id = "C1"    

    for area_type in ['Region','CoCs','HRAs','rural','suburban','urban']:
        # households
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_tothh_%s' % area_type,year,dbp]    = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                              & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                              & (transitproximity_df['area']==area_type), 'tothh_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_hhq1_%s' % area_type,year,dbp]     = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                              & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                              & (transitproximity_df['area']==area_type), 'hhq1_share'].sum()
        # jobs
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_totemp_%s' % area_type,year,dbp]       = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                 & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'totemp_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_RETEMPNjobs_%s' % area_type,year,dbp]  = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                  & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'RETEMPN_share'].sum()
        metrics_dict[runid,metric_id,'transitproximity_majorstop_shareof_MWTEMPNjobs_%s' % area_type,year,dbp]  = transitproximity_df.loc[(transitproximity_df['Service_Level']=="Major_Transit_Stop") \
                                                                                                                  & (transitproximity_df['year']==int(year)) & (transitproximity_df['blueprint'].str.contains(dbp)) \
                                                                                                                  & (transitproximity_df['area']==area_type), 'MWTEMPN_share'].sum()



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
        if row['operator'] in ['Shuttle','SFMTA LRT','SFMTA Bus','SamTrans Local','VTA Bus Local','AC Transit Local','Alameda Bus Operators','Contra Costa Bus Operators',\
                               'Solano Bus Operators','Napa Bus Operators','Sonoma Bus Operators','GGT Local','CC AV Shuttle','ReX Express','SamTrans Express','VTA Bus Express',\
                               'AC Transit Transbay','County Connection Express','GGT Express','WestCAT Express','Soltrans Express','FAST Express','VINE Express','SMART Express',\
                               'WETA','Golden Gate Ferry','Hovercraft','VTA LRT','Dumbarton GRT','Oakland/Alameda Gondola','Contra Costa Gondolas','BART','Caltrain',\
                               'Capitol Corridor','Amtrak','ACE','Dumbarton Rail','SMART', 'Valley Link','High-Speed Rail']:
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

    for index,row in trn_operator_travel_times_df.iterrows():    # for bus only
        if row['operator'] in ['AC Transit Local','AC Transit Transbay','SFMTA Bus','VTA Bus Local','SamTrans Local','GGT Express','SamTrans Express', 'ReX Express']:
            metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['operator'],year,dbp] = row['time_per_dist_AM'] 

    for index,row in trn_mode_travel_times_df.iterrows():
        metrics_dict[runid,metric_id,'time_per_dist_AM_%s' % row['mode_name'],year,dbp] = row['time_per_dist_AM'] 


def calculate_Connected2_transit_asset_condition(runid, year, dbp, transit_asset_condition_df, metrics_dict):
    
    metric_id = "C2"                         
                     
    metrics_dict[runid,metric_id,'asset_life_transit_revveh_beyondlife_pct_of_count',year,dbp]      = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_revveh_beyondlife_pct_of_count")      & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'asset_life_transit_nonveh_beyondlife_pct_of_value',year,dbp]      = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_nonveh_beyondlife_pct_of_value")      & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'asset_life_transit_all_beyondlife_pct_of_value',year,dbp]   = transit_asset_condition_df.loc[(transit_asset_condition_df['name']=="transit_allassets_beyondlife_pct_of_value")   & (transit_asset_condition_df['year']==int(year)) & (transit_asset_condition_df['blueprint'].str.contains(dbp)), 'value'].sum()
  

def calculate_Healthy1_safety(runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict):

    metric_id = "H1"
    population = tm_taz_input_df.TOTPOP.sum()
    per_x_people = 100000
    print('population %d' % population)

    fatalities   = safety_df.loc[(safety_df['index']=="N_total_fatalities")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_m = safety_df.loc[(safety_df['index']=="N_motorist_fatalities")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    fatalities_b = safety_df.loc[(safety_df['index']=="N_bike_fatalities")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    fatalities_p = safety_df.loc[(safety_df['index']=="N_ped_fatalities")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
    injuries     = safety_df.loc[(safety_df['index']=="N_injuries")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum() 
                                                                               
    metrics_dict[runid,metric_id,'fatalities_annual_per_100Kppl_calc',year,dbp]         = float(fatalities)   / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100Kppl_calc',year,dbp]    = float(fatalities_m) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100Kppl_calc',year,dbp]    = float(fatalities_b) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100Kppl_calc',year,dbp]     = float(fatalities_p) / float(population / per_x_people)
    metrics_dict[runid,metric_id,'injuries_annual_per_100Kppl_calc',year,dbp]           = float(injuries)     / float(population / per_x_people)

    metrics_dict[runid,metric_id,'fatalities_annual_per_100MVMT',year,dbp]         = safety_df.loc[(safety_df['index']=="N_total_fatalities_per_100M_VMT")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_motorist_fatalities_per_100M_VMT")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100MVMT',year,dbp]    = safety_df.loc[(safety_df['index']=="N_bike_fatalities_per_100M_VMT")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100MVMT',year,dbp]     = safety_df.loc[(safety_df['index']=="N_ped_fatalities_per_100M_VMT")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'injuries_annual_per_100MVMT',year,dbp]           = safety_df.loc[(safety_df['index']=="N_injuries_per_100M_VMT")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()

    metrics_dict[runid,metric_id,'fatalities_annual_per_100Kppl',year,dbp]         = safety_df.loc[(safety_df['index']=="N_total_fatalities_per_100K_pop")     & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_auto_annual_per_100Kppl',year,dbp]    = safety_df.loc[(safety_df['index']=="N_motorist_fatalities_per_100K_pop")  & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_bike_annual_per_100Kppl',year,dbp]    = safety_df.loc[(safety_df['index']=="N_bike_fatalities_per_100K_pop")      & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'fatalities_ped_annual_per_100Kppl',year,dbp]     = safety_df.loc[(safety_df['index']=="N_ped_fatalities_per_100K_pop")       & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'injuries_annual_per_100Kppl',year,dbp]           = safety_df.loc[(safety_df['index']=="N_injuries_per_100K_pop")             & (safety_df['modelrunID'].str.contains(dbp)), 'value'].sum()


def calculate_Healthy1_safety_TAZ(runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict):

    metric_id = "H1"

    population        = tm_taz_input_df.TOTPOP.sum()
    population_coc    = tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'TOTPOP'].sum()
    population_noncoc = tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'TOTPOP'].sum()
    population_hra    = tm_taz_input_df.loc[(tm_taz_input_df['taz_hra']==1),'TOTPOP'].sum()

 

    per_x_people      = 100000
    days_per_year     = 300

    metrics_dict[runid,metric_id,'fatalities_annual',year,dbp] = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Fatality'].sum()) * days_per_year                                                         
    metrics_dict[runid,metric_id,'injuries_annual',year,dbp]   = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Injury'].sum())  * days_per_year                                                              


    metrics_dict[runid,metric_id,'fatalities_annual_per100K',year,dbp] = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Fatality'].sum()) / float(population / per_x_people) * days_per_year                                                          
    metrics_dict[runid,metric_id,'injuries_annual_per100K',year,dbp]   = float(tm_vmt_metrics_df.loc[:,'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[:,'Bike Injury'].sum()) / float(population / per_x_people) * days_per_year



    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Motor Vehicle Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Walk Fatality'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Bike Fatality'].sum()) / float(population / per_x_people) * days_per_year
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Motor Vehicle Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Walk Injury'].sum() + \
                                                                           tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'Bike Injury'].sum()) / float(population / per_x_people) * days_per_year                                                           


    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_coc',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Bike Fatality'].sum()) / float(population_coc / per_x_people) * days_per_year     
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_coc',year,dbp]   =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1),'Bike Injury'].sum()) / float(population_coc / per_x_people) * days_per_year                                                               
  
    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_noncoc',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Bike Fatality'].sum()) / float(population_noncoc / per_x_people) * days_per_year                                                              
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_noncoc',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0),'Bike Injury'].sum()) / float(population_noncoc / per_x_people) * days_per_year                                                              

    metrics_dict[runid,metric_id,'fatalities_annual_per100K_nonfwy_hra',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Motor Vehicle Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Walk Fatality'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Bike Fatality'].sum()) / float(population_hra / per_x_people) * days_per_year                                                                
    metrics_dict[runid,metric_id,'injuries_annual_per100K_nonfwy_hra',year,dbp]   = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Motor Vehicle Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Walk Injury'].sum() + \
                                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1),'Bike Injury'].sum()) / float(population_hra / per_x_people) * days_per_year                                                               
    

    #VMT density per 100K people 
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum()  / float(population / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()  / float(population_coc / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  / float(population_noncoc / per_x_people)
    metrics_dict[runid,metric_id,'VMT_per100K_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum()  / float(population_hra / per_x_people)


def calculate_Healthy2_GHGemissions(runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    
    '''
    metric_id = "H2"

    population        = tm_taz_input_df.TOTPOP.sum()

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
    '''

def calculate_Healthy2_PM25emissions(runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict):

    # Note - these metrics are grabbed directly from metrics_manual.xlsx
    
    '''
    metric_id = "H2"
    population = tm_taz_input_df.TOTPOP.sum()

    METRIC_TONS_TO_US_TONS      = 1.10231            # Metric tons to US tons
    PM25_ROADDUST               = 0.018522           # Grams of PM2.5 from road dust per vehicle mile
                                                     # Source: CARB - Section 7.  ARB Miscellaneous Processes Methodologies
                                                     #         Paved Road Dust [Revised and updated, March 2018]
                                                     #         https://www.arb.ca.gov/ei/areasrc/fullpdf/full7-9_2018.pdf
    GRAMS_TO_US_TONS            = 0.00000110231131  # Grams to US tons

    ACRES_TO_SQMILE             = 0.0015625


    metrics_dict[runid,metric_id,'PM25',year,dbp] =        tm_vmt_metrics_df.loc[:,'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                           tm_vmt_metrics_df.loc[:,'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                           tm_vmt_metrics_df.loc[:,'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS

    urbanarea          = float(tm_taz_input_df['acres_urbanized'].sum()) * ACRES_TO_SQMILE
    
    num_coc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'acres_urbanized'].count()) 
    num_noncoc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'acres_urbanized'].count()) 
    print num_coc
    print num_noncoc
  
    urbanarea_coc      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==1),'acres_urbanized'].sum()) * ACRES_TO_SQMILE    
    urbanarea_noncoc   = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_coc']==0),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    print urbanarea_coc
    print urbanarea_noncoc

    urbanarea_hra      = float(tm_taz_input_df.loc[(tm_taz_input_df['taz_hra']==1),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_rural    = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="rural"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_suburban = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="suburban"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
    urbanarea_urban    = float(tm_taz_input_df.loc[(tm_taz_input_df['area_type']=="urban"),'acres_urbanized'].sum()) * ACRES_TO_SQMILE
       
    #VMT total
    metrics_dict[runid,metric_id,'VMT',year,dbp]         =  tm_vmt_metrics_df.loc[:,'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_fwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="freeway"),'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum() 
    metrics_dict[runid,metric_id,'VMT_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()
    metrics_dict[runid,metric_id,'VMT_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  
    metrics_dict[runid,metric_id,'VMT_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum() 

    #VMT density per sq mile
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy',year,dbp]         =  tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['road_type']=="non-freeway"),'VMT'].sum()  / float(urbanarea)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_coc',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==1)),'VMT'].sum()  / float(urbanarea_coc)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_noncoc',year,dbp]  =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_coc']==0)),'VMT'].sum()  / float(urbanarea_noncoc)
    metrics_dict[runid,metric_id,'VMT_persqmi_nonfwy_hra',year,dbp]     =  tm_vmt_metrics_df.loc[((tm_vmt_metrics_df['road_type']=="non-freeway") & (tm_vmt_metrics_df['taz_hra']==1)),'VMT'].sum()  / float(urbanarea_hra)
    

    #PM2.5 density Tons per sq mile 
    metrics_dict[runid,metric_id,'PM25_density',year,dbp] =        float(tm_vmt_metrics_df.loc[:,'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                   tm_vmt_metrics_df.loc[:,'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                   tm_vmt_metrics_df.loc[:,'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea
    
    metrics_dict[runid,metric_id,'PM25_density_coc',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==1),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_coc
    
    metrics_dict[runid,metric_id,'PM25_density_noncoc',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_coc']==0),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS)  / urbanarea_noncoc
    metrics_dict[runid,metric_id,'PM25_density_hra',year,dbp]    = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                    tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['taz_hra']==1),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_hra


    metrics_dict[runid,metric_id,'PM25_density_rural',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="rural"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) /  urbanarea_rural
    metrics_dict[runid,metric_id,'PM25_density_suburban',year,dbp] = float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="suburban"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_suburban
    metrics_dict[runid,metric_id,'PM25_density_urban',year,dbp] =    float(tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'PM2.5_wear'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'PM2.5_exhaust'].sum()*METRIC_TONS_TO_US_TONS + \
                                                                      tm_vmt_metrics_df.loc[(tm_vmt_metrics_df['area_type']=="urban"),'VMT'].sum() * PM25_ROADDUST*GRAMS_TO_US_TONS) / urbanarea_urban
    '''

def calculate_Healthy2_commutemodeshare(runid, year, dbp, commute_mode_share_df, metrics_dict):
    
    # Note - these metrics are grabbed directly from metrics_manual.xlsx

    '''
    metric_id = "H2"
    year = int(year)                              
    
    metrics_dict[runid,metric_id,'Commute_mode_share_sov',year,dbp]          = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_sov")         & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_hov',year,dbp]          = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_hov")         & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_taxi_tnc',year,dbp]     = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_taxi_tnc")    & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_transit',year,dbp]      = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_transit")     & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_bike',year,dbp]         = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_bike")        & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_walk',year,dbp]         = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_walk")        & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    metrics_dict[runid,metric_id,'Commute_mode_share_telecommute',year,dbp]  = commute_mode_share_df.loc[(commute_mode_share_df['name']=="Commute_mode_share_telecommute") & (commute_mode_share_df['year']==year) & (commute_mode_share_df['modelrunID'].str.contains(dbp)), 'value'].sum()
    '''

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

        '''
        metric_id = "A1"

        # Tolls
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_LIHH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'tolls_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'tolls_per_inc1HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'tolls_per_inc1HH',y2,"NoProject"] - 1
        # Transit Fares
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_HH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_LIHH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_LIHH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_LIHH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_LIHH',y2,"NoProject"] - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2015',year,dbp] = metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2015_runid,metric_id,'fares_per_inc1HH',y1,'2015']  - 1
        metrics_dict[tm_runid,metric_id,'fares_per_inc1HH_change_2050noproject',year,dbp] =  metrics_dict[tm_runid,metric_id,'fares_per_inc1HH',year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'fares_per_inc1HH',y2,"NoProject"] - 1
        '''

        metric_id = "C2"

        # Highway corridor travel times
        for route in ['Antioch_SF','Vallejo_SF','SanJose_SF','Oakland_SanJose','Oakland_SF']:
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2015_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'travel_time_AM_%s' % route,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'travel_time_AM_change_2050noproject_%s' % route,year,dbp] = metrics_dict[tm_runid,metric_id,'travel_time_AM_%s' % route,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'travel_time_AM_%s' % route,y2,'NoProject']  - 1
        

        # Transit Crowding by operator
        for operator in ['Shuttle','SFMTA LRT','SFMTA Bus','SamTrans Local','VTA Bus Local','AC Transit Local','Alameda Bus Operators','Contra Costa Bus Operators',\
                               'Solano Bus Operators','Napa Bus Operators','Sonoma Bus Operators','GGT Local','CC AV Shuttle','ReX Express','SamTrans Express','VTA Bus Express',\
                               'AC Transit Transbay','County Connection Express','GGT Express','WestCAT Express','Soltrans Express','FAST Express','VINE Express','SMART Express',\
                               'WETA','Golden Gate Ferry','Hovercraft','VTA LRT','Dumbarton GRT','Oakland/Alameda Gondola','Contra Costa Gondolas','BART','Caltrain',\
                               'Capitol Corridor','Amtrak','ACE','Dumbarton Rail','SMART', 'Valley Link','High-Speed Rail']:
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y1,'2015']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2015_%s' % operator,year,dbp] = 0
            try:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'crowded_pct_personhrs_AM_%s' % operator,y2,'NoProject']  - 1
            except:
                metrics_dict[tm_runid,metric_id,'crowded_pct_personhrs_AM_change_2050noproject_%s' % operator,year,dbp] = 0
        

         # Transit travel times by operator (for bus only)
        for operator in ['AC Transit Local','AC Transit Transbay','SFMTA Bus','VTA Bus Local','SamTrans Local','GGT Express','SamTrans Express', 'ReX Express']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % operator,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % operator,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % operator,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % operator,y2,'NoProject']  - 1

         # Transit travel times by mode
        for mode_name in ['Local','Express','Ferry','Light Rail','Heavy Rail','Commuter Rail']:
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2015_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2015_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y1,'2015']  - 1
            metrics_dict[tm_runid,metric_id,'time_per_dist_AM_change_2050noproject_%s' % mode_name,year,dbp] = metrics_dict[tm_runid,metric_id,'time_per_dist_AM_%s' % mode_name,year,dbp] / metrics_dict[tm_2050_FBP_NoProject_runid,metric_id,'time_per_dist_AM_%s' % mode_name,y2,'NoProject']  - 1


def calc_travelmodel_metrics():

    coc_flag_df                 = pd.read_csv(coc_flag_file)
    transit_operator_df         = pd.read_csv(transit_operator_file)
    hwy_corridor_links_df       = pd.read_csv(hwy_corridor_links_file)
    safety_df                   = pd.read_csv(safety_file)
    emfac_df                    = pd.read_csv(emfac_file)
    commute_mode_share_df       = pd.read_csv(commute_mode_share_file)
    transitproximity_df         = pd.read_csv(transitproximity_file)
    transit_asset_condition_df  = pd.read_csv(transit_asset_condition_file)
    housing_costs_df            = pd.read_csv(housing_costs_file)
    taz_coc_xwalk_df            = pd.read_csv(taz_coc_crosswalk_file)
    taz_hra_xwalk_df            = pd.read_csv(taz_hra_crosswalk_file)
    taz_areatype_df             = pd.read_csv(taz_areatype_file)
    taz_urbanizedarea_df        = pd.read_csv(taz_urbanizedarea_file)

    for tm_runid in list_tm_runid:

        year = tm_runid[:4]

        if "NoProject" in tm_runid:
            dbp = "NoProject"
        elif "DBP_Plus" in tm_runid:
            dbp = "DBP"
        elif "FBP_Plus" in tm_runid:
            dbp = "Plus"
        elif "Alt1" in tm_runid:
            dbp = "Alt1"
        elif "Alt2" in tm_runid:
            dbp = "Alt2"            
        elif  "2015" in tm_runid:
            dbp = "2015"
        else:
            dbp = "Unknown"
        
        # Read relevant metrics files
        if "2015" in tm_runid: tm_run_location = tm_run_location_ipa
        else: tm_run_location = tm_run_location_bp
        tm_scen_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
        tm_auto_owned_df      = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/autos_owned.csv')
        tm_auto_times_df      = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/auto_times.csv',sep=",", index_col=[0,1])
        tm_travel_cost_df     = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/TravelCost.csv')
        tm_parking_cost_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/parking_costs_tour.csv')       
        tm_commute_df         = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv')
        tm_taz_input_df       = pd.read_csv(tm_run_location+tm_runid+'/INPUT/landuse/tazData.csv')
        
        tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics_by_taz.csv')            
        #tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics.csv')            
        tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_coc_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_hra_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_coc_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_hra_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_areatype_df, left_on="ZONE", right_on="TAZ1454", how="left")
        tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_urbanizedarea_df, left_on="ZONE", right_on="TAZ1454", how="left")
        
        
        print("Starting travel model functions for %s..."% dbp)
        calculate_Affordable1_HplusT_costs(tm_runid, year, dbp, tm_scen_metrics_df, tm_auto_owned_df, tm_auto_times_df, tm_travel_cost_df, tm_parking_cost_df, housing_costs_df, metrics_dict)
        print("@@@@@@@@@@@@@ A1 Done")
        calculate_Connected1_proximity(tm_runid, year, dbp, transitproximity_df, metrics_dict)
        print("@@@@@@@@@@@@@ C1 Done")
        calculate_Connected2_hwy_traveltimes(tm_runid, year, dbp, hwy_corridor_links_df, metrics_dict)
        calculate_Connected2_trn_traveltimes(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        calculate_Connected2_crowding(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        print("@@@@@@@@@@@@@ C2 Done")
        calculate_Connected2_transit_asset_condition(tm_runid, year, dbp, transit_asset_condition_df, metrics_dict)
        calculate_Healthy1_safety(tm_runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict)
        calculate_Healthy1_safety_TAZ(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        print("@@@@@@@@@@@@@ H1 Done")
        calculate_Healthy2_GHGemissions(tm_runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict)
        calculate_Healthy2_PM25emissions(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        calculate_Healthy2_commutemodeshare(tm_runid, year, dbp, commute_mode_share_df, metrics_dict)
        print("@@@@@@@@@@@@@ H2 Done")
        calculate_Vibrant1_median_commute(tm_runid, year, dbp, tm_commute_df, metrics_dict)
        print("@@@@@@@@@@@@@ V1 Done")
        print("@@@@@@@@@@@@@%s Done"% dbp)
    
    #calculate_travelmodel_metrics_change(list_tm_runid_blueprintonly, metrics_dict)



if __name__ == '__main__':

    #pd.set_option('display.width', 500)

    # Handle box drives in E: (e.g. for virtual machines)
    USERNAME    = os.getenv('USERNAME')
    BOX_DIR     = pathlib.Path(f"C:/Users/{USERNAME}/Box")
    if USERNAME.lower() in ['lzorn']:
        BOX_DIR = pathlib.Path("E:\Box")

    # Set location of Travel model inputs
    tm_run_location_bp                = 'M:/Application/Model One/RTP2021/Blueprint/'
    tm_run_location_ipa               = 'M:/Application/Model One/RTP2021/IncrementalProgress/'
    tm_2015_runid                     = '2015_TM152_IPA_17'
    #tm_2050_DBP_NoProject_runid      = '2050_TM152_DBP_NoProject_08'
    #tm_2050_DBP_runid                = '2050_TM152_DBP_PlusCrossing_08'
    #tm_2050_DBP_PlusFixItFirst_runid = '2050_TM152_DBP_PlusCrossing_01'
    tm_2050_FBP_NoProject_runid       = '2050_TM152_FBP_NoProject_24'
    tm_2050_FBP_runid                 = '2050_TM152_FBP_PlusCrossing_24'
    tm_2050_FBP_EIRAlt1_runid         = '2050_TM152_EIR_Alt1_06'
    tm_2050_FBP_EIRAlt2_runid         = '2050_TM152_EIR_Alt2_05'
    list_tm_runid                     = [tm_2015_runid, tm_2050_FBP_NoProject_runid, tm_2050_FBP_runid, tm_2050_FBP_EIRAlt1_runid, tm_2050_FBP_EIRAlt2_runid]
    #list_tm_runid                     = [tm_2015_runid, tm_2050_FBP_runid]
    list_tm_runid_blueprintonly       = [tm_2050_FBP_runid]

    # Set location of external inputs
    #All files are located in below folder / check sources.txt for sources
    metrics_source_folder         = BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / "metrics_input_files"
    taz_coc_crosswalk_file        = metrics_source_folder / 'taz_coc_crosswalk.csv'
    taz_hra_crosswalk_file        = metrics_source_folder / 'taz_hra_crosswalk.csv'
    taz_areatype_file             = metrics_source_folder / 'taz_areatype.csv'
    taz_urbanizedarea_file        = metrics_source_folder / 'taz_urbanizedarea.csv'

    coc_flag_file                 = metrics_source_folder / 'COCs_ACS2018_tbl_TEMP.csv'
    transit_operator_file         = metrics_source_folder / 'transit_system_lookup.csv'
    hwy_corridor_links_file       = metrics_source_folder / 'maj_corridors_hwy_links.csv'
    
    # Set location of intermediate metric outputs
    # These are for metrics generated by Raleigh, Bobby, James
    intermediate_metrics_source_folder  =  BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / \
        "Metrics_Outputs_FinalBlueprint" / "Intermediate Metrics"
    housing_costs_file            = intermediate_metrics_source_folder / 'housing_costs_share_income.csv'         # from Bobby, based on Urbansim outputs only
    transitproximity_file         = intermediate_metrics_source_folder / 'metrics_proximity.csv'                  # from Bobby, based on Urbansim outputs only
    transit_asset_condition_file  = intermediate_metrics_source_folder / 'transit_asset_condition.csv'            # from Raleigh, not based on model outputs
    safety_file                   = intermediate_metrics_source_folder / 'fatalities_injuries_export.csv'         # from Raleigh, based on Travel Model outputs 
    commute_mode_share_file       = intermediate_metrics_source_folder / 'commute_mode_share.csv'                 # from Raleigh, based on Travel Model outputs
    emfac_file                    = intermediate_metrics_source_folder / 'emfac.csv'                              # from James
    remi_jobs_file                = intermediate_metrics_source_folder / 'emp by ind11_s23.csv'                   # from Bobby, based on REMI
    jobs_wagelevel_file           = intermediate_metrics_source_folder / 'jobs_wagelevel.csv'                     # from Bobby, based on REMI

    # All summarized outputs (i.e. by TRA or PDA or tract) will be written to this folder
    sum_outputs_filepath = BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics" / "Metrics_Outputs_FinalBlueprint" / "Summary Outputs"

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
    print("Starting travel model data gathering...")
    calc_travelmodel_metrics()
    print("*****************#####################Completed calc_travelmodel_metrics#####################*******************")

    # Write output
    idx = pd.MultiIndex.from_tuples(metrics_dict.keys(), names=['modelrunID','metric','name','year','blueprint'])
    metrics = pd.Series(metrics_dict, index=idx)
    metrics.name = 'value'
    # out_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Metrics_Outputs_FinalBlueprint/metrics.csv'.format(os.getenv('USERNAME'))
    # write it locally for now
    out_filename = 'metrics.csv'
    metrics.to_csv(out_filename, header=True, sep=',')
    
    print("Wrote metrics.csv output")

    
