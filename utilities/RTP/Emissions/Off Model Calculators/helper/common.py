import os

def get_paths(dirType):
    """
    dirType='mtc'
    Import the absolute paths used within the MTC team. 
    E.g. links to box or other local directories.

    dirType='external'
    Import relative paths from repo pointing to sample folders.
    """
    if dirType=='mtc':
        # Input data paths
        box_dir = r'C:\Users\{}\Box\Plan Bay Area 2050+\Blueprint\Off-Model\PBA50+ Off-Model'\
            .format(os.environ.get('USERNAME'))
        model_data_box_dir = os.path.join(box_dir, 'model_data_all')

        # Models
        off_model_calculator_dir = os.path.join(
            box_dir, 'DBP_v2', 'PBA50+ Off-Model Calculators')

        # Outputs
        off_model_calculator_dir_output = off_model_calculator_dir

        # Variables locations
        vars=os.path.join(off_model_calculator_dir, "Variable_locations.xlsx")

        sb_dir=os.path.join(off_model_calculator_dir,
                        "SB375_data.csv")
        
    
    elif dirType=='external':
    
        abs_dirname=os.path.join(os.path.dirname(__file__),"..")
        # Input data paths
        box_dir = os.path.join(abs_dirname,
                            r"data\input\IPA_TM2")

        model_data_box_dir = os.path.join(box_dir,"ModelData")

        # Models
        off_model_calculator_dir = os.path.join(abs_dirname,
                                                "models")

        # Output
        off_model_calculator_dir_output = os.path.join(abs_dirname,
                                                    r"data\output")

        # Variables locations
        vars=os.path.join(abs_dirname,
                        r"models\Variable_locations.xlsx")
        
        sb_dir=os.path.join(abs_dirname,
                        r"models\SB375_data.csv")
                
    else:
        raise ValueError("-d can be either mtc or external")

    return {'BOX_DIR': box_dir, 
            'MODEL_DATA_BOX_DIR':model_data_box_dir, 
            'OFF_MODEL_CALCULATOR_DIR':off_model_calculator_dir,
            'OFF_MODEL_CALCULATOR_DIR_OUTPUT':off_model_calculator_dir_output, 
            'VARS':vars,
            'SB375':sb_dir,
            }


def get_directory_constants(dirType):
    '''
    This function extracts the corresponding relative or absolute paths
    used in the external or mtc options.
    '''
    # directory file paths (input, models)
    paths=get_paths(dirType)
    
    return paths['MODEL_DATA_BOX_DIR'], paths['OFF_MODEL_CALCULATOR_DIR']

def get_vars_directory(dirType):
    # directory file paths (variable locations)
    paths=get_paths(dirType)
        
    return paths['VARS']

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

    path=get_paths(c.pathType)

    runName=c.uid.replace(':','--')
    pathToRun=os.path.join(path['OFF_MODEL_CALCULATOR_DIR_OUTPUT'],
                           f"{runName}")

    if not os.path.exists(pathToRun):
        os.makedirs(pathToRun)

    if verbose:
        print(f"New run created: {runName}")
        print(f"Location: {pathToRun}")

    return pathToRun
