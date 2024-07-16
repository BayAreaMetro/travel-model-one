USAGE = """
Update off-model calculator based on travel model output of given runs.
Only include calculators that are based on travel model output - bike share, car share, targeted transportation alternatives, vanpools.

Prerequisite: run off-model prep R scripts (https://github.com/BayAreaMetro/travel-model-one/tree/master/utilities/RTP/Emissions/Off%20Model%20Calculators)
to create a set of "model data" for the off-model calculators.

Example call: 
`python update_offmodel_calculator_workbooks_with_TM_output.py bike_share 2035_TM160_DBP_Plan_04 2050_TM160_DBP_Plan_04`

Args inputs: 
off-model calculator, including -
    - bike share
    - car share
    - targeted transportation alternatives
    - vanpools
run_name_a: following the pattern for the name year_model_runid (e.g.2035_TM160_IPA_16)
run_name_b: following the pattern for the name year_model_runid (e.g.2050_TM160_IPA_16)
    
Flags:
 -d: directory paths
 for MTC team, select -d mtc
 for external team members -d external (set as default)

Templates:
You can access and update directory paths for the model in the templates folder.
- mtc.py: includes all paths in BOX (MTC users)
- external.py: includes all the relative paths when cloning the repo.

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

import argparse, os
import pandas as pd

# from helper import mons
from helper.bshare import Bikeshare

# calculator name choices
BIKE_SHARE = 'bike_share'
CAR_SHARE = 'car_share'
TARGETED_TRANS_ALT = 'targeted_trans_alt'
VAN_POOL = 'vanpools'

#####################################
#### ALL THESE METHODS WOULD BE REMOVED FROM HERE
#####################################
# ########## Bike Share
# def update_bikeshare_calculator(model_runID_ls):
#     # make a copy of the workbook
#     bikeshare_master_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Bikeshare.xlsx')
#     bikeshare_new_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Bikeshare__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

#     print(bikeshare_master_workbook_file)
#     print(bikeshare_new_workbook_file)
#     shutil.copy2(bikeshare_master_workbook_file, bikeshare_new_workbook_file)

#     # load and filter model run data of selected runs
#     bikeshare_model_data = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Bikeshare.csv'),
#         skiprows=1)
#     # display(bikeshare_model_data.head(5))
#     print(bikeshare_model_data['directory'].unique())
#     bikeshare_model_data = bikeshare_model_data.loc[
#         bikeshare_model_data['directory'].isin(model_runID_ls)]

#     # add model data of selected runs to 'Model Data' sheet
#     print(bikeshare_new_workbook_file)
#     with pd.ExcelWriter(bikeshare_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
#         # note this only works with pandas=1.4.3 or later; in earlier version, it will not overwrite sheet, but add new one with sheet name 'Model Data1'
#         bikeshare_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=1, startcol=0)

#     # get needed data into the worksheet
#     model_data_info = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Bikeshare.csv'),
#         nrows=0)
#     model_data_info = model_data_info.columns[0]
#     print(model_data_info)

#     # also add model data log info
#     bikeshare_new_workbook = openpyxl.load_workbook(bikeshare_new_workbook_file)
#     model_data_ws = bikeshare_new_workbook['Model Data']
#     model_data_ws['A1'] = model_data_info

#     # also add run_id to 'Main sheet'
#     bikeshare_mainsheet = bikeshare_new_workbook['Main sheet']
#     bikeshare_mainsheet['C14'] = model_runID_ls[0]
#     bikeshare_mainsheet['D14'] = model_runID_ls[1]

#     # save file
#     bikeshare_new_workbook.save(bikeshare_new_workbook_file)    

# ########## Car Share
# def update_carshare_calculator(model_runID_ls):
#     # make a copy of the workbook
#     carshare_master_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Carshare.xlsx')
#     carshare_new_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Carshare__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

#     print(carshare_master_workbook_file)
#     print(carshare_new_workbook_file)

#     shutil.copy2(carshare_master_workbook_file, carshare_new_workbook_file)

#     # load and filter model run data of selected runs
#     carshare_model_data = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - carshare.csv'),
#         skiprows=2)
#     print(carshare_model_data.head(5))
#     print(carshare_model_data['directory'].unique())
#     carshare_model_data = carshare_model_data.loc[
#         carshare_model_data['directory'].isin(model_runID_ls)]

#     # add model data of selected runs to 'Model Data' sheet
#     print(carshare_new_workbook_file)
#     with pd.ExcelWriter(carshare_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
#         carshare_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=2, startcol=0)

#     # get needed data into the worksheet
#     model_data_info_df = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Carshare.csv'),
#         nrows=1)
#     model_data_info_df.reset_index(inplace=True)
#     model_data_info = model_data_info_df.columns[0]
#     model_data_var = model_data_info_df.iloc[0, 0]
#     model_data_val = model_data_info_df.iloc[0, 1]
#     print(model_data_info)
#     print(model_data_var)
#     print(model_data_val)

#     # also add model data log info
#     carshare_new_workbook = openpyxl.load_workbook(carshare_new_workbook_file)
#     model_data_ws = carshare_new_workbook['Model Data']
#     model_data_ws['A1'] = model_data_var
#     model_data_ws['B1'] = model_data_val
#     model_data_ws['A2'] = model_data_info

#     # also add run_id to 'Main sheet'
#     carshare_mainsheet = carshare_new_workbook['Main Sheet']
#     carshare_mainsheet['C36'] = model_runID_ls[0]
#     carshare_mainsheet['D36'] = model_runID_ls[1]

#     # save file
#     carshare_new_workbook.save(carshare_new_workbook_file)


# ########## targeted transportation alternatives
# def update_targetedTransAlt_calculator(model_runID_ls):
#     # make a copy of the workbook
#     targetedTransAlt_master_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_TargetedTransAlt.xlsx')
#     targetedTransAlt_new_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_TargetedTransAlt__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

#     print(targetedTransAlt_master_workbook_file)
#     print(targetedTransAlt_new_workbook_file)
#     shutil.copy2(targetedTransAlt_master_workbook_file, targetedTransAlt_new_workbook_file)

#     # load and filter model run data of selected runs
#     targetedTransAlt_model_data = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Targeted Transportation Alternatives.csv'),
#         skiprows=1)

#     # display(targetedTransAlt_model_data.head(5))
#     print(targetedTransAlt_model_data['directory'].unique())
#     targetedTransAlt_model_data = targetedTransAlt_model_data.loc[
#         targetedTransAlt_model_data['directory'].isin(model_runID_ls)]

#     # add model data of selected runs to 'Model Data' sheet
#     print(targetedTransAlt_new_workbook_file)
#     with pd.ExcelWriter(targetedTransAlt_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
#         targetedTransAlt_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=1, startcol=0)

#     # get needed data into the worksheet
#     model_data_info = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Targeted Transportation Alternatives.csv'),
#         nrows=0)
#     model_data_info = model_data_info.columns[0]
#     print(model_data_info)

#     # also add model data log info
#     targetedTransAlt_new_workbook = openpyxl.load_workbook(targetedTransAlt_new_workbook_file)
#     model_data_ws = targetedTransAlt_new_workbook['Model Data']
#     model_data_ws['A1'] = model_data_info

#     # also add run_id to 'Main sheet'
#     targetedTransAlt_mainsheet = targetedTransAlt_new_workbook['Main sheet']
#     targetedTransAlt_mainsheet['C26'] = model_runID_ls[0]
#     targetedTransAlt_mainsheet['D26'] = model_runID_ls[1]

#     # save file
#     targetedTransAlt_new_workbook.save(targetedTransAlt_new_workbook_file)


# ########## van pools
# def update_valpools_calculator(model_runID_ls):
#     # make a copy of the workbook
#     vanpool_master_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Vanpools.xlsx')
#     vanpool_new_workbook_file = os.path.join(
#         OFF_MODEL_CALCULATOR_DIR, 
#         'PBA50+_OffModel_Vanpools__{}__{}.xlsx'.format(model_runID_ls[0], model_runID_ls[1]))

#     print(vanpool_master_workbook_file)
#     print(vanpool_new_workbook_file)
#     shutil.copy2(vanpool_master_workbook_file, vanpool_new_workbook_file)

#     # load and filter model run data of selected runs
#     vanpool_model_data = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Employer Shuttles.csv'),
#         skiprows=1)

#     # display(vanpool_model_data.head(5))
#     print(vanpool_model_data['directory'].unique())
#     vanpool_model_data = vanpool_model_data.loc[
#         vanpool_model_data['directory'].isin(model_runID_ls)]

#     # add model data of selected runs to 'Model Data' sheet
#     print(vanpool_new_workbook_file)
#     with pd.ExcelWriter(vanpool_new_workbook_file, engine='openpyxl', mode = 'a', if_sheet_exists = 'replace') as writer:
#         vanpool_model_data.to_excel(writer, sheet_name='Model Data', index=False, startrow=1, startcol=0)

#     # get needed data into the worksheet
#     model_data_info = pd.read_csv(
#         os.path.join(MODEL_DATA_BOX_DIR, 'Model Data - Employer Shuttles.csv'),
#         nrows=0)
#     model_data_info = model_data_info.columns[0]
#     print(model_data_info)

#     # also add model data log info
#     vanpool_new_workbook = openpyxl.load_workbook(vanpool_new_workbook_file)
#     model_data_ws = vanpool_new_workbook['Model Data']
#     model_data_ws['A1'] = model_data_info

#     # also add run_id to 'Main sheet'
#     vanpool_mainsheet = vanpool_new_workbook['Main Sheet']
#     vanpool_mainsheet['C12'] = model_runID_ls[0]
#     vanpool_mainsheet['D12'] = model_runID_ls[1]
#     vanpool_mainsheet['E12'] = model_runID_ls[1]

#     # save file
#     vanpool_new_workbook.save(vanpool_new_workbook_file)

# TODO: add function for the new e-bike calculator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('calculator', choices=[BIKE_SHARE,CAR_SHARE,TARGETED_TRANS_ALT,VAN_POOL], help='Calculator name')
    parser.add_argument('model_run_id_2035', help='travel model run_id of a 2035 run')
    parser.add_argument('model_run_id_2050', help='travel model run_id of a 2050 run')
    parser.add_argument('-d', choices=['mtc','external'], default='external', help='choose directory mtc or external')
    ARGS = parser.parse_args()


    # TODO: add logging
    if ARGS.calculator == BIKE_SHARE:
        print("### TEST NEW CALC class ###")
        # Create Calculator instance
        c=Bikeshare(ARGS, False)
        c.update_calculator()
        print("### END TEST ###")

    elif ARGS.calculator == CAR_SHARE:
        ## TODO: add subclass
        pass
    
    elif ARGS.calculator == TARGETED_TRANS_ALT:
        ## TODO: add subclass
        pass

    elif ARGS.calculator == VAN_POOL:
        ## TODO: add subclass
        pass

    ### TODO: add missing calculators (ebike, regional charger, accii, vehicle buyback)

    else:
        raise ValueError(
            "Choice not in options. Check the calculator name is correct.")
    
    # if ARGS.calculator == BIKE_SHARE:
    #     update_bikeshare_calculator(MODEL_RUNS)
    # elif ARGS.calculator == CAR_SHARE:
    #     update_carshare_calculator(MODEL_RUNS)
    # elif ARGS.calculator == TARGETED_TRANS_ALT:
    #     update_targetedTransAlt_calculator(MODEL_RUNS)
    # elif ARGS.calculator == VAN_POOL:
    #     update_valpools_calculator(MODEL_RUNS)
