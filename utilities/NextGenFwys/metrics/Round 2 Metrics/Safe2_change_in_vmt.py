USAGE = """

  python Safe2_change_in_vmt.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Safe2_change_in_vmt_XX.csv
  
  This file will have the following columns:
    'grouping1',
    'grouping2',
    'grouping3',
    'modelrun_id',
    'metric_id',
    'intermediate/final', 
    'key',
    'metric_desc',
    'year',
    'value'
    
  Metrics are:
    1) Safe 2: Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

"""

import os, sys
import pandas as pd
import simpledbf
import argparse
import logging
import csv


# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios"

# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Safe2_change_in_vmt.log" # in the cwd
LOGGER                  = None # will initialize in main     

# EPC lookup file - indicates whether a TAZ is designated as an EPC in PBA2050
NGFS_EPC_TAZ_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "metrics", "Input Files", "taz_epc_crosswalk.csv")
NGFS_EPC_TAZ_DF      = pd.read_csv(NGFS_EPC_TAZ_FILE)

METRICS_COLUMNS = [
    'grouping1',
    'grouping2',
    'grouping3',
    'modelrun_id',
    'metric_id',
    'intermediate/final', # TODO: suggest renaming this to 'metric_level' since other options are used beyond intermediate and final
    'key',
    'metric_desc',
    'year',
    'value'
]

