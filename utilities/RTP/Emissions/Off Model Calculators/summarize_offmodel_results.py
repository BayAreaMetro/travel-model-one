USAGE = """
Pull results from off-model calculator Excel workbooks and save summary files to Travel Model Tableau cross-run visualization folder.

Prerequisite: run update_offmodel_calculator_workbooks_with_TM_output.py (https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/Emissions/Off%20Model%20Calculators/update_offmodel_calculator_workbooks_with_TM_output.py)
to update the Excel workbooks with a set of "model data".

Example call: 
`python summarize_offmodel_results.py 2035_TM160_DBP_Plan_04 2050_TM160_DBP_Plan_04 --include_bike_share bike_share --include_car_share car_share --include_targetedTransAlt targeted_trans_alt --include_vanpools vanpools --include_evCharger regional_charger --include_vehBuyBack vehicle_buyback`

"""

import argparse, datetime, os, sys
import pandas as pd
import xlwings as xl

# calculator names

BIKE_SHARE = 'bike_share'
CAR_SHARE = 'car_share'
TARGETED_TRANS_ALT = 'targeted_trans_alt'
VAN_POOL = 'vanpools'
CHARGER = 'regional_charger'
VEH_BUYBACK = 'vehicle_buyback'
EBIKE = 'ebike'

#####################################
# inputs and outputs 
BOX_DIR = r'C:\Users\{}\Box\Plan Bay Area 2050+\Blueprint\Off-Model\PBA50+ Off-Model'.format(os.environ.get('USERNAME'))
MODEL_DATA_BOX_DIR = os.path.join(BOX_DIR, 'model_data_all')

# TODO: make directory an argument
OFF_MODEL_CALCULATOR_DIR = os.path.join(BOX_DIR, 'DBP_v2', 'PBA50+ Off-Model Calculators')
# OFF_MODEL_CALCULATOR_DIR = os.path.join(BOX_DIR, 'IPA_TM2_v2_refactor', 'PBA50+ Off-Model Calculators')
SUMMARY_M_DIR = r'M:\Application\Model One\RTP2025\Blueprint\across_runs'

# OFF_MODEL_CALCULATOR_DIR = os.path.join(BOX_DIR, 'IPA_TM2_v2_refactor', 'PBA50+ Off-Model Calculators')
# SUMMARY_M_DIR = r'M:\Application\Model One\RTP2025\IncrementalProgress\across_runs'

off_model_metrics = ['daily_vehTrip_reduction', 'daily_vmt_reduction', 'daily_ghg_reduction']

#####################################

######### get bike share strategy result    
def get_bikeshare_result(runid_2035, runid_2050):

    bikeshare_summary_all = pd.DataFrame()

    bikeshare_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_Bikeshare__{}__{}.xlsx'.format(runid_2035, runid_2050))
    print(bikeshare_wb_file)

    if os.path.exists(bikeshare_wb_file):
        bikeshare_df = pd.read_excel(
            bikeshare_wb_file,
            sheet_name='Main sheet',
            header=None
        )

        # verify the calculator name and run_id are correct
        print(bikeshare_df.iloc[0, 0] == 'Bike Share')
        print(bikeshare_df.iloc[13, 2] == runid_2035)
        print(bikeshare_df.iloc[13, 3] == runid_2050)

        # print(bikeshare_df)
        bikeshare_df = bikeshare_df.iloc[15:24, [0, 2, 3]]
        bikeshare_df.columns = ['Variable', '2035', '2050']
        print(bikeshare_df)

        for model_year in ['2035', '2050']:
            bikeshare_summary = bikeshare_df.loc[
                bikeshare_df['Variable'].isin(
                    ['Estimated daily bike share trips', 'Total daily VMT reductions', 'Total daily GHG reductions (tons)'])][['Variable', model_year]]

            bikeshare_summary = bikeshare_summary.set_index('Variable').transpose().reset_index()
            bikeshare_summary.columns = ['year'] + off_model_metrics
            bikeshare_summary['strategy'] = 'bike share'

            bikeshare_summary_all = pd.concat([bikeshare_summary_all, bikeshare_summary])
            print(bikeshare_summary_all)
    else:
        print('{} does not exist'.format(bikeshare_wb_file))

    return bikeshare_summary_all


