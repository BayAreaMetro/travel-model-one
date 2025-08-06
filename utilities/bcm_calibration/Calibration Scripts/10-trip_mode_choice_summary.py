import pandas as pd
import numpy as np
import os
import xlsxwriter

import math 

import argparse

#Set Directory
parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")

args = parser.parse_args()

model_results=args.run_name

set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/09_TripsSummary/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)


indiv_trip_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTripData_1.csv'))
calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'TripsbyTripMode_Targets.csv'))

distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
distance_skim = distance_skim[(distance_skim['dist'].notnull())&(distance_skim['dist']<10000)]

trip_mode_dict={1:'Drive Alone',
                2:'Drive Alone',
                3:'Shared Ride 2',
                4:'Shared Ride 2',
                5:'Shared Ride 3+',
                6:'Shared Ride 3+',
                7:'Walk',
                8:'Bike',
                9:'Walk-Bus',
                10:'Walk-LRT',
                11:'Walk-Bus',
                12:'Walk-UR',
                13:'Walk-CR',
                14:'PNR-Bus',
                15:'PNR-LRT',
                16:'PNR-Bus',
                17:'PNR-UR',
                18:'PNR-CR',
                19:'Taxi',
                20:'TNC',
                21:'TNC-Shared'}

calib_mode_dict={'Auto SOV (Free)            ':'Drive Alone',
                'Auto 2 Person (Free)       ':'Shared Ride 2',
                'Auto 3+ Person (Free)      ':'Shared Ride 3+',
                'Walk':'Walk',
                'Bike/Moped':'Bike',
                'Walk-Bus':'Walk-Bus',
                'Walk-BRT/Streetcar':'Walk-Bus',
                'Walk-LRT':'Walk-LRT',
                'Walk-UR':'Walk-UR',
                'Walk-CR':'Walk-CR',
                'PNR-Bus':'PNR-Bus',
                'PNR-LRT':'PNR-LRT',
                'PNR-Bus':'PNR-Bus',
                'PNR-BRT/Streetcar':'PNR-Bus',
                'PNR-UR':'PNR-UR',
                'PNR-CR':'PNR-CR',
                'Taxi/Shuttle':'Taxi',
                'KNR-Bus':'Other',
                'KNR-LRT':'Other',
                'KNR-Bus':'Other',
                'KNR-UR':'Other',
                'KNR-CR':'Other',
                'School Bus':'Other',
                'Other':'Other',
                }

indiv_trip_df['dimension_01_value']=indiv_trip_df['trip_mode'].map(trip_mode_dict)

trip_mode=indiv_trip_df.groupby(['dimension_01_value']).agg(total_trips=('dimension_01_value','count'))
trip_mode['Total']=trip_mode.total_trips.sum()
trip_mode[model_results]=trip_mode['total_trips']/trip_mode['Total']
trip_mode=trip_mode.reset_index()[['dimension_01_value',model_results]]

calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'TripsbyTripMode_Targets.csv'))
calib_target['dimension_01_value']=calib_target['dimension_01_value'].map(calib_mode_dict)
calib_target_grouped=calib_target.groupby(['dimension_01_name','dimension_01_value']).agg(trips=('estimate_value','sum'))
calib_target_grouped['Total']=calib_target_grouped['trips'].sum()
calib_target_grouped['Target']=calib_target_grouped['trips']/calib_target_grouped['Total']
#calib_target=calib_target[['estimate','dimension_01_name','dimension_01_value','Target']]
calib_target_grouped=calib_target_grouped.reset_index()[['dimension_01_name','dimension_01_value','Target']]

comparison_df=pd.merge(calib_target_grouped,trip_mode, on='dimension_01_value', how='outer')


writer = pd.ExcelWriter(os.path.join(set_output_dir,'TripModeChoiceSummary.xlsx'), engine='xlsxwriter')
comparison_df.to_excel(writer, sheet_name='All', startrow=1, header=False, index=False)

workbook  = writer.book
worksheet = writer.sheets['All']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = comparison_df.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(comparison_df.columns.values):
    worksheet.write(0, col_num, value, header_format)

writer.save()