def calculate_Safe2_change_in_vmt(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Safety 2: Change in vehicle miles travelled (VMT) on freeway and non-freeway facilities
    Additionally, calculates VMT segmented by different categories (households by income, non-houehold and trucks)
    and VMT segmented by whether or not the links are located in Equity Priority Communities (EPC) TAZS.

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns a subset of METRICS_COLUMNS, including
          metric_id          = 'Safe2'
          modelrun_id        = tm_run_id
          intermediate/final = final
        Metrics return:
          grouping1              key                                    metric_desc
          Income Level           inc[1234]                              VMT|VHT  (category breakdown)
          Non-Household          air|ix|zpv_tnc                         VMT|VHT
          Truck                  truck                                  VMT|VHT
          Freeway|Non-Freeway    Freeway|Arterial|Collector|Expressway  VMT|VHT  (facility type breakdown)
          Freeway|Non-Freeway    EPCs|Non-EPCs|Region                   VMT|VHT  (EPC/non-EPC breakdown)

    Notes: Uses
    * auto_times.csv (for category breakdown)
    * avgload5period.csv (for facility type breakdown)
    * vmt_vht_metrics_by_taz.csv (for EPC/non-EPC breakdown)
    """
    METRIC_ID = 'Safe 2'
    metric_id = METRIC_ID
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    # read network-based auto times
    auto_times_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "metrics", "auto_times.csv")
    auto_times_df = pd.read_csv(auto_times_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(auto_times_df), auto_times_file))

    # we'll summarize by these
    auto_times_df['grouping1'] = 'Income Level'
    auto_times_df['key']      = auto_times_df['Income']  # for households, use income
    auto_times_df.loc[ auto_times_df.Mode.str.endswith('ix'),  ['grouping1', 'key']] = ['Non-Household', 'ix'     ]
    auto_times_df.loc[ auto_times_df.Mode.str.endswith('air'), ['grouping1', 'key']] = ['Non-Household', 'air'    ]
    auto_times_df.loc[ auto_times_df.Mode == 'zpv_tnc',        ['grouping1', 'key']] = ['Non-Household', 'zpv_tnc']
    auto_times_df.loc[ auto_times_df.Mode == 'truck',          ['grouping1', 'key']] = ['Truck',         'truck'  ]

    auto_times_df = auto_times_df.groupby(by=['grouping1','key']).agg({'Vehicle Miles':'sum', 'Vehicle Minutes':'sum'}).reset_index()
    auto_times_df['VHT'] = auto_times_df['Vehicle Minutes']/60.0
    auto_times_df.drop(columns=['Vehicle Minutes'], inplace=True)
    auto_times_df.rename(columns={'Vehicle Miles':'VMT'}, inplace=True)
    LOGGER.debug("auto_times_df:\n{}".format(auto_times_df))

    loaded_network_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "avgload5period.csv")
    loaded_network_df = pd.read_csv(loaded_network_file)
    loaded_network_df.rename(columns=lambda x: x.strip(), inplace=True)
    LOGGER.info("  Read {:,} rows from {}".format(len(loaded_network_df), loaded_network_file))
    LOGGER.debug("  Columns:".format(list(loaded_network_df.columns)))
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    # load network_links_TAZ.csv as lookup df to use for equity metric:
    #     --> calculate VMT for arterial road links in EPCs vs region
    #         --> tolled aerterials within EPCs 
    # load network link to TAZ lookup file

    tm_network_links_taz_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links_TAZ.csv")
    tm_network_links_taz_df = pd.read_csv(tm_network_links_taz_file)[['A', 'B', 'TAZ1454', 'linktaz_share']]
    LOGGER.info("  Read {:,} rows from {}".format(len(tm_network_links_taz_df), tm_network_links_taz_file))
    # join to epc lookup table
    tm_network_links_with_epc_df = pd.merge(
        left=tm_network_links_taz_df,
        right=NGFS_EPC_TAZ_DF,
        left_on="TAZ1454",
        right_on="TAZ1454",
        how='left')
    tm_network_links_with_epc_df = tm_network_links_with_epc_df.sort_values('linktaz_share', ascending=False).drop_duplicates(['A', 'B']).sort_index()
    LOGGER.debug("tm_network_links_with_epc_df =\n{}".format(tm_network_links_with_epc_df))
    
    loaded_network_df = pd.merge(left= loaded_network_df, right= tm_network_links_with_epc_df, left_on= ['a','b'], right_on= ['A', 'B'], how='left')
    LOGGER.debug("loaded_network_df =\n{}".format(loaded_network_df))

    # compute Fwy and Non_Fwy VMT
    loaded_network_df['VMT'] = \
        (loaded_network_df['volEA_tot']+
         loaded_network_df['volAM_tot']+
         loaded_network_df['volMD_tot']+
         loaded_network_df['volPM_tot']+
         loaded_network_df['volEV_tot'])*loaded_network_df['distance']
    loaded_network_df['VHT'] = (\
        (loaded_network_df['ctimEA']*loaded_network_df['volEA_tot']) + \
        (loaded_network_df['ctimAM']*loaded_network_df['volAM_tot']) + \
        (loaded_network_df['ctimMD']*loaded_network_df['volMD_tot']) + \
        (loaded_network_df['ctimPM']*loaded_network_df['volPM_tot']) + \
        (loaded_network_df['ctimEV']*loaded_network_df['volEV_tot']))/60.0
    
    # https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    ft_to_grouping_key_df = pd.DataFrame(columns=['ft','grouping1','key'], data=[
        ( 1, 'Freeway',    'Freeway'   ), # freeway-to-freeway connector
        ( 2, 'Freeway',    'Freeway'   ), # freeway
        ( 3, 'Non-Freeway','Expressway'), # expressway
        ( 4, 'Non-Freeway','Collector' ), # collector
        ( 5, 'Freeway',    'Freeway'   ), # freeway ramp
        ( 6, 'Non-Freeway','Other'     ), # dummy link --> include VMT from FT==6 links because they’re a proxy for VMT on roads not included in the model network.
        ( 7, 'Non-Freeway','Arterial'  ), # major arterial
        ( 8, 'Freeway',    'Freeway'   ), # managed freeway
        ( 9, None,          None       ), # special facility
        (10, None,          None       )  # toll plaza
    ])
    # NOTE: this is inconsistent with the vmt_vht_metrics.csv road_type for 'non-freeway' which includes
    # ft [1,2,3,5,8] as 'freeway' and all others as 'non-freeway'
    # https://github.com/BayAreaMetro/travel-model-one/blob/78fb93e881348f794e3423f3a987753a0eef1255/utilities/RTP/metrics/hwynet.py#L334

    LOGGER.debug("  Using facility type categories:\n{}".format(ft_to_grouping_key_df))
    loaded_network_df = pd.merge(left=loaded_network_df, right=ft_to_grouping_key_df, on='ft', how='left')

    # Recode
    loaded_network_df['grouping2'] = 'Non-EPCs'
    loaded_network_df.loc[ loaded_network_df.taz_epc == 1, 'grouping2'] = 'EPCs'

    # identify tolled arterial links 
    loaded_network_df['grouping3'] = 'Non-tolled facilities'
    loaded_network_df.loc[loaded_network_df.tollclass > 700000, 'grouping3'] = 'Tolled facilities'

    # add field for county using TAZ
    # temporarily replacing 'year' column
    # reference: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
    loaded_network_df['year'] = 'San Francisco'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 190) & (loaded_network_df.TAZ1454 < 347), 'year'] = 'San Mateo'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 346) & (loaded_network_df.TAZ1454 < 715), 'year'] = 'Santa Clara'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 714) & (loaded_network_df.TAZ1454 < 1040), 'year'] = 'Alameda'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1039) & (loaded_network_df.TAZ1454 < 1211), 'year'] = 'Contra Costa'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1210) & (loaded_network_df.TAZ1454 < 1291), 'year'] = 'Solano'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1290) & (loaded_network_df.TAZ1454 < 1318), 'year'] = 'Napa'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1317) & (loaded_network_df.TAZ1454 < 1404), 'year'] = 'Sonoma'
    loaded_network_df.loc[(loaded_network_df.TAZ1454 > 1403) & (loaded_network_df.TAZ1454 < 1455), 'year'] = 'Marin'

    ft_metrics_df = loaded_network_df.groupby(by=['grouping1','key', 'grouping2', 'grouping3', 'year']).agg({'VMT':'sum', 'VHT':'sum'}).reset_index()
    LOGGER.debug("ft_metrics_df:\n{}".format(ft_metrics_df))

    # put it together, move to long form and return
    metrics_df = pd.concat([auto_times_df, ft_metrics_df])
    metrics_df = metrics_df.melt(id_vars=['grouping1','key','grouping2', 'grouping3', 'year'], var_name='metric_desc')
    metrics_df['modelrun_id'] = tm_run_id
    metrics_df['metric_id'] = METRIC_ID
    metrics_df['intermediate/final'] = 'final'
    # metrics_df['year'] = tm_run_id[:4]
    LOGGER.debug("metrics_df for Safe 2:\n{}".format(metrics_df))

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

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Safe2_change_in_vmt_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # #temporary run location for testing purposes
        tm_run_location = os.path.join(NGFS_SCENARIOS, tm_run_id)

        # metric dict input: year
        year = tm_run_id[:4]

        # results will be stored here
        # key=grouping1, grouping2, grouping3, tm_run_id, metric_id, top_level|extra|intermediate|final, key, metric_desc, year
        # TODO: convert to pandas.DataFrame with these column headings.  It's far more straightforward.
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Safe2_change_in_vmt(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ S2 Done")


        metrics_df[METRICS_COLUMNS].loc[(metrics_df['modelrun_id'] == tm_run_id)].to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()