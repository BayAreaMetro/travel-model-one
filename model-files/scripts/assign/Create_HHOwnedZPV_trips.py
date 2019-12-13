# This script creates the trip tables for trips by household-owned AV with no passenger (aka owned AV ZPV)
# It calculates the ratio between the parking cost and operating cost
# i.e. (duration * parking cost per hour) / (auto operating cost * trip distance)
# if Park_Drive_CostRatio > 1, add two vehicle trips (one going home and one coming back to pick-up)
# if Park_Drive_CostRatio <= 1, do not add (as it is assume that the vehicle will be parked)

import os
import pandas as pd
import sys
import numpy as np

# how to call this script
# need to run a .job script to get the distance - a much simplify version of ZeroPassengerVehicles.job
# set path=%path%;c:/python27
# set ITER=1
# python ctramp\scripts\preprocess\Create_HHOwnedZPV_trips.py


ITER = os.getenv('ITER')

# -----------------------
# read inputs
# -----------------------
# read in the trip lists
indivTripData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "indivTripData_" + ITER + ".csv"), index_col=False, sep=",")
jointTripData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "jointTripData_" + ITER + ".csv"), index_col=False, sep=",")
# note that jointTripData doesn't have the field person_id so we need to fill that in
jointTripData_df['person_id'] = 'hhid_' +  jointTripData_df['hh_id'].astype(str)

# read in taz data for parking cost (peak and non peak)
tazData_df = pd.read_csv(os.path.join(os.getcwd(), 'landuse', "tazData.csv"), index_col=False, sep=",")

# read in the OD distances for ZPV by time period
# no column names - would be nice to fix this in the Cube script
zpv_distances_ea_df =  pd.read_csv(os.path.join(os.getcwd(), 'main', "zpv_distances_ev.csv"), header=None, index_col=False, sep=",")
zpv_distances_am_df =  pd.read_csv(os.path.join(os.getcwd(), 'main', "zpv_distances_ev.csv"), header=None, index_col=False, sep=",")
zpv_distances_md_df =  pd.read_csv(os.path.join(os.getcwd(), 'main', "zpv_distances_ev.csv"), header=None, index_col=False, sep=",")
zpv_distances_pm_df =  pd.read_csv(os.path.join(os.getcwd(), 'main', "zpv_distances_ev.csv"), header=None, index_col=False, sep=",")
zpv_distances_ev_df =  pd.read_csv(os.path.join(os.getcwd(), 'main', "zpv_distances_ev.csv"), header=None, index_col=False, sep=",")
# add column names
zpv_distances_ea_df.columns=['orig', 'dest', 'ColumnOf1s', 'OD_dist']
zpv_distances_am_df.columns=['orig', 'dest', 'ColumnOf1s', 'OD_dist']
zpv_distances_md_df.columns=['orig', 'dest', 'ColumnOf1s', 'OD_dist']
zpv_distances_pm_df.columns=['orig', 'dest', 'ColumnOf1s', 'OD_dist']
zpv_distances_ev_df.columns=['orig', 'dest', 'ColumnOf1s', 'OD_dist']

# also need to read in AUTOOPC (auto opeating cost) and autoCPMFactor (the cost per mile discount for AV) from INPUT/params.properties
# this is done in the "Calulate the Park vs Drive Cost Ratio" section


# -----------------------
# Processing the trip list
# -----------------------
# append jointTripData_df to indivTripData_df
TripList_df = indivTripData_df.append(jointTripData_df, sort=False)

# start from sorting the trip list data frame first
# in the individual trip data from CTRAMP, mandatory trips are always listed before non mandatory trips, so the trips may not appear in chrnological order
TripList_df.sort_values(by=['hh_id', 'person_id', 'depart_hour'], inplace=True)
# after sorting, reset the index
TripList_df = TripList_df.reset_index(drop=True)

# calculate duration
TripList_df['duration'] = np.where(TripList_df['person_id'].shift(-1) == TripList_df['person_id'], TripList_df['depart_hour'].shift(-1)-TripList_df['depart_hour'], 0)

