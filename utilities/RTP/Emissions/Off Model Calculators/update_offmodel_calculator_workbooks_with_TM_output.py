USAGE = """
Update off-model calculator based on travel model output of given runs.
Only include calculators that are based on travel model output - bike share, car share, targeted transportation alternatives, vanpools.

Prerequisite: run off-model prep R scripts (https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/RTP/Emissions/Off%20Model%20Calculators)
to create a set of "model data" for the off-model calculators.

Example call: 
`python update_offmodel_calculator_workbooks_with_TM_output.py bike_share 2035_TM160_DBP_Plan_04 2050_TM160_DBP_Plan_04`

Inputs: off-model calculator, including -
    - bike share
    - car share
    - targeted transportation alternatives
    - vanpools

Outputs: a copy of the calculator Excel workbook, with updated travel model data.

"""

import argparse, os
import shutil, openpyxl
import pandas as pd

from helper import mons

# Main directory
ABS_DIRNAME = os.path.dirname(__file__).replace("\\","/")

# calculator names
BIKE_SHARE = 'bike_share'
CAR_SHARE = 'car_share'
TARGETED_TRANS_ALT = 'targeted_trans_alt'
VAN_POOL = 'vanpools'

#####################################
def get_directory_constants(dirType):
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

########## Bike Share
def update_bikeshare_calculator(model_runID_ls, verbose=False):
    
    masterWorkbookName="PBA50+_OffModel_Bikeshare" 

    # Step 1: Create run and copy files  
    try:
        newWBpath = mons.copy_workbook(masterWorkbookName
                                            , OFF_MODEL_CALCULATOR_DIR
                                            ,model_runID_ls
                                            # ,verbose=True
                                            )
    except NameError:
        print("The calculator name is wrong. Can't locate file.")

    # Step 2: load and filter model data of selected runs
    
    rawModelDataFileName="Model Data - Bikeshare"
    modelData, metaData=mons.get_model_data(MODEL_DATA_BOX_DIR
                                , rawModelDataFileName
                                , model_runID_ls
                                # , verbose=True
                                )

    # Step 3: add model data of selected runs to 'Model Data' sheet
    mons.write_model_data_to_excel(newWBpath,modelData,metaData)
    
    # Step 4:
    mons.write_runid_to_mainsheet(newWBpath
                                  ,model_runID_ls
                                #   , verbose= True
                                  )
    

########## Car Share
def update_carshare_calculator(model_runID_ls):
    # make a copy of the workbook
    carshare_master_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_Carshare.xlsx')
    carshare_new_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_Carshare__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

    print(carshare_master_workbook_file)
    print(carshare_new_workbook_file)

    shutil.copy2(carshare_master_workbook_file, carshare_new_workbook_file)

    # load and filter model run data of selected runs
    carshare_model_data = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - carshare.csv'),
        skiprows=2)
    print(carshare_model_data.head(5))
    print(carshare_model_data['directory'].unique())
    carshare_model_data = carshare_model_data.loc[
        carshare_model_data['directory'].isin(model_runID_ls)]

    # add model data of selected runs to 'Model Data' sheet
    print(carshare_new_workbook_file)
    with pd.ExcelWriter(carshare_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
        carshare_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=2, startcol=0)

    # get needed data into the worksheet
    model_data_info_df = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Carshare.csv'),
        nrows=1)
    model_data_info_df.reset_index(inplace=True)
    model_data_info = model_data_info_df.columns[0]
    model_data_var = model_data_info_df.iloc[0, 0]
    model_data_val = model_data_info_df.iloc[0, 1]
    print(model_data_info)
    print(model_data_var)
    print(model_data_val)

    # also add model data log info
    carshare_new_workbook = openpyxl.load_workbook(carshare_new_workbook_file)
    model_data_ws = carshare_new_workbook['Model Data']
    model_data_ws['A1'] = model_data_var
    model_data_ws['B1'] = model_data_val
    model_data_ws['A2'] = model_data_info

    # also add run_id to 'Main sheet'
    carshare_mainsheet = carshare_new_workbook['Main Sheet']
    carshare_mainsheet['C36'] = model_runID_ls[0]
    carshare_mainsheet['D36'] = model_runID_ls[1]

    # save file
    carshare_new_workbook.save(carshare_new_workbook_file)


