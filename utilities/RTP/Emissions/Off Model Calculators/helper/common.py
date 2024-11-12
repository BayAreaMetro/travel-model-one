import os
import re

def get_paths(run_dir_name):
    """
    dirType='mtc'
    Import the absolute paths used within the MTC team. 
    E.g. links to box or other local directories.

    dirType='external'
    Import relative paths from repo pointing to sample folders.
    """

    print("Running test paths")
    username=os.environ.get('USERNAME')

    # abs_dirname would be Box in the future
    box_dir_test=r"C:\Users\{}\Box\ICF PBA50+ Off-Model_EXT shared\Scripting\demo_for_ICF_20240916"\
                .format(username)
    
    masterWorkbookFolder, newestWorkbookMaster=get_latest_masterworkbook(box_dir_test)
    
    abs_dirname=os.path.join(os.path.dirname(__file__),"..")

    # Input data paths
    model_data_box_dir = os.path.join(box_dir_test
                            , "NETWORKDRIVE_travel_model_data"
                            , run_dir_name['run']
                            , "OUTPUT"
                            , "off_model"
                            , "input")

    sb_dir=os.path.join(model_data_box_dir,
                        "Model Data - SB375_data.csv")
    
        # Models (From Box Demo Folder)
    off_model_calculator_dir = os.path.join(masterWorkbookFolder
                                            ,newestWorkbookMaster
    )

    # Output
    off_model_calculator_dir_output = os.path.join(box_dir_test
                                                , "NETWORKDRIVE_travel_model_data"
                                                , run_dir_name['run']
                                                , "OUTPUT"
                                                , "off_model"
                                                , "output")
    
    off_model_calculator_log_file_path=os.path.join(masterWorkbookFolder
                                                ,"offmodel_master_log_all_versions_all_runs.xlsx")

    # Variables locations
    vars=os.path.join(off_model_calculator_dir,
                    "Variable_locations.xlsx")

    return {
            'MODEL_DATA_BOX_DIR':model_data_box_dir, 
            'OFF_MODEL_CALCULATOR_DIR':off_model_calculator_dir,
            'OFF_MODEL_CALCULATOR_DIR_OUTPUT':off_model_calculator_dir_output, 
            'OFF_MODEL_CALCULATOR_LOG_PATH':off_model_calculator_log_file_path,
            'VARS':vars,
            'SB375':sb_dir,
            }

def get_last_workbook_version(listWorkbooks):
    maxVersion=None
    currentName=None
    for name in listWorkbooks:
        # Use regex to find all versions that start with 'v' followed by digits
        versions = re.findall(r'v(\d+)', name)
        
        # Convert versions to integers and find the maximum
        if versions:
            if maxVersion==None:
                maxVersion=max(map(int, versions))
                currentName=name
                currentVersion=max(map(int, versions))
            else:
                currentVersion=max(map(int, versions))

            if currentVersion>maxVersion:
                maxVersion=currentVersion
                currentName=name
    return currentName
         

def get_latest_masterworkbook(boxDirectory):
    # masterWorkbooks folder inside demo
    masterWorkbookFolder="BOX_off_model_calculator_masterWorkbook"
    offmodelDirectory=os.path.join(boxDirectory,masterWorkbookFolder)
    foldersList=[name for name in os.listdir(offmodelDirectory)
            if os.path.isdir(os.path.join(offmodelDirectory, name))]
    masterWorkbookName=get_last_workbook_version(foldersList)
    return offmodelDirectory, masterWorkbookName

def get_directory_constants(dirType,run_dir_name):
    '''
    This function extracts the corresponding relative or absolute paths
    used in the external or mtc options.
    '''
    # directory file paths (input, models)
    paths=get_paths(run_dir_name)
    
    return paths['MODEL_DATA_BOX_DIR'], paths['OFF_MODEL_CALCULATOR_DIR']

def get_vars_directory(dirType, run_dir_name):
    # directory file paths (variable locations)
    paths=get_paths(run_dir_name)
        
    return paths['VARS']

def get_master_log_path(dirType, run_dir_name):
    paths=get_paths(run_dir_name)
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

    path=get_paths(c.runs)

    runName=c.uid.replace(':','--')
    pathToRun=os.path.join(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],
                           f"{runName}")

    if not os.path.exists(pathToRun):
        os.makedirs(pathToRun)

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