USAGE = """

    This script is to be run at the end of a travel model run, automatically by the batch file RunPrepareEmfac.bat.

    This script replaces the old script CreateSpeedBinsBetweenZones.job

"""

import pandas as pd
import numpy as np

import os.path
from os import path

#import argparse

# -------------------------------------------------------------------
# Input/output file names and locations
# -------------------------------------------------------------------
# loaded network assignment file
loadednet_df = pd.read_csv(os.path.join(os.getcwd(), "hwy", "iter3", "avgload5period_vehclasses.csv"), index_col=False, sep=",")

# Todo: add truck or no truck

output_csv = "emfac\\emfac_prep\\CreateSpeedBinsBetweenZones_sums.csv"


# -------------------------------------------------------------------
# Read the data and output them
# by county and 13 speed bins (as rows)
# by hours as columns
# -------------------------------------------------------------------

GL_conditions = [
    (loadednet_df['gl'] == 1),
    (loadednet_df['gl'] == 2),
    (loadednet_df['gl'] == 3),
    (loadednet_df['gl'] == 4),
    (loadednet_df['gl'] == 5),
    (loadednet_df['gl'] == 6),
    (loadednet_df['gl'] == 7),
    (loadednet_df['gl'] == 8),
    (loadednet_df['gl'] == 9),
    (loadednet_df['gl'] == 10)]

CountyName_choices = ["San Francisco", "San Mateo", "Santa Clara", "Alameda", "Contra Costa", "Solano", "Napa", "Sonoma", "Marin", "external"]
loadednet_df['countyName'] = np.select(GL_conditions, CountyName_choices , default='null')

#  arbCounty - this variable is not actually needed for subsequent processing. CountyName is enough.
arbCounty_choices = ["38", "41", "43", "01", "07", "48", "28", "49", "21", "9999"]
loadednet_df[' arbCounty'] = np.select(GL_conditions, arbCounty_choices , default='null')

# create dataframe for each time period and loop through tem
# store dataframes into a dictionary
timeperiodList = ['EA', 'AM', 'MD', 'PM', 'EV']

dict_of_df = {}
for tp in timeperiodList:

    # speed bins
    Speed_conditions = [
        (loadednet_df['cspd'+tp] >= 0) & (loadednet_df['cspd'+tp] < 5),
        (loadednet_df['cspd'+tp] >= 5) & (loadednet_df['cspd'+tp] < 10),
        (loadednet_df['cspd'+tp] >= 10) & (loadednet_df['cspd'+tp] < 15),
        (loadednet_df['cspd'+tp] >= 15) & (loadednet_df['cspd'+tp] < 20),
        (loadednet_df['cspd'+tp] >= 20) & (loadednet_df['cspd'+tp] < 25),
        (loadednet_df['cspd'+tp] >= 25) & (loadednet_df['cspd'+tp] < 30),
        (loadednet_df['cspd'+tp] >= 30) & (loadednet_df['cspd'+tp] < 35),
        (loadednet_df['cspd'+tp] >= 35) & (loadednet_df['cspd'+tp] < 40),
        (loadednet_df['cspd'+tp] >= 40) & (loadednet_df['cspd'+tp] < 45),
        (loadednet_df['cspd'+tp] >= 45) & (loadednet_df['cspd'+tp] < 50),
        (loadednet_df['cspd'+tp] >= 50) & (loadednet_df['cspd'+tp] < 55),
        (loadednet_df['cspd'+tp] >= 55) & (loadednet_df['cspd'+tp] < 60),
        (loadednet_df['cspd'+tp] >= 60)]
    SpeedBin_choices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    loadednet_df[' speedBin'] = np.select(Speed_conditions, SpeedBin_choices, default='null')

    # reset speeds to 25 mph for dummy links (these are dummy/centroid connector-access links)
    loadednet_df[' speedBin'] = np.where(loadednet_df['ft']==6, 6, loadednet_df[' speedBin']).astype(int)

    # calculate vmt
    loadednet_df['vmt_'+tp] = loadednet_df['distance'] *  loadednet_df['vol'+tp+'_tot']

    # keep the relevant columns
    loadednet1_df =  loadednet_df[['countyName', ' arbCounty', ' speedBin', 'vmt_'+tp]]

    # save as new dataframe
    key_name = 'VMTBySpeedBin_'+ tp +'_df'
    key_name = loadednet1_df.groupby(['countyName', ' arbCounty', ' speedBin'], as_index=False).sum()

    # merge the data frames
    if tp=='EA':
        VMTBySpeedBin_allTP_df = key_name
    else: VMTBySpeedBin_allTP_df = pd.merge(VMTBySpeedBin_allTP_df, key_name, left_on=['countyName', ' arbCounty', ' speedBin'], right_on=['countyName', ' arbCounty', ' speedBin'], how='outer')

# set within time period diurnal factor consistent with EMFAC
# (these diurnal factors came from the old script CreateSpeedBinsBetweenZones.job)

VMTBySpeedBin_allTP_df[' hour04'] = 0.157 * VMTBySpeedBin_allTP_df['vmt_EA']
VMTBySpeedBin_allTP_df[' hour05'] = 0.298 * VMTBySpeedBin_allTP_df['vmt_EA']
VMTBySpeedBin_allTP_df[' hour06'] = 0.545 * VMTBySpeedBin_allTP_df['vmt_EA']