######### get car share strategy result
def get_carshare_result(runid_2035, runid_2050):

    carshare_summary_all = pd.DataFrame()

    carshare_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_Carshare__{}__{}.xlsx'.format(runid_2035, runid_2050))
    print(carshare_wb_file)
    if os.path.exists(carshare_wb_file):
        carshare_df = pd.read_excel(
            carshare_wb_file,
            sheet_name='Main Sheet',
            header=None
        )
        # print(carshare_df)
        # verify the calculator name and run_id are correct
        print(carshare_df.iloc[0, 0] == 'Car Share')
        print(carshare_df.iloc[35, 2] == runid_2035)
        print(carshare_df.iloc[35, 3] == runid_2050)

        carshare_df = carshare_df.iloc[37:52, [0, 2, 3]]
        # print(carshare_df)
        carshare_df.columns = ['Variable', '2035', '2050']
        # print(carshare_df)

        for model_year in ['2035', '2050']:
        # for model_year in ['2050']:
            carshare_summary = carshare_df.loc[
                carshare_df['Variable'].isin(
                    ['Total daily VMT reductions from car sharing members driving less', 'Total daily GHG reductions (tons)'])][['Variable', model_year]]
            # print(carshare_summary)
            carshare_summary = carshare_summary.set_index('Variable').transpose().reset_index()
            # print(carshare_summary)
            carshare_summary.columns = ['year'] + off_model_metrics[1:]
            carshare_summary['strategy'] = 'car share'
            
            carshare_summary_all = pd.concat([carshare_summary_all, carshare_summary])
            # print(carshare_summary)
            print(carshare_summary_all)
    else:
        print('{} does not exist'.format(carshare_wb_file))

    return carshare_summary_all


######### get targeted transportaion alternative result
def get_targetedTransAlt_result(runid_2035, runid_2050):

    targetedTransAlt_summary_all = pd.DataFrame()

    targetedTransAlt_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_TargetedTransAlt__{}__{}.xlsx'.format(runid_2035, runid_2050))
    print(targetedTransAlt_wb_file)
    if os.path.exists(targetedTransAlt_wb_file):
        alternative_df = pd.read_excel(
            targetedTransAlt_wb_file,
            sheet_name='Main sheet',
            header=None
        )

        # verify the calculator name and run_id are correct
        print(alternative_df.iloc[0, 0] == 'Targeted Transportation Alternatives')
        print(alternative_df.iloc[25, 2] == runid_2035)
        print(alternative_df.iloc[25, 3] == runid_2050)

        # print(alternative_df)
        alternative_df = alternative_df.iloc[27:49, [0, 2, 3]]
        # alternative_df.dropna(axis=1, how='all', inplace=True)
        alternative_df.columns = ['Variable', '2035', '2050']
        # print(alternative_df)

        for model_year in ['2035', '2050']:
            targetedTransAlt_summary = alternative_df.loc[
                alternative_df['Variable'].isin(
                    ['Total daily vehicle trip reductions - all', 
                    'Total daily VMT reductions - all',
                    'Total daily GHG reductions (tons)'])][['Variable', model_year]]

            targetedTransAlt_summary = targetedTransAlt_summary.set_index('Variable').transpose().reset_index()
            targetedTransAlt_summary.columns = ['year'] + off_model_metrics
            targetedTransAlt_summary['strategy'] = 'targeted transportation alternative'

            targetedTransAlt_summary_all = pd.concat([targetedTransAlt_summary_all, targetedTransAlt_summary])
            # print(carshare_summary)
            print(targetedTransAlt_summary_all)
    else:
        print('{} does not exist'.format(targetedTransAlt_wb_file))

    return targetedTransAlt_summary_all


######### get vanpool result
def get_vanpool_result(runid_2035, runid_2050):

    vanpools_summary_all = pd.DataFrame()

    vanpools_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_Vanpools__{}__{}.xlsx'.format(runid_2035, runid_2050))
    print(vanpools_wb_file)
    if os.path.exists(vanpools_wb_file):
        vanpools_df = pd.read_excel(
            vanpools_wb_file,
            sheet_name='Main Sheet',
            header=None
        )

        # verify the calculator name and run_id are correct
        print(vanpools_df.iloc[0, 0] == 'Vanpool')
        print(vanpools_df.iloc[11, 2] == runid_2035)
        print(vanpools_df.iloc[11, 3] == runid_2050)

        # print(vanpools_df)
        vanpools_df = vanpools_df.iloc[13:19, [0, 2, 3]]
        vanpools_df.columns = ['Variable', '2035', '2050']
        # print(vanpools_df)

        for model_year in ['2035', '2050']:
            vanpools_summary = vanpools_df.loc[
                vanpools_df['Variable'].isin(
                    ['Total daily one-way vehicle trip reductions',
                    'Total daily VMT reductions', 
                    'Total daily GHG reductions (tons)'])][['Variable', model_year]]

            vanpools_summary = vanpools_summary.set_index('Variable').transpose().reset_index()
            vanpools_summary.columns = ['year'] + off_model_metrics
            vanpools_summary['strategy'] = 'vanpool'

            vanpools_summary_all = pd.concat([vanpools_summary_all, vanpools_summary])
            # print(carshare_summary)
            print(vanpools_summary_all)
    else:
        print('{} does not exist'.format(vanpools_wb_file))

    return vanpools_summary_all


