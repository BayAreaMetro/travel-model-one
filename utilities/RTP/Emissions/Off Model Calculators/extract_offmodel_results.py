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

LOG_FILE = "extract_offmodel_results_{}.log"

# create logger
LOGGER = logging.getLogger(__name__)

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
    LOGGER.info(f'Workbook {wb_file} refreshed')

def get_runs_with_off_model(modelruns_xlsx):
    """
    Get the model runs that have off-model calculator workbooks generated.
    """
    LOGGER.info('Reading modelruns xlsx file: {}'.format(modelruns_xlsx))
    modelruns_df = pd.read_excel(modelruns_xlsx)
    modelruns_df = modelruns_df[['directory','year','run_offmodel']]
    LOGGER.info('modelruns off_model run tally:\n{}'.format(modelruns_df['run_offmodel'].value_counts()))
    modelruns_with_off_model_IP = modelruns_df.loc[modelruns_df['run_offmodel']=='IP']
    modelruns_with_off_model_FBP = modelruns_df.loc[modelruns_df['run_offmodel']=='FBP']
    return modelruns_with_off_model_IP, modelruns_with_off_model_FBP

def read_output_data(off_model_wb, run_id, output_tab_name='Output_test'):
    """
    Read output data from Excel workbook.
    Supports vertical format (Output_test/Output tab with Sheet, Variable Name, Value, Location columns).
    Returns DataFrame in horizontal format for compatibility with existing pipeline.

    Args:
        off_model_wb: Path to Excel workbook
        run_id: Model run ID (e.g., '2035_TM160_IPA_16')
        output_tab_name: Name of output tab to read from (default: 'Output_test')

    Returns:
        DataFrame with columns: Horizon Run ID, Out_daily_GHG_reduced_{year}, Out_per_capita_GHG_reduced_{year}
    """
    year = run_id[:4]

    # Read vertical format from Output tab
    df = pd.read_excel(off_model_wb, sheet_name=output_tab_name)
    print("Read first 15 rows from {} tab:\n{}".format(output_tab_name, df.head(15)))
    print("")
    # Filter for output variables (those starting with 'Out_')
    # In the Output_test tab, output variables are identified by their variable name, not by Sheet column
    output_vars = df[df['Variable Name'].str.startswith('Out_', na=False)].copy()

    # Get year-specific variables
    year_suffix = f'_{year}'
    output_vars_year = output_vars[output_vars['Variable Name'].str.endswith(year_suffix)]

    # Create lookup dictionary: variable_name -> value
    var_lookup = dict(zip(output_vars_year['Variable Name'], output_vars_year['Value']))

    # Extract specific variables
    daily_ghg_key = f'Out_daily_GHG_reduced_{year}'
    per_capita_ghg_key = f'Out_per_capita_GHG_reduced_{year}'

    # Reshape to horizontal format (same structure as old Output tab)
    result_df = pd.DataFrame({
        'Horizon Run ID': [run_id],
        f'Out_daily_GHG_reduced_{year}': [var_lookup.get(daily_ghg_key, None)],
        f'Out_per_capita_GHG_reduced_{year}': [var_lookup.get(per_capita_ghg_key, None)]
    })

    # Log warnings if variables are missing
    if daily_ghg_key not in var_lookup:
        LOGGER.warning(f'Variable {daily_ghg_key} not found in {output_tab_name} tab')
    if per_capita_ghg_key not in var_lookup:
        LOGGER.warning(f'Variable {per_capita_ghg_key} not found in {output_tab_name} tab')

    return result_df

def extract_off_model_calculator_result(run_directory, run_id, calculator_name):
    """
    Extract the result from one off-model calculator workbook.
    """
    off_model_output_dir = os.path.join(
        run_directory, 'OUTPUT', 'offmodel', 'offmodel_output')

    # for calculator_name in calculator_names:
    off_model_wb = os.path.join(off_model_output_dir, 'PBA50+_OffModel_{}__{}.xlsx'.format(calculator_name, run_id))

    if not os.path.exists(off_model_wb):
        LOGGER.info(f'Workbook {off_model_wb} does not exist')
        return None
    else:
        refresh_excelworkbook(off_model_wb)

        # Read from vertical format Output_test tab (will be renamed to 'Output' after migration)
        # TODO: Change 'Output_test' to 'Output' after Excel tab is renamed
        off_model_df = read_output_data(off_model_wb, run_id, output_tab_name='Output_test')

        # Rename columns to match expected format
        off_model_df.rename(
            columns={'Horizon Run ID': 'directory',
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
            'per_capita_ghg_reduction': 'sum'})
        LOGGER.info(f'Off-model summary:\n{off_model_tot}')

    return off_model_summary, off_model_tot

if __name__ == '__main__':
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
    LOGGER.info(f'IPA runs with off-model calculations:\n{runs_with_off_models_IP}')
    LOGGER.info(f'Final Blueprint runs with off-model calculations:\n{runs_with_off_models_FBP}')

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
            LOGGER.info(f'Off-model output directory does not exist for run {run}')
        else:
            LOGGER.info(f'Off-model summary already exists for run {run}')

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
            LOGGER.info(f'Off-model output directory does not exist for run {run}')
        else:
            LOGGER.info(f'Off-model summary already exists for run {run}')
