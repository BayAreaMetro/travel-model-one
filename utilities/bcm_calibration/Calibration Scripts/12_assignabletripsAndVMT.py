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
set_output_dir = 'calibration_output/'+model_results+'/09_TripsSummary/'

if not os.path.exists(set_output_dir):
    os.makedirs(set_output_dir)

geo_crosswalk=pd.read_csv(os.path.join(set_model_result_dir,'geo_crosswalk.csv'))

taz_county_dict=dict(zip(geo_crosswalk['TAZ'], geo_crosswalk['COUNTYNAME']))

indiv_trip_df = pd.read_csv(os.path.join(set_model_result_dir, 'indivTripData_1.csv'))
joint_trip_df = pd.read_csv(os.path.join(set_model_result_dir, 'jointTripData_1.csv'))
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
                9:'Transit Walk',
                10:'Transit Walk',
                11:'Transit Walk',
                12:'Transit Walk',
                13:'Transit Walk',
                14:'Transit Drive',
                15:'Transit Drive',
                16:'Transit Drive',
                17:'Transit Drive',
                18:'Transit Drive',
                19:'Taxi-TNC',
                20:'Taxi-TNC',
                21:'Taxi-TNC'}

indiv_trip_df['trip_mode_verbose']=indiv_trip_df['trip_mode'].map(trip_mode_dict)
joint_trip_df['trip_mode_verbose']=joint_trip_df['trip_mode'].map(trip_mode_dict)

indiv_trip_df['trip_id']=indiv_trip_df.index+1
indiv_trip_df['origin_county']=indiv_trip_df['orig_taz'].map(taz_county_dict)
indiv_trip_df['destination_county'] = indiv_trip_df['dest_taz'].map(taz_county_dict)

joint_trip_df['trip_id']=joint_trip_df.index+1
joint_trip_df['origin_county']=joint_trip_df['orig_taz'].map(taz_county_dict)
joint_trip_df['destination_county'] = joint_trip_df['dest_taz'].map(taz_county_dict)

samplesize=indiv_trip_df['sampleRate']

indiv_trip_lengths=indiv_trip_df.merge(distance_skim[['origin','destination','dist']],
                                    how='left',
                                    left_on=['orig_taz','dest_taz'],
                                    right_on=['origin','destination'])[['trip_id', 'dist']]
indiv_trip_lengths_dict=dict(zip(indiv_trip_lengths['trip_id'], indiv_trip_lengths['dist']))
joint_trip_lengths=joint_trip_df.merge(distance_skim[['origin','destination','dist']],
                                    how='left',
                                    left_on=['orig_taz','dest_taz'],
                                    right_on=['origin','destination'])[['trip_id','dist']]
joint_trip_lengths_dict=dict(zip(joint_trip_lengths['trip_id'], joint_trip_lengths['dist']))


indiv_trip_df['dist']=indiv_trip_df['trip_id'].map(indiv_trip_lengths_dict)
joint_trip_df['dist']=joint_trip_df['trip_id'].map(joint_trip_lengths_dict)



def vmt_factor(x):
    if x in ['Drive Alone','TNC']:
        return 1
    elif x in ['Shared Ride 2','Taxi-TNC']:
        return 2
    elif x in ['Shared Ride 3+','TNC-Shared']:
        return 3.25
    else:
        return 1

indiv_trip_df['vmt_factor']=indiv_trip_df['trip_mode_verbose'].apply(vmt_factor)
joint_trip_df['vmt_factor']=joint_trip_df['trip_mode_verbose'].apply(vmt_factor)/joint_trip_df['num_participants']

indiv_trip_df['vmt'] = indiv_trip_df['dist']/indiv_trip_df['vmt_factor']/samplesize
joint_trip_df['vmt'] = joint_trip_df['dist']/joint_trip_df['vmt_factor']/samplesize

all_vehicle_trips = pd.concat([indiv_trip_df[['trip_id','trip_mode_verbose','origin_county','destination_county','vmt','orig_taz','dest_taz']],
                               joint_trip_df[['trip_id','trip_mode_verbose','origin_county','destination_county','vmt','orig_taz','dest_taz']]])

all_vehicle_trips_assignable = all_vehicle_trips[all_vehicle_trips['orig_taz']!=all_vehicle_trips['dest_taz']]


county_dict=['San Francisco',
             'San Mateo',
             'Santa Clara',
             'Alameda',
             'Contra Costa',
             'Solano',
             'Napa',
             'Sonoma',
             'Marin','San Joaquin']

county_sorter_index = dict(zip(county_dict, range(len(county_dict))))
trips_by_county = all_vehicle_trips_assignable.groupby(['origin_county','trip_mode_verbose']).agg(NumberOfTrips=('trip_id','nunique'),
                                                                                                  VMT=('vmt','sum')).reset_index()
trips_by_county['NumberOfTrips_Scaled']=trips_by_county['NumberOfTrips']/samplesize
trips_by_county.to_csv(os.path.join(set_output_dir, 'AssignableTripsandVMT_'+model_results+'.csv'))
from pandas.api.types import CategoricalDtype
county_sort=CategoricalDtype(county_dict, ordered=True)
only_vehicle_trips = all_vehicle_trips_assignable[all_vehicle_trips_assignable['trip_mode_verbose'].isin(['Drive Alone',
                                                                                                          'Shared Ride 2',
                                                                                                          'Shared Ride 3+',
                                                                                                          'Transit Drive',
                                                                                                          'Taxi-TNC'])]
vmt_total = only_vehicle_trips.groupby(['origin_county']).agg(VMT=('vmt','sum')).reset_index()
vmt_total['origin_county']=vmt_total['origin_county'].astype(county_sort)
vmt_total.sort_values(by='origin_county').to_csv(os.path.join(set_output_dir,'VMT_Assignable_By_County.csv'), index=False)