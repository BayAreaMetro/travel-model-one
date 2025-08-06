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

#Set Directory
set_model_result_dir = model_results+'/'
set_calibration_target_dir='Calibration Targets/'
set_output_dir = 'calibration_output/'+model_results+'/09_TripsSummary/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)


indiv_trip_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTripData_1.csv'))
calib_target = pd.read_csv(os.path.join(set_calibration_target_dir, 'TripsbyTourModeandTripMode_Targets.csv'))

distance_skim = pd.read_csv(os.path.join(set_model_result_dir, 'da_am_skims.csv'))
distance_skim = distance_skim[(distance_skim['dist'].notnull())&(distance_skim['dist']<10000)]

def tour_purpose_category(x):
    if x in ['work_med', 'work_very high', 'work_high','work_low']:
        return 'Work'
    elif x in ['school_grade','school_high']:
        return 'School'
    elif x in ['atwork_eat','atwork_maint','atwork_business']:
        return 'At-Work'
    elif x == 'shopping':
        return 'Shopping'
    elif x in ['escort_no kids','escort_kids']:
        return 'Escorting'
    elif x=='university':
        return 'University'
    elif x=='eatout':
        return 'Eat Out'
    elif x=='social':
        return 'Social'
    elif x=='othdiscr':
        return 'Discretionary'
    elif x=='othmaint':
        return 'Maintenance'
    else:
        return None

def time_period(x):
    if x<7:
        return 'EA'
    elif x<11:
        return 'AM'
    elif x<16:
        return 'MD'
    elif x<20:
        return 'PM'
    else:
        return 'EV'

tour_mode_dict={1:'Drive Alone',
                2:'Drive Alone',
                3:'Shared 2 Free',
                4:'Shared 2 Free',
                5:'Shared 3 Free',
                6:'Shared 3 Free',
                7:'Walk',
                8:'Bike',
                9:'Walk-Transit',
                10:'Walk-Transit',
                11:'Walk-Transit',
                12:'Walk-Transit',
                13:'Walk-Transit',
                14:'PNR-Transit',
                15:'PNR-Transit',
                16:'PNR-Transit',
                17:'PNR-Transit',
                18:'PNR-Transit',
                19:'Taxi',
                20:'TNC',
                21:'TNC-Shared'}

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

indiv_trip_df['dimension_01_value']=indiv_trip_df['tour_mode'].map(tour_mode_dict)
indiv_trip_df['dimension_02_value']=indiv_trip_df['trip_mode'].map(trip_mode_dict)
indiv_trip_df['TimePeriod']=indiv_trip_df['depart_hour'].apply(time_period)
indiv_trip_df['Tour Purpose']=indiv_trip_df['tour_purpose'].apply(tour_purpose_category)

indiv_trip_df=indiv_trip_df[indiv_trip_df['orig_taz']!=indiv_trip_df['dest_taz']]

trip_lengths=indiv_trip_df.merge(distance_skim[['origin','destination','dist']],
                                    how='left',
                                    left_on=['orig_taz','dest_taz'],
                                    right_on=['origin','destination'])[['hh_id', 'person_id', 'person_num', 'tour_id', 'orig_purpose', 'dest_purpose', 'orig_taz', 'dest_taz',
                                                                        'depart_hour', 'trip_mode', 'tour_mode', 'tour_category',
                                                                        'dimension_01_value', 'dimension_02_value', 'TimePeriod',
                                                                        'Tour Purpose', 'dist']]

length_by_purpose = trip_lengths.groupby(['Tour Purpose','dimension_02_value']).agg(Trips=('dist','mean')).reset_index()
length_by_purpose['estimate']='By Tour Purpose and Trip Mode'

length_by_trip_mode = trip_lengths.groupby(['dimension_02_value']).agg(Trips=('dist','mean')).reset_index()
length_by_trip_mode['estimate']='By Trip Mode'

length_by_timeperiod = trip_lengths.groupby(['TimePeriod']).agg(Trips=('dist','mean')).reset_index()
length_by_timeperiod['estimate']='By Time Period'


