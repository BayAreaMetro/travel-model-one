USAGE = """
Update off-model calculator based on travel model output of given runs.
Only include calculators that are based on travel model output - bike share, car share, targeted transportation alternatives, vanpools.

Models:
Includes all Excel sheet master model calculators. These models contain the logs of runs created after running the script.

Data:
    |input: includes a folder with the following strucure
        |directory in BOX: IPA_TM2/OUTPUT/off_model
        -> |input
            -> All model data input files (xlsx)
    |output: contains a copy of the calculator Excel workbook, with updated travel model data.
        |run folder: named based on the uid (timestamp).
                e.g. 2024-08-09 15--50--53 (format:YYYY-MM-DD 24H--MM--SS)
"""

import pandas as pd
import os
from datetime import datetime
import logging
 
from helper.bshare import Bikeshare
from helper.cshare import Carshare
from helper.targtransalt import TargetedTransAlt
from helper.vpool import VanPools
from helper.ebk import EBike
from helper.vbuyback import BuyBack
from helper.regchar import RegionalCharger
from helper.common import (get_year_modelrun_id,get_paths)

# calculator name choices
BIKE_SHARE = 'bike_share'
CAR_SHARE = 'car_share'
TARGETED_TRANS_ALT = 'targeted_trans_alt'
VAN_POOL = 'vanpools'
E_BIKE = 'e_bike'
BUY_BACK='buy_back'
REG_CHARGER='regional_charger'

if __name__ == '__main__':

    # DIRECTORY="mtc"
    LOG_FILE = "offmodel\\run_offmodel_calculators_{}.log"
    UID=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    calculators_list=['bike_share','car_share','targeted_trans_alt'
                      ,'vanpools','e_bike','buy_back','regional_charger']

    MODEL_RUN_ID = os.path.basename(os.getcwd())
    for calc_name in calculators_list:
        CALCULATOR=calc_name
    
        if CALCULATOR == BIKE_SHARE:
            logging.info('')
            c=Bikeshare(MODEL_RUN_ID, UID, False)

        elif CALCULATOR == CAR_SHARE:
            c=Carshare(MODEL_RUN_ID, UID, False)
                    
        elif CALCULATOR == TARGETED_TRANS_ALT:
            c=TargetedTransAlt(MODEL_RUN_ID, UID, False)

        elif CALCULATOR == VAN_POOL:
            c=VanPools(MODEL_RUN_ID, UID, False)

        elif CALCULATOR == E_BIKE:
            c=EBike(MODEL_RUN_ID, UID, False)

        elif CALCULATOR == BUY_BACK:
            c=BuyBack(MODEL_RUN_ID, UID, False)
        
        elif CALCULATOR == REG_CHARGER:
            c=RegionalCharger(MODEL_RUN_ID, UID, False)

        else:
            raise ValueError(
                "Choice not in options. Check the calculator name is correct.")
    
        c.update_calculator()
        c.paths=get_paths()
        # outputSummary=c.create_output_summary_path(r['run'])
        # outputSummary=c.create_output_summary_path(MODEL_RUN_ID)            
        # if not os.path.exists(outputSummary):
        #     c.initialize_summary_file(outputSummary)
        # else:
        #     print("Summary file exists.")
        
        # c.update_summary_file(outputSummary,MODEL_RUN_ID)