VMTBySpeedBin_allTP_df['hour07'] = 0.164 * VMTBySpeedBin_allTP_df['vmt_AM'] #note missing space
VMTBySpeedBin_allTP_df[' hour08'] = 0.336 * VMTBySpeedBin_allTP_df['vmt_AM']
VMTBySpeedBin_allTP_df[' hour09'] = 0.309 * VMTBySpeedBin_allTP_df['vmt_AM']
VMTBySpeedBin_allTP_df[' hour10'] = 0.191 * VMTBySpeedBin_allTP_df['vmt_AM']

VMTBySpeedBin_allTP_df[' hour11'] = 0.157 * VMTBySpeedBin_allTP_df['vmt_MD']
VMTBySpeedBin_allTP_df[' hour12'] = 0.198 * VMTBySpeedBin_allTP_df['vmt_MD']
VMTBySpeedBin_allTP_df[' hour13'] = 0.207 * VMTBySpeedBin_allTP_df['vmt_MD']
VMTBySpeedBin_allTP_df[' hour14'] = 0.203 * VMTBySpeedBin_allTP_df['vmt_MD']
VMTBySpeedBin_allTP_df[' hour15'] = 0.235 * VMTBySpeedBin_allTP_df['vmt_MD']

VMTBySpeedBin_allTP_df[' hour16'] = 0.251 * VMTBySpeedBin_allTP_df['vmt_PM']
VMTBySpeedBin_allTP_df['hour17'] = 0.261 * VMTBySpeedBin_allTP_df['vmt_PM'] #note missing space
VMTBySpeedBin_allTP_df[' hour18'] = 0.288 * VMTBySpeedBin_allTP_df['vmt_PM']
VMTBySpeedBin_allTP_df[' hour19'] = 0.200 * VMTBySpeedBin_allTP_df['vmt_PM']

VMTBySpeedBin_allTP_df[' hour20'] = 0.248 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour21'] = 0.190 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour22'] = 0.192 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour23'] = 0.144 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour24'] = 0.109 * VMTBySpeedBin_allTP_df['vmt_EV']

VMTBySpeedBin_allTP_df[' hour01'] = 0.067 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour02'] = 0.025 * VMTBySpeedBin_allTP_df['vmt_EV']
VMTBySpeedBin_allTP_df[' hour03'] = 0.025 * VMTBySpeedBin_allTP_df['vmt_EV']



# make sure all 13 speed bins are listed (since the script emfac_prep needs this)
CountyList = ["San Francisco", "San Mateo", "Santa Clara", "Alameda", "Contra Costa", "Solano", "Napa", "Sonoma", "Marin", "external"]

for cnty in CountyList:
    speedBin_dummy = {'dummy_col': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]}
    speedBin_dummy_df = pd.DataFrame(data=speedBin_dummy)

    speedBin_dummy_df['county_dummy'] = cnty
    
    if cnty=="San Francisco":
       speedBin_dummy_df['arbCnty_dummy'] = "38"
    if cnty=="San Mateo":
       speedBin_dummy_df['arbCnty_dummy'] = "41"             
    if cnty=="Santa Clara":
       speedBin_dummy_df['arbCnty_dummy'] = "43" 
    if cnty=="Alameda":
       speedBin_dummy_df['arbCnty_dummy'] = "01" 
    if cnty=="Contra Costa":
       speedBin_dummy_df['arbCnty_dummy'] = "07"
    if cnty=="Solano":
       speedBin_dummy_df['arbCnty_dummy'] = "48"
    if cnty=="Napa":
       speedBin_dummy_df['arbCnty_dummy'] = "28"
    if cnty=="Sonoma":
       speedBin_dummy_df['arbCnty_dummy'] = "49"
    if cnty=="Marin":
       speedBin_dummy_df['arbCnty_dummy'] = "21"
    if cnty=="external":
       speedBin_dummy_df['arbCnty_dummy'] = "9999"

  # append the data frames
    if cnty=='San Francisco':
        dummy_df = speedBin_dummy_df
    else: dummy_df = pd.concat([dummy_df, speedBin_dummy_df])


VMTBySpeedBin_allTP_df = pd.merge(VMTBySpeedBin_allTP_df, dummy_df, left_on=['countyName',' speedBin'], right_on=['county_dummy', 'dummy_col'], how='outer')

# make the dummy column the speed bin column
VMTBySpeedBin_allTP_df['countyName'] = VMTBySpeedBin_allTP_df['county_dummy'] 
VMTBySpeedBin_allTP_df[' arbCounty'] = VMTBySpeedBin_allTP_df['arbCnty_dummy'] 
VMTBySpeedBin_allTP_df[' speedBin'] = VMTBySpeedBin_allTP_df['dummy_col'] 

# keep the relevant columns and recorder
VMTBySpeedBin_allTP_df =  VMTBySpeedBin_allTP_df[['countyName', ' arbCounty', ' speedBin',
                                                  ' hour01', ' hour02', ' hour03', ' hour04', ' hour05', ' hour06', 'hour07', ' hour08', ' hour09', ' hour10',
                                                  ' hour11', ' hour12', ' hour13', ' hour14', ' hour15', ' hour16', 'hour17', ' hour18', ' hour19', ' hour20',
                                                  ' hour21', ' hour22', ' hour23', ' hour24']]

# sort the file
VMTBySpeedBin_allTP_df.sort_values(by=['countyName', ' speedBin'], inplace=True)

# fill in the blank cells
VMTBySpeedBin_allTP_df.fillna(0, inplace=True)

VMTBySpeedBin_allTP_df.to_csv(output_csv, header=True, index=False)
