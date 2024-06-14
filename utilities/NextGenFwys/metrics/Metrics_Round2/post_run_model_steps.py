USAGE = """

  python post_run_model_steps.py
  see asana task for reference: https://app.asana.com/0/1201809392759895/1204121195919332/f
  
  Run this from the model run dir.

  accomplishes the following tasks:
    Shapefiles output
        Runs the run_CubeToShapefile.bat batch file to generate the shapefiles outputs from each completed model run directory's OUTPUT\\shapefile directory. 
        The batch file needs to be run from a machine with ArcGIS Pro, NetworkWrangler and geopandas installed. satmodel is recommended
    metrics\\vmt_vht_metrics_by_taz.csv
        Steps:
            Shapefiles output from above are required
            Correspond links to taz by running (in the shapefile directory):  python X:\\travel-model-one-master\\utilities\\cube-to-shapefile\\correspond_link_to_TAZ.py network_links.shp network_links_TAZ.csv
            Rerun hwynet.py in the model run directory on the modeling machine: python X:\\travel-model-one-master\\utilities\\RTP\\metrics\\hwynet.py --filter PBA50 --year 2035 --link_mapping L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\[Scenario]\\OUTPUT\\shapefile\\network_links_TAZ.csv TAZ1454 linktaz_share _by_taz .\\hwy\\iter3\\avgload5period_vehclasses.csv
            Copy resulting vmt_vht_metrics_by_taz.csv to L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\[Scenario]\OUTPUT\metrics
            run copyFilesAcrossScenarios.py again to copy the files to the across_runs_union directory (see detailed steps under Step 1 of "across_NGFS_runs_union tableau")        

"""

import os
import pandas as pd
import logging
import subprocess 
import shutil

# paths
TM1_GIT_DIR             = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
NGFS_MODEL_RUNS_FILE    = os.path.join(TM1_GIT_DIR, "utilities", "NextGenFwys", "ModelRuns_Round2.xlsx")
NGFS_SCENARIOS          = "L:\\Application\\Model_One\\NextGenFwys_Round2\\Scenarios"
CORRESPOND_LINK_TO_TAZ_SCRIPT = "X:\\travel-model-one-master\\utilities\\cube-to-shapefile\\correspond_link_to_TAZ.py"
# These calculations are complex enough that a debug log file would be helpful to track what's happening
LOG_FILE                = "post_run_model_steps.log" # in the cwd
LOGGER                  = None # will initialize in main     

# Save the current working directory
ORIGINAL_DIRECTORY = os.getcwd()

if __name__ == "__main__":
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
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    current_runs_df = pd.read_excel(NGFS_MODEL_RUNS_FILE, sheet_name='all_runs', usecols=['project','year','directory','run_set','category','short_name','status'])
    current_runs_df = current_runs_df.loc[current_runs_df['status'] == 'current']
    # only process metrics for 2035 model runs 
    current_runs_df = current_runs_df.loc[current_runs_df['year'] == 2035]
    # # TODO: delete later after NP10 runs are completed
    # current_runs_df = current_runs_df.loc[ (current_runs_df['directory'].str.contains('NP10') == False)]

    current_runs_list = current_runs_df['directory'].to_list()

    for tm_run_id in current_runs_list:
        LOGGER.info("Processing run {}".format(tm_run_id))
        
        # Change the directory to the desired location
        new_directory = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile")
        os.chdir(new_directory)
        
        # define directory for file and script of interest
        network_links_directory = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links.shp")
        CubeToShapefile_batch_script = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "run_CubeToShapefile.bat")
        
        # Check if the network_links.shp file exists
        if not os.path.exists(network_links_directory):
            print(network_links_directory + " does not exist, running run_CubeToShapefile.bat")
            # Run the batch script
            try:
                print("run_CubeToShapefile.bat started.")
                subprocess.run([CubeToShapefile_batch_script], shell=True)
                print("run_CubeToShapefile.bat executed successfully!")
                # programatically "press enter" to continue with other subprocesses
                os.system("\n")
            except subprocess.CalledProcessError as e:
                print(f"Error executing run_CubeToShapefile.bat: {e}")
            
        else:
            print(network_links_directory + " exists.")
            
        # define directory for file
        network_links_TAZ_directory = os.path.join(NGFS_SCENARIOS, tm_run_id, "OUTPUT", "shapefile", "network_links_TAZ.csv")
            
        # Check if the network_links_TAZ.csv file exists
        if not os.path.exists(network_links_TAZ_directory):
            print(network_links_TAZ_directory + " does not exist, running correspond_link_to_TAZ.py")
            # Run the batch script
            try:
                print("correspond_link_to_TAZ.py started.")
                # Define the command to run your Python script with arguments
                command = ["python", CORRESPOND_LINK_TO_TAZ_SCRIPT, "network_links.shp", "network_links_TAZ.csv"]
                # Run the command
                subprocess.run(command)
                print("correspond_link_to_TAZ.py executed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"Error executing correspond_link_to_TAZ.py: {e}")
            
        else:
            print(network_links_TAZ_directory + " exists.")

        LOGGER.info("@@@@@@@@@@@@@ Done")

        # for testing, stop here
        # sys.exit()
        
    # Change back to the original directory
    os.chdir(ORIGINAL_DIRECTORY)