# add time period based on depart_hour
# definition of depart_hour: goes from 5 to 23, where 5 is the hour from 5 am to 6 am and 23 is the hour from 11 pm to midnight
# The time periods are: (a) early AM, 3 am to 6 am; (b) AM peak period, 6 am to 10 am; (c) midday, 10 am to 3 pm; (d) PM peak period, 3 pm to 7 pm; and, (e) evening, 7 pm to 3 am the next day.
TP_conditions = [
    (TripList_df['depart_hour'] < 6),
    (TripList_df['depart_hour'] >= 6) & (TripList_df['depart_hour'] <10),
    (TripList_df['depart_hour'] >= 10) & (TripList_df['depart_hour'] <15),
    (TripList_df['depart_hour'] >= 15) & (TripList_df['depart_hour'] <19),
    (TripList_df['depart_hour'] >= 19)]
TP_choices = ['EA', 'AM', 'MD', 'PM', 'EV']
TripList_df['time_period_gohome'] = np.select(TP_conditions, TP_choices, default='null') # assuming the vehicle goes home in the same TP as the drop-off trip


TP_pickup_conditions = [
    (TripList_df['depart_hour'].shift(-1) < 6),
    (TripList_df['depart_hour'].shift(-1) >= 6) & (TripList_df['depart_hour'].shift(-1) <10),
    (TripList_df['depart_hour'].shift(-1) >= 10) & (TripList_df['depart_hour'].shift(-1) <15),
    (TripList_df['depart_hour'].shift(-1) >= 15) & (TripList_df['depart_hour'].shift(-1) <19),
    (TripList_df['depart_hour'].shift(-1) >= 19)]
TripList_df['time_period_pickup'] = np.select(TP_pickup_conditions, TP_choices, default='null')

# merge in the parking cost (peak and non peak)
# joinining on dest_taz (there is field called parking_taz but it's not used)
TripList_df = pd.merge(TripList_df, tazData_df[['ZONE','PRKCST','OPRKCST']], left_on='dest_taz', right_on='ZONE', how='left')
# drop the column "ZONE"
TripList_df.drop('ZONE', axis=1, inplace=True)
# TripList_df.drop('ZONE', axis=1, inplace=True)

# determine parking cost based on whether it is peak or nonpeak (AM and PM are peak, the rest is nonpeak)
TripList_df['ParkingCostPerHour'] = np.where( (TripList_df['time_period_gohome']=='AM') | (TripList_df['time_period_gohome']=='PM') , TripList_df['PRKCST'], TripList_df['OPRKCST'])

# merge in the OD distances by time period
TripList_df = pd.merge(TripList_df, zpv_distances_ea_df[['orig','dest','OD_dist']], left_on=['orig_taz', 'dest_taz'], right_on=['orig','dest'], how='left', suffixes=('', '_ea'))
TripList_df.drop(['orig','dest'], axis=1, inplace=True)
TripList_df = pd.merge(TripList_df, zpv_distances_am_df[['orig','dest','OD_dist']], left_on=['orig_taz', 'dest_taz'], right_on=['orig','dest'], how='left', suffixes=('', '_am'))
TripList_df.drop(['orig','dest'], axis=1, inplace=True)
TripList_df = pd.merge(TripList_df, zpv_distances_md_df[['orig','dest','OD_dist']], left_on=['orig_taz', 'dest_taz'], right_on=['orig','dest'], how='left', suffixes=('', '_md'))
TripList_df.drop(['orig','dest'], axis=1, inplace=True)
TripList_df = pd.merge(TripList_df, zpv_distances_pm_df[['orig','dest','OD_dist']], left_on=['orig_taz', 'dest_taz'], right_on=['orig','dest'], how='left', suffixes=('', '_pm'))
TripList_df.drop(['orig','dest'], axis=1, inplace=True)
TripList_df = pd.merge(TripList_df, zpv_distances_ev_df[['orig','dest','OD_dist']], left_on=['orig_taz', 'dest_taz'], right_on=['orig','dest'], how='left', suffixes=('', '_ev'))
TripList_df.drop(['orig','dest'], axis=1, inplace=True)
# force the "_ea" suffix
TripList_df.rename(columns={"OD_dist": "OD_dist_ea"}, inplace=True)


