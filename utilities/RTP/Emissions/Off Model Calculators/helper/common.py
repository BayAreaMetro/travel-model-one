import os
import re

def get_paths():

    # run directory
    run_directory=os.getcwd()

    # locations of the master workbooks
    off_model_calculator_dir=".\\CTRAMP\\scripts\\offmodel\\calculators"

    # Input data paths
    model_data_dir = os.path.join(run_directory
                            , "offmodel"
                            , "offmodel_prep")

    sb_dir=os.path.join(off_model_calculator_dir, "SB375_data.csv")

    # Output
    off_model_calculator_dir_output = os.path.join(run_directory
                                                , "offmodel"
                                                , "offmodel_output")
    # TODO: where to store the master log?
    off_model_calculator_log_file_path=os.path.join(off_model_calculator_dir_output
                                                ,"offmodel_master_log_all_versions_all_runs.xlsx")

    # Variables locations
    vars=os.path.join(off_model_calculator_dir,
                    "Variable_locations.csv")

    return {
            'MODEL_DATA_DIR':model_data_dir, 
            'OFF_MODEL_CALCULATOR_DIR':off_model_calculator_dir,
            'OFF_MODEL_CALCULATOR_DIR_OUTPUT':off_model_calculator_dir_output, 
            'OFF_MODEL_CALCULATOR_LOG_PATH':off_model_calculator_log_file_path,
            'VARS':vars,
            'SB375':sb_dir,
            }

def get_directory_constants():
    '''
    This function extracts the corresponding relative or absolute paths
    used in the external or mtc options.
    '''
    # directory file paths (input, models)
    paths=get_paths()
    
    return paths['MODEL_DATA_DIR'], paths['OFF_MODEL_CALCULATOR_DIR']

def get_vars_directory():
    # directory file paths (variable locations)
    paths=get_paths()
        
    return paths['VARS']

def get_master_log_path():
    paths=get_paths()
    return paths['OFF_MODEL_CALCULATOR_LOG_PATH']

def getNextFilePath(output_folder, run):
    """
    This method checks for folders with the same name.
    If the folder exists, provides the next number in the sequence.
    """
    
    lastRunId=0
    for f in os.listdir(output_folder):
        fileNameList=f.split("__")
        if f"{fileNameList[0]}__{fileNameList[1]}"== run:
            if int(fileNameList[2])>lastRunId:
                lastRunId=int(fileNameList[2])

        else:
            continue

    return lastRunId + 1

def createNewRun(c, verbose=False):
    """
    Given the two model_run_id_year selected, an output folder is created.
    In this folder, outputs will be saved.
    If the output folder already exists, a sequence is created
    to differentiate outputs.
    """

    path=get_paths()

    runName=c.uid.replace(':','--')
    # pathToRun=os.path.join(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],
    #                        f"{runName}")
    pathToRun=path['OFF_MODEL_CALCULATOR_DIR_OUTPUT']

    # if not os.path.exists(pathToRun):
    #     os.makedirs(pathToRun)

    if verbose:
        print(f"New run created: {runName}")
        print(f"Location: {pathToRun}")

    return pathToRun

def get_year_modelrun_id(directory_string):
    # Define the regex pattern
    pattern = r"(\d{4})_(TM\d{3})_([A-Za-z0-9_]+)"
    
    # Search for matches
    match = re.match(pattern, directory_string)
    
    if match:
        year = match.group(1)
        model = match.group(2)
        id_value = match.group(3)
        
        if "NoProject" in id_value:
            return None
        
        return {
            'run':directory_string,
            'year': year,
            'model': model,
            'id': id_value
        }
    else:
        print(f"Could not find a match for {directory_string}")
        return None
