USAGE = """
Pull results from off-model calculator Excel workbooks and save summary files to Travel Model Tableau cross-run visualization folder.

Prerequisite: off model calculator workbooks for a given run has been generated via run_offmodel_calculators.py
(https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/Emissions/Off%20Model%20Calculators/run_offmodel_calculators.py).

Example call: 
`python extract_offmodel_results.py

"""

import argparse, datetime, logging, os, sys, pathlib
import pandas as pd
import xlwings as xl

#####################################
# inputs and outputs
TM_RUN_LOCATION_BP   = r'M:\Application\Model One\RTP2025\Blueprint'
TM_RUN_LOCATION_IP   = r'M:\Application\Model One\RTP2025\IncrementalProgress'
MODELRUNS_XLSX       = r'X:\travel-model-one-master\utilities\RTP\config_RTP2025\ModelRuns_RTP2025.xlsx'

# calculator names
BIKE_SHARE = 'Bikeshare'
CAR_SHARE = 'Carshare'
TARGETED_TRANS_ALT = 'TargetedTransAlt'
VAN_POOL = 'Vanpools'
CHARGER = 'RegionalCharger'
VEH_BUYBACK = 'VehicleBuyback'
EBIKE = 'Ebike'

#####################################

def refresh_excelworkbook(wb_file):
    """
    The auto-generated excel workbooks need to be refreshed to update the formulas.
    """
    excel_app = xl.App(visible=False)
    excel_workbook = excel_app.books.open(wb_file)
    excel_workbook.save()
    excel_workbook.close()
    excel_app.quit()
    logging.info(f'Workbook {wb_file} refreshed')

def get_runs_with_off_model(modelruns_xlsx):
    """
    Get the model runs that have off-model calculator workbooks generated.
    """
    logging.info('Reading modelruns xlsx file: {}'.format(modelruns_xlsx))
    modelruns_df = pd.read_excel(modelruns_xlsx)
    modelruns_df = modelruns_df[['directory','year','run_offmodel']]
    logging.info('modelruns off_model run tally:\n{}'.format(modelruns_df['run_offmodel'].value_counts()))
    modelruns_with_off_model_IP = modelruns_df.loc[modelruns_df['run_offmodel']=='IP']
    modelruns_with_off_model_FBP = modelruns_df.loc[modelruns_df['run_offmodel']=='FBP']
    return modelruns_with_off_model_IP, modelruns_with_off_model_FBP

def extract_off_model_calculator_result(run_directory, run_id, calculator_name):
    """
    Extract the result from one off-model calculator workbook.
    """
    off_model_output_dir = os.path.join(
        run_directory, 'OUTPUT', 'offmodel', 'offmodel_output')
    
    # for calculator_name in calculator_names:
    off_model_wb = os.path.join(off_model_output_dir, 'PBA50+_OffModel_{}__{}.xlsx'.format(calculator_name, run_id))

    if not os.path.exists(off_model_wb):
        logging.info(f'Workbook {off_model_wb} does not exist')
        return None
    else:
        refresh_excelworkbook(off_model_wb)
        off_model_df = pd.read_excel(off_model_wb, sheet_name='Output', skiprows=1)
        off_model_df = off_model_df[[
            'Horizon Run ID', 
            # 'Out_daily_VMT_reduced_{}'.format(run_id[:4]), 
            'Out_daily_GHG_reduced_{}'.format(run_id[:4]), 
            'Out_per_capita_GHG_reduced_{}'.format(run_id[:4])]]
        off_model_df.rename(
            columns={'Horizon Run ID': 'run_id',
                     'Out_daily_GHG_reduced_{}'.format(run_id[:4]): 'daily_ghg_reduction',
                     'Out_per_capita_GHG_reduced_{}'.format(run_id[:4]): 'per_capita_ghg_reduction'},
            inplace=True)
        off_model_df['offmodel_strategy'] = calculator_name
        return off_model_df

