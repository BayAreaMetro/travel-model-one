import pandas as pd
import numpy as np
import os
import xlsxwriter

import math 

import argparse

#Set Directory
parser = argparse.ArgumentParser()
parser.add_argument("--run_name",type=str, help="Model run output file relative location")
parser.add_argument("--sample_share",type=int, help="Model run output file relative location")

args = parser.parse_args()
sampling_rate = args.sample_share
samplesize = 100/5
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

indiv_trip_df['trip_mode_verbose']=indiv_trip_df['trip_mode'].map(trip_mode_dict)
joint_trip_df['trip_mode_verbose']=joint_trip_df['trip_mode'].map(trip_mode_dict)

indiv_trip_df['trip_id']=indiv_trip_df.index+1
indiv_trip_df['origin_county']=indiv_trip_df['orig_taz'].map(taz_county_dict)
indiv_trip_df['destination_county'] = indiv_trip_df['dest_taz'].map(taz_county_dict)

joint_trip_df['trip_id']=joint_trip_df.index+1
joint_trip_df['origin_county']=joint_trip_df['orig_taz'].map(taz_county_dict)
joint_trip_df['destination_county'] = joint_trip_df['dest_taz'].map(taz_county_dict)

vehicle_trips=['Drive Alone','Shared Ride 2','Shared Ride 3+','Taxi','TNC','TNC-Shared']

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

indiv_vehicle_trips = indiv_trip_df[indiv_trip_df['trip_mode_verbose'].isin(vehicle_trips)]
joint_vehicle_trips = joint_trip_df[joint_trip_df['trip_mode_verbose'].isin(vehicle_trips)]

def vmt_factor(x):
    if x in ['Drive Alone','TNC']:
        return 1
    elif x in ['Shared Ride 2','Taxi']:
        return 2
    elif x in ['Shared Ride 3+','TNC-Shared']:
        return 3.25
    else:
        return 1

indiv_vehicle_trips['vmt_factor']=indiv_vehicle_trips['trip_mode_verbose'].apply(vmt_factor)
joint_vehicle_trips['vmt_factor']=joint_vehicle_trips['trip_mode_verbose'].apply(vmt_factor)/joint_vehicle_trips['num_participants']

indiv_vehicle_trips['vmt'] = samplesize*indiv_vehicle_trips['dist']/indiv_vehicle_trips['vmt_factor']
joint_vehicle_trips['vmt'] = samplesize*joint_vehicle_trips['dist']/joint_vehicle_trips['vmt_factor']

all_vehicle_trips = pd.concat([indiv_vehicle_trips[['trip_id','trip_mode_verbose','origin_county','destination_county','vmt']],
                               joint_vehicle_trips[['trip_id','trip_mode_verbose','origin_county','destination_county','vmt']]])

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

for county in all_vehicle_trips['origin_county'].unique():

    if county not in county_dict:
        county_dict.remove(county)


vehicle_trips_c_c_flow= pd.crosstab(all_vehicle_trips['origin_county'],
                                    all_vehicle_trips['destination_county'], 
                                    values=all_vehicle_trips['vmt'], 
                                    aggfunc='sum',
                                    margins=True,
                                    margins_name='Total VMT').sort_index(key=lambda x: x.map(county_sorter_index))[county_dict]

vehicle_trips_c_c_flow.to_csv(os.path.join(set_output_dir, 'VMT_'+model_results+'.csv'))