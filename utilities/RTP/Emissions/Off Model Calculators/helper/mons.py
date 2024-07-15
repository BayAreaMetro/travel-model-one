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