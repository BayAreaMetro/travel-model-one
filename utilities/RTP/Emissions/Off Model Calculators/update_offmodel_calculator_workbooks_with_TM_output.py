USAGE = """
Update off-model calculator based on travel model output of given runs.
Only include calculators that are based on travel model output - bike share, car share, targeted transportation alternatives, vanpools.

Prerequisite: run off-model prep R scripts (https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/RTP/Emissions/Off%20Model%20Calculators)
to create a set of "model data" for the off-model calculators.

Example call: 
`python update_offmodel_calculator_workbooks_with_TM_output.py`
Args inputs:  
 Flags:
 -d: directory paths
 for MTC team, select -d mtc (set as default)
 for external team members -d external 

Models:
Includes all Excel sheet master model calculators. These models contain the logs of runs created after running the script.

Data:
    |input: includes a folder with the following strucure
        |name: IPA_TM2
        -> |ModelData
            -> All model data input files (xlsx)
           |PBA50+ Off-Model Calculators
            -> Calculators (not used)
    |output: contains a copy of the calculator Excel workbook, with updated travel model data.
        |run folder: named based on the uid (timestamp).
                e.g. 2024-08-09 15--50--53 (format:YYYY-MM-DD 24H--MM--SS)
"""

import argparse
import pandas as pd
import os
from datetime import datetime
 
from helper.bshare import Bikeshare
from helper.cshare import Carshare
from helper.targtransalt import TargetedTransAlt
from helper.vpool import VanPools
from helper.ebk import EBike
from helper.vbuyback import BuyBack
from helper.regchar import RegionalCharger

# calculator name choices
BIKE_SHARE = 'bike_share'
CAR_SHARE = 'car_share'
TARGETED_TRANS_ALT = 'targeted_trans_alt'
VAN_POOL = 'vanpools'
E_BIKE = 'e_bike'
BUY_BACK='buy_back'
REG_CHARGER='regional_charger'

# template location
CWD=os.path.dirname(__file__)
TEMPLATE_DIR=os.path.join(CWD, r'update_omc_template.xlsx')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('-d', choices=['mtc','external'], default='external', 
                        help='choose directory mtc or external'
    )
    ARGS = parser.parse_args()
    DIRECTORY=ARGS.d
    UID=datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    templateData=pd.read_excel(TEMPLATE_DIR
                               ,sheet_name='Template'
                               ,header=[0]).fillna("")
    
    for ix in range(len(templateData)):
        CALCULATOR=templateData.iloc[ix]['Calculator']
        R1=templateData.iloc[ix]['model_run_id baseline']
        R2=templateData.iloc[ix]['model_run_id horizon']
        MODEL_RUN_IDS=[R1,R2]
        
        if CALCULATOR == BIKE_SHARE:
            c=Bikeshare(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()

        elif CALCULATOR == CAR_SHARE:
            c=Carshare(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()
        
        elif CALCULATOR == TARGETED_TRANS_ALT:
            c=TargetedTransAlt(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()

        elif CALCULATOR == VAN_POOL:
            c=VanPools(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()

        elif CALCULATOR == E_BIKE:
            c=EBike(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()

        elif CALCULATOR == BUY_BACK:
            c=BuyBack(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()
        
        elif CALCULATOR == REG_CHARGER:
            c=RegionalCharger(MODEL_RUN_IDS,DIRECTORY, UID, False)
            c.update_calculator()

        ## TODO: Add Complete Streets calculator

        else:
            raise ValueError(
                "Choice not in options. Check the calculator name is correct.")
        
