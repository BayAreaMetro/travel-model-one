USAGE = """
Update off-model calculator based on travel model output of given runs.
Only include calculators that are based on travel model output - bike share, car share, targeted transportation alternatives, vanpools.

Prerequisite: run off-model prep R scripts (https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/RTP/Emissions/Off%20Model%20Calculators)
to create a set of "model data" for the off-model calculators.

Example call: 
`python update_offmodel_calculator_workbooks_with_TM_output.py bike_share 2035_TM160_DBP_Plan_04 2050_TM160_DBP_Plan_04`

Args inputs: 
off-model calculator, including -
    - bike share (req: r1,r2)
    - car share (req: r1,r2)
    - targeted transportation alternatives (req: r1,r2)
    - vanpools (req: r1,r2)
    - ebike
    - vehicle buy back
    - regional charger
    - complete streets (req: r1,r2)

 Flags:
 -d: directory paths
 for MTC team, select -d mtc (set as default)
 for external team members -d external 
-r1: run_name_a - following the pattern for the name year_model_runid (e.g.2035_TM160_IPA_16)
-r2: run_name_b - following the pattern for the name year_model_runid (e.g.2050_TM160_IPA_16)

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
        |run folder: named based on the run. If same run names used, then creates id
                e.g. 2035_TM160_IPA_16__2050_TM160_IPA_16__0
                e.g. 2035_TM160_IPA_16__2050_TM160_IPA_16__1
        -> New calculator with updated data

"""
import argparse
 
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE)

    # Args used in all calculators
    parser.add_argument('calculator', choices=[BIKE_SHARE,CAR_SHARE,\
                                               TARGETED_TRANS_ALT,VAN_POOL,\
                                               E_BIKE,BUY_BACK,REG_CHARGER], \
                                               help='Calculator name'\
    )
    parser.add_argument('-d', choices=['mtc','external'], default='external', 
                        help='choose directory mtc or external'
    )
    
    # Args used in some calcs (optional)
    parser.add_argument('-r1','--model_run_id_2035', 
                        default="r1",
                        help='travel model run_id of a 2035 run'
    )
    parser.add_argument('-r2','--model_run_id_2050', 
                        default="r2",
                        help='travel model run_id of a 2050 run'
    )
    ARGS = parser.parse_args()

    MODEL_RUN_IDS=[ARGS.model_run_id_2035,ARGS.model_run_id_2050]
    DIRECTORY=ARGS.d


    # TODO: add logging
    if ARGS.calculator == BIKE_SHARE:
        # Create Calculator instance
        c=Bikeshare(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()

    elif ARGS.calculator == CAR_SHARE:
        ## TODO: add subclass
        c=Carshare(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()
    
    elif ARGS.calculator == TARGETED_TRANS_ALT:
        c=TargetedTransAlt(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()

    elif ARGS.calculator == VAN_POOL:
        c=VanPools(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()

    elif ARGS.calculator == E_BIKE:
        c=EBike(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()

    elif ARGS.calculator == BUY_BACK:
        c=BuyBack(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()
    
    elif ARGS.calculator == REG_CHARGER:
        c=RegionalCharger(MODEL_RUN_IDS,DIRECTORY, False)
        c.update_calculator()

    ## TODO: Add Complete Streets calculator

    else:
        raise ValueError(
            "Choice not in options. Check the calculator name is correct.")
    