# pick the distance according to the time period (when the vehicle goes home)
ODdist_choices = [TripList_df['OD_dist_ea'], TripList_df['OD_dist_am'], TripList_df['OD_dist_md'], TripList_df['OD_dist_pm'], TripList_df['OD_dist_ev']]
TripList_df['ZPV_dist_gohome'] = np.select(TP_conditions, ODdist_choices, default='null')
TripList_df['ZPV_dist_gohome'] = TripList_df['ZPV_dist_gohome'].astype('float64')

# pick the distance according to the time period (when the vehicle comes back to pickup)
ODdist_choices = [TripList_df['OD_dist_ea'], TripList_df['OD_dist_am'], TripList_df['OD_dist_md'], TripList_df['OD_dist_pm'], TripList_df['OD_dist_ev']]
TripList_df['ZPV_dist_pickup'] = np.select(TP_pickup_conditions, ODdist_choices, default='null')
TripList_df.loc[len(TripList_df)-1,'ZPV_dist_pickup'] = 0 #set the last row to have a value of 0, because it doesn't have a pick-up time
TripList_df['ZPV_dist_pickup'] = TripList_df['ZPV_dist_pickup'].astype('float64')

# -----------------------
# Calulate the Park vs Drive Cost Ratio
# -----------------------
# read in AUTOOPC (auto opeating cost) and autoCPMFactor (the cost per mile discount for AV) from INPUT/params.properties
sys.path.append(os.path.join(os.getcwd(),"CTRAMP","scripts","preprocess"))
from RuntimeConfiguration import *
params_filename = os.path.join("INPUT", "params.properties")
myfile          = open(params_filename, 'r' )
myfile_contents = myfile.read()
myfile.close()
auto_opc = float(get_property(params_filename, myfile_contents, "AutoOpCost"))
avCPMFactor = float(get_property(params_filename, myfile_contents, "Mobility.AV.CostPerMileFactor"))

# Calculate the ratio between the parking cost and operating cost
# i.e. (duration * parking cost per hour) / (auto operating cost * trip distance)
TripList_df['Park_Drive_CostRatio'] = (TripList_df['ParkingCostPerHour'] * TripList_df['duration']) / (auto_opc * avCPMFactor * (TripList_df['ZPV_dist_gohome']+TripList_df['ZPV_dist_pickup']))

# Park_Drive_CostRatio applies only if an AV is used for that trip
TripList_df['Park_Drive_CostRatio'] = np.where((TripList_df['trip_mode']<=6) & (TripList_df['avAvailable']==1), TripList_df['Park_Drive_CostRatio'], 0)

# Park_Drive_CostRatio is 0 if destiantion purpose is "Home"
TripList_df['Park_Drive_CostRatio'] = np.where(TripList_df['dest_purpose']=='Home', 0, TripList_df['Park_Drive_CostRatio'])

# if Park_Drive_CostRatio > 1, then add a trip
# if Park_Drive_CostRatio <= 1, then park
TripList_df['Trip'] = np.where(TripList_df['Park_Drive_CostRatio']<=1, 0, 1)

# output the trip list with the owned zpv "park vs drive cost ratios" for visualization, can delete this after this script is fully tested
output_triplist_filename = "main/output_triplist.csv"
TripList_df.to_csv(output_triplist_filename, header=True, index=False)

# Generate the owned ZPV trip table
# by summing up the trips by ODs, for (i) the trip going back home and (ii) the trip returning to the pick up location
# by 5 time periods
TripList_gohome_4var_df = TripList_df[['orig_taz', 'dest_taz', 'time_period_gohome','Trip']]
TripList_pickup_4var_df = TripList_df[['orig_taz', 'dest_taz', 'time_period_pickup','Trip']]