trip_length_df=pd.concat([length_by_purpose,length_by_trip_mode,length_by_timeperiod])
trip_length_df=trip_length_df[['estimate','Tour Purpose','TimePeriod','dimension_02_value','Trips']]


time_period_summary_df= indiv_trip_df.groupby(['TimePeriod','dimension_02_value']).agg(Trips=('dimension_02_value', 'count')).reset_index()
time_period_summary_df_wide=time_period_summary_df.pivot(index=['TimePeriod'], columns=['dimension_02_value'], values='Trips')
time_period_summary_df_wide=time_period_summary_df_wide[['Drive Alone','Shared Ride 2','Shared Ride 3+', 
                    'Walk','Bike', 
                    'Walk-Bus', 'Walk-LRT', 'Walk-UR', 'Walk-CR',
                    'PNR-Bus','PNR-LRT',  'PNR-UR', 'PNR-CR','Taxi','TNC','TNC-Shared']]

calib_target['dimension_02_value']=calib_target['dimension_02_value'].fillna('Other')
calib_target['dimension_02_value']=calib_target['dimension_02_value'].map(calib_mode_dict)

calib_target['Tour Purpose']=calib_target['estimate'].apply(lambda x: x.split(' trips by ')[0].split(' of ')[1])
calib_target['Tour Purpose']=np.where(calib_target['Tour Purpose']=='Social/Visit',
                                      'Social',
                                      calib_target['Tour Purpose'])
calib_target=calib_target.rename(columns={'estimate_value':'Target'})
trip_df_grouped=indiv_trip_df.groupby(['Tour Purpose','dimension_01_value','dimension_02_value']).agg(Total_Trips=('dimension_02_value', 'count')).reset_index()

trip_df_grouped['Total_Level_01_02']= trip_df_grouped.groupby(['Tour Purpose','dimension_01_value'])['Total_Trips'].transform(sum)
trip_df_grouped['Model']=trip_df_grouped['Total_Trips']/trip_df_grouped['Total_Level_01_02']


trip_df_by_purpose_grouped=indiv_trip_df.groupby(['Tour Purpose','dimension_02_value']).agg(Trips=('dimension_02_value', 'count')).reset_index()

trip_df_by_purpose_grouped_wide=trip_df_by_purpose_grouped.pivot(index=['Tour Purpose'], columns=['dimension_02_value'], values='Trips')
trip_df_by_purpose_grouped_wide=trip_df_by_purpose_grouped_wide[['Drive Alone','Shared Ride 2','Shared Ride 3+', 
                    'Walk','Bike', 
                    'Walk-Bus', 'Walk-LRT', 'Walk-UR', 'Walk-CR',
                    'PNR-Bus','PNR-LRT',  'PNR-UR', 'PNR-CR','Taxi','TNC','TNC-Shared']]


comparison_df=pd.merge(calib_target,
                        trip_df_grouped[['Tour Purpose','dimension_01_value','dimension_02_value','Model']],
                        on=['Tour Purpose','dimension_01_value','dimension_02_value'], how='outer').fillna(0)

comparison_df['dimension_01_name']='Tour Mode'
comparison_df['dimension_02_name']='Trip Mode'
comparison_df['estimate_name']='Share of Trips'

comparison_df=comparison_df[['Tour Purpose','dimension_01_name','dimension_01_value','dimension_02_name','dimension_02_value','estimate_name','Target','Model']]

tour_purpose_sorter = [ 'Work','School', 'University', 'Discretionary', 'Eat Out', 'Escorting', 'Maintenance','At-Work','Shopping', 'Social']
tour_mode_sorter = ['Drive Alone', 'Shared 2 Free','Shared 3 Free','Walk', 'Bike', 'Walk-Transit','PNR-Transit',  'KNR-Transit','School Bus', 'Taxi', 'TNC', 'TNC-Shared','Other']
trip_mode_sorter = ['Drive Alone','Shared Ride 2','Shared Ride 3+', 
                    'Walk','Bike', 
                    'Walk-Bus', 'Walk-LRT', 'Walk-UR', 'Walk-CR',
                    'PNR-Bus','PNR-LRT',  'PNR-UR', 'PNR-CR','Taxi','TNC','TNC-Shared','Other' ]

