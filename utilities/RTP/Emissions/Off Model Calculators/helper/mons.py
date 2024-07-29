'''
This module includes common functions within the calculators.
'''

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
    else:
        raise ValueError("-d can be either mtc or external")

    return {'BOX_DIR': box_dir, 
            'MODEL_DATA_BOX_DIR':model_data_box_dir, 
            'OFF_MODEL_CALCULATOR_DIR':off_model_calculator_dir,
            'OFF_MODEL_CALCULATOR_DIR_OUTPUT':off_model_calculator_dir_output, 
            'VARS':vars}


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

# method depricated, now file names added inside subclasses
def get_master_and_data_file_names(calcChoice):
    """
    This function contains the calculator official names and corresponding
    model data name (input) that will be updated in the calculator.
    """
    
    if calcChoice=='bike_share':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_Bikeshare" 
        MODEL_DATA_FILE_NAME="Model Data - Bikeshare"
    
    elif calcChoice=='car_share':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_Carshare" 
        MODEL_DATA_FILE_NAME="Model Data - Carshare"

    elif calcChoice=='ebike':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_EBIKE" 
        MODEL_DATA_FILE_NAME=None # Needs model data name

    elif calcChoice=='regional_charger':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_RegionalCharger" 
        MODEL_DATA_FILE_NAME=None # Needs model data name

    elif calcChoice=='regional_charger_accii':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_RegionalCharger_ACCII" 
        MODEL_DATA_FILE_NAME=None # Needs model data name

    elif calcChoice=='targeted_trans_alt':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_TargetedTransAlt" 
        MODEL_DATA_FILE_NAME="Model Data - Targeted Transportation Alternatives"

    elif calcChoice=='vanpools':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_Vanpools" 
        MODEL_DATA_FILE_NAME="Model Data - Employer Shuttles" # confirm  name

    elif calcChoice=='vehicle_buyback':
        MASTER_WORKBOOK_NAME="PBA50+_OffModel_VehicleBuyback" 
        MODEL_DATA_FILE_NAME=None # Needs model data name
    
    else:
        raise ValueError("Choice not in options. Check the calculator name is correct.")
    
    return MASTER_WORKBOOK_NAME, MODEL_DATA_FILE_NAME