time_period_list = ["EA", "AM", "MD", "PM", "EV"]
for tp in time_period_list:
    # keep the data for a single time period
    TripList_gohome_4var_tp_df = TripList_gohome_4var_df[TripList_gohome_4var_df['time_period_gohome'] == tp]
    TripList_pickup_4var_tp_df = TripList_pickup_4var_df[TripList_pickup_4var_df['time_period_pickup'] == tp]

    # keep rows that have non-zero trips
    TripList_gohome_4var_tp_df = TripList_gohome_4var_tp_df[TripList_gohome_4var_tp_df['Trip'] == 1]
    TripList_pickup_4var_tp_df = TripList_pickup_4var_tp_df[TripList_pickup_4var_tp_df['Trip'] == 1]

    # zpv trips going home
    ZPV_gohome_tp_df = TripList_gohome_4var_tp_df.groupby(['orig_taz', 'dest_taz'], as_index=False).sum()
    # transpose it
    ZPV_gohome_tp_df['orig'] = ZPV_gohome_tp_df['dest_taz']
    ZPV_gohome_tp_df['dest'] = ZPV_gohome_tp_df['orig_taz']
    ZPV_gohome_tp_df.drop(['orig_taz','dest_taz'], axis=1, inplace=True)
    # reorder and resort
    ZPV_gohome_tp_df = ZPV_gohome_tp_df[['orig', 'dest','Trip']]
    ZPV_gohome_tp_df.sort_values(by=['orig', 'dest'], inplace=True)

    # zpv trips returning to pickup
    ZPV_pickup_tp_df = TripList_pickup_4var_tp_df.groupby(['orig_taz', 'dest_taz'], as_index=False).sum()
    # no transpose, just reorder and resort
    ZPV_pickup_tp_df = ZPV_pickup_tp_df[['orig_taz', 'dest_taz','Trip']]
    ZPV_pickup_tp_df.sort_values(by=['orig_taz', 'dest_taz'], inplace=True)

    # add the go home and pick up trip table together
    ZPV_triptable_tp_df = pd.merge(ZPV_gohome_tp_df, ZPV_pickup_tp_df, left_on=['orig', 'dest'], right_on=['orig_taz','dest_taz'], how='outer', suffixes=('_gohome','_pickup'))
    ZPV_triptable_tp_df['orig'] = np.where(pd.notnull(ZPV_triptable_tp_df['orig']), ZPV_triptable_tp_df['orig'], ZPV_triptable_tp_df['orig_taz'])
    ZPV_triptable_tp_df['dest'] = np.where(pd.notnull(ZPV_triptable_tp_df['dest']), ZPV_triptable_tp_df['dest'], ZPV_triptable_tp_df['dest_taz'])
    ZPV_triptable_tp_df['Trip_gohome'].fillna(0, inplace=True)
    ZPV_triptable_tp_df['Trip_pickup'].fillna(0, inplace=True)
    ZPV_triptable_tp_df['Trip'] = ZPV_triptable_tp_df['Trip_gohome'] + ZPV_triptable_tp_df['Trip_pickup']
    ZPV_triptable_tp_df.drop(['orig_taz','dest_taz','Trip_gohome','Trip_pickup'], axis=1, inplace=True)
    ZPV_triptable_tp_df.sort_values(by=['orig', 'dest'], inplace=True)


    output_ZPVtriptable_tp_filename = "main/ownedZPV_triptable_"+tp+".csv"
    # ZPV_triptable_tp_df.to_csv(output_ZPVtriptable_tp_filename, header=True, index=False)
    # output to a fixed width file format for Cube
    output_ZPVtriptable_tp_filename_dat = "main/ownedZPV_triptable_"+tp+".dat"
    np.savetxt(output_ZPVtriptable_tp_filename_dat, ZPV_triptable_tp_df.values, fmt='%20.5f')


 # getting the mean may be interesting too for reasonableness checks
 #ZPV_triptable_df = TripList_df.groupby(['orig_taz', 'dest_taz']).mean()
