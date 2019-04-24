import os
from dbfread import DBF
import dbf
import csv
import copy
import pandas as pd
import sys
from pandas import DataFrame

'''
    This code sources transit outputs by links that are sourced in five files, one for each period.
    Based on the volume of trips for each link, and the seating capacity for the link, it calculates a crowding factor.
    This crowding factor is applied as a penalty on in-vehicle transit time, which is number of trips * time for each trip.
    The penalty on the IVTT is used by CoBRA to calculate the benefit that a project may create by alleviating crowding.

    transitcrowding.py is run with the proj folder as an argument. eg:
    projects root dir\python transitcrowding.py 1_CaltrainMod\2050_TM150_BF_00_1_CaltrainMod_00

'''

# import seat capacities from lookup file and create dictionary with key:value as vehicletype:seatedcapacity
# this transitSeatCap.csv file should be placed in the working directory with all the project runs and runresults.py
with open('TransitSeatCap.csv', mode='r') as infile:
    reader = csv.reader(infile)
    next(reader)
    transit_seatcap = {rows[0]:float(rows[3]) for rows in reader}

'''
# Making list of base folders
folder_base_list = [i for i in os.listdir('.') if '2050' in i]

# Making list of project folders
project_folders = []
folder_project_list = []
for folder in project_folders:
    os.chdir(os.path.join(os.getcwd(), folder))
    folder_project_list.extend([(folder + '/' + i) for i in os.listdir('.') if '2050' in i])
    os.chdir('..')

# Combined list of folders in which to run transitcrowding.py
folder_list =  folder_project_list + folder_base_list



# Iterating through each folder in which to create crowding metrics csv
for folder in folder_list:
'''    
#os.chdir(os.path.join(os.getcwd(), folder, 'OUTPUT','trn'))
# get transit model output files for five time periods
os.chdir(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT','trn'))
file_list = [i for i in os.listdir('.') if 'ALLMSA.dbf' in i]


# calculate effective ivtt that includes crowding penalty, for each transportation link for each time period

list_rows = []

for file in file_list:

    table = DBF(file, load=True)
    period = file[7:9]       # name of time period is in the file name

    table.field_names += [u'period', u'veh_type_updated', u'seatcap', u'period_seatcap', u'load_seatcap', u'ivtt_hours',\
                            u'crowdingfactor_ukdft', u'crowdingfactor_metrolinx', u'crowdingfactor_metrolinx_max2pt5', \
                             u'effective_ivtt_ukdft', u'effective_ivtt_metrolinx', u'effective_ivtt_metrolinx_max2pt5', \
                             u'crowding_penalty_hrs_ukdft', u'crowding_penalty_hrs_metrolinx', u'crowding_penalty_hrs_metrolinx_max2pt5']                            

    for record in table:

        veh_type_updated = record.get('VEHTYPE')
        
        # manually updating some vehicle types
        if record.get('SYSTEM') == 'AC Transit':
            veh_type_updated = 'AC Plus Bus'
        if "30_1AC" in record.get('NAME'):
            veh_type_updated = 'Motor Articulated Bus'
        if "522VTA" in record.get('NAME'):
            veh_type_updated = 'Motor Articulated Bus'
        if "120_EBART" in record.get('NAME') and (period=='AM' or period=='PM'):
            veh_type_updated = 'eBart 2 car'
        if "120_EBART" in record.get('NAME') and (period!='AM' and period!='PM'):
            veh_type_updated = 'eBart 1 car'

        # updating vehicle types for Crossings projects     
        if "130_RR" in record.get('NAME'):
            veh_type_updated = 'Caltrain PCBB 10 car'
        if veh_type_updated=='8 Car BART' and (period=='AM' or period=='PM'): 
            veh_type_updated = '10 Car BART RENOVATED'
        if veh_type_updated=='8 Car BART' and (period!='AM' and period!='PM'): 
            veh_type_updated = '5 Car BART RENOVATED'
            


        ab_vol = record.get('AB_VOL')
        seat_cap = transit_seatcap.get(veh_type_updated)                           # sourcing seated capacity imported from lookup file
        period_seatcap = record.get('PERIODCAP')/record.get('VEHCAP')*seat_cap    # total seated capacity in time period
        load_seatcap = ab_vol/period_seatcap                                      # load over time period
        ivtt_hours = ab_vol*record.get('TIME')/100/60                                # number of trips * time per trip
        record.update({u'period':period})
        record.update({u'veh_type_updated':veh_type_updated})
        record.update({u'seatcap':seat_cap})
        record.update({u'period_seatcap':period_seatcap})
        record.update({u'load_seatcap':load_seatcap})
        record.update({u'ivtt_hours':ivtt_hours})

        # setting default crowding factors
        cf_metrolinx = 1
        cf_metrolinx_max2pt5 = 1
        cf_ukdft = 1

        # calculating crowding factors based on methodologies from UK DFT and Metrolinx

        if (ab_vol > period_seatcap):
            cf_metrolinx = (((1 + (0.1*(load_seatcap**1.4)))*min(period_seatcap,ab_vol))  +  \
                            ((1.4 + (0.2*(load_seatcap**3.4)))*max(0,ab_vol-period_seatcap))) / ab_vol
            cf_metrolinx_max2pt5 = min(cf_metrolinx,2.5)

            if(load_seatcap >= 2):
                sit   = 1.83
                stand = 2.37
            elif (load_seatcap >= 1.8) & (load_seatcap < 2):
                sit   = 1.68
                stand = 2.20           
            elif (load_seatcap >= 1.6) & (load_seatcap < 1.8):
                sit   = 1.53
                stand = 2.02
            elif (load_seatcap >= 1.4) & (load_seatcap < 1.6):
                sit   = 1.38
                stand = 1.85              
            elif (load_seatcap >= 1.2) & (load_seatcap < 1.4):
                sit   = 1.23
                stand = 1.67              
            elif (load_seatcap >= 1.0) & (load_seatcap < 1.2):
                sit   = 1.08
                stand = 1.50
            else:
                sit   = 1
                stand = 1

            cf_ukdft = ((period_seatcap*sit) + ((ab_vol-period_seatcap)*stand)) / ab_vol

        # calculating effective ivtt = ivtt * crowding factor
        effective_ivtt_ukdft = ivtt_hours * cf_ukdft
        effective_ivtt_metrolinx = ivtt_hours * cf_metrolinx
        effective_ivtt_metrolinx_max2pt5 = ivtt_hours * cf_metrolinx_max2pt5

        crowding_penalty_ukdft = effective_ivtt_ukdft - ivtt_hours
        crowding_penalty_metrolinx = effective_ivtt_metrolinx - ivtt_hours
        crowding_penalty_metrolinx_max2pt5 = effective_ivtt_metrolinx_max2pt5 - ivtt_hours
               

        record.update({u'crowdingfactor_ukdft':cf_ukdft})
        record.update({u'crowdingfactor_metrolinx':cf_metrolinx})
        record.update({u'crowdingfactor_metrolinx_max2pt5':cf_metrolinx_max2pt5})

        record.update({u'effective_ivtt_ukdft':effective_ivtt_ukdft})
        record.update({u'effective_ivtt_metrolinx':effective_ivtt_metrolinx})
        record.update({u'effective_ivtt_metrolinx_max2pt5':effective_ivtt_metrolinx_max2pt5})

        record.update({u'crowding_penalty_hrs_ukdft':crowding_penalty_ukdft})
        record.update({u'crowding_penalty_hrs_metrolinx':crowding_penalty_metrolinx})
        record.update({u'crowding_penalty_hrs_metrolinx_max2pt5':crowding_penalty_metrolinx_max2pt5})

        list_rows.append(list(record.values()))


os.chdir(os.path.join("..", '..'))
df_crowding = pd.DataFrame(list_rows)
df_crowding.columns = table.field_names



# writing file with all columns into output\metrics folder of the project
#'''
transit_crowding_filename = os.path.join(os.getcwd(), 'OUTPUT', 'metrics', "transit_crowding_complete.csv")
df_crowding.to_csv(transit_crowding_filename, header=True, index=False)
print("Wrote transit_crowding_complete.csv into %s/OUTPUT/metrics folder"%sys.argv[1])
#'''

# writing file into essential columns output\metrics folder of the project
df_crowding2 = df_crowding[['NAME', 'SYSTEM', 'AB_BRDA', 'period', 'ivtt_hours',\
            'effective_ivtt_ukdft','effective_ivtt_metrolinx', 'effective_ivtt_metrolinx_max2pt5',\
            'crowding_penalty_hrs_ukdft', 'crowding_penalty_hrs_metrolinx', 'crowding_penalty_hrs_metrolinx_max2pt5']]
transit_crowding_filename = os.path.join(os.getcwd(),  'OUTPUT', 'metrics', "transit_crowding.csv")
df_crowding2.to_csv(transit_crowding_filename, header=True, index=False)

print("Wrote transit_crowding.csv into %s/OUTPUT/metrics folder"%sys.argv[1])

'''
if '/' in folder:
    os.chdir(os.path.join("..", '..'))
else:
    os.chdir('..')        
'''