tour_purpose_sorterIndex = dict(zip(tour_purpose_sorter, range(len(tour_purpose_sorter))))
tour_mode_sorterIndex = dict(zip(tour_mode_sorter, range(len(tour_mode_sorter))))
trip_mode_sorterIndex = dict(zip(trip_mode_sorter, range(len(trip_mode_sorter))))


geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))

taz_county_dict=dict(zip(geo_crosswalk['TAZ'], geo_crosswalk['COUNTYNAME']))

indiv_trip_df['trip_id']=indiv_trip_df.index+1
indiv_trip_df['origin_county']=indiv_trip_df['orig_taz'].map(taz_county_dict)
indiv_trip_df['destination_county'] = indiv_trip_df['dest_taz'].map(taz_county_dict)


trip_modes=['Drive Alone','Shared Ride 2','Shared Ride 3+', 
                    'Walk','Bike', 
                    'Walk-Bus', 'Walk-LRT', 'Walk-UR', 'Walk-CR',
                    'PNR-Bus','PNR-LRT',  'PNR-UR', 'PNR-CR','Taxi','TNC','TNC-Shared']

vehicle_trips=['Drive Alone','Shared Ride 2','Shared Ride 3+', 
                    'Taxi','TNC','TNC-Shared']

trip_weight = {'Drive Alone':1,'Shared Ride 2':0.5,'Shared Ride 3+':0.3, 
                    'Taxi':1,'TNC':1,'TNC-Shared':1}  

person_trips_c_c_flow= pd.crosstab(indiv_trip_df['origin_county'],
                                    indiv_trip_df['destination_county'], 
                                    values=indiv_trip_df['trip_id'], 
                                    aggfunc='count')

vehicle_trips=indiv_trip_df[indiv_trip_df['dimension_02_value'].isin(vehicle_trips)]
vehicle_trips['trip_weight']=vehicle_trips['dimension_02_value'].map(trip_weight)

vehicle_trips_c_c_flow= pd.crosstab(vehicle_trips['origin_county'],
                            vehicle_trips['destination_county'], 
                            values=vehicle_trips['trip_weight'], 
                            aggfunc='sum')




comparison_wide = comparison_df.groupby(['Tour Purpose',
                                         'dimension_01_name',
                                         'dimension_01_value',
                                         'dimension_02_value']).agg({'Target':'mean',
                                                                     'Model':'mean'}).reset_index().pivot(index=['Tour Purpose',
                                                                                                                 'dimension_01_name',
                                                                                                                 'dimension_01_value'],
                                                                                                          columns=['dimension_02_value'], 
                                                                                                          values=['Target','Model']).reset_index()

comparison_wide=comparison_wide.sort_values(by='Tour Purpose',
                                            key=lambda x: x.map(tour_purpose_sorterIndex))

all_dfs={}

for tour in comparison_wide['Tour Purpose'].unique():

    _df = comparison_wide[comparison_wide['Tour Purpose']==tour]

    _df=_df.sort_values(by='dimension_01_value',key=lambda x: x.map(tour_mode_sorterIndex))

    all_dfs[tour] = _df

all_df_concat=pd.concat(all_dfs)