######### get EV charger result
def get_evCharger_result():

    evCharger_summary_all = pd.DataFrame()

    evCharger_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_RegionalCharger.xlsx')
    print(evCharger_wb_file)
    if os.path.exists(evCharger_wb_file):
        evCharger_df = pd.read_excel(
            evCharger_wb_file,
            sheet_name='Main Sheet',
            header=None
        )

        # verify the calculator name
        print(evCharger_df.iloc[0, 0] == 'Regional Electric Vehicle Charger Program')

        # print(evCharger_df)
        evCharger_df = evCharger_df.iloc[32:36, [0, 2, 3]]
        print(evCharger_df)
        # evCharger_df.dropna(axis=1, how='all', inplace=True)
        evCharger_df.columns = ['Variable', '2035', '2050']
        # print(evCharger_df)

        for model_year in ['2035', '2050']:
            evCharger_summary = evCharger_df.loc[
                evCharger_df['Variable'].isin(
                    ['Total daily GHG reductions (tons)'])][['Variable', model_year]]

            evCharger_summary = evCharger_summary.set_index('Variable').transpose().reset_index()
            evCharger_summary.columns = ['year'] + off_model_metrics[2:]
            evCharger_summary['strategy'] = 'ev charger'

            evCharger_summary_all = pd.concat([evCharger_summary_all, evCharger_summary])
            # print(evCharger_summary)
            print(evCharger_summary_all)
    else:
        print('{} does not exist'.format(evCharger_wb_file))
    
    return evCharger_summary_all


######### get vehicle buyback result
def get_vehBuyBack_result():

    vehBuyBack_summary_all = pd.DataFrame()

    vehBuyBack_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_VehicleBuyback.xlsx')
    print(vehBuyBack_wb_file)
    if os.path.exists(vehBuyBack_wb_file):
        vehBuyBack_df = pd.read_excel(
            vehBuyBack_wb_file,
            sheet_name='Main Sheet',
            header=None
        )

        # verify the calculator name
        print(vehBuyBack_df.iloc[0, 0] == 'Vehicle Buyback')

        # print(vehBuyBack_df)
        vehBuyBack_df = vehBuyBack_df.iloc[22:25, [0, 2, 3]]
        print(vehBuyBack_df)
        vehBuyBack_df.columns = ['Variable', '2035', '2050']
        # print(vehBuyBack_df)

        for model_year in ['2035', '2050']:
            vehBuyBack_summary = vehBuyBack_df.loc[
                vehBuyBack_df['Variable'].isin(
                    ['Total daily GHG reductions (tons)'])][['Variable', model_year]]

            vehBuyBack_summary = vehBuyBack_summary.set_index('Variable').transpose().reset_index()
            vehBuyBack_summary.columns = ['year'] + off_model_metrics[2:]
            vehBuyBack_summary['strategy'] = 'vehicle buy back'

            vehBuyBack_summary_all = pd.concat([vehBuyBack_summary_all, vehBuyBack_summary])
            # print(vehBuyBack_summary)
            print(vehBuyBack_summary_all)
    else:
        print('{} does not exist'.format(vehBuyBack_wb_file))
    
    return vehBuyBack_summary_all

