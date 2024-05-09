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

def calculate_Affordable1_HplusT_costs(model_runs_dict: dict, args_rtp: str, 
                                       BOX_METRICS_OUTPUT_DIR: pathlib.Path) -> pd.DataFrame:
    """Pulls transportation costs from other files and converts to annual
    to calculate them as a percentage of household income; these calculations
    are segmented by income quartiles.

    Reads the following files:
    1. BOX_METRICS_OUTPUT_DIR/metrics_affordable1_housing_cost_share_of_income.csv which has columns:
       modelrun_id,modelrun_alias,year,quartile,tenure,households,share_income
       This was produced by: https://github.com/BayAreaMetro/bayarea_urbansim/blob/metrics_update/scripts/metrics/metrics_affordable.py

    2. [model_run_dir]/OUTPUT/metrics/scenario_metrics.csv for income-segmented
       total_households, total_hh_inc,
       total_auto_cost (daily), total_auto_trips (daily),
       total_transit_fares (daily), total_transit_trips (daily)

    3. [model_run_dir]/OUTPUT/metrics/parking_costs_tour.csv for income-segmented
       parking_costs (daily)

    4. [model_run_dir]/OUTPUT/metrics/autos_owned.csv for income-segmented auto ownership

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'

    Writes metrics_affordable1_HplusT_costs.csv with columns:
        modelrun_id
        modelrun_alias
        BAUS_modelrun_id                    BAUS modelrun_id (source for housing_cost_share_of_hh_income)
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
        total_auto_op_cost_annual           total_auto_cost, annualized (per-mile cost plus bridge, value and cordon tolls)
        total_transit_fares_annual          total_transit_fares, annualized
        total_parking_cost_annual           parking_cost, annualized
        total_tansp_cost_annual             annual transportation costs: auto op cost, auto ownership cost, parking cost, transit fares
        transp_cost_share_of_hh_income      total_tansp_cost_annual / total_hh_inc_with_UBI
        housing_cost_share_of_hh_income     housing cost as a share of household income, from housing_costs_share_income.csv
        H+T_cost_share_of_hh_income         sum of housing + transportation costs as a share of household income

    Also writes metrics_affordable1_HplusT_costs_detail.csv with columns:
        modelrun_alias
        modelrun_id
        BAUS_modelrun_id                    BAUS modelrun_id (source for housing_cost_share_of_hh_income)
        incQ                                one of ['1','all']
        cost_type                           one of ['housing_cost','transit_fare','auto_op_cost','auto_own_cost','parking_cost']
        share_of_hh_income                  percentage of household income

    Returns DataFrame written
    """
    LOGGER.info("calculate_Affordable1_HplusT_costs()")

    # BOX_METRICS_OUTPUT_DIR/metrics_affordable1_housing_cost_share_of_income.csv which has columns:
    #   modelrun_id,modelrun_alias,year,quartile,tenure,households,share_income
    #   This was produced by: https://github.com/BayAreaMetro/bayarea_urbansim/blob/metrics_update/scripts/metrics/metrics_affordable.py

    # Read Housing costs input
    HOUSING_COSTS_FILE = BOX_METRICS_OUTPUT_DIR / 'metrics_affordable1_housing_cost_share_of_income.csv'
    LOGGER.info(f"  Reading {HOUSING_COSTS_FILE}")
    housing_costs_df = pd.read_csv(HOUSING_COSTS_FILE)
    LOGGER.debug("  housing_costs_df.head() (len={}):\n{}".format(
        len(housing_costs_df), housing_costs_df.head()))
    LOGGER.debug(f"{housing_costs_df.modelrun_alias.unique().tolist()}")
    
    # select only columns we need
    housing_costs_df = housing_costs_df.loc[ 
        ((housing_costs_df.quartile=='Quartile1'  )&(housing_costs_df.tenure=='all_tenures')) | # low income
        ((housing_costs_df.quartile=='all_incomes')&(housing_costs_df.tenure=='all_tenures')) ] # all incomes
    housing_costs_df.drop(columns=['tenure','year','households'],inplace=True)

    # RTP2021 travel model aliases: 2015, 2050 No Project, 2050 Plan, 2050 EIR Alt1, 2050 EIR Alt2
    #                 BAUS aliases: 2015 No Project, 2050 No Project, 2050 FBP, 2050 EIR Alt1, 2050 EIR Alt2
    # RTP2025 travel model aliases: 2023, 2050 No Project, 2050 Plan
    #                 BAUS aliases: 2023 No Project, 2050 No Project, 2050 DBP
    # convert BAUS modelrun_alias to match travel model
    housing_costs_df.replace(to_replace={
        '2015 No Project':'2015',
        '2023 No Project':'2023',
        '2050 FBP'       :'2050 Plan',
        '2050 DBP'       :'2050 Plan',
        '2050 EIR Alt 1' :'2050 EIR Alt1',
        '2050 EIR Alt 2' :'2050 EIR Alt2',
    }, inplace=True)
    # RTP2025 Draft Blueprint - 2050 Trend instead of 2050 No Project
    if args_rtp=="RTP2025":
        housing_costs_df.replace(to_replace={'2050 No Project':'2050 Trend'}, inplace=True)

    # rename quartile and recode to match
    housing_costs_df.rename(columns={
        'quartile'    :'incQ',
        'modelrun_id' :'BAUS_modelrun_id',
        'share_income':'housing_cost_share_of_hh_income',
    }, inplace=True)
    housing_costs_df.replace(to_replace={
        'Quartile1':'1',
        'Quartile2':'2',
        'Quartile3':'3',
        'Quartile4':'4',
        'all_incomes':'all'
    }, inplace=True)
    LOGGER.debug(f"  housing_costs_df:\n{housing_costs_df}")

    affordable_hplust_costs_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        model_run_category = model_runs_dict[tm_runid]['category']
        LOGGER.info(f"  Processing {tm_runid} with category {model_run_category}")

        # read scenario metrics
        scenario_metrics_file = model_run_dir / "OUTPUT" / "metrics" / "scenario_metrics.csv"
        if not os.path.exists(scenario_metrics_file): continue  # not ready yet
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
        LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))

        # h+t = h + t
        tm_scen_metrics_df['H+T_cost_share_of_hh_income'] = tm_scen_metrics_df.housing_cost_share_of_hh_income + tm_scen_metrics_df.transp_cost_share_of_hh_income

        LOGGER.debug("  tm_scen_metrics_df:\n{}".format(tm_scen_metrics_df))
        affordable_hplust_costs_df = pd.concat([affordable_hplust_costs_df, tm_scen_metrics_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_affordable1_HplusT_costs.csv'
    affordable_hplust_costs_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

    # additional output for investigation
    LOGGER.debug(f"affordable_hplust_costs_df:\n{affordable_hplust_costs_df}")
    # only q1 and all incomes
    cost_detail_df = affordable_hplust_costs_df.loc[ affordable_hplust_costs_df.incQ.isin(['1','all'])].copy()
    # only cost and incomes
    cost_detail_df = cost_detail_df[['modelrun_alias','modelrun_id','BAUS_modelrun_id','incQ',
                         'total_hh_inc_with_UBI',
                         'total_transit_fares',
                         'total_auto_op_cost_annual','total_auto_ownership_cost_annual','total_parking_cost_annual',
                         'housing_cost_share_of_hh_income']]
    # make them all fractions
    cost_detail_df['transit_fare_share_of_hh_income' ] = cost_detail_df.total_transit_fares              / cost_detail_df.total_hh_inc_with_UBI
    cost_detail_df['auto_op_cost_share_of_hh_income' ] = cost_detail_df.total_auto_op_cost_annual        / cost_detail_df.total_hh_inc_with_UBI
    cost_detail_df['auto_own_cost_share_of_hh_income'] = cost_detail_df.total_auto_ownership_cost_annual / cost_detail_df.total_hh_inc_with_UBI
    cost_detail_df['parking_cost_share_of_hh_income' ] = cost_detail_df.total_parking_cost_annual        / cost_detail_df.total_hh_inc_with_UBI
    # drop other columns, cost type to column
    cost_detail_df.drop(columns=['total_hh_inc_with_UBI','total_transit_fares',
                         'total_auto_op_cost_annual','total_auto_ownership_cost_annual','total_parking_cost_annual'], inplace=True)
    cost_detail_df = pd.melt(
        cost_detail_df, 
        id_vars=['modelrun_alias','modelrun_id','BAUS_modelrun_id','incQ'],
        var_name='cost_type',
        value_name='share_of_hh_income'
    )
    cost_detail_df['cost_type'] = cost_detail_df.cost_type.str.replace('_share_of_hh_income','')
    
    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_affordable1_HplusT_costs_detail.csv'
    cost_detail_df.to_csv(output_file, index=False)
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
        total_auto_cost                     daily auto operating cost, from scenario_metrics.csv (AOC-based, plus bridge, value and cordong tolls)
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
    LOGGER.info("calculate_Affordable1_trip_costs()")

    affordable_trip_costs_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        model_run_category = model_runs_dict[tm_runid]['category']
        LOGGER.info(f"  Processing {tm_runid} with category {model_run_category}")

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
        if not os.path.exists(auto_times_file): continue  # not ready yet
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
        AUTO_TIMES_COLUMNS = list(tm_auto_times_df.columns.values)
        LOGGER.debug("  AUTO_TIMES_COLUMNS:{}".format(AUTO_TIMES_COLUMNS))
        if 'Value Tolls with discount' in AUTO_TIMES_COLUMNS and 'Cordon tolls with discount' in AUTO_TIMES_COLUMNS:
            tm_auto_times_df['Value Tolls'] = tm_auto_times_df['Value Tolls with discount'] + tm_auto_times_df['Cordon tolls with discount']

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
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
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
        if not os.path.exists(scenario_metrics_file): continue  # not ready yet
        LOGGER.info("    Reading {}".format(scenario_metrics_file))
        scenario_metrics_df = pd.read_csv(scenario_metrics_file, header=None, names=['modelrun_id', 'metric_name','value'])

        # filter to only jobacc2_* metrics and then strip that off
        scenario_metrics_df = scenario_metrics_df.loc[ scenario_metrics_df.metric_name.str.startswith('jobacc2_')]
        scenario_metrics_df['metric_name'] = scenario_metrics_df.metric_name.str[8:]

        # filter to only acc_accessible_job_share[_coc,_hra]
        scenario_metrics_df = scenario_metrics_df.loc[ 
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share') |
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share_coc') |
            scenario_metrics_df.metric_name.str.endswith('accessible_job_share_epc') |
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
    trn_mode_operator_df = pd.read_csv(TRN_MODE_OPERATOR_LOOKUP_FILE, usecols=['mode','operator'])
    trn_mode_operator_df = trn_mode_operator_df.drop_duplicates(ignore_index=True)
    LOGGER.debug("trn_mode_operator_df:\n{}".format(trn_mode_operator_df))

    all_trn_crowding_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
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
        tm_crowding_df = pd.merge(
            left     = tm_crowding_df, 
            right    = trn_mode_operator_df, 
            left_on  = 'MODE',
            right_on = 'mode',
            how      = "left",
            validate = 'many_to_one')

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
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        LOGGER.info(f"  Processing {tm_runid}")

        # read the loaded roadway network
        network_file = model_run_dir / "OUTPUT" / "avgload5period.csv"
        if not os.path.exists(network_file): continue  # not ready yet
        LOGGER.info(f"    Reading {network_file}")
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


def extract_Connected2_transit_asset_condition(model_runs_dict: dict):
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
    LOGGER.info("extract_Connected2_transit_asset_condition()")
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

    These metrics are calculated by VZ_saftey_calc_correction_v2.R, so
      this simply reads results in [modelrun_id]\\OUTPUT\\metrics\\fatalies_injuries.csv

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'

    Writes metrics_healthy1_safety.csv with columns:
        modelrun_id
        modelrun_alias
      # these are from VZ_safety_calc_correction_V2.R
        N_injuries
        N_injuries_per_100K_pop
        N_injuries_per_100M_VMT
        N_total_fatalities
        N_total_fatalities_per_100K_pop
        N_total_fatalities_per_100M_VMT
        Population (for RTP2021 only)
        annual_VMT (for RTP2021 only)
    """
    LOGGER.info("extract_Healthy1_safety()")

    safety_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        
        fatalities_injuries_file = model_run_dir / "OUTPUT" / "metrics" / "fatalities_injuries.csv"
        LOGGER.info(f"  Reading {fatalities_injuries_file}")
        tm_safety_df = pd.read_csv(fatalities_injuries_file)
        LOGGER.debug("  tm_safety_df.head(10):\n{}".format(tm_safety_df))

        # select only key=all, model_run_id = this one
        tm_safety_df = tm_safety_df.loc[ (tm_safety_df.key=='all') & (tm_safety_df.model_run_id == tm_runid)]
        # rename columns
        tm_safety_df.rename(columns={
            'model_run_id':'modelrun_id',
            'N_serious_injuries':'N_injuries',
            'N_serious_injuries_per_100K_pop':'N_injuries_per_100K_pop',
            'N_serious_injuries_per_100M_VMT':'N_injuries_per_100M_VMT',
            'N_fatalities_total':'N_total_fatalities',
            'N_fatalities_per_100K_pop_total':'N_total_fatalities_per_100K_pop',
            'N_fatalities_per_100M_VMT_total':'N_total_fatalities_per_100M_VMT',
        }, inplace=True)
        tm_safety_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']

        # compile with others
        safety_df = pd.concat([safety_df, tm_safety_df])

    safety_df = safety_df[[
        'modelrun_id',
        'modelrun_alias',
        'N_injuries',
        'N_injuries_per_100K_pop',
        'N_injuries_per_100M_VMT',
        'N_total_fatalities',
        'N_total_fatalities_per_100K_pop',
        'N_total_fatalities_per_100M_VMT',
    ]]
    LOGGER.debug("safety_df:\n{}".format(safety_df))
    
    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_healthy1_safety.csv'
    safety_df.to_csv(output_file, index=False)
    LOGGER.info(f"Wrote {output_file}")

def extract_Healthy1_PM25(model_runs_dict: dict, args_rtp: str):
    """
    Extracts PM2.5 from the EMFAC output.

    Per Harold in Update emission / pollution metrics (PM2.5)
    https://app.asana.com/0/0/1206701395344040/f
    this comes from EIR\E2017\E2017web_[modelrun_id]_winter_planning_[timestamp].xlsx

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'

    Writes metrics_healthy1_PM25.csv with columns:
        modelrun_id
        modelrun_alias
        area = 'Regionwide'
        PM2_5_TOTAL
    """
    LOGGER.info("extract_Healthy1_PM25()")

    pm25_results = [] # dict records
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid

            # this comes from EIR\E2017\E2017_[modelrun_id]_winter_planning_[timestamp].xlsx
        emfac2017_dir = model_run_dir / "OUTPUT/emfac/EIR/E2017"
        emfac2017_winter_planning_files = sorted(emfac2017_dir.glob(f"E2017web_{tm_runid}_winter_planning_*.xlsx"))
        if len(emfac2017_winter_planning_files) != 1:
            LOGGER.info(f"  {tm_runid} Found 0 or 2+ emfac2017_winter_planning_files: {emfac2017_winter_planning_files}")
            LOGGER.info("    Skipping...")
            continue
        LOGGER.info(f"  Reading {tm_runid} emfac2017_winter_planning_file:")
        LOGGER.info(f"    {emfac2017_winter_planning_files[0]}")
        emfac2017_winter_df = pd.read_excel(emfac2017_winter_planning_files[0], sheet_name="Total MTC")
        # remove leading or trailing spaces
        emfac2017_winter_df.Veh_Tech = emfac2017_winter_df.Veh_Tech.str.strip()
        LOGGER.debug("  emfac2017_winter_df.head():\n{}".format(emfac2017_winter_df.head()))

        # select row with All Vehicles
        emfac2017_winter_df = emfac2017_winter_df.loc[ emfac2017_winter_df.Veh_Tech == 'All Vehicles', :]
        assert(len(emfac2017_winter_df)==1)
        all_veh_series = emfac2017_winter_df.squeeze()
        LOGGER.debug(f"  all_veh_series:\n{all_veh_series}")

        # verify other values
        assert(all_veh_series.Area == 'MTC')
        assert(all_veh_series.Season == 'Winter')
        assert(all_veh_series['Cal. Year'] == model_runs_dict[tm_runid]['year'])
        LOGGER.debug(f"  all_veh_series['PM2_5_TOTAL']:\n{all_veh_series['PM2_5_TOTAL']}")

        pm25_results.append({
            'modelrun_id'   : tm_runid,
            'modelrun_alias': model_runs_dict[tm_runid]['Alias'],
            'area'          : 'Regionwide',
            'PM2_5_TOTAL'   : all_veh_series['PM2_5_TOTAL']
        })
    pm25_results_df = pd.DataFrame(pm25_results)
    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_healthy1_PM25.csv'
    pm25_results_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

def extract_Healthy2_CO2_Emissions(model_runs_dict: dict, args_rtp: str):
    """
    Extracts CO2_TOTEX from the EMFAC output.

    Per Harold in Update emission / pollution metrics (PM2.5)
    https://app.asana.com/0/0/1206701395344040/f
    this comes from EIR\E2017\E2017web_[modelrun_id]_annnual_planning_[timestamp].xlsx

    Args:
        model_runs_dict (dict): contents of ModelRuns.xlsx with modelrun_id key
        args_rtp (str): one of 'RTP2021' or 'RTP2025'

    Writes metrics_healthy2_CO2_emissions.csv with columns:
        modelrun_id
        modelrun_alias
        veh_type = 'All Vehicles'
        SB375 = False
        TOTPOP
        CO2_TOTEX
        CO2_TOTEX_per_capita
    """
    LOGGER.info("extract_Healthy2_CO2_Emissions()")

    co2_results = [] # dict records
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid

        # read tazdata for total population
        tazdata_file = model_run_dir / "INPUT" / "landuse" / "tazData.csv"
        LOGGER.info("    Reading {}".format(tazdata_file))
        tazdata_df = pd.read_csv(tazdata_file)
        TOTPOP = tazdata_df['TOTPOP'].sum()
        LOGGER.debug("  TOTPOP: {:,}".format(TOTPOP))

        # this comes from EIR\E2017\E2017_[modelrun_id]_annual_planning_[timestamp].xlsx
        emfac2017_dir = model_run_dir / "OUTPUT/emfac/EIR/E2017"
        emfac2017_annual_planning_files = sorted(emfac2017_dir.glob(f"E2017web_{tm_runid}_annual_planning_*.xlsx"))
        if len(emfac2017_annual_planning_files) != 1:
            LOGGER.info(f"  {tm_runid} Found 0 or 2+ emfac2017_annual_planning_files: {emfac2017_annual_planning_files}")
            LOGGER.info("    Skipping...")
            continue
        LOGGER.info(f"  Reading {tm_runid} emfac2017_annual_planning_file:")
        LOGGER.info(f"    {emfac2017_annual_planning_files[0]}")
        emfac2017_annual_df = pd.read_excel(emfac2017_annual_planning_files[0], sheet_name="Total MTC")
        # remove leading or trailing spaces
        emfac2017_annual_df.Veh_Tech = emfac2017_annual_df.Veh_Tech.str.strip()
        LOGGER.debug("  emfac2017_annual_df.head():\n{}".format(emfac2017_annual_df.head()))

        # select row with All Vehicles
        emfac2017_annual_df = emfac2017_annual_df.loc[ emfac2017_annual_df.Veh_Tech == 'All Vehicles', :]
        assert(len(emfac2017_annual_df)==1)
        all_veh_series = emfac2017_annual_df.squeeze()
        LOGGER.debug(f"  all_veh_series:\n{all_veh_series}")

        # verify other values
        assert(all_veh_series.Area == 'MTC')
        assert(all_veh_series.Season == 'Annual')
        assert(all_veh_series['Cal. Year'] == model_runs_dict[tm_runid]['year'])
        LOGGER.debug(f"  all_veh_series['CO2_TOTEX']:\n{all_veh_series['CO2_TOTEX']}")

        co2_results.append({
            'modelrun_id'   : tm_runid,
            'modelrun_alias': model_runs_dict[tm_runid]['Alias'],
            'veh_type'      : 'All Vehicles',
            'SB375'         : False,
            'TOTPOP'        : TOTPOP,
            'CO2_TOTEX'     : all_veh_series['CO2_TOTEX'],
            'CO2_TOTEX_per_capita': all_veh_series['CO2_TOTEX']/TOTPOP
        })
    co2_results_df = pd.DataFrame(co2_results)
    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_healthy2_CO2_emissions.csv'
    co2_results_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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
    
    all_jtw_modes_df = pd.DataFrame()
    for tm_runid in model_runs_dict.keys():
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
            model_run_dir = TM_RUN_LOCATION_IP / tm_runid
        else:
            model_run_dir = TM_RUN_LOCATION_BP / tm_runid
        
        jtw_modes_file = model_run_dir / "OUTPUT" / "core_summaries" / "JourneyToWork_modes.csv"
        LOGGER.info(f"  Reading {jtw_modes_file}")
        jtw_modes_df = pd.read_csv(jtw_modes_file)
        LOGGER.debug("  jtw_modes_df.head(10):\n{}".format(jtw_modes_df.head(10)))

        # groupby ptype_label, wfh_choice, tour_mode
        jtw_modes_df =  jtw_modes_df.groupby(by=['ptype_label','wfh_choice','tour_mode']).agg({'freq':'sum'}).reset_index()
        # LOGGER.debug("  jtw_modes_df:\n{}".format(jtw_modes_df))

        # keep rows with workers either making a work tour or telecommuting; drop people not working this day
        jtw_modes_df = jtw_modes_df.loc[ (jtw_modes_df.wfh_choice == 1) | (jtw_modes_df.tour_mode > 0)]
        # https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes
        # categorize to Auto: Single Occupancy, Auto: Other, Transit, Active Modes (Bike/Walk), Telecommute
        mode_mapping = {
            0:  "telecommute",  # these are telecommuters
            1:  "auto_SOV",
            2:  "auto_SOV",
            3:  "auto_other",
            4:  "auto_other",
            5:  "auto_other",
            6:  "auto_other",
            7:  "walk_bike",
            8:  "walk_bike",
            9:  "transit",
            10: "transit",
            11: "transit",
            12: "transit",
            13: "transit",
            14: "transit",
            15: "transit",
            16: "transit",
            17: "transit",
            18: "transit",
            19: "auto_other", # taxi
            20: "auto_other", # tnc single
            21: "auto_other", # tnc shared
        }
        jtw_modes_df = jtw_modes_df.assign(tour_mode_simple = jtw_modes_df.tour_mode.map(mode_mapping))
        # LOGGER.debug("  jtw_modes_df.head(10):\n{}".format(jtw_modes_df))

        # summarize it further to tour_mode_simple
        jtw_modes_df =  jtw_modes_df.groupby(by=['ptype_label','tour_mode_simple']).agg({'freq':'sum'}).reset_index()

        # this is sufficient; shares and ptype filtering can be done in Tableau. Ship it squirrel
        jtw_modes_df['modelrun_id'] = tm_runid
        jtw_modes_df['modelrun_alias'] = model_runs_dict[tm_runid]['Alias']
        LOGGER.debug("  jtw_modes_df:\n{}".format(jtw_modes_df))

        all_jtw_modes_df = pd.concat([all_jtw_modes_df, jtw_modes_df])

    # write it
    output_file = METRICS_OUTPUT_DIR / 'metrics_healthy2_commute_mode_share.csv'
    all_jtw_modes_df.to_csv(output_file, index=False)
    LOGGER.info("Wrote {}".format(output_file))

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
        if model_runs_dict[tm_runid]['run_set'] in ["IP","RTP2025_IP"]:
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
    parser.add_argument('--only', required=False, choices=['affordable','connected','diverse','growth','healthy','vibrant'], 
                        help='To only run one metric set')
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
        BOX_METRICS_OUTPUT_DIR           = BOX_DIR / "Plan Bay Area 2050+" / "Performance and Equity" / "Plan Performance" / "Equity_Performance_Metrics" / "PBA50_reproduce_for_QA"
        METRICS_OUTPUT_DIR               = BOX_METRICS_OUTPUT_DIR
    else:
        METRICS_BOX_DIR                  = BOX_DIR / "Plan Bay Area 2050+" / "Performance and Equity" / "Plan Performance" / "Equity_Performance_Metrics" / "Draft_Blueprint"
        METRICS_SOURCE_DIR               = METRICS_BOX_DIR / "metrics_input_files"
        INTERMEDIATE_METRICS_SOURCE_DIR  = METRICS_BOX_DIR # These aren't really "intermediate"
        BOX_METRICS_OUTPUT_DIR           = METRICS_BOX_DIR
        METRICS_OUTPUT_DIR               = BOX_METRICS_OUTPUT_DIR

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
    # we only care about these columns
    MODELRUNS_COLUMNS = ['directory','year','run_set','category','status','Alias']
    if my_args.rtp == 'RTP2025': MODELRUNS_COLUMNS = MODELRUNS_COLUMNS + ['description']
    model_runs_df = model_runs_df[MODELRUNS_COLUMNS]
    # select current runs with Alias
    model_runs_df = model_runs_df.loc[ model_runs_df.status == 'current' ]
    model_runs_df = model_runs_df.loc[ pd.notna(model_runs_df.Alias) ]

    if my_args.rtp == 'RTP2021':
        # for RTP2021, select base year (pre 2025) and horizon year (2050)
        model_runs_df = model_runs_df.loc[ (model_runs_df.year < 2025) | (model_runs_df.year == 2050) ]
    else:
        pass

    # select out UrbanSim run since it's a dummy and not really a travel model run
    model_runs_df = model_runs_df.loc[ model_runs_df.directory.str.find('UrbanSim') == -1 ]
    model_runs_df.set_index(keys='directory', inplace=True)
    LOGGER.info('Using Model runs with status==current from {}:\n{}\n\n'.format(MODELRUNS_XLSX, model_runs_df))
    model_runs_dict = model_runs_df.to_dict(orient='index')


    #### Calculate/pull metrics ###################################################################################################
    # Note: These methods iterate through all the relevant runs and output the metrics results

    # Affordable
    if (my_args.only == None) or (my_args.only == 'affordable'):
        affordable_hplust_costs_df = calculate_Affordable1_HplusT_costs(model_runs_dict, my_args.rtp, BOX_METRICS_OUTPUT_DIR)
        calculate_Affordable1_trip_costs(model_runs_dict, affordable_hplust_costs_df)

    # Connected
    if (my_args.only == None) or (my_args.only == 'connected'):
        extract_Connected1_JobAccess(model_runs_dict)
        calculate_Connected2_hwy_traveltimes(model_runs_dict)
        calculate_Connected2_crowding(model_runs_dict)
        # don't bother for RTP2025; this script doesn't add anything
        if my_args.rtp == "RTP2021":
            extract_Connected2_transit_asset_condition(model_runs_dict)

    # Healthy
    if (my_args.only == None) or (my_args.only == 'healthy'):
        extract_Healthy1_safety(model_runs_dict, my_args.rtp)
        extract_Healthy1_PM25(model_runs_dict, my_args.rtp)
        extract_Healthy2_CO2_Emissions(model_runs_dict, my_args.rtp)
        calculate_Healthy2_commutemodeshare(model_runs_dict, my_args.rtp)

    # Vibrant
    if (my_args.only == None) or (my_args.only == 'vibrant'):
        calculate_Vibrant1_mean_commute(model_runs_dict)
    