all_df_concat=all_df_concat[[(      'Tour Purpose',               ''),
                             ( 'dimension_01_name',               ''),
                             ('dimension_01_value',               ''),
                             (            'Target',    'Drive Alone'),
                             (            'Target',  'Shared Ride 2'),
                             (            'Target', 'Shared Ride 3+'),
                            (            'Target',           'Walk'),
                            (            'Target',           'Bike'),
                            (            'Target',       'Walk-Bus'),
                            (            'Target',        'Walk-CR'),
                            (            'Target',       'Walk-LRT'),
                            (            'Target',        'Walk-UR'),
                            (            'Target',        'PNR-Bus'),
                            (            'Target',         'PNR-CR'),
                            (            'Target',        'PNR-LRT'),
                            (            'Target',         'PNR-UR'),
                            (            'Target',            'TNC'),
                            (            'Target',     'TNC-Shared'),
                            (            'Target',           'Taxi'),
                            (            'Target',          'Other'),
                             (            'Model',    'Drive Alone'),
                             (            'Model',  'Shared Ride 2'),
                             (            'Model', 'Shared Ride 3+'),
                            (            'Model',           'Walk'),
                            (            'Model',           'Bike'),
                            (            'Model',       'Walk-Bus'),
                            (            'Model',        'Walk-CR'),
                            (            'Model',       'Walk-LRT'),
                            (            'Model',        'Walk-UR'),
                            (            'Model',        'PNR-Bus'),
                            (            'Model',         'PNR-CR'),
                            (            'Model',        'PNR-LRT'),
                            (            'Model',         'PNR-UR'),
                            (            'Model',            'TNC'),
                            (            'Model',     'TNC-Shared'),
                            (            'Model',           'Taxi'),
                            (            'Model',          'Other')]]

all_df_concat.columns= ['_'.join(col) for col in all_df_concat.columns.values]

all_df_concat_long= pd.melt(all_df_concat.reset_index(), id_vars=['Tour Purpose_', 'dimension_01_name_','dimension_01_value_'],
                             value_vars=all_df_concat.columns[3:])
all_df_concat_long['Legend']=all_df_concat_long['variable'].apply(lambda x: x.split('_')[0])
all_df_concat_long['dimension_02_value']=all_df_concat_long['variable'].apply(lambda x: x.split('_')[1])

writer = pd.ExcelWriter(os.path.join(set_output_dir,'AssignedTripModeChoiceSummary_categorical.xlsx'), engine='xlsxwriter')

all_df_concat_long.to_excel(writer, sheet_name='All', startrow=1, header=False, index=False)


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
(max_row, max_col) = all_df_concat_long.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)

for col_num, value in enumerate(all_df_concat_long.columns.values):
    worksheet.write(0, col_num, value, header_format)

time_period_summary_df_wide.to_excel(writer, sheet_name='Trips by Mode', startrow=1)
workbook  = writer.book
worksheet = writer.sheets['Trips by Mode']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = time_period_summary_df_wide.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)


trip_df_by_purpose_grouped_wide.to_excel(writer, sheet_name='Trips by Mode', startrow=5+len(time_period_summary_df_wide))
workbook  = writer.book
worksheet = writer.sheets['Trips by Mode']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = trip_df_by_purpose_grouped_wide.shape

# Make the columns wider for clarity.
worksheet.set_column(5+len(time_period_summary_df_wide),  max_col - 1, 12)
worksheet.autofilter(5+len(time_period_summary_df_wide), 0, max_row, max_col - 1)


trip_length_df.to_excel(writer, sheet_name='Trip Length', startrow=0, index=False)
workbook  = writer.book
worksheet = writer.sheets['Trip Length']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = trip_length_df.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)


person_trips_c_c_flow.to_excel(writer, sheet_name='Person Trips', startrow=0)
workbook  = writer.book
worksheet = writer.sheets['Person Trips']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = person_trips_c_c_flow.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)



vehicle_trips_c_c_flow.to_excel(writer, sheet_name='Vehicle Trips', startrow=0)
workbook  = writer.book
worksheet = writer.sheets['Vehicle Trips']
# Add a header format.
header_format = workbook.add_format({
    'bold': True,
    'text_wrap': True,
    'valign': 'top',
    'fg_color': '#D7E4BC',
    'border': 1})

# Get the dimensions of the dataframe.
(max_row, max_col) = vehicle_trips_c_c_flow.shape

# Make the columns wider for clarity.
worksheet.set_column(0,  max_col - 1, 12)
worksheet.autofilter(0, 0, max_row, max_col - 1)


writer.save()

           