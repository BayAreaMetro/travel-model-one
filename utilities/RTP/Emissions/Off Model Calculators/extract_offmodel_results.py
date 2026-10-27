USAGE = """
Pull results from off-model calculator Excel workbooks and save summary files to Travel Model Tableau cross-run visualization folder.

Prerequisite: off model calculator workbooks for a given run has been generated via run_offmodel_calculators.py
(https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/Emissions/Off%20Model%20Calculators/run_offmodel_calculators.py).

Example call:
`python extract_offmodel_results.py ModelRuns.xlsx`

"""

import argparse
import datetime
import logging
import pathlib
import pandas as pd
import xlwings as xl

LOG_FILE = "extract_offmodel_results_{}.log"

# create logger
LOGGER = logging.getLogger(__name__)

#####################################
RUN_LOCATIONS = {
    'RTP2025_IP':           pathlib.Path(r'M:\Application\Model One\RTP2025\IncrementalProgress'),
    'RTP2025':              pathlib.Path(r'M:\Application\Model One\RTP2025\Blueprint'),
    'RTP2030StrategyEval':  pathlib.Path(r'M:\Application\Model One\RTP2030\StrategyEvaluation'),
}

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
    excel_workbook = excel_app.books.open(str(wb_file))
    excel_workbook.save()
    excel_workbook.close()
    excel_app.quit()
    LOGGER.info(f'Workbook {wb_file} refreshed')

def get_runs_with_off_model(modelruns_xlsx):
    """
    Get the model runs that have off-model calculator workbooks generated.
    """
    LOGGER.info('Reading modelruns xlsx file: {}'.format(modelruns_xlsx))
    modelruns_df = pd.read_excel(modelruns_xlsx)
    modelruns_df = modelruns_df[['directory','year','run_offmodel','run_set']]
    modelruns_df = modelruns_df.loc[modelruns_df['run_offmodel'].notnull()]
    LOGGER.info('modelruns off_model run tally:\n{}'.format(modelruns_df['run_offmodel'].value_counts()))
    return modelruns_df

def extract_off_model_calculator_result(run_directory, run_id, calculator_name):
    """
    Extract the result from one off-model calculator workbook.
    """
    off_model_output_dir = pathlib.Path(run_directory) / 'OUTPUT' / 'offmodel' / 'offmodel_output'
    
    # for calculator_name in calculator_names:
    off_model_wb = off_model_output_dir / f'PBA50+_OffModel_{calculator_name}__{run_id}.xlsx'

    if not off_model_wb.exists():
        LOGGER.info(f'Workbook {off_model_wb} does not exist')
        return None
    else:
        refresh_excelworkbook(off_model_wb)
        off_model_df = pd.read_excel(off_model_wb, sheet_name='Output', skiprows=1)
        year = run_id[:4]
        extract_cols = {
            'Horizon Run ID': 'directory',
            f'Out_daily_GHG_reduced_{year}': 'daily_ghg_reduction',
            f'Out_per_capita_GHG_reduced_{year}': 'per_capita_ghg_reduction'
        }
        vmt_col = f'Out_daily_VMT_reduced_{year}'
        if vmt_col in off_model_df.columns:
            extract_cols[vmt_col] = 'daily_vmt_reduction'
       
        off_model_df = off_model_df[list(extract_cols.keys())].rename(columns=extract_cols)

        # Keep output schema consistent across all calculators
        if 'daily_vmt_reduction' not in off_model_df.columns:
            off_model_df['daily_vmt_reduction'] = 0
        
        off_model_df['offmodel_strategy'] = calculator_name
        return off_model_df

def summarize_off_model_calculator_results(run_directory, run_id, calculator_names_list):
    """
    Extract and summarize off-model results from all calculators for a given run.
    """
    all_calculators_results = []
    for name in calculator_names_list:
        LOGGER.info(f'Extracting {name} results for run {run_id}')
        calculator_result = extract_off_model_calculator_result(run_directory, run_id, name)
        if calculator_result is not None:
            all_calculators_results.append(calculator_result)

    if len(all_calculators_results) == 0:
        off_model_summary = pd.DataFrame()
    else:
        off_model_summary = pd.concat(all_calculators_results)
    LOGGER.info(f'Completed for run {run_id}, Off-model summary:\n{off_model_summary}')

    off_model_tot = None
    if len(off_model_summary) > 0:
        off_model_tot = off_model_summary.groupby('directory').agg({
            'daily_ghg_reduction'     : 'sum',
            'per_capita_ghg_reduction': 'sum',
            'daily_vmt_reduction'     : 'sum'
            })
        LOGGER.info(f'Off-model summary:\n{off_model_tot}')

    return off_model_summary, off_model_tot

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument("modelruns_xlsx", help="Path to ModelRuns.xlsx")
    args = parser.parse_args()

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
    runs_with_off_models = get_runs_with_off_model(args.modelruns_xlsx)
    LOGGER.info(f'Runs with off-model calculations:\n{runs_with_off_models}')
    calculator_names = [
        BIKE_SHARE, CAR_SHARE, TARGETED_TRANS_ALT, VAN_POOL,
        CHARGER, VEH_BUYBACK, EBIKE,
    ]

    for model_run in runs_with_off_models.itertuples(index=False):
        run = model_run.directory
        run_location = RUN_LOCATIONS.get(model_run.run_set)
        if run_location is None:
            LOGGER.warning(
                f'run_set value {model_run.run_set} has no off-model run location; skipping run {run}'
            )
            continue
        run_directory = run_location / run

        off_model_output_dir = run_directory / 'OUTPUT' / 'offmodel' / 'offmodel_output'
        summary_file = off_model_output_dir / 'off_model_summary_withVMT.csv'
        totals_file = run_directory / 'OUTPUT' / 'offmodel' / 'off_model_tot_withVMT.csv'
        if not off_model_output_dir.exists():
            LOGGER.info(f'Off-model output directory {off_model_output_dir} does not exist for run {run}')
        elif summary_file.exists() and totals_file.exists():
            LOGGER.info(f'Off-model summary and totals already exist for run {run}')
        else:
            off_model_summary, off_model_tot = summarize_off_model_calculator_results(
                run_directory,
                run,
                calculator_names,
            )
            if len(off_model_summary) > 0:
                if not summary_file.exists():
                    off_model_summary.to_csv(summary_file, index=False)
                if not totals_file.exists():
                    off_model_tot.to_csv(totals_file)
