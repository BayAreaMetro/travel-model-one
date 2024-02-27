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

import argparse, datetime, logging,os, pathlib, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict

LOG_FILE = "pba50_metrics.log"

# Global Assumptions
INFLATION_2000_TO_2020 = 1.53
INFLATION_2018_TO_2020 = 1.04

# Used in calculate_Affordable1_HplusT_costs()
UNIVERSAL_BASIC_INCOME_START_YEAR = 2025
UNIVERSAL_BASIC_INCOME_IN_2020_DOLLARS = 6000
UNIVERSAL_BASIC_INCOME_CATEGORIES = ['Plus','Alt1','Alt2'] # model run categories

# Annual Auto ownership cost in 2018$
# Source: Consumer Expenditure Survey 2018 (see Box\Horizon and Plan Bay Area 2050\Equity and Performance\7_Analysis\Metrics\Affordable\auto_ownership_costs.xlsx)
# (includes depreciation, insurance, finance charges, license fees)
AUTO_OWNERSHIP_COST_ALLINC_IN_2018_DOLLARS = 5945
AUTO_OWNERSHIP_COST_INCQ1_IN_2018_DOLLARS  = 2585
AUTO_OWNERSHIP_COST_INCQ2_IN_2018_DOLLARS  = 4224

# Handle box drives in E: (e.g. for virtual machines)
USERNAME    = os.getenv('USERNAME')
BOX_DIR     = pathlib.Path(f"C:/Users/{USERNAME}/Box")
if USERNAME.lower() in ['lzorn']:
    BOX_DIR = pathlib.Path("E:\Box")

METRICS_COLUMNS = [
    'modelrun_id',  # directory from ModelRuns.xlsx
    'year',         # from ModelRuns.xlsx
    'run_set',      # from ModelRuns.xlsx
    'category',     # from ModelRuns.xlsx
    'metric_id',    # e.g., Connected 1, Affordable 2, etc.
    'metric_name',
    'value'
]

