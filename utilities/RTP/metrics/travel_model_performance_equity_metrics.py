USAGE = """

  python travel_model_performance_equity_metrics.py

  The script calculates or extracts Performance and Equity metrics related to travel model output
  for the current set of runs.  Each metric is output to its own file:
  e.g. 
   1) metrics_affordable1_HplusT_costs.csv
   2) metrics_affordable1_trip_costs.csv
   3) metrics_connected1_jobaccess.csv
   4) metrics_connected2_hwy_traveltimes.csv
   5) metrics_connected2_trn_crowding.csv
   6) metrics_connected2_transit_asset_conditions.csv
   7) metrics_healthy1_safety.csv
   8) metrics_vibrant1_mean_commute_distance.csv

  For more detail regarding each of these files, see inline method documentation.
  
  The script also writes two logs, 
   1) travel_model_performance_equity_metrics_info.log and 
   2) travel_model_performance_equity_metrics_debug.log

  The first logs all input and output, and the second includes detailed debug information.
"""

import argparse, datetime, logging,os, pathlib, sys
import numpy, pandas as pd
from collections import OrderedDict, defaultdict

LOG_FILE = "travel_model_performance_equity_metrics_{}.log"

# Global Assumptions
INFLATION_2000_TO_2020 = 1.53
INFLATION_2018_TO_2020 = 1.04

# annualization used in calculate_Affordable1_HplusT_costs()
DAYS_PER_YEAR = 300

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

