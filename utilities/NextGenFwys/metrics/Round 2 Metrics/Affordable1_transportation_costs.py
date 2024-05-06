USAGE = """

  python Affordable1_transportation_costs.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Affordable1_transportation_costs_XX.csv
  
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
    1) Affordable 1: Transportation costs as a share of household income, by different income groups

"""

import os
import pandas as pd
import argparse
import logging

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"
# line below for round 2 runs
# NGFS_ROUND2_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
NGFS_TOLLCLASS_FILE     = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "TOLLCLASS_Designations.xlsx")

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Affordable1_transportation_costs.log" # in the cwd
LOGGER                  = None # will initialize in main

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

def calculate_Affordable1_transportation_costs(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Affordable 1: Transportation costs as a share of household income

    Args:
        tm_run_id (str): Travel model run ID

    Returns:
        pd.DataFrame: with columns a subset of METRICS_COLUMNS, including 
          metric_id   = 'Affordable 1'
          modelrun_id = tm_run_id
        Metrics returned:


        where [income_category] is one of: incQ1, incQ2, incQ1Q2, all_inc, referring to travel model income quartiles
        and   [hhld_travel_category] is based on whether the houseld makes private auto trips, transit trips, both, or neither, 
                                     so it is one of auto_and_transit, auto_no_transit, transit_no_auto, no_auto_no_transit
        See travel-cost-by-income-driving-households.r for more

    """
    METRIC_ID = "Affordable 1"
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    travel_cost_by_travel_hhld_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "travel-cost-hhldtraveltype.csv")
    # line below for round 2 runs
    # travel_cost_by_travel_hhld_file = os.path.join(NGFS_ROUND2_SCENARIOS, tm_run_id, "OUTPUT", "core_summaries", "travel-cost-hhldtraveltype.csv")
    travel_cost_df = pd.read_csv(travel_cost_by_travel_hhld_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(travel_cost_df), travel_cost_by_travel_hhld_file))
    LOGGER.debug("  Head:\n{}".format(travel_cost_df.head()))

    # columns are: incQ, incQ_label, home_taz, hhld_travel, 
    #              num_hhlds, num_persons, num_auto_trips, num_transit_trips, 
    #              total_auto_cost, total_transit_cost, total_cost, total_hhld_autos, total_hhld_income
    #              total_auto_op_cost, total_bridge_toll, total_cordon_toll, total_value_toll, 
    #              total_fare, total_drv_trn_op_cost, total_taxitnc_cost,
    #              total_detailed_auto_cost, total_detailed_transit_cost
    # convert incQ from number to string
    travel_cost_df['incQ'] = "incQ" + travel_cost_df['incQ'].astype('str')
    # Summarize to incQ_label, hhld_travel segments
    travel_cost_df = travel_cost_df.groupby(by=['incQ','hhld_travel']).agg({
        'num_hhlds':            'sum',
        'total_auto_op_cost':      'sum',
        'total_detailed_auto_cost':      'sum',
        'total_detailed_transit_cost':      'sum',
        'total_parking_cost':      'sum',
        'total_bridge_toll':      'sum',
        'total_value_toll':      'sum',
        'total_cordon_toll':      'sum',
        'total_fare':   'sum',
        'total_drv_trn_op_cost':   'sum',
        'total_taxitnc_cost':   'sum',
        'total_hhld_autos':     'sum',
        'total_hhld_income':    'sum',
        'num_auto_trips':    'sum',
        'num_transit_trips':    'sum',
        'num_taxitnc_trips':    'sum'
    })
    # note: the index is not reset so it's a MultiIndex with incQ, hhld_travel
    LOGGER.debug("  travel_cost_df:\n{}".format(travel_cost_df))

    # add variable costs to df:
    #   Ops cost (includes fuel+maintenance)
    #   Parking costs
    #   Bridge Toll costs
    #   Value Toll costs
    #   Transit fare costs

    # annualize and convert daily costs from 2000 cents to 2023 dollars 
    travel_cost_df['total_auto_op_cost_annual_2023d']    = travel_cost_df['total_auto_op_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_parking_cost_annual_2023d']    = travel_cost_df['total_parking_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_bridge_toll_cost_annual_2023d']    = travel_cost_df['total_bridge_toll']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_value_toll_cost_annual_2023d']    = travel_cost_df['total_value_toll']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_cordon_toll_cost_annual_2023d']    = travel_cost_df['total_cordon_toll']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_transit_op_cost_annual_2023d'] = travel_cost_df['total_fare']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_drive_to_transit_cost_annual_2023d'] = travel_cost_df['total_drv_trn_op_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    
    travel_cost_df['total_taxitnc_cost_annual_2023d'] = travel_cost_df['total_taxitnc_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23

    travel_cost_df['total_detailed_auto_cost_annual_2023d'] = travel_cost_df['total_detailed_auto_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23
    travel_cost_df['total_detailed_transit_cost_annual_2023d'] = travel_cost_df['total_detailed_transit_cost']*REVENUE_DAYS_PER_YEAR * 0.01 * INFLATION_00_23

    # add fixed costs to df:
    #   ownership + finance
    #   insurance
    #   registration/taxes

    # add auto ownership costs (by income)
    travel_cost_df.loc['incQ1', 'total_auto_own_finance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_OWNERSHIP_COST_2020D + AUTO_FINANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ2', 'total_auto_own_finance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_OWNERSHIP_COST_2020D + AUTO_FINANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ3', 'total_auto_own_finance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_OWNERSHIP_COST_2020D + AUTO_FINANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ4', 'total_auto_own_finance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_OWNERSHIP_COST_2020D + AUTO_FINANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23

    # add auto insurance costs (by income)
    travel_cost_df.loc['incQ1', 'total_auto_insurance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_INSURANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ2', 'total_auto_insurance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_INSURANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ3', 'total_auto_insurance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_INSURANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ4', 'total_auto_insurance_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_INSURANCE_COST_2020D) / INFLATION_00_20 * INFLATION_00_23

    # add auto registration/taxes costs (by income)
    travel_cost_df.loc['incQ1', 'total_auto_registration_taxes_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_REGISTRATION_TAXES_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ2', 'total_auto_registration_taxes_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_REGISTRATION_TAXES_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ3', 'total_auto_registration_taxes_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_REGISTRATION_TAXES_COST_2020D) / INFLATION_00_20 * INFLATION_00_23
    travel_cost_df.loc['incQ4', 'total_auto_registration_taxes_cost_annual_2023d'] = travel_cost_df['total_hhld_autos']*(AUTO_REGISTRATION_TAXES_COST_2020D) / INFLATION_00_20 * INFLATION_00_23

    # all transportation costs
    travel_cost_df['total_transportation_cost_annual_2023d']       = \
        travel_cost_df['total_detailed_auto_cost_annual_2023d']          + \
        travel_cost_df['total_detailed_transit_cost_annual_2023d']       + \
        travel_cost_df['total_auto_own_finance_cost_annual_2023d'] + \
        travel_cost_df['total_auto_insurance_cost_annual_2023d']   + \
        travel_cost_df['total_auto_registration_taxes_cost_annual_2023d'] + \
        travel_cost_df['total_taxitnc_cost_annual_2023d']

    # and finally annual household income from 2000 dollars to 2023 dollars
    travel_cost_df['total_hhld_income_annual_2023d']    = travel_cost_df['total_hhld_income']*INFLATION_00_23

    # create a combined incQ1Q2 and all_ind
    incQ1Q2_df = \
        travel_cost_df.loc['incQ1'] + \
        travel_cost_df.loc['incQ2'] 
    all_inc_df = \
        travel_cost_df.loc['incQ1'] + \
        travel_cost_df.loc['incQ2'] + \
        travel_cost_df.loc['incQ3'] + \
        travel_cost_df.loc['incQ4']
    # make index consistent and add to our table
    incQ1Q2_df.index = pd.MultiIndex.from_arrays([['incQ1Q2']*len(incQ1Q2_df.index.tolist()), incQ1Q2_df.index.tolist()], names=('incQ','hhld_travel'))
    all_inc_df.index = pd.MultiIndex.from_arrays([['all_inc']*len(all_inc_df.index.tolist()), all_inc_df.index.tolist()], names=('incQ','hhld_travel'))
    travel_cost_df = pd.concat([travel_cost_df, incQ1Q2_df, all_inc_df])
    LOGGER.debug("   travel_cost_df:\n{}".format(travel_cost_df))

    # calculate average per household
    travel_cost_df['avg_num_autos_per_hhld']                                 = travel_cost_df['total_hhld_autos']                                   /travel_cost_df['num_hhlds']
    travel_cost_df['avg_hhld_income_annual_2023d_per_hhld']                  = travel_cost_df['total_hhld_income_annual_2023d']                     /travel_cost_df['num_hhlds']
    travel_cost_df['avg_auto_op_cost_annual_2023d_per_hhld']                 = travel_cost_df['total_auto_op_cost_annual_2023d']                    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_parking_cost_annual_2023d_per_hhld']                 = travel_cost_df['total_parking_cost_annual_2023d']                    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_bridge_toll_cost_annual_2023d_per_hhld']             = travel_cost_df['total_bridge_toll_cost_annual_2023d']                    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_value_toll_cost_annual_2023d_per_hhld']              = travel_cost_df['total_value_toll_cost_annual_2023d']                    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_cordon_toll_cost_annual_2023d_per_hhld']             = travel_cost_df['total_cordon_toll_cost_annual_2023d']                    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_transit_op_cost_annual_2023d_per_hhld']              = travel_cost_df['total_transit_op_cost_annual_2023d']                 /travel_cost_df['num_hhlds']
    travel_cost_df['avg_drive_to_transit_cost_annual_2023d_per_hhld']        = travel_cost_df['total_drive_to_transit_cost_annual_2023d']                 /travel_cost_df['num_hhlds']
    travel_cost_df['avg_taxitnc_cost_annual_2023d_per_hhld']                 = travel_cost_df['total_taxitnc_cost_annual_2023d']                 /travel_cost_df['num_hhlds']
    travel_cost_df['avg_auto_own_finance_cost_annual_2023d_per_hhld']        = travel_cost_df['total_auto_own_finance_cost_annual_2023d']           /travel_cost_df['num_hhlds']
    travel_cost_df['avg_auto_insurance_cost_annual_2023d_per_hhld']          = travel_cost_df['total_auto_insurance_cost_annual_2023d']             /travel_cost_df['num_hhlds']
    travel_cost_df['avg_auto_registration_taxes_cost_annual_2023d_per_hhld'] = travel_cost_df['total_auto_registration_taxes_cost_annual_2023d']    /travel_cost_df['num_hhlds']
    travel_cost_df['avg_transportation_cost_annual_2023d_per_hhld']          = travel_cost_df['total_transportation_cost_annual_2023d']             /travel_cost_df['num_hhlds']
    # calculate average per trip
    travel_cost_df['avg_auto_cost_annual_2023d_per_trip']             = (travel_cost_df['total_detailed_auto_cost_annual_2023d'] + \
                                                                             travel_cost_df['total_auto_own_finance_cost_annual_2023d'] + \
                                                                             travel_cost_df['total_auto_insurance_cost_annual_2023d']   + \
                                                                             travel_cost_df['total_auto_registration_taxes_cost_annual_2023d'])     /travel_cost_df['num_auto_trips']
    travel_cost_df['avg_transit_cost_annual_2023d_per_trip']          = (travel_cost_df['total_detailed_transit_cost_annual_2023d'] + \
                                                                             travel_cost_df['total_auto_own_finance_cost_annual_2023d'] + \
                                                                             travel_cost_df['total_auto_insurance_cost_annual_2023d']   + \
                                                                             travel_cost_df['total_auto_registration_taxes_cost_annual_2023d'])     /travel_cost_df['num_transit_trips']
    travel_cost_df['avg_taxitnc_cost_annual_2023d_per_trip']          = travel_cost_df['total_taxitnc_cost_annual_2023d']                                  /travel_cost_df['num_taxitnc_trips']
    travel_cost_df['avg_transportation_cost_annual_2023d_per_trip']   = travel_cost_df['total_transportation_cost_annual_2023d']                    /(travel_cost_df['num_auto_trips'] + \
                                                                                                                                                      travel_cost_df['num_transit_trips'] + \
                                                                                                                                                      travel_cost_df['num_taxitnc_trips'])
    # calculate pct of income
    travel_cost_df['auto_op_cost_pct_of_income']                 = travel_cost_df['total_auto_op_cost_annual_2023d']                 /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['parking_cost_pct_of_income']                 = travel_cost_df['total_parking_cost_annual_2023d']                 /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['bridge_toll_cost_pct_of_income']             = travel_cost_df['total_bridge_toll_cost_annual_2023d']                 /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['value_toll_cost_pct_of_income']              = travel_cost_df['total_value_toll_cost_annual_2023d']                 /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['cordon_toll_cost_pct_of_income']             = travel_cost_df['total_cordon_toll_cost_annual_2023d']                 /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['transit_op_cost_pct_of_income']              = travel_cost_df['total_transit_op_cost_annual_2023d']              /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['drive_to_transit_cost_pct_of_income']        = travel_cost_df['total_drive_to_transit_cost_annual_2023d']              /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['taxitnc_cost_pct_of_income']                 = travel_cost_df['total_taxitnc_cost_annual_2023d']              /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['auto_own_finance_cost_pct_of_income']        = travel_cost_df['total_auto_own_finance_cost_annual_2023d']        /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['auto_insurance_cost_pct_of_income']          = travel_cost_df['total_auto_insurance_cost_annual_2023d']          /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['auto_registration_taxes_cost_pct_of_income'] = travel_cost_df['total_auto_registration_taxes_cost_annual_2023d'] /travel_cost_df['total_hhld_income_annual_2023d']
    travel_cost_df['transportation_cost_pct_of_income']          = travel_cost_df['total_transportation_cost_annual_2023d']          /travel_cost_df['total_hhld_income_annual_2023d']

    # package for returning
    # create key
    travel_cost_df.reset_index(drop=False, inplace=True)
    travel_cost_df['key'] = travel_cost_df['incQ'] + " " + travel_cost_df['hhld_travel']

    # drop unused rows
    travel_cost_df = travel_cost_df.loc[ (travel_cost_df['incQ'] != 'incQ3') & (travel_cost_df['incQ'] != 'incQ4') ]

    # drop unused columns
    travel_cost_df.drop(columns=[
        'incQ', 'hhld_travel', # now in key
        'total_auto_op_cost',
        'total_parking_cost',
        'total_bridge_toll',
        'total_value_toll',
        'total_cordon_toll',
        'total_fare',
        'total_drv_trn_op_cost',
        'total_taxitnc_cost',
        'total_detailed_auto_cost',
        'total_detailed_transit_cost',
        'total_hhld_income',
        'total_auto_op_cost_annual_2023d',
        'total_parking_cost_annual_2023d',
        'total_bridge_toll_cost_annual_2023d',
        'total_value_toll_cost_annual_2023d',
        'total_cordon_toll_cost_annual_2023d',
        'total_transit_op_cost_annual_2023d',
        'total_drive_to_transit_cost_annual_2023d',
        'total_taxitnc_cost_annual_2023d',
        'total_detailed_auto_cost_annual_2023d',
        'total_detailed_transit_cost_annual_2023d',
        'total_auto_own_finance_cost_annual_2023d',
        'total_auto_insurance_cost_annual_2023d',
        'total_auto_registration_taxes_cost_annual_2023d',
        'total_transportation_cost_annual_2023d',
        'total_hhld_income_annual_2023d'], 
        inplace=True)

    LOGGER.debug("  travel_cost_df:\n{}".format(travel_cost_df))
    travel_cost_df.rename(columns={'total_hhld_autos':'total_hhld_num_autos'}, inplace=True)
    # move columns to rows
    metrics_df = pd.melt(travel_cost_df,
                         id_vars=['key'],
                         var_name='metric_desc',
                         value_name='value')
    metrics_df[['income levels', 'modes']] = metrics_df['key'].str.split(' ', n=1, expand=True)
    metrics_df.drop(columns=['key'], inplace=True)
    metrics_df['intermediate/final'] = 'intermediate'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('num_'), 'intermediate/final'] = 'extra'
    metrics_df.loc[ metrics_df['metric_desc'].str.endswith('_pct_of_income'), 'intermediate/final'] = 'final'
    metrics_df['modelrun_id'] = tm_run_id
    metrics_df['year'] = tm_run_id[:4]
    metrics_df['metric_id'] = METRIC_ID
    
    # add column for value type
    metrics_df['value type'] = 'actual/count'
    metrics_df.loc[metrics_df['metric_desc'].str.contains('per') == True, 'value type'] = 'average/ratio'
    metrics_df.loc[metrics_df['metric_desc'].str.contains('pct') == True, 'value type'] = 'percent'
    
    # add column for 'Households, Income, Autos, Trips, Costs' for Tableau view
    metrics_df.loc[ metrics_df['metric_desc'] == 'num_hhlds', 'Households, Income, Autos, Trips, Costs'] = 'Households'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('hhld_income') == True, 'Households, Income, Autos, Trips, Costs'] = 'Income'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('num_autos') == True, 'Households, Income, Autos, Trips, Costs'] = 'Autos'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('_trips') == True, 'Households, Income, Autos, Trips, Costs'] = 'Trips'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('auto_own_finance_cost') == True, 'Households, Income, Autos, Trips, Costs'] = 'Fixed Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('auto_insurance_cost') == True, 'Households, Income, Autos, Trips, Costs'] = 'Fixed Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('auto_registration_taxes_cost') == True, 'Households, Income, Autos, Trips, Costs'] = 'Fixed Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('auto_op_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('parking_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('bridge_toll_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('value_toll_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('cordon_toll_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('transit_op_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('drive_to_transit_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('taxitnc_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('transportation_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Total Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('auto_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'
    metrics_df.loc[ metrics_df['metric_desc'].str.contains('transit_cost') == True , 'Households, Income, Autos, Trips, Costs'] = 'Variable Costs'

    LOGGER.debug("  returning:\n{}".format(metrics_df))

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
    
    # line below for round 2 runs
    # current_runs_list = ['2035_TM160_NGF_r2_NoProject_01', '2035_TM160_NGF_r2_NoProject_01_AOCx1.25_v2', '2035_TM160_NGF_r2_NoProject_03_pretollcalib', '2035_TM160_NGFr2_NP04_Path1_02']

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Affordable1_transportation_costs_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Affordable1_transportation_costs(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ S2 Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()