def calculate_Affordable1_HplusT_costs(model_runs_dict: dict):
    """Pulls transportation costs from other files and converts to annual
    to calculate them as a percentage of household income; these calculations
    are segmented by income quartiles.

    Reads the following files:
    1. INTERMEDIATE_METRICS_SOURCE_DIR/housing_costs_share_income.csv which has columns:
       year, blueprint, w_q1, w_q2, w_q2, w_q4, w_q1_q2, w_all -- which presumably mean the share of household income spent on housing.
       This looks like it was produced by
       https://github.com/BayAreaMetro/regional_forecast/blob/main/housing_income_share_metric/Share_Housing_Costs_Q1-4.R

    2. [model_run_dir]/OUTPUT/metrics/scenario_metrics.csv for income-segmented
       total_households, total_hh_inc,
       total_auto_cost (daily), total_auto_trips (daily),
       total_transit_fares (daily), total_transit_trips (daily)

    3. [model_run_dir]/OUTPUT/metrics/parking_costs_tour.csv for income-segmented
       parking_costs (daily)

    4. [model_run_dir]/OUTPUT/metrics/autos_owned.csv for income-segmented auto ownership

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key

    Writes metrics_affordable1_HplusT_costs.csv with columns:
        modelrun_id
        modelrun_alias

    """
    LOGGER.info("calculate_Affordable1_HplusT_costs()")

    # assumptions
    DAYS_PER_YEAR = 300

    # Read Housing costs intermediate input
    HOUSING_COSTS_FILE = INTERMEDIATE_METRICS_SOURCE_DIR / 'housing_costs_share_income.csv' # from Bobby, based on Urbansim outputs only
    LOGGER.info(f"  Reading {HOUSING_COSTS_FILE}")
    housing_costs_df   = pd.read_csv(HOUSING_COSTS_FILE)
    LOGGER.debug("  housing_costs_df (len={}):\n{}".format(
        len(housing_costs_df), housing_costs_df))
    # select to only these cols
    housing_costs_df = housing_costs_df[['year','blueprint','w_q1','w_q2','w_q3','w_q4','w_q1_q2','w_all']]
    # convert to long - move income quartiles to rows
    housing_costs_df = pd.wide_to_long(df=housing_costs_df, i=['year','blueprint'], 
                                       stubnames='w', sep='_', suffix='(all|q[1-4](_q2)?)', j='incQ').reset_index()
    # rename "w" column to be more clear; recode quartiles
    housing_costs_df.rename(columns={'w':'housing_cost_share_of_hh_income'}, inplace=True)
    housing_costs_df['incQ']  = housing_costs_df.incQ.map({'q1':'1', 'q2':'2', 'q3':'3', 'q4':'4', 'q1_q2':'1&2', 'all':'all'})
    # recode year/blueprint to model run alias
    housing_costs_df['modelrun_alias'] = housing_costs_df.year.astype(str) + " " + housing_costs_df.blueprint
    housing_costs_df['modelrun_alias'] = housing_costs_df.modelrun_alias.map({
        '2015 2015':'2015', '2050 NoProject':'2050 No Project', '2050 Plus':'2050 Plan', '2050 Alt1':'2050 EIR Alt1', '2050 Alt2':'2050 EIR Alt2'})
    housing_costs_df.drop(columns=['year','blueprint'], inplace=True)
    LOGGER.debug("  housing_costs_df (len={}):\n{}".format(
        len(housing_costs_df), housing_costs_df))

    affordable_hplust_costs_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        model_run_category = model_runs_dict[tm_runid]['category']
        LOGGER.info(f"  Processing {tm_runid} with categery {model_run_category}")

        # read scenario metrics
        scenario_metrics_file = model_run_dir / "OUTPUT" / "metrics" / "scenario_metrics.csv"
        LOGGER.info(f"  Reading {scenario_metrics_file}")
        tm_scen_metrics_df = pd.read_csv(scenario_metrics_file, header=None, names=['modelrun_id', 'metric_name','value'])

        # filter to metric_name in: [total_auto_cost,total_auto_trips,total_hh_inc,total_households,total_transit_fares,total_transit_trips]_inc[1,2,3,4]
        income_segmented_metrics = [
            'total_auto_cost',
            'total_auto_trips',
            'total_hh_inc',
            'total_households',
            'total_transit_fares',
            'total_transit_trips'
        ]
        tm_scen_metrics_df = tm_scen_metrics_df.loc[ tm_scen_metrics_df.metric_name.str[:-5].isin(income_segmented_metrics)]
        tm_scen_metrics_df['incQ']        = tm_scen_metrics_df.metric_name.str[-1:].astype(int)
        tm_scen_metrics_df['metric_name'] = tm_scen_metrics_df.metric_name.str[:-5]
        LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))

        # pivot so columns are modelrun_id, inc, + metric_names in income_segmented_metrics above
        tm_scen_metrics_df = tm_scen_metrics_df.pivot(index=['modelrun_id','incQ'], columns='metric_name', values='value').reset_index()
        LOGGER.debug("  pivoted tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))

        # Universal Basic Income: check year and model category
        tm_scen_metrics_df['total_hh_inc_with_UBI'] = tm_scen_metrics_df.total_hh_inc
        if (model_run_category in UNIVERSAL_BASIC_INCOME_CATEGORIES) and (model_runs_dict[tm_runid]['year'] >= UNIVERSAL_BASIC_INCOME_START_YEAR):
            # add in UBI for Q1 households; since this is *total* income, it's multiplied by the number of households
            assert(len(tm_scen_metrics_df.loc[ tm_scen_metrics_df.incQ == 1 ]) == 1)
            tm_scen_metrics_df.loc[ tm_scen_metrics_df.incQ == 1, 'total_hh_inc_with_UBI'] = tm_scen_metrics_df.total_hh_inc + \
                (UNIVERSAL_BASIC_INCOME_IN_2020_DOLLARS / INFLATION_2000_TO_2020)*tm_scen_metrics_df.total_households
            LOGGER.debug(  "tm_scen_metrics_df with UBI applied:\n{}".format(tm_scen_metrics_df))

        # read parking costs; these are daily costs in 2000 dollars
        parking_cost_file = model_run_dir / "OUTPUT" / "metrics" / "parking_costs_tour.csv"
        LOGGER.info(f"  Reading {parking_cost_file}")
        tm_parking_cost_df = pd.read_csv(parking_cost_file)
        # LOGGER.debug("  tm_parking_cost_df:\n{}".format(tm_parking_cost_df))
        tm_parking_cost_df = tm_parking_cost_df.groupby(by='incQ').agg({'parking_cost':'sum'}).reset_index()
        # LOGGER.debug("  tm_parking_cost_df:\n{}".format(tm_parking_cost_df))
        # join to tm_scen_metrics_df; so it now has parking_cost column
        tm_scen_metrics_df = pd.merge(
            left  = tm_scen_metrics_df,
            right = tm_parking_cost_df,
            how   = 'left',
            on    = 'incQ'
        )

        # read auto ownership summary
        autos_owned_file = model_run_dir / "OUTPUT" / "metrics" / "autos_owned.csv"
        LOGGER.info(f"  Reading {autos_owned_file}")
        tm_auto_owned_df = pd.read_csv(autos_owned_file)
        # LOGGER.debug("  tm_auto_owned_df:\n{}".format(tm_auto_owned_df))
        tm_auto_owned_df['total_autos'] = tm_auto_owned_df.autos * tm_auto_owned_df.households
        tm_auto_owned_df = tm_auto_owned_df.groupby('incQ').agg({'total_autos':'sum'}).reset_index()
        # LOGGER.debug("  tm_auto_owned_df:\n{}".format(tm_auto_owned_df))
        # join to tm_scen_metrics_df; so it now has total_autos column
        tm_scen_metrics_df = pd.merge(
            left  = tm_scen_metrics_df,
            right = tm_auto_owned_df[['incQ','total_autos']],
            how   = 'left',
            on    = 'incQ'
        )

        # make index: modelrun_id, incQ
        tm_scen_metrics_df['incQ'] = tm_scen_metrics_df['incQ'].astype('str')
        tm_scen_metrics_df.set_index(keys=['modelrun_id','incQ'], inplace=True)

        # add aggregte rows: all incomes, incQ1 & incQ2
        tm_scen_metrics_df.loc[(tm_runid, 'all'),:] = tm_scen_metrics_df.sum(axis=0)
        tm_scen_metrics_df.loc[(tm_runid, '1&2'),:] = tm_scen_metrics_df.loc[ tm_scen_metrics_df.index.get_level_values('incQ').isin(['1','2']) ].sum(axis=0)

        # total auto ownership cost in 2000 dollars = 
        #     total autos x cost per auto (in 2018 dollars) x INFLATION_2018_TO_2020/INFLATION_2000_TO_2020
        # we only have aggregate version, inc1 version and inc2 version
        tm_scen_metrics_df['total_auto_ownership_cost_annual'] = numpy.nan
        tm_scen_metrics_df.loc[    (tm_runid, 'all'), 'total_auto_ownership_cost_annual'] = \
            tm_scen_metrics_df.loc[(tm_runid, 'all'), 'total_autos']*AUTO_OWNERSHIP_COST_ALLINC_IN_2018_DOLLARS * (INFLATION_2018_TO_2020/INFLATION_2000_TO_2020)
        tm_scen_metrics_df.loc[    (tm_runid, '1'  ), 'total_auto_ownership_cost_annual'] = \
            tm_scen_metrics_df.loc[(tm_runid, '1'  ), 'total_autos']*AUTO_OWNERSHIP_COST_INCQ1_IN_2018_DOLLARS* (INFLATION_2018_TO_2020/INFLATION_2000_TO_2020)
        tm_scen_metrics_df.loc[    (tm_runid, '2'  ), 'total_auto_ownership_cost_annual'] = \
            tm_scen_metrics_df.loc[(tm_runid, '2'  ), 'total_autos']*AUTO_OWNERSHIP_COST_INCQ2_IN_2018_DOLLARS* (INFLATION_2018_TO_2020/INFLATION_2000_TO_2020)
        LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))

        # annualize - these are in 2000 dollars
        tm_scen_metrics_df['total_auto_op_cost_annual' ] = DAYS_PER_YEAR*tm_scen_metrics_df['total_auto_cost'    ]
        tm_scen_metrics_df['total_transit_fares_annual'] = DAYS_PER_YEAR*tm_scen_metrics_df['total_transit_fares']
        tm_scen_metrics_df['total_parking_cost_annual' ] = DAYS_PER_YEAR*tm_scen_metrics_df['parking_cost'       ]
        # LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))

        # total annual transportation costs in 2000 dollars
        tm_scen_metrics_df['total_tansp_cost_annual'] = \
            tm_scen_metrics_df.total_auto_op_cost_annual + \
            tm_scen_metrics_df.total_transit_fares_annual + \
            tm_scen_metrics_df.total_auto_ownership_cost_annual + \
            tm_scen_metrics_df.total_parking_cost_annual

        # Transportation cost % of income
        tm_scen_metrics_df['transp_cost_share_of_hh_income'] = tm_scen_metrics_df.total_tansp_cost_annual / tm_scen_metrics_df.total_hh_inc_with_UBI

        # reset index and pull alias from ModelRuns.xlsx info
        tm_scen_metrics_df.reset_index(drop=False, inplace=True)
        tm_scen_metrics_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']

        # join to housing costs
        tm_scen_metrics_df = pd.merge(
            left    = tm_scen_metrics_df,
            right   = housing_costs_df,
            how     = 'left',
            on      = ['modelrun_alias', 'incQ'],
            validate='one_to_one'
        )

        # h+t = h + t
        tm_scen_metrics_df['H+T_cost_share_of_hh_income'] = tm_scen_metrics_df.housing_cost_share_of_hh_income + tm_scen_metrics_df.transp_cost_share_of_hh_income


        LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))
        affordable_hplust_costs_df = pd.concat([affordable_hplust_costs_df, tm_scen_metrics_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_affordable1_HplusT_costs.csv'
    affordable_hplust_costs_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

    return

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
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_numHH',year,dbp]       = tm_tot_hh * INFLATION_2000_TO_2020

    # All households
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$',year,dbp]             = tp_cost / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown',year,dbp]     = tm_tot_auto_owner_cost / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop',year,dbp]      = tm_tot_auto_op_cost / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark',year,dbp]    = tm_tot_auto_park_cost / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare',year,dbp] = tm_tot_transit_fares / tm_tot_hh * INFLATION_2000_TO_2020

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check',year,dbp]         = tm_tot_auto_op_cost_check / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint  / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls  / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls / tm_tot_hh * INFLATION_2000_TO_2020   
    
    # Q1 HHs
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp]             = tp_cost_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoown_inc1',year,dbp]     = tm_tot_auto_owner_cost_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_inc1',year,dbp]      = tm_tot_auto_op_cost_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autopark_inc1',year,dbp]    = tm_tot_auto_park_cost_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_transitfare_inc1',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_check_inc1',year,dbp]         = tm_tot_auto_op_cost_check_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_fuel_maint_inc1',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_valuetolls_inc1',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_autoop_bridgetolls_inc1',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020   

    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc1',year,dbp] = tp_cost_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'mean_transportation_cost_2020$_inc2',year,dbp] = tp_cost_inc2 / tm_tot_hh_inc2 * INFLATION_2000_TO_2020

    
    
    # Average Daily Tolls per household
    metrics_dict[runid,metric_id,'tolls_per_HH',year,dbp]           = total_tolls_allHH / tm_tot_hh * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'tolls_per_inc1and2HH',year,dbp]   = total_tolls_inc1and2 / (tm_tot_hh_inc1+tm_tot_hh_inc2) * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'tolls_per_inc1HH',year,dbp]       = total_tolls['inc1'] / tm_tot_hh_inc1 * INFLATION_2000_TO_2020

    # Average Daily Fares per Household   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'fares_per_HH',year,dbp]     = tm_tot_transit_fares / tm_tot_hh * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1and2HH',year,dbp]   = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_hh_inc1+tm_tot_hh_inc2) * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'fares_per_inc1HH',year,dbp] = tm_tot_transit_fares_inc1 / tm_tot_hh_inc1 * INFLATION_2000_TO_2020 / days_per_year

    

    ####### per trip auto

    # Total auto trips per day (model outputs are in trips, per day)
    tm_tot_auto_trips      = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_auto_trips") == True), 'value'].sum()
    tm_tot_auto_trips_inc1 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc1"),'value'].item() 
    tm_tot_auto_trips_inc2 = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_auto_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_auto_perday',year,dbp]          = tm_tot_auto_trips
    metrics_dict[runid,metric_id,'trips_total_auto_perday_inc1',year,dbp]     = tm_tot_auto_trips_inc1

    # Average Tolls per trip  (total_tolls_xx is calculated above as per day tolls in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_tolls',year,dbp]          = total_tolls_allHH / tm_tot_auto_trips * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1and2',year,dbp] = total_tolls_inc1and2 / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * INFLATION_2000_TO_2020
    metrics_dict[runid,metric_id,'per_trip_tolls_inc1',year,dbp]     = total_tolls['inc1'] / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020

    # Total auto operating cost per trip (tm_tot_auto_op_cost and tm_tot_auto_park_cost are calculated above as annual costs in 2000 dollars)
    metrics_dict[runid,metric_id,'per_trip_autocost',year,dbp]           = (tm_tot_auto_op_cost + tm_tot_auto_park_cost) / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_park',year,dbp]      = tm_tot_auto_park_cost / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op',year,dbp]        = tm_tot_auto_op_cost / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_op_check',year,dbp]             = tm_tot_auto_op_cost_check / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_fuel_maint',year,dbp]        = tm_tot_auto_op_cost_fuel_maint / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_valuetolls',year,dbp]        = tm_tot_auto_op_cost_valuetolls / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_op_bridgetolls',year,dbp]       = tm_tot_auto_op_cost_bridgetolls / tm_tot_auto_trips * INFLATION_2000_TO_2020 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_park_cost_inc1) / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year 
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op',year,dbp]               = tm_tot_auto_op_cost_inc1             / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_check',year,dbp]         = tm_tot_auto_op_cost_check_inc1       / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_fuel_maint',year,dbp]    = tm_tot_auto_op_cost_fuel_maint_inc1  / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_valuetolls',year,dbp]    = tm_tot_auto_op_cost_valuetolls_inc1  / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_op_bridgetolls',year,dbp]   = tm_tot_auto_op_cost_bridgetolls_inc1 / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_autocost_inc1_park',year,dbp]             = tm_tot_auto_park_cost_inc1           / tm_tot_auto_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year

    metrics_dict[runid,metric_id,'per_trip_autocost_inc1and2',year,dbp]  = (tm_tot_auto_op_cost_inc1 + tm_tot_auto_op_cost_inc2 + tm_tot_auto_park_cost_inc1 + tm_tot_auto_park_cost_inc2) / (tm_tot_auto_trips_inc1+tm_tot_auto_trips_inc2) * INFLATION_2000_TO_2020  / days_per_year


    ####### per trip transit

    # Total transit trips per day (model outputs are in trips, per day)
    tm_tot_transit_trips            = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'].str.contains("total_transit_trips") == True), 'value'].sum() 
    tm_tot_transit_trips_inc1       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc1"),'value'].item() 
    tm_tot_transit_trips_inc2       = tm_scen_metrics_df.loc[(tm_scen_metrics_df['metric_name'] == "total_transit_trips_inc2"),'value'].item() 
    metrics_dict[runid,metric_id,'trips_total_transit_perday',year,dbp]          = tm_tot_transit_trips
    metrics_dict[runid,metric_id,'trips_total_transit_perday_inc1',year,dbp]     = tm_tot_transit_trips_inc1

    # Average Fares per trip   (note: transit fares totals calculated above are annual and need to be divided by days_per_year)
    metrics_dict[runid,metric_id,'per_trip_fare',year,dbp]          = tm_tot_transit_fares / tm_tot_transit_trips * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1and2',year,dbp] = (tm_tot_transit_fares_inc1 + tm_tot_transit_fares_inc2) / (tm_tot_transit_trips_inc1+tm_tot_transit_trips_inc2) * INFLATION_2000_TO_2020 / days_per_year
    metrics_dict[runid,metric_id,'per_trip_fare_inc1',year,dbp]     = tm_tot_transit_fares_inc1 / tm_tot_transit_trips_inc1 * INFLATION_2000_TO_2020 / days_per_year

