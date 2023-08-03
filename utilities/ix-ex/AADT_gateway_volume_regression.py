import pandas as pd
import numpy as np
import xlrd
from openpyxl import load_workbook
from sklearn.linear_model import LinearRegression
import os, sys, time, logging

# get date for the logging file
today = time.strftime("%Y_%m_%d")

# I/O
WORKING_DIR = r"C:\Users\ywang\Box\Plan Bay Area 2050+\Federal and State Approvals\CARB Technical Methodology\Exogenous Forces\gateway_traffic_vol"
GATEWAY_AADT_DATA_FILE = os.path.join(WORKING_DIR, "aadt_data_cleanup.xlsx")
GATEWAY_AADT_TAB = "5_aadt_annual"
GATEWAY_AADT_3YR_AVG_TAB = "6_aadt_3YR_moving_avg"

GATEWAY_AADT_FORECAST_FILE = os.path.join(WORKING_DIR, "Interregional Volumes pba50+_v1_cp.xlsx")
LOG_FILE = os.path.join(WORKING_DIR, "aadt_regression_{}.log".format(today))

# set up logging
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')
# console handler
ch = logging.StreamHandler()
ch.setLevel('INFO')
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
logger.addHandler(ch)
# file handler
fh = logging.FileHandler(LOG_FILE, mode='w')
fh.setLevel('DEBUG')
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
logger.addHandler(fh)



def run_regression_and_write_to_excel(raw_data_type, regression_sheet_name):

    aadt_df = pd.read_excel(open(GATEWAY_AADT_DATA_FILE, 'rb'), sheet_name=raw_data_type)
    logger.info(
        "loaded raw AADT data: \n Including {} gateways: \n{}\n including years: {}".format(
            aadt_df['Gateway'].nunique(),
            aadt_df['Gateway'].unique(),
            list(aadt_df)[7:]
        ))

    # create a dictionary to store key model attributes, and a dictionary to store predictions
    regression_model_dict = {}
    regression_pred_dict = {}

    for row_num in range(aadt_df.shape[0]):
        gateway_name = aadt_df.iloc[row_num, 0]

        # if gateway_name == 'U.S. Route 101 (Sonoma)':

        logger.info("linear regression for {}".format(gateway_name))

        # run linear regression with Year as x and AADT as y
        x = np.array(list(aadt_df)[7:]).reshape((-1, 1))
        y = np.array(list(aadt_df.iloc[row_num, 7:]))
        model = LinearRegression().fit(x,y)
        r_sq = model.score(x, y)
        intercept = model.intercept_
        coefficient = model.coef_[0]
        reg_equation = "AADT = " + str(coefficient) + " * Year + " + str(intercept)
        logger.info("regression: {}; R-square: {}".format(reg_equation, r_sq))

        # save the results to the regression_model_dict
        regression_model_dict[gateway_name] = [reg_equation, coefficient, intercept, r_sq]

        # calculate corresponding predicted responses
        aadt_pred = model.intercept_ + model.coef_ * x.reshape(-1)

        # predict aadt for 2022-2050
        x_new = np.arange(2022, 2051).reshape((-1, 1))
        y_new = model.predict(x_new)

        # add to dictionary
        regression_pred_dict[gateway_name] = list(aadt_pred) + list(y_new)


    # format regression_model_dict into a dataframe
    regression_models = pd.DataFrame.from_dict(regression_model_dict, orient ='index').reset_index()
    regression_models.columns = ['Gateway', 'Regression', 'Coefficient', 'Intercept', 'R-square']
    logger.info('regression model df has {} rows'.format(regression_models.shape[0]))

    # format prediction into a dataframe
    regression_preds = pd.DataFrame.from_dict(regression_pred_dict, orient ='index').reset_index()
    regression_preds.columns = ['Gateway'] + list(aadt_df)[7:] + list(range(2022, 2051))
    logger.info('regression predictions has {} rows'.format(regression_preds.shape[0]))

    # put together
    regression_summary = regression_models.merge(regression_preds, on='Gateway', how='inner')
    logger.info('regression summary df has {} rows'.format(regression_summary.shape[0]))

    # also add abserved data

    # write to gateway vol forecast workbook
    book = load_workbook(GATEWAY_AADT_FORECAST_FILE)
    writer = pd.ExcelWriter(GATEWAY_AADT_FORECAST_FILE, engine = 'openpyxl')
    writer.book = book

    regression_summary.to_excel(writer, sheet_name = regression_sheet_name)
    writer.close()


# do two regression runs based on two aadt input data types:
regression_runs = {GATEWAY_AADT_TAB: 'reg_based_on_annual_aadt',
                   GATEWAY_AADT_3YR_AVG_TAB: 'reg_based_on_3YrAvg_aadt'}


for raw_aadt_data_type in regression_runs:
    logger.info('run regression based on {}'.format(raw_aadt_data_type))
    run_regression_and_write_to_excel(raw_aadt_data_type, regression_runs[raw_aadt_data_type])