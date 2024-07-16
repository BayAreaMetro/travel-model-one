'''
This module includes common functions within the main script.
'''

def get_directory_constants(dirType):
    '''
    This function extracts the corresponding relative or absolute paths
    used in the external or mtc options.
    '''
    # directory file paths (input, models, outputs)
    if dirType=="external":
        from templates.external import (
                        MODEL_DATA_BOX_DIR,
                        OFF_MODEL_CALCULATOR_DIR,
                        )
    else:
        from templates.mtc import (
                    MODEL_DATA_BOX_DIR,
                    OFF_MODEL_CALCULATOR_DIR,
                    )
    
    return MODEL_DATA_BOX_DIR, OFF_MODEL_CALCULATOR_DIR

def get_vars_directory(dirType):
    # directory file paths (input, models, outputs)
    if dirType=="external":
        from templates.external import (
                        VARS
                        )
    else:
        from templates.mtc import (
                    VARS
                    )
        
    return VARS

# method depricated, now file names added inside subclasses
def get_master_and_data_file_names(calcChoice):
    
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