def calculate_Affordable1_HplusT_costs(model_runs_dict: dict) -> pd.DataFrame:
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
        incQ                                one of ['1','2','3','4','all','1&2']
        total_auto_cost                     daily auto operating cost, from scenario_metrics.csv
        total_auto_trips                    daily auto trips, from scenario_metrics.csv
        total_hh_inc                        sum of all annual household income for households in this quartile, in 2000 dollars, from scenario_metrics.csv
        total_hh_inc_with_UBI               the same as total_hh_inc, but with Universal Basic Income applied to q1 households
        total_households                    total number of households, from scenario_metrics.csv
        total_transit_fares                 sum of daily transit fares, in 2000 dollars, from scenario_metrics.csv
        total_transit_trips                 daily transit trips, from scenario_metrics.csv
        parking_cost                        daily parking costs, from parking_costs_tour.csv
        total_autos                         total household autos, from autos_owned.csv
        total_auto_ownership_cost_annual    annual auto ownership cost based on total_autos and auto ownership cost assumptions, in 2000 dollars
        total_auto_op_cost_annual           total_auto_cost, annualized
        total_transit_fares_annual          total_transit_fares, annualized
        total_parking_cost_annual           parking_cost, annualized
        total_tansp_cost_annual             annual transportation costs: auto op cost, auto ownership cost, parking cost, transit fares
        transp_cost_share_of_hh_income      total_tansp_cost_annual / total_hh_inc_with_UBI
        housing_cost_share_of_hh_income     housing cost as a share of household income, from housing_costs_share_income.csv
        H+T_cost_share_of_hh_income         sum of housing + transportation costs as a share of household income

    Returns DataFrame written
    """
    LOGGER.info("calculate_Affordable1_HplusT_costs()")

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
        LOGGER.info(f"  Processing {tm_runid} with category {model_run_category}")

        # read scenario metrics
        scenario_metrics_file = model_run_dir / "OUTPUT" / "metrics" / "scenario_metrics.csv"
        LOGGER.info(f"    Reading {scenario_metrics_file}")
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
        LOGGER.info(f"    Reading {parking_cost_file}")
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
        LOGGER.info(f"    Reading {autos_owned_file}")
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
    return affordable_hplust_costs_df

def calculate_Affordable1_trip_costs(model_runs_dict: dict, affordable_hplust_costs_df:pd.DataFrame):
    """ Building off calculate_Affordable1_HplusT_costs(), calculates per auto trip auto costs
    and per transit trip transit fares.

    The only new data source here is the use of
    [model_run_dir]/OUTPUT/metrics/auto_times.csv for tolls = bridge tolls + value tolls

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        pandas.DataFrame: Dataframe. see calculate_Affordable1_HplusT_costs() for description.

    Writes metrics_affordable1_trip_costs.csv with columns:
        modelrun_id
        modelrun_alias
      (same as metrics_affordable1_HplusT_costs.csv)
        incQ                                one of ['1','2','3','4','all','1&2']
        total_households                    total number of households, from scenario_metrics.csv
        total_auto_trips                    daily auto trips, from scenario_metrics.csv
        total_transit_trips                 daily transit trips, from scenario_metrics.csv
        total_auto_cost                     daily auto operating cost, from scenario_metrics.csv
        parking_cost                        daily parking costs, from parking_costs_tour.csv
        total_transit_fares                 sum of daily transit fares, in 2000 dollars, from scenario_metrics.csv
      (new!)
        auto_times_bridge_tolls                  daily bridge tolls, from auto_times.csv, in 2000 dollars
        auto_times_value_tolls                   daily value tolls, from auto_times.csv, in 2000 dollars
        auto_times_auto_op_cost                  daily auto operating cost, from auto_times.csv, in 2000 dollars
        auto_times_total_tolls                   auto_times_bridge_tolls + auto_times_value_tolls
        mean_transit_fare_2020dollars            total_transit_fares / total_transit_trips, converted to 2020 dollars
        mean_auto_op_cost_2020dollars            total_auto_cost / total_auto_trips, converted to 2020 dollars
        mean_parking_cost_2020dollars            parking_cost / total_auto_trips, converted to 2020 dollars
        mean_tolls_cost_2020dollars              auto_times_total_tolls / total_auto_trips, converted to 2020 dollars
        # TODO: I think this last row isn't intuitive; parking is out of pocket but not tolls?
        mean_auto_outofpocket_cost_2020dollars   mean_auto_op_cost_2020dollars + mean_parking_cost_2020dollars
    """

    affordable_trip_costs_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        model_run_category = model_runs_dict[tm_runid]['category']
        LOGGER.info(f"  Processing {tm_runid} with categery {model_run_category}")

        # start with columns from calculate_Affordable1_HplusT_costs() filtered to this run
        trip_costs_df = affordable_hplust_costs_df.loc[ 
            affordable_hplust_costs_df.modelrun_alias == model_runs_dict[tm_runid]['Alias']]
        # LOGGER.debug('  trip_costs_df from affordable_hplust_costs_df:\n{}'.format(trip_costs_df))
        trip_costs_df = trip_costs_df[
            ['modelrun_id','modelrun_alias','incQ','total_households',
             # trips detail since we want avg per trip
             'total_auto_trips','total_transit_trips',
             # keep daily cost detail
             'total_auto_cost','parking_cost','total_transit_fares']]
        LOGGER.debug('  trip_costs_df from affordable_hplust_costs_df:\n{}'.format(trip_costs_df))

        # read auto_times.csv
        auto_times_file = model_run_dir / "OUTPUT" / "metrics" / "auto_times.csv"
        LOGGER.info(f"    Reading {auto_times_file}")
        tm_auto_times_df = pd.read_csv(auto_times_file)
        LOGGER.debug("  tm_auto_times_df.head(10):\n{}".format(tm_auto_times_df.head(10)))

        # what are the Income==na?
        # looks like these are ix, air, zpv_tnc and truck
        # ok to drop
        # LOGGER.debug("  tm_auto_times_df with Income==na? \n{}".format(tm_auto_times_df.loc[ tm_auto_times_df.Income=='na']))
        tm_auto_times_df = tm_auto_times_df.loc[ tm_auto_times_df.Income != 'na' ]

        # columns are Income, Mode, Daily Person Trips, Daily Vehicle Trips, Person Minutes, Vehicle Minutes, Person Miles, Vehicle Miles
        #            Total Cost, VTOLL nonzero AM, VTOLL nonzero MD,  Bridge Tolls,  Value Tolls
        # costs are in 2000 cents
        # groupby income and sum
        tm_auto_times_df = tm_auto_times_df.groupby(by='Income').aggregate({
            'Bridge Tolls':'sum',
            'Value Tolls':'sum',
            'Total Cost':'sum'}).reset_index()

        # convert to 2000 dollars (from cents)
        tm_auto_times_df['Bridge Tolls'] = 0.01*tm_auto_times_df['Bridge Tolls']
        tm_auto_times_df['Value Tolls' ] = 0.01*tm_auto_times_df['Value Tolls']
        tm_auto_times_df['Total Cost'  ] = 0.01*tm_auto_times_df['Total Cost']
        # combine tolls
        tm_auto_times_df['auto_times_total_tolls'] = tm_auto_times_df['Bridge Tolls'] + tm_auto_times_df['Value Tolls']

        # rename
        tm_auto_times_df.rename(columns={
            'Bridge Tolls':'auto_times_bridge_tolls',
            'Value Tolls':'auto_times_value_tolls',
            'Total Cost':'auto_times_auto_op_cost'},
            inplace=True)

        # recode income to be consistent with trip_costs_df and make it the index
        tm_auto_times_df.rename(columns={'Income':'incQ'}, inplace=True)
        tm_auto_times_df['incQ'] = tm_auto_times_df.incQ.str[-1:]
        tm_auto_times_df.set_index('incQ', inplace=True)
        LOGGER.debug("  tm_auto_times_df.groupby(Income):\n{}".format(tm_auto_times_df))

        # add aggregte rows: all incomes, incQ1 & incQ2
        tm_auto_times_df.loc['all',:] = tm_auto_times_df.sum(axis=0)
        tm_auto_times_df.loc['1&2',:] = tm_auto_times_df.loc[ tm_auto_times_df.index.isin(['1','2']) ].sum(axis=0)
        LOGGER.debug("  tm_auto_times_df.groupby(Income):\n{}".format(tm_auto_times_df))

        # merge it back with trip_costs_df from scenario_metrics.csv
        trip_costs_df = pd.merge(
            left        = trip_costs_df,
            right       = tm_auto_times_df,
            how         = 'left',
            left_on     = ['incQ'],
            right_index = True,
            validate    = 'one_to_one'
        )
        LOGGER.debug("  trip_costs_df:\n{}".format(trip_costs_df))

        # convert to avg per trip cost in 2020 dollars
        trip_costs_df['mean_transit_fare_2020dollars'] = (trip_costs_df.total_transit_fares     / trip_costs_df.total_transit_trips) * INFLATION_2000_TO_2020
        trip_costs_df['mean_auto_op_cost_2020dollars'] = (trip_costs_df.total_auto_cost         / trip_costs_df.total_auto_trips   ) * INFLATION_2000_TO_2020
        trip_costs_df['mean_parking_cost_2020dollars'] = (trip_costs_df.parking_cost            / trip_costs_df.total_auto_trips   ) * INFLATION_2000_TO_2020
        # auto times sourced
        trip_costs_df['mean_tolls_cost_2020dollars'  ] = (trip_costs_df.auto_times_total_tolls  / trip_costs_df.total_auto_trips   ) * INFLATION_2000_TO_2020
        # out of pocket = auto op cost + parking cost (but not tolls...)
        trip_costs_df['mean_auto_outofpocket_cost_2020dollars'] = trip_costs_df.mean_auto_op_cost_2020dollars + trip_costs_df.mean_parking_cost_2020dollars
        LOGGER.debug("  trip_costs_df:\n{}".format(trip_costs_df))

        # save
        affordable_trip_costs_df = pd.concat([affordable_trip_costs_df, trip_costs_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_affordable1_trip_costs.csv'
    affordable_trip_costs_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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
        LOGGER.info(f"  Processing {tm_runid}")

        # read tazdata for total employment
        tazdata_file = model_run_dir / "INPUT" / "landuse" / "tazData.csv"
        LOGGER.info("    Reading {}".format(tazdata_file))
        tazdata_df = pd.read_csv(tazdata_file)
        LOGGER.debug("  TOTEMP: {:,}".format(tazdata_df['TOTEMP'].sum()))

        # read scenario metrics
        scenario_metrics_file = model_run_dir / "OUTPUT" / "metrics" / "scenario_metrics.csv"
        LOGGER.info("    Reading {}".format(scenario_metrics_file))
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
        LOGGER.info(f"  Processing {tm_runid}")

        # read the transit crowing model results
        trn_crowding_file = model_run_dir / "OUTPUT" / "metrics" / "transit_crowding_complete.csv"
        LOGGER.info("    Reading {}".format(trn_crowding_file))
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
        LOGGER.info(f"  Processing {tm_runid}")

        # read the loaded roadway network
        network_file = model_run_dir / "OUTPUT" / "avgload5period.csv"
        LOGGER.info("    Reading {}".format(network_file))
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

def extract_Healthy1_safety(model_runs_dict: dict, args_rtp: str):
    """
    Calculates fatalities and injuries per 100 thousand residents.

    For PBA50, this works by reading INTERMEDIATE_METRICS_SOURCE_DIR/fatalities_injuries_export.csv

    For PBA50+, the source script, VZ_saftey_calc_correction_v2.R, has been updated so 
      this works by reading [modelrun_id]\\OUTPUT\\metrics\\fatalies_injuries.csv

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'

    Writes metrics_healthy1_safety.csv with columns:
        modelrun_id
        modelrun_alias
      # these are from VZ_safety_calc_correction_V2.R
        N_bike_fatalities
        N_bike_fatalities_per_100K_pop
        N_bike_fatalities_per_100M_VMT
        N_injuries  N_injuries_per_100K_pop
        N_injuries_per_100M_VMT
        N_motorist_fatalities
        N_motorist_fatalities_per_100K_pop
        N_motorist_fatalities_per_100M_VMT
        N_ped_fatalities
        N_ped_fatalities_per_100K_pop
        N_ped_fatalities_per_100M_VMT
        N_total_fatalities
        N_total_fatalities_per_100K_pop
        N_total_fatalities_per_100M_VMT
        Population 
        annual_VMT
    """
    LOGGER.info("extract_Healthy1_safety()")

    safety_df = pd.DataFrame()
    if args_rtp == "RTP2021":
        SAFETY_FILE = INTERMEDIATE_METRICS_SOURCE_DIR / 'fatalities_injuries_export.csv'         # from Raleigh, based on Travel Model outputs 
        LOGGER.info("  Reading {}".format(SAFETY_FILE))
        safety_df = pd.read_csv(SAFETY_FILE)
        LOGGER.debug("  safety_df.head(10)\n:{}".format(safety_df.head(10)))
        # columns are index, value, Year, modelrunID

        # strip leading and trailing '/' from modelRunID
        safety_df['modelrunID'] = safety_df.modelrunID.str.strip('/')
        # and leading IncrementalProgress/
        safety_df['modelrunID'] = safety_df.modelrunID.str.replace(r'IncrementalProgress/', '')
        LOGGER.debug("  safety_df.head(10)\n:{}".format(safety_df.head(10)))

        # long to wide
        safety_df = pd.pivot_table(safety_df, values='value', index=['modelrunID','Year'], columns='index').reset_index(drop=False)

        # drop Year and rename modelrunID to modelrun_id
        safety_df.drop(columns=['Year'], inplace=True)
        safety_df.rename(columns={'modelrunID':'modelrun_id'}, inplace=True)
        # add alias
        aliases_dict = {runid:model_runs_dict[runid]['Alias'] for runid in model_runs_dict.keys()}
        # input file seems to be based on previous version
        aliases_dict['2050_TM152_EIR_Alt1_05'] = '2050 EIR Alt1'

        safety_df['modelrun_alias'] = safety_df.modelrun_id.map(aliases_dict)
        LOGGER.debug("  aliases_dict:{}".format(aliases_dict))
        LOGGER.debug("  safety_df.head(10)\n:{}".format(safety_df.head(10)))

    else:
        # TODO
        raise
    
     # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_healthy1_safety.csv'
    safety_df.to_csv(output_file, index=False)
    LOGGER.info(f"Wrote {output_file}")

def extract_Healthy1_safety_TAZ(runid, year, dbp, tm_taz_input_df, tm_vmt_metrics_df, metrics_dict):

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


def calculate_Healthy2_commutemodeshare(model_runs_dict: dict, args_rtp: str):
    """
    This is only implemented for RTP2025 since the RTP2021 TM1.5 version was significantly more complicated.

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'
    """
    LOGGER.info("calculate_Healthy2_commutemodeshare()")
    if args_rtp == 'RTP2021':
        LOGGER.warn("Not implemented for RTP2021 because the methodology changed so QA code is not useful")
        return
    
    # TODO: Implement
    raise


def calculate_Vibrant1_mean_commute(model_runs_dict: dict):
    """
    Extracts mean commute distance from [modelrun_id]/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv
    See https://github.com/BayAreaMetro/travel-model-one/tree/master/model-files/scripts/core_summaries#commutebyincomehousehold

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key

    Writes metrics_vibrant1_mean_commute_distance.csv with columns:
        modelrun_id
        modelrun_alias
        incQ                                one of ['1','2','3','4','all']
        total_commute_miles                 total commute miles (freq x commute miles)
        freq                                number of tours
        mean_commute_dist                   total commute miles divided by freq
    """
    LOGGER.info("calculate_Vibrant1_mean_commute()")

    all_tm_commute_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] == "IP":
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        
        commute_file = model_run_dir / "OUTPUT" / "core_summaries" / "CommuteByIncomeHousehold.csv"
        LOGGER.info(f"  Reading {commute_file}")
        tm_commute_df = pd.read_csv(commute_file)
        LOGGER.debug("  tm_commute_df.head(10):\n{}".format(tm_commute_df))

        tm_commute_df['total_commute_miles'] = tm_commute_df['freq'] * tm_commute_df['distance']
        tm_commute_df = tm_commute_df.groupby(by='incQ').agg({'total_commute_miles':'sum', 'freq':'sum'})

        # add aggregate row: all incomes
        tm_commute_df.loc['all'] = tm_commute_df.sum(axis=0)
        tm_commute_df['mean_commute_dist']   = tm_commute_df['total_commute_miles']/tm_commute_df['freq']

        # add metadata
        # reset index and pull alias from ModelRuns.xlsx info
        tm_commute_df.reset_index(drop=False, inplace=True)
        tm_commute_df['modelrun_id']    = tm_runid
        tm_commute_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']
        LOGGER.debug("  tm_commute_df:\n{}".format(tm_commute_df))

        all_tm_commute_df = pd.concat([all_tm_commute_df, tm_commute_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_vibrant1_mean_commute_distance.csv'
    all_tm_commute_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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
    # file handlers
    fh = logging.FileHandler(METRICS_OUTPUT_DIR / LOG_FILE.format("debug"), mode='w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)
    # file handlers
    fh = logging.FileHandler(METRICS_OUTPUT_DIR / LOG_FILE.format("info"), mode='w')
    fh.setLevel('INFO')
    fh.setFormatter(logging.Formatter('%(message)s'))
    LOGGER.addHandler(fh)

    LOGGER.info("The following log is output by https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/metrics/travel_model_performance_equity_metrics.py")
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
    LOGGER.info('Using Model runs with status==current from {}:\n{}\n\n'.format(MODELRUNS_XLSX, model_runs_df))
    model_runs_dict = model_runs_df.to_dict(orient='index')


    #### Calculate/pull metrics ###################################################################################################
    # Note: These methods iterate through all the relevant runs and output the metrics results

    # Affordable
    affordable_hplust_costs_df = calculate_Affordable1_HplusT_costs(model_runs_dict)
    calculate_Affordable1_trip_costs(model_runs_dict, affordable_hplust_costs_df)

    # Connected
    extract_Connected1_JobAccess(model_runs_dict)
    calculate_Connected2_hwy_traveltimes(model_runs_dict)
    calculate_Connected2_crowding(model_runs_dict)
    calculate_Connected2_transit_asset_condition(model_runs_dict)

    # Healthy
    extract_Healthy1_safety(model_runs_dict, my_args.rtp)

    # Vibrant
    calculate_Vibrant1_mean_commute(model_runs_dict)
    