def summarize_off_model_calculator_results(run_directory, run_id, calculator_names_list):
    """
    Extract and summarize off-model results from all calculators for a given run.
    """
    all_calculators_results = []
    for name in calculator_names_list:
        logging.info(f'Extracting {name} results for run {run_id}')
        calculator_result = extract_off_model_calculator_result(run_directory, run_id, name)
        if calculator_result is not None:
            all_calculators_results.append(calculator_result)

    off_model_summary = pd.concat(all_calculators_results)
    logging.info(f'Completed for run {run_id}, Off-model summary:\n{off_model_summary}')

    if len(off_model_summary) > 0:

        off_model_tot = off_model_summary.groupby('run_id').agg({
            'daily_ghg_reduction'     : 'sum',
            'per_capita_ghg_reduction': 'sum'})
        logging.info(f'Off-model summary:\n{off_model_tot}')

    return off_model_summary, off_model_tot

if __name__ == '__main__':

    LOG_FILE = "extract_offmodel_results_{}.log"

    # create logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel('INFO')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(ch)
    # file handlers
    fh = logging.FileHandler(LOG_FILE.format(datetime.date.today()), mode='w')
    fh.setLevel('INFO')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    LOGGER.addHandler(fh)

    # get all runs with off-model calculation
    runs_with_off_models_IP, runs_with_off_models_FBP = get_runs_with_off_model(MODELRUNS_XLSX)
    logging.info(f'IPA runs with off-model calculations:\n{runs_with_off_models_IP}')
    logging.info(f'Final Blueprint runs with off-model calculations:\n{runs_with_off_models_FBP}')

    # extract FBP off-model results
    for run in runs_with_off_models_FBP['directory']:
        run_directory = os.path.join(TM_RUN_LOCATION_BP, run)
        off_model_output_dir = os.path.join(run_directory, 'OUTPUT', 'offmodel', 'offmodel_output')
        if not os.path.exists(os.path.join(off_model_output_dir, 'off_model_summary.csv')):
            off_model_summary, off_model_tot = summarize_off_model_calculator_results(
                run_directory, 
                run,
                [BIKE_SHARE, CAR_SHARE, TARGETED_TRANS_ALT, VAN_POOL, CHARGER, VEH_BUYBACK, EBIKE]
                )
            if len(off_model_summary) > 0:
                off_model_summary.to_csv(os.path.join(run_directory, 'OUTPUT', 'offmodel', 'off_model_summary.csv'), index=False)
                off_model_tot.to_csv(os.path.join(run_directory, 'OUTPUT', 'offmodel', 'off_model_tot.csv'))
        elif not os.path.exists(off_model_output_dir):
            logging.info(f'Off-model output directory does not exist for run {run}')
        else:
            logging.info(f'Off-model summary already exists for run {run}')

    # extract IP off-model results
    for run in runs_with_off_models_IP['directory']:
        run_directory = os.path.join(TM_RUN_LOCATION_IP, run)
        off_model_output_dir = os.path.join(run_directory, 'OUTPUT', 'offmodel', 'offmodel_output')
        if not os.path.exists(os.path.join(off_model_output_dir, 'off_model_summary.csv')):
            off_model_summary, off_model_tot = summarize_off_model_calculator_results(
                run_directory, 
                run,
                [BIKE_SHARE, CAR_SHARE, TARGETED_TRANS_ALT, VAN_POOL, CHARGER, VEH_BUYBACK, EBIKE]
                )
            if len(off_model_summary) > 0:
                off_model_summary.to_csv(os.path.join(run_directory, 'OUTPUT', 'offmodel', 'off_model_summary.csv'), index=False)
                off_model_tot.to_csv(os.path.join(run_directory, 'OUTPUT', 'offmodel', 'off_model_tot.csv'))
        elif not os.path.exists(off_model_output_dir):
            logging.info(f'Off-model output directory does not exist for run {run}')
        else:
            logging.info(f'Off-model summary already exists for run {run}')