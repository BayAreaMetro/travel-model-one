import os
import csv
import numpy as np
import pandas as pd
from pandas import DataFrame
import xlrd
import pyreadr

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# Compare results for the following runs (i.e. show metric values and percent change)
# Location: L:\Application\Model_One\NextGenFwys:
# 2035 No Project (2035_TM152_NGF_NoProject_01)
# 2035 PBA2035 Pricing (2035_TM152_FBP_Plus_24)
# (Script should be able to compare for more model runs easily)

# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# names of folders for runs listed above
# #might want to come back and make this iterable through a folder
list_dir = ['2035_TM152_FBP_Plus_24','2035_TM152_NGF_NoProject_01','2035_TM152_NGF_SensDiscount_01', '2035_TM152_NGF_SensDiscount_02', '2035_TM152_NGF_SensDiscount_04','2035_TM152_NGF_SensDiscount_05']
# #alt list_dir for rdata testing
# list_dir = ['2035_TM152_FBP_Plus_24','2035_TM152_NGF_NoProject_01']

# define path location for folders above
file_loc = "L:\\Application\\Model_One\\NextGenFwys"

# mapping dictionaries
tourmode_mapping = {
                    1  : "sov",
                    2  : "sov",
                    3  : "hov2",
                    4  : "hov2",
                    5  : "hov3",
                    6  : "hov3",
                    7  : "walk",
                    8  : "bike",
                    9  : "WLK_LOC",
                    10 : "WLK_LRF",
                    11 : "WLK_EXP",
                    12 : "WLK_HVY",
                    13 : "WLK_COM",
                    14 : "DRV_LOC",
                    15 : "DRV_LRF",
                    16 : "DRV_EXP",
                    17 : "DRV_HVY",
                    18 : "DRV_COM",
                    19 : "taxi",
                    20 : "TNCsp",
                    21 : "TNCsws"
                }
taz_mapping = {
                    (1,190)      : "San Francisco",
                    (191,346)    : "San Mateo",
                    (347,714)    : "Santa Clara",
                    (715,1039)   : "Alameda",
                    (1040,1210)  : "Contra Costa",
                    (1211,1290)  : "Solano",
                    (1291,1317)  : "Napa",
                    (1318,1403)  : "Sonoma",
                    (1404,1454)  : "Marin"
                }
# taz_to_city_mapping
citytaz = pd.read_csv('C:/Users/jalatorre/Box/NextGen Freeways Study/07 Tasks/05_GoalsandMetrics/Metrics/taz_with_cities.csv') 
taz_to_city_mapping = citytaz.set_index('taz1454').to_dict()['CITY']
#list of full file directories

MTB_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'core_summaries' , 'CommuteByIncomeHousehold.csv') for i in list_dir]
MTR_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'metrics' , 'transit_boards_miles.csv') for i in list_dir]
MVMTM_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'metrics' , 'vmt_vht_metrics.csv') for i in list_dir]
MR_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'metrics' , 'auto_times.csv') for i in list_dir]
MTT_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'avgload5period.csv') for i in list_dir]
MMS_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'avgload5period_vehclasses.csv') for i in list_dir]
MRDATA_file_list = [os.path.join(file_loc, i, 'OUTPUT', 'updated_output', 'trips.rdata') for i in list_dir]



def get_rate(number, table): # mapping function within range ex: taz OD    
    for key in table:
        if key[0] <= number <= key[1]:
            return table[key]

def file_list_to_csv(file_list, file_name): # read through a list of directories for files of the same type (different blueprints), combine the files in one csv and add identifying columns
    df = pd.DataFrame()
    i=0 # this variable used to iterate through the names of the blueprint folders

    for file in file_list:
        print("Opening and saving %s"%file)

        try:

            if '.rdata' in file: # runtime: 2-3 mins to load and clean each file, 2-3 minutes to write csv. 26 minute runtime for 5 or 6 files
                df_temp = pyreadr.read_r(file)['trips']
                df_temp = df_temp[['orig_taz', 'dest_taz', 'trip_mode', 'timeperiod_label', 'incQ_label', 'tour_purpose']]
                df_temp['Origin'] = df_temp['orig_taz'].map(taz_to_city_mapping)
                df_temp['Destination'] = df_temp['dest_taz'].map(taz_to_city_mapping)
                df_temp['mode'] = df_temp['trip_mode'].map(tourmode_mapping)
            else:
                df_temp = pd.read_csv(file)

            if "vmt_vht_metrics" in file:
                # aggregate vehicle classes // possibly put in a function if this step is needed for other files
                vehclass_mapping = {
                    "da"   : "sov",
                    "s2"   : "hov2",
                    "s3"   : "hov3",
                    "sm"   : "truck",
                    "hv"   : "truck",
                    "dat"  : "sov",
                    "s2t"  : "hov2",
                    "s3t"  : "hov3",
                    "smt"  : "truck",
                    "hvt"  : "truck",
                    "daav" : "sov",
                    "s2av" : "hov2",
                    "s3av" : "hov3",
                }
                df_temp.replace({"vehicle class":vehclass_mapping}, inplace=True)

            if "CommuteByIncomeHousehold" in file:
                # aggregate tours by mode             
                df_temp['mode'] = df_temp['tour_mode'].map(tourmode_mapping)

            # add column with Run ID
            df_temp['Run_ID'] = list_dir[i]

            # add column with year
            df_temp['Year'] = list_dir[i].split("_")[0]

            # add column for Blueprint
            df_temp['Blueprint'] = list_dir[i].split("_")[2]

            df = df.append(df_temp)
            print("Appended %s"%file)   

        except:
            print("Folder does not exist") 
        i+=1

    df.to_csv(os.path.join(os.getcwd(),file_name), header=True, index=False)
    print ("Successfully wrote " + file_name)

# # CONSIDER ADDING "[METRIC OUTPUT] " TO FILE NAME TO MAKE IT EASIER TO IDENTIFY IN THE FOLDER
# file_list_to_csv(MTB_file_list, "[METRIC OUTPUT] trips_by_mode_and_income.csv")
# file_list_to_csv(MTR_file_list, "[METRIC OUTPUT] transit_ridership_by_mode.csv")
# file_list_to_csv(MVMTM_file_list, "[METRIC OUTPUT] vmt_by_mode.csv")
# # can probably reuse trips by mode and income for vmt calc // do the calc in tableau
# file_list_to_csv(MR_file_list, "[METRIC OUTPUT] revenue.csv")
# file_list_to_csv(MTT_file_list, "[METRIC OUTPUT] trips_by_link.csv")
# file_list_to_csv(MMS_file_list, "[METRIC OUTPUT] trips_by_link_with_mode_share.csv")
file_list_to_csv(MRDATA_file_list, "rdatacompiled.csv")

