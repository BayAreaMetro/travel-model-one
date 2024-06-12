USAGE = """

  python Safe1_run_fatalities_Rscript.py

  Run this from the model run dir.
  runs VZ_safety_calc_correction_v2.R and copies output to L:\\Application\\Model_One\\NextGenFwys_Round2\\Metrics     
  Metrics are:
    1) Safe 1: Fatalities on freeways and local streets in region and EPCs

"""

import os
import pandas as pd
import argparse
import logging
import subprocess 
import shutil
# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
# Path to your R script
R_SCRIPT_PATH = "C:\\Program Files\\R\\R-4.3.3\\bin\\x64\\Rscript.exe"
SAFETY_CALC_SCRIPT = "X:\\travel-model-one-master\\utilities\\RTP\\metrics\\VZ_safety_calc_correction_v2.R"
# No Project Pathway
NO_PROJECT_PATHWAY = "2035_TM160_NGF_r2_NoProject_03_pretollcalib"
# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "Safe1_run_fatalities_Rscript.log" # in the cwd
LOGGER                  = None # will initialize in main     


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
        out_filename = os.path.join(os.getcwd(),"fatalities_injuries_{}.csv".format(tm_run_id))

        if args.skip_if_exists and os.path.exists(out_filename):
            LOGGER.info("Skipping {} -- {} exists".format(tm_run_id, out_filename))
            continue

        LOGGER.info("Processing run {}".format(tm_run_id))

        # Arguments for the R script
        r_script_args = ["NGF", NO_PROJECT_PATHWAY, tm_run_id]

        # Execute the R script
        try:
            subprocess.run([R_SCRIPT_PATH, SAFETY_CALC_SCRIPT] + r_script_args, check=True)
            print("R script executed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error executing R script: {e}")
            
        # copy files to L:\Application\Model_One\NextGenFwys_Round2\Metrics
        file_to_copy = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "metrics", "fatalities_injuries.csv")
        destination_dir = f"L:\\Application\\Model_One\\NextGenFwys_Round2\\Metrics\\fatalities_injuries_{tm_run_id}.csv" 
        # copy files from source to destination
        shutil.copy(file_to_copy,destination_dir)
        LOGGER.info("@@@@@@@@@@@@@ Done")

        # for testing, stop here
        # sys.exit()