def extract_Connected1_JobAccess(model_runs_dict: dict):
    """
    Pulls the relevant Connected 1 - Job Access metrics from scenario_metrics.csv
    These are calculated in scenarioMetrics.py:tally_access_to_jobs_v2() and have the prefix jobacc2_
    We only keep the following: jobacc2_*_acc_accessible_job_share[_coc,_hra]

    Args:
        model_runs_dict: contents of ModelRuns.xlsx with modelrun_id key

    Writes metrics_connected1_jobaccess.csv with columns:
        modelrun_id
        modelrun_alias
        mode (e.g. 'bike', 'wtrn')
        time (e.g. 20, 45) - time threshold
        person_segment ('coc','hra','all')
        job_share
        accessible_jobs (job_share x TOTEMP)
    """
    LOGGER.info("extract_Connected1_JobAccess()")

    job_acc_metrics_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid

        # read tazdata for total employment
        tazdata_file = model_run_dir / "INPUT" / "landuse" / "tazData.csv"
        LOGGER.info("  Reading {}".format(tazdata_file))
        tazdata_df = pd.read_csv(tazdata_file)
        LOGGER.info("  TOTEMP: {:,}".format(tazdata_df['TOTEMP'].sum()))

        # read scenario metrics
        scenario_metrics_file = model_run_dir / "OUTPUT" / "metrics" / "scenario_metrics.csv"
        LOGGER.info("  Reading {}".format(scenario_metrics_file))
        scenario_metrics_df = pd.read_csv(scenario_metrics_file, header=None, names=['modelrun_id', 'metric_name','value'])

        # filter to only jobacc2_* metrics and then strip that off
        scenario_metrics_df = scenario_metrics_df.loc[ scenario_metrics_df.metric_name.str.startswith('jobacc2_')]
        scenario_metrics_df['metric_name'] = scenario_metrics_df.metric_name.str[8:]

        # filter to only acc_accessible_job_share[_coc,_hra]
        scenario_metrics_df = scenario_metrics_df.loc[ 
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share') |
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share_coc') |
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share_hra')]

        # extract mode, time, person_segment
        scenario_metrics_df['mode'] = scenario_metrics_df.metric_name.str.extract(r'^([a-z]+)')
        scenario_metrics_df['time'] = scenario_metrics_df.metric_name.str.extract(r'^[a-z]+[_]([0-9]+)')
        scenario_metrics_df['person_segment'] = scenario_metrics_df.metric_name.str.extract(r'share[_]([a-z]*)$')
        scenario_metrics_df.loc[ pd.isna(scenario_metrics_df['person_segment']), 'person_segment' ] = 'all'
        LOGGER.debug("scenario_metrics_df:\n{}".format(scenario_metrics_df))

        # value is all job share
        scenario_metrics_df.rename(columns={'value':'job_share'}, inplace=True)
        # metric_name is not useful any longer -- drop it
        scenario_metrics_df.drop(columns='metric_name', inplace=True)
        # calculate the number of jobs
        scenario_metrics_df['accessible_jobs'] = scenario_metrics_df['job_share']*tazdata_df['TOTEMP'].sum()
        # pull alias from ModelRuns.xlsx info
        scenario_metrics_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']
        LOGGER.debug("scenario_metrics_df:\n{}".format(scenario_metrics_df))

        job_acc_metrics_df = pd.concat([job_acc_metrics_df, scenario_metrics_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_connected1_jobaccess.csv'
    job_acc_metrics_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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



def calculate_Connected2_crowding(model_runs_dict: dict):
    """
    Reads the transit crowding results for each model run and summarizes percent of person-time in
    crowded (load_standcap > 0.85) and over capacity (load_standcap > 1.0) conditions.

    Person time is summarized using the mapping in METRICS_SOURCE_DIR / transit_system_lookup.csv
    which includes columns: mode, SYSTEM, operator, mode_name
    We only use mode -> operator here

    Args:
        model_runs_dict (dict): ModelRuns.xlsx contents, indexed by modelrun_id

    Writes metrics_connected2_trn_crowding.csv with columns:
        modelrun_id
        modelrun_alias
        operator - this is based on the mode -> operator mapping from transit_system_lookup.csv
        pct_crowded - percent of person-time in crowded vehicles
        pct_overcapacity - percent of person-time in overcapacity vehicles
    """
    LOGGER.info("calculate_Connected2_crowding()")

    TRN_MODE_OPERATOR_LOOKUP_FILE = METRICS_SOURCE_DIR / 'transit_system_lookup.csv'
    LOGGER.info("  Reading {}".format(TRN_MODE_OPERATOR_LOOKUP_FILE))
    trn_mode_operator_df = pd.read_csv(TRN_MODE_OPERATOR_LOOKUP_FILE, usecols=['mode','SYSTEM','operator'])

    # verify SYSTEM is unique
    trn_mode_operator_df['SYSTEM_dupe'] = trn_mode_operator_df.duplicated(subset=['SYSTEM'], keep=False)
    # note: it is not
    LOGGER.debug("  trn_mode_operator_df with SYSTEM_dupe:\n{}".format(
        trn_mode_operator_df.loc[ trn_mode_operator_df.SYSTEM_dupe == True]))

    all_trn_crowding_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid

        # read the transit crowing model results
        trn_crowding_file = model_run_dir / "OUTPUT" / "metrics" / "transit_crowding_complete.csv"
        LOGGER.info("  Reading {}".format(trn_crowding_file))
        tm_crowding_df = pd.read_csv(trn_crowding_file, usecols=['TIME','SYSTEM','MODE','ABNAMESEQ','period','load_standcap','AB_VOL'])

        # select only AM
        tm_crowding_df = tm_crowding_df.loc[tm_crowding_df['period'] == "AM"]
        LOGGER.debug("tm_crowding_df.head(10)\n{}".format(tm_crowding_df))

        # set time for links that are overcapacity (load_standcap > 1)
        tm_crowding_df['time_overcapacity'] = 0.0
        tm_crowding_df.loc[ tm_crowding_df.load_standcap > 1, 'time_overcapacity'] = tm_crowding_df.TIME

        # set time for links that are crowded (load_standcap > 0.85)
        tm_crowding_df['time_crowded'] = 0.0
        tm_crowding_df.loc[ tm_crowding_df.load_standcap > 0.85, 'time_crowded'] = tm_crowding_df.TIME

        # convert to person-time (TIME is in hundredths of a minute)
        tm_crowding_df['person_time_total']   = tm_crowding_df['AB_VOL']*tm_crowding_df['TIME']
        tm_crowding_df['person_time_overcap'] = tm_crowding_df['AB_VOL']*tm_crowding_df['time_overcapacity']
        tm_crowding_df['person_time_crowded'] = tm_crowding_df['AB_VOL']*tm_crowding_df['time_crowded']

        # join with SYSTEM -> operator
        # TODO: I think joinin on SYSTEM is wrong since there are duplicates - Leaving bug in for now, but
        # TODO: this should be fixed
        tm_crowding_df = pd.merge(
            left     = tm_crowding_df, 
            right    = trn_mode_operator_df, 
            # left_on  = 'MODE',
            # right_on = 'mode',
            on       = 'SYSTEM',
            how      = "left")

        system_crowding_df = tm_crowding_df.groupby('operator').agg({
            'person_time_total'  :'sum',
            'person_time_overcap':'sum',
            'person_time_crowded':'sum'
        }).reset_index()
        
        system_crowding_df['pct_overcapacity'] = system_crowding_df['person_time_overcap'] / system_crowding_df['person_time_total'] 
        system_crowding_df['pct_crowded']      = system_crowding_df['person_time_crowded'] / system_crowding_df['person_time_total'] 
        LOGGER.debug("system_crowding_df:\n{}".format(system_crowding_df))

        # drop intermediate columns
        system_crowding_df.drop(columns=['person_time_total','person_time_overcap','person_time_crowded'], inplace=True)

        # keep metadata
        system_crowding_df['modelrun_id'] = tm_runid
        system_crowding_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']

        # roll it up
        all_trn_crowding_df = pd.concat([all_trn_crowding_df, system_crowding_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_connected2_trn_crowding.csv'
    all_trn_crowding_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

def calculate_Connected2_hwy_traveltimes(model_runs_dict: dict):
    """
    Reads loaded roadway network, filtering to highway corridor links,
    as defined by METRICS_SOURCE_DIR/maj_corridors_hwy_links.csv
    That file has columns, route, a, b
    
    Args:
        model_runs_dict (dict): ModelRuns.xlsx contents, indexed by modelrun_id
    
    Writes metrics_connected2_hwy_traveltimes.csv with columns:
        modelrun_id
        modelrun_alias
        route - this is from METRICS_SOURCE_DIR/maj_corridors_hwy_links.csv
        ctimAM - congested travel time in the AM, in minutes
    """
    LOGGER.info("calculate_Connected2_hwy_traveltimes()")
    MAJ_CORRIDORS_HWY_LINKS_FILE = METRICS_SOURCE_DIR / 'maj_corridors_hwy_links.csv'
    LOGGER.info(f"  Reading {MAJ_CORRIDORS_HWY_LINKS_FILE}")
    maj_corridors_hwy_links_df   = pd.read_csv(MAJ_CORRIDORS_HWY_LINKS_FILE)
    maj_corridors_hwy_links_df   = maj_corridors_hwy_links_df[['route','a','b']]
    LOGGER.debug("  maj_corridors_hwy_links_df (len={}):\n{}".format(
        len(maj_corridors_hwy_links_df), maj_corridors_hwy_links_df.head(10)))

    hwy_times_metrics_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid

        # read the loaded roadway network
        network_file = model_run_dir / "OUTPUT" / "avgload5period.csv"
        LOGGER.info("  Reading {}".format(network_file))
        tm_loaded_network_df = pd.read_csv(network_file)

        # Keeping essential columns of loaded highway network: node A and B, distance, free flow time, congested time
        tm_loaded_network_df = tm_loaded_network_df.rename(columns=lambda x: x.strip())
        tm_loaded_network_df = tm_loaded_network_df[['a','b','distance','fft','ctimAM']]

        # Only keep those from maj_corridor_hwy_links
        tm_loaded_network_df = pd.merge(
            left  = maj_corridors_hwy_links_df,
            right = tm_loaded_network_df,
            on    = ['a','b'],
            how   = 'left')
        LOGGER.debug("  tm_loaded_network_df filtered to maj_corridors_hwy_links (len={}):\n{}".format(
            len(tm_loaded_network_df), tm_loaded_network_df.head(10)
        ))

        # groupby route and sum the congested AM time
        corridor_times_df = tm_loaded_network_df.groupby('route').agg({'ctimAM':'sum'}).reset_index()
        LOGGER.debug('corridor_times_df:\n{}'.format(corridor_times_df))

        # keep metadata
        corridor_times_df['modelrun_id'] = tm_runid
        corridor_times_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']

        # roll it up
        hwy_times_metrics_df = pd.concat([hwy_times_metrics_df, corridor_times_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_connected2_hwy_traveltimes.csv'
    hwy_times_metrics_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))


def calculate_Connected2_trn_traveltimes(runid, year, dbp, transit_operator_df, metrics_dict):

    metric_id = "C2"

    if "2015" in runid: tm_run_location = TM_RUN_LOCATION_IPA
    else: tm_run_location = TM_RUN_LOCATION_BP
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


def calculate_Connected2_transit_asset_condition(model_runs_dict: dict):
    """
    This is really just a passthrough for the file, 
    INTERMEDIATE_METRICS_SOURCE_DIR/transit_asset_condition.csv which has columns:
    metric, name, year, blueprint, value

    Retains rows from this file where
        blueprint=identifier corresponding to a run
        metric=[transit_revveh_beyondlife_pct_of_count|
                transit_nonveh_beyondlife_pct_of_value]   
    
    Args:
        model_runs_dict (dict): ModelRuns.xlsx contents, indexed by modelrun_id

    Writes metrics_connected2_transit_asset_conditions.csv with columns:
        modelrun_id
        modelrun_alias
        transit_allassets_beyondlife_pct_of_value
        transit_nonveh_beyondlife_pct_of_value
        transit_revveh_beyondlife_pct_of_count
    """
    LOGGER.info("calculate_Connected2_transit_asset_condition()")
    TRANSIT_ASSET_CONDITION_FILE = INTERMEDIATE_METRICS_SOURCE_DIR / 'transit_asset_condition.csv' # from Raleigh, not based on model outputs
    LOGGER.info(f"  Reading {TRANSIT_ASSET_CONDITION_FILE}")
    transit_asset_condition_df   = pd.read_csv(TRANSIT_ASSET_CONDITION_FILE)
    LOGGER.debug("  transit_asset_condition_df (len={}):\n{}".format(
        len(transit_asset_condition_df), transit_asset_condition_df.head(10)))
    
    # drop unused column ('metric'), convert long to wide
    transit_asset_condition_df.drop(columns=['metric'], inplace=True)
    transit_asset_condition_df = transit_asset_condition_df.pivot(index=['year','blueprint'], columns=['name'], values='value')
    transit_asset_condition_df.reset_index(inplace=True)
    LOGGER.debug("  transit_asset_condition_df (len={}):\n{}".format(
        len(transit_asset_condition_df), transit_asset_condition_df.head(10)))

    all_assets_conditions_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        LOGGER.info("  Processing {}: category={}".format(tm_runid, model_runs_dict[tm_runid]['category']))

        # filter to year
        run_asset_condition_df = transit_asset_condition_df.loc[transit_asset_condition_df.year==model_runs_dict[tm_runid]['year']]

        # some translation for "blueprint" (should be scenario)
        category = model_runs_dict[tm_runid]['category']
        if model_runs_dict[tm_runid]['year'] == 2015: category = "2015"
        if category=="No Project": category = "NoProject"

        # filter to the category
        run_asset_condition_df = transit_asset_condition_df.loc[transit_asset_condition_df.blueprint==category]
        # assert we found one row
        assert(len(run_asset_condition_df) == 1)
        run_asset_condition_df.drop(columns=['year','blueprint'], inplace=True)

        # keep metadata
        run_asset_condition_df['modelrun_id'] = tm_runid
        run_asset_condition_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']

        # roll it up
        all_assets_conditions_df = pd.concat([all_assets_conditions_df, run_asset_condition_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_connected2_transit_asset_conditions.csv'
    all_assets_conditions_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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


if __name__ == '__main__':

    #### Args ######################################################################################################################
    parser = argparse.ArgumentParser(
        description = USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rtp', type=str, choices=['RTP2021','RTP2025'])
    parser.add_argument('--test', action='store_true', help='If passed, writes output to cwd instead of METRICS_OUTPUT_DIR')
    my_args = parser.parse_args()

    #### Pandas options ############################################################################################################
    # Affects logs file
    pd.options.display.width = 500 # redirect output to file so this will be readable
    pd.options.display.max_columns = 100
    pd.options.display.max_rows = 500
    pd.options.mode.chained_assignment = None  # default='warn'

    #### File locations ############################################################################################################
    TM_RUN_LOCATION      = pathlib.Path('M:/Application/Model One/{}/'.format(my_args.rtp))
    TM_RUN_LOCATION_IP   = TM_RUN_LOCATION / 'IncrementalProgress'
    TM_RUN_LOCATION_BP   = TM_RUN_LOCATION / 'Blueprint'
    MODELRUNS_XLSX       = pathlib.Path('../config_{}/ModelRuns_{}.xlsx'.format(my_args.rtp, my_args.rtp))

    # Set location of external inputs
    #All files are located in below folder / check sources.txt for sources
    if my_args.rtp == 'RTP2021':
        METRICS_BOX_DIR                  = BOX_DIR / "Horizon and Plan Bay Area 2050" / "Equity and Performance" / "7_Analysis" / "Metrics"
        METRICS_SOURCE_DIR               = METRICS_BOX_DIR / "metrics_input_files"
        INTERMEDIATE_METRICS_SOURCE_DIR  = METRICS_BOX_DIR / "Metrics_Outputs_FinalBlueprint" / "Intermediate Metrics"
        # This is for reproducing RTP2021 (PBA50) metrics for QAQC
        METRICS_OUTPUT_DIR               = BOX_DIR / "Plan Bay Area 2050+" / "Performance and Equity" / "Plan Performance" / "Equity_Performance_Metrics" / "PBA50_reproduce_for_QA"
    else:
        # todo
        METRICS_BOX_DIR                  = BOX_DIR / "Plan Bay Area 2050+" / "Performance and Equity" / "Plan Performance" / "Equity_Performance_Metrics" / "Draft_Blueprint"
        raise

    #### Test Mode ################################################################################################################
    # test mode -- write output here
    if my_args.test:
        METRICS_OUTPUT_DIR = pathlib.Path(".")
        print("Running in test mode!")

    #### Setup logging ############################################################################################################
    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handler -- append if skip_if_exists is passed
    fh = logging.FileHandler(METRICS_OUTPUT_DIR / LOG_FILE, mode='w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)
    LOGGER.debug("args = {}".format(my_args))

    #### Read ModelRuns.xlsx ######################################################################################################
    model_runs_df = pd.read_excel(MODELRUNS_XLSX)
    # select current
    model_runs_df = model_runs_df.loc[ model_runs_df.status == 'current' ]
    # select base year (pre 2025) and horizon year (2050)
    model_runs_df = model_runs_df.loc[ (model_runs_df.year < 2025) | (model_runs_df.year == 2050) ]
    # select out UrbanSim run since it's a dummy and not really a travel model run
    model_runs_df = model_runs_df.loc[ model_runs_df.directory.str.find('UrbanSim') == -1 ]
    model_runs_df.set_index(keys='directory', inplace=True)
    LOGGER.info('Model runs from {}:\n{}'.format(MODELRUNS_XLSX, model_runs_df))
    model_runs_dict = model_runs_df.to_dict(orient='index')


    #### Calculate/pull metrics ###################################################################################################

    # Affordable
    calculate_Affordable1_HplusT_costs(model_runs_dict)

    # Connected
    extract_Connected1_JobAccess(model_runs_dict)
    calculate_Connected2_hwy_traveltimes(model_runs_dict)
    calculate_Connected2_crowding(model_runs_dict)
    calculate_Connected2_transit_asset_condition(model_runs_dict)

    # TODO: deprecating the below code
    taz_coc_crosswalk_file          = METRICS_SOURCE_DIR / 'taz_coc_crosswalk.csv'
    taz_hra_crosswalk_file          = METRICS_SOURCE_DIR / 'taz_hra_crosswalk.csv'
    taz_areatype_file               = METRICS_SOURCE_DIR / 'taz_areatype.csv'
    taz_urbanizedarea_file          = METRICS_SOURCE_DIR / 'taz_urbanizedarea.csv'

    coc_flag_file                   = METRICS_SOURCE_DIR / 'COCs_ACS2018_tbl_TEMP.csv'
    transit_operator_file           = METRICS_SOURCE_DIR / 'transit_system_lookup.csv'
    
    # Set location of intermediate metric outputs
    # These are for metrics generated by Raleigh, Bobby, James
    transitproximity_file         = INTERMEDIATE_METRICS_SOURCE_DIR / 'metrics_proximity.csv'                  # from Bobby, based on Urbansim outputs only
    safety_file                   = INTERMEDIATE_METRICS_SOURCE_DIR / 'fatalities_injuries_export.csv'         # from Raleigh, based on Travel Model outputs 
    commute_mode_share_file       = INTERMEDIATE_METRICS_SOURCE_DIR / 'commute_mode_share.csv'                 # from Raleigh, based on Travel Model outputs
    emfac_file                    = INTERMEDIATE_METRICS_SOURCE_DIR / 'emfac.csv'                              # from James
    remi_jobs_file                = INTERMEDIATE_METRICS_SOURCE_DIR / 'emp by ind11_s23.csv'                   # from Bobby, based on REMI
    jobs_wagelevel_file           = INTERMEDIATE_METRICS_SOURCE_DIR / 'jobs_wagelevel.csv'                     # from Bobby, based on REMI

    metrics_dict = OrderedDict()
    y1        = "2015"
    y2        = "2050"
    y_diff    = "2050"

    # Calculate all metrics
    coc_flag_df                 = pd.read_csv(coc_flag_file)
    transit_operator_df         = pd.read_csv(transit_operator_file)
    safety_df                   = pd.read_csv(safety_file)
    emfac_df                    = pd.read_csv(emfac_file)
    commute_mode_share_df       = pd.read_csv(commute_mode_share_file)
    transitproximity_df         = pd.read_csv(transitproximity_file)
    taz_coc_xwalk_df            = pd.read_csv(taz_coc_crosswalk_file)
    taz_hra_xwalk_df            = pd.read_csv(taz_hra_crosswalk_file)
    taz_areatype_df             = pd.read_csv(taz_areatype_file)
    taz_urbanizedarea_df        = pd.read_csv(taz_urbanizedarea_file)

    # columns are METRICS_COLUMNS
    all_metrics_df = pd.DataFrame()

    for tm_runid in model_runs_dict.keys():
        LOGGER.info("Processing {}".format(tm_runid))
        tm_run_info_dict = model_runs_dict[tm_runid]
        year = tm_run_info_dict['year']
        
        # Read relevant metrics files
        # if "2015" in tm_runid: tm_run_location = TM_RUN_LOCATION_IPA
        # else: tm_run_location = TM_RUN_LOCATION_BP
        # tm_scen_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/scenario_metrics.csv',names=["runid", "metric_name", "value"])
        # tm_auto_times_df      = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/auto_times.csv',sep=",", index_col=[0,1])
        # tm_travel_cost_df     = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/TravelCost.csv')
        # tm_commute_df         = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv')
        # tm_taz_input_df       = pd.read_csv(tm_run_location+tm_runid+'/INPUT/landuse/tazData.csv')
        # 
        # tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics_by_taz.csv')            
        # #tm_vmt_metrics_df    = pd.read_csv(tm_run_location+tm_runid+'/OUTPUT/metrics/vmt_vht_metrics.csv')            
        # tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_coc_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        # tm_vmt_metrics_df = pd.merge(left=tm_vmt_metrics_df, right=taz_hra_xwalk_df, left_on="TAZ1454", right_on="TAZ1454", how="left")
        # tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_coc_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        # tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_hra_xwalk_df, left_on="ZONE", right_on="TAZ1454", how="left")
        # tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_areatype_df, left_on="ZONE", right_on="TAZ1454", how="left")
        # tm_taz_input_df = pd.merge(left=tm_taz_input_df, right=taz_urbanizedarea_df, left_on="ZONE", right_on="TAZ1454", how="left")
        
        # all_metrics_df = pd.concat([all_metrics_df, ])
        # print("@@@@@@@@@@@@@ A1 Done")
        # calculate_Connected1_proximity(tm_runid, year, dbp, transitproximity_df, metrics_dict)
        # print("@@@@@@@@@@@@@ C1 Done")
        # calculate_Connected2_trn_traveltimes(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        # calculate_Connected2_crowding(tm_runid, year, dbp, transit_operator_df, metrics_dict)
        # print("@@@@@@@@@@@@@ C2 Done")
        # calculate_Healthy1_safety(tm_runid, year, dbp, tm_taz_input_df, safety_df, metrics_dict)
        # calculate_Healthy1_safety_TAZ(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        # print("@@@@@@@@@@@@@ H1 Done")
        # calculate_Healthy2_GHGemissions(tm_runid, year, dbp, tm_taz_input_df, tm_auto_times_df, emfac_df, metrics_dict)
        # calculate_Healthy2_PM25emissions(tm_runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict)
        # calculate_Healthy2_commutemodeshare(tm_runid, year, dbp, commute_mode_share_df, metrics_dict)
        # print("@@@@@@@@@@@@@ H2 Done")
        # calculate_Vibrant1_median_commute(tm_runid, year, dbp, tm_commute_df, metrics_dict)
        # print("@@@@@@@@@@@@@ V1 Done")
        # print("@@@@@@@@@@@@@%s Done"% dbp)

    # Write output
    # out_filename = 'C:/Users/{}/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Metrics_Outputs_FinalBlueprint/metrics.csv'.format(os.getenv('USERNAME'))
    # write it locally for now
    # out_filename = 'metrics.csv'
    # all_metrics_df.to_csv(out_filename, index=False)
    # print("Wrote metrics.csv output")

    