######### get e-bike result
def get_ebike_result():

    ebike_summary_all = pd.DataFrame()

    ebike_wb_file = os.path.join(OFF_MODEL_CALCULATOR_DIR, 'PBA50+_OffModel_Ebike.xlsx')
    print(ebike_wb_file)
    if os.path.exists(ebike_wb_file):
        ebike_df = pd.read_excel(
            ebike_wb_file,
            sheet_name='Main sheet',
            header=None
        )

        # verify the calculator name
        print(ebike_df.iloc[0, 0] == 'Electric Bicycle Rebates')

        # print(ebike_df)
        ebike_df = ebike_df.iloc[23:26, [0, 2, 3]]
        print(ebike_df)
        ebike_df.columns = ['Variable', '2035', '2050']
        # print(ebike_df)

        for model_year in ['2035', '2050']:
            ebike_summary = ebike_df.loc[
                ebike_df['Variable'].isin(
                    ['Total daily VMT reductions', 'Total daily GHG reductions (tons)'])][['Variable', model_year]]

            ebike_summary = ebike_summary.set_index('Variable').transpose().reset_index()
            ebike_summary.columns = ['year'] + off_model_metrics[1:]
            ebike_summary['strategy'] = 'electric bike rebates'

            ebike_summary_all = pd.concat([ebike_summary_all, ebike_summary])
            # print(ebike_summary)
            print(ebike_summary_all)
    else:
        print('{} does not exist'.format(ebike_wb_file))
    
    return ebike_summary_all

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=USAGE)
    
    parser.add_argument('model_run_id_2035', help='travel model run_id of a 2035 run')
    parser.add_argument('model_run_id_2050', help='travel model run_id of a 2050 run')

    parser.add_argument('--include_bike_share', required=False, help='whether to include bike share calculation')
    parser.add_argument('--include_car_share', required=False, help='whether to include car share calculation')
    parser.add_argument('--include_targetedTransAlt', required=False, help='whether to include targeted transportation alternative calculation')
    parser.add_argument('--include_vanpools', required=False, help='whether to include vanpools calculation')
    parser.add_argument('--include_evCharger', required=False, help='whether to include ev charger calculation')
    parser.add_argument('--include_vehBuyBack', required=False, help='whether to include vehicle buy back calculation')
    parser.add_argument('--include_ebike', required=False, help='whether to include e-bike calculation')
    

    args = parser.parse_args()

    # TODO: add logging

    modelrun_2035 = args.model_run_id_2035
    modelrun_2050 = args.model_run_id_2050
    print('model runs to include: {}, {}'.format(modelrun_2035, modelrun_2050))

    strategies_to_include = []

    if args.include_bike_share == BIKE_SHARE:
        bikeshare_result = get_bikeshare_result(modelrun_2035, modelrun_2050)
        strategies_to_include.append(bikeshare_result)

    if args.include_car_share == CAR_SHARE:
        carshare_result = get_carshare_result(modelrun_2035, modelrun_2050)
        strategies_to_include.append(carshare_result)

    if args.include_targetedTransAlt == TARGETED_TRANS_ALT:
        targetedTransAlt_result = get_targetedTransAlt_result(modelrun_2035, modelrun_2050)
        strategies_to_include.append(targetedTransAlt_result)

    if args.include_vanpools == VAN_POOL:
        vanpools_result = get_vanpool_result(modelrun_2035, modelrun_2050)
        strategies_to_include.append(vanpools_result)
    
    if args.include_evCharger == CHARGER:
        evCharger_result = get_evCharger_result()
        strategies_to_include.append(evCharger_result)

    if args.include_vehBuyBack == VEH_BUYBACK:
        vehBuyBack_result = get_vehBuyBack_result()
        strategies_to_include.append(vehBuyBack_result)
    
    if args.include_ebike == EBIKE:
        ebike_result = get_ebike_result()
        strategies_to_include.append(ebike_result)

    off_model_summary = pd.concat(strategies_to_include)

    # print(off_model_summary)

    if len(off_model_summary) > 0:

        off_model_summary.loc[off_model_summary['year'] == '2035', 'directory'] = modelrun_2035
        off_model_summary.loc[off_model_summary['year'] == '2050', 'directory'] = modelrun_2050
        print(off_model_summary)
        off_model_summary_allStrategies = off_model_summary.groupby('directory').agg({
            'year': 'min',
            'daily_vehTrip_reduction': 'sum',
            'daily_vmt_reduction': 'sum',
            'daily_ghg_reduction': 'sum'})
        print(off_model_summary_allStrategies)
        
        # write out all-strategies summary 
        off_model_summary_allStrategies.loc[off_model_summary_allStrategies['year'] == '2035'].to_csv(
            os.path.join(SUMMARY_M_DIR, 'off_model_tot_{}.csv'.format(modelrun_2035)))
        off_model_summary_allStrategies.loc[off_model_summary_allStrategies['year'] == '2050'].to_csv(
            os.path.join(SUMMARY_M_DIR, 'off_model_tot_{}.csv'.format(modelrun_2050)))

        # write out summary by strategy
        off_model_summary.loc[off_model_summary['year'] == '2035'].to_csv(
            os.path.join(SUMMARY_M_DIR, 'off_model_summary_by_strategy_{}.csv'.format(modelrun_2035)), index=False)
        off_model_summary.loc[off_model_summary['year'] == '2050'].to_csv(
            os.path.join(SUMMARY_M_DIR, 'off_model_summary_by_strategy_{}.csv'.format(modelrun_2050)), index=False)