########## targeted transportation alternatives
def update_targetedTransAlt_calculator(model_runID_ls):
    # make a copy of the workbook
    targetedTransAlt_master_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_TargetedTransAlt.xlsx')
    targetedTransAlt_new_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_TargetedTransAlt__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

    print(targetedTransAlt_master_workbook_file)
    print(targetedTransAlt_new_workbook_file)
    shutil.copy2(targetedTransAlt_master_workbook_file, targetedTransAlt_new_workbook_file)

    # load and filter model run data of selected runs
    targetedTransAlt_model_data = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Targeted Transportation Alternatives.csv'),
        skiprows=1)

    # display(targetedTransAlt_model_data.head(5))
    print(targetedTransAlt_model_data['directory'].unique())
    targetedTransAlt_model_data = targetedTransAlt_model_data.loc[
        targetedTransAlt_model_data['directory'].isin(model_runID_ls)]

    # add model data of selected runs to 'Model Data' sheet
    print(targetedTransAlt_new_workbook_file)
    with pd.ExcelWriter(targetedTransAlt_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
        targetedTransAlt_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=1, startcol=0)

    # get needed data into the worksheet
    model_data_info = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Targeted Transportation Alternatives.csv'),
        nrows=0)
    model_data_info = model_data_info.columns[0]
    print(model_data_info)

    # also add model data log info
    targetedTransAlt_new_workbook = openpyxl.load_workbook(targetedTransAlt_new_workbook_file)
    model_data_ws = targetedTransAlt_new_workbook['Model Data']
    model_data_ws['A1'] = model_data_info

    # also add run_id to 'Main sheet'
    targetedTransAlt_mainsheet = targetedTransAlt_new_workbook['Main sheet']
    targetedTransAlt_mainsheet['C26'] = model_runID_ls[0]
    targetedTransAlt_mainsheet['D26'] = model_runID_ls[1]

    # save file
    targetedTransAlt_new_workbook.save(targetedTransAlt_new_workbook_file)


########## van pools
def update_valpools_calculator(model_runID_ls):
    # make a copy of the workbook
    vanpool_master_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_Vanpools.xlsx')
    vanpool_new_workbook_file = os.path.join(
        OFF_MODEL_CALCULATOR_DIR, 
        'PBA50+_OffModel_Vanpools__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

    print(vanpool_master_workbook_file)
    print(vanpool_new_workbook_file)
    shutil.copy2(vanpool_master_workbook_file, vanpool_new_workbook_file)

    # load and filter model run data of selected runs
    vanpool_model_data = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Employer Shuttles.csv'),
        skiprows=1)

    # display(vanpool_model_data.head(5))
    print(vanpool_model_data['directory'].unique())
    vanpool_model_data = vanpool_model_data.loc[
        vanpool_model_data['directory'].isin(model_runID_ls)]

    # add model data of selected runs to 'Model Data' sheet
    print(vanpool_new_workbook_file)
    with pd.ExcelWriter(vanpool_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
        vanpool_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=1, startcol=0)

    # get needed data into the worksheet
    model_data_info = pd.read_csv(
        os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Employer Shuttles.csv'),
        nrows=0)
    model_data_info = model_data_info.columns[0]
    print(model_data_info)

    # also add model data log info
    vanpool_new_workbook = openpyxl.load_workbook(vanpool_new_workbook_file)
    model_data_ws = vanpool_new_workbook['Model Data']
    model_data_ws['A1'] = model_data_info

    # also add run_id to 'Main sheet'
    vanpool_mainsheet = vanpool_new_workbook['Main Sheet']
    vanpool_mainsheet['C12'] = model_runID_ls[0]
    vanpool_mainsheet['D12'] = model_runID_ls[1]
    vanpool_mainsheet['E12'] = model_runID_ls[1]

    # save file
    vanpool_new_workbook.save(vanpool_new_workbook_file)

# TODO: add function for the new e-bike calculator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('calculator', choices=[BIKE_SHARE,CAR_SHARE,TARGETED_TRANS_ALT,VAN_POOL], help='Calculator name')
    parser.add_argument('model_run_id_2035', help='travel model run_id of a 2035 run')
    parser.add_argument('model_run_id_2050', help='travel model run_id of a 2050 run')
    parser.add_argument('-d', choices=['mtc','external'], default='external', help='choose directory mtc or external')
    args = parser.parse_args()


    # TODO: add logging

    MODEL_RUNS = [args.model_run_id_2035, args.model_run_id_2050]
    MODEL_DATA_BOX_DIR, OFF_MODEL_CALCULATOR_DIR = get_directory_constants(args.d)

    if args.calculator == BIKE_SHARE:
        update_bikeshare_calculator(MODEL_RUNS)
    elif args.calculator == CAR_SHARE:
        update_carshare_calculator(MODEL_RUNS)
    elif args.calculator == TARGETED_TRANS_ALT:
        update_targetedTransAlt_calculator(MODEL_RUNS)
    elif args.calculator == VAN_POOL:
        update_valpools_calculator(MODEL_RUNS)
