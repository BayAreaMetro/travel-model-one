USAGE = """

  python Change_in_vmt_from_auto_times.py

  Run this from the model run dir.
  Processes model outputs and creates a single csv with scenario metrics, called metrics\Change_in_vmt_from_auto_times_XX.csv
  
  This file will have the following columns:
    'Household/Non-Household',
    'Income Level/Travel Mode',
    'value',
    'Model Run ID',
    'Metric ID',
    'Intermediate/Final', 
    'Metric Description',
    'Year'
    
  Metrics are:
    1) Safe 2: Change in vehicle miles travelled on freeway and adjacent non-freeway facilities

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
LOG_FILE                = "Change_in_vmt_from_auto_times.log" # in the cwd
LOGGER                  = None # will initialize in main     

def calculate_Change_in_vmt_from_auto_times(tm_run_id: str) -> pd.DataFrame:
    """ Calculates Safety 2: Change in vehicle miles travelled (VMT) on freeway and non-freeway facilities
    Additionally, calculates VMT segmented by different categories (households by income, non-houehold and trucks)
    and VMT segmented by whether or not the links are located in Equity Priority Communities (EPC) TAZS.

    Args:
        tm_run_id (str): Travel model run ID
    
    Returns:
        pd.DataFrame: with columns including
          Metric ID          = 'Safe2'
          Model Run ID        = tm_run_id
          Intermediate/Final = final
        Metrics return:
          Freeway/Non-Freeway              Facility Type Definition                                    Metric Description
          Household/Non-Household           inc[1234]                              VMT|VHT  (category breakdown)
          Non-Household          air|ix|zpv_tnc                         VMT|VHT
          Truck                  truck                                  VMT|VHT
          Freeway|Non-Freeway    Freeway|Arterial|Collector|Expressway  VMT|VHT  (facility type breakdown)
          Freeway|Non-Freeway    EPCs|Non-EPCs|Region                   VMT|VHT  (EPC/non-EPC breakdown)

    Notes: Uses
    * auto_times.csv (for category breakdown)
    """
    METRIC_ID = 'Safe 2'
    LOGGER.info("Calculating {} for {}".format(METRIC_ID, tm_run_id))

    # read network-based auto times
    auto_times_file = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "metrics", "auto_times.csv")
    # line below for round 2 runs
    # auto_times_file = os.path.join(NGFS_ROUND2_SCENARIOS, tm_run_id, "OUTPUT", "metrics", "auto_times.csv")
    auto_times_df = pd.read_csv(auto_times_file)
    LOGGER.info("  Read {:,} rows from {}".format(len(auto_times_df), auto_times_file))

    # we'll summarize by these
    auto_times_df['Household/Non-Household'] = 'Household'
    auto_times_df['Income Level/Travel Mode']      = auto_times_df['Income']  # for households, use income
    auto_times_df.loc[ auto_times_df.Mode.str.endswith('ix'),  ['Household/Non-Household', 'Income Level/Travel Mode']] = ['Non-Household', 'ix'     ]
    auto_times_df.loc[ auto_times_df.Mode.str.endswith('air'), ['Household/Non-Household', 'Income Level/Travel Mode']] = ['Non-Household', 'air'    ]
    auto_times_df.loc[ auto_times_df.Mode == 'zpv_tnc',        ['Household/Non-Household', 'Income Level/Travel Mode']] = ['Non-Household', 'zpv_tnc']
    auto_times_df.loc[ auto_times_df.Mode == 'truck',          ['Household/Non-Household', 'Income Level/Travel Mode']] = ['Truck',         'truck'  ]

    auto_times_df = auto_times_df.groupby(by=['Household/Non-Household','Income Level/Travel Mode']).agg({'Vehicle Miles':'sum', 'Vehicle Minutes':'sum'}).reset_index()
    auto_times_df['VHT'] = auto_times_df['Vehicle Minutes']/60.0
    auto_times_df.drop(columns=['Vehicle Minutes'], inplace=True)
    auto_times_df.rename(columns={'Vehicle Miles':'VMT'}, inplace=True)
    LOGGER.debug("auto_times_df:\n{}".format(auto_times_df))

    metrics_df = auto_times_df
    metrics_df = metrics_df.melt(id_vars=['Household/Non-Household', 'Income Level/Travel Mode'], var_name='Metric Description')
    metrics_df['Model Run ID'] = tm_run_id
    metrics_df['Metric ID'] = METRIC_ID
    metrics_df['Intermediate/Final'] = 'final'
    metrics_df['Year'] = tm_run_id[:4]
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
    
    # line below for round 2 runs
    # current_runs_list = ['2035_TM160_NGF_r2_NoProject_01', '2035_TM160_NGF_r2_NoProject_01_AOCx1.25_v2', '2035_TM160_NGF_r2_NoProject_03_pretollcalib']

    for tm_run_id in current_runs_list:
        out_filename = os.path.join(os.getcwd(),"Change_in_vmt_from_auto_times_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # results will be stored here
        metrics_df = pd.DataFrame()

        metrics_df = calculate_Change_in_vmt_from_auto_times(tm_run_id)
        LOGGER.info("@@@@@@@@@@@@@ S2 Done")

        metrics_df.to_csv(out_filename, float_format='%.5f', index=False) #, header=False
        LOGGER.info("Wrote {}".format(out_filename))

        # for testing, stop here
        # sys.exit()