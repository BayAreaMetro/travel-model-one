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
with open('transitSeatCap.csv', mode='r') as infile:
    reader = csv.reader(infile)
    next(reader)
    transit_seatcap = {rows[0]:float(rows[3]) for rows in reader}

# get transit model output files for five time periods
os.chdir(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT','trn'))
file_list = [i for i in os.listdir('.') if 'ALLMSA.dbf' in i]
  

# calculate effective ivtt that includes crowding penalty, for each transportation link for each time period

list_rows = []

for file in file_list:

    table = DBF(file, load=True)
    period = file[7:9]       # name of time period is in the file name

    table.field_names += [u'period',u'seatcap', u'period_seatcap', u'load_seatcap', u'ivtt',\
                            u'crowdingfactor_ukdft', u'crowdingfactor_metrolinx', u'crowdingfactor_metrolinx_max2pt5', \
                             u'effective_ivtt_ukdft', u'effective_ivtt_metrolinx', u'effective_ivtt_metrolinx_max2pt5']                            

    #(table,['A','B','TIME','MODE','FREQ','PLOT','COLOR','STOP_A','STOP_B','DIST','NAME','SEQ OWNER','AB','ABNAMESEQ', \
     # 'FULLNAME','SYSTEM','GROUP','AB_BRDA','AB_XITA','AB_BRDB','AB_XITB', 'BA_BRDA','BA_XITA','BA_BRDB','BA_XITB'])


    for record in table:

        ab_vol = record.get('AB_VOL')
        seat_cap = transit_seatcap.get(record.get('VEHTYPE'))                   # sourcing seated capacity imported from lookup file
        period_seatcap = record.get('PERIODCAP')/record.get('VEHCAP')*seat_cap  # total seated capacity in time period
        load_seatcap = ab_vol/period_seatcap                                    # load over time period
        ivtt = ab_vol*record.get('TIME')/100/60                         # number of trips * time per trip
        record.update({u'period':period})
        record.update({u'seatcap':seat_cap})
        record.update({u'period_seatcap':period_seatcap})
        record.update({u'load_seatcap':load_seatcap})
        record.update({u'ivtt':ivtt})

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
        effective_ivtt_ukdft = ivtt * cf_ukdft
        effective_ivtt_metrolinx = ivtt * cf_metrolinx
        effective_ivtt_metrolinx_max2pt5 = ivtt * cf_metrolinx_max2pt5

        record.update({u'crowdingfactor_ukdft':cf_ukdft})
        record.update({u'crowdingfactor_metrolinx':cf_metrolinx})
        record.update({u'crowdingfactor_metrolinx_max2pt5':cf_metrolinx_max2pt5})

        record.update({u'effective_ivtt_ukdft':effective_ivtt_ukdft})
        record.update({u'effective_ivtt_metrolinx':effective_ivtt_metrolinx})
        record.update({u'effective_ivtt_metrolinx_max2pt5':effective_ivtt_metrolinx_max2pt5})
           
        list_rows.append(list(record.values()))


# writing file with all columns into output\metrics folder of the project
os.chdir("..")
df_crowding = pd.DataFrame(list_rows)
transit_crowding_filename = os.path.join(os.getcwd(), "metrics", "transit_crowding_complete.csv")
df_crowding.to_csv(transit_crowding_filename, header=True, index=False)

print("Wrote transit_crowding_complete.csv into %s/OUTPUT/metrics folder"%(sys.argv[1]))

# deleting unnecessary columns to reduce file size
for l in list_rows:
    del l[0:16]
    del l[1:16]
    del l[2:5]
    del l[3:6]

# writing file into essential columns output\metrics folder of the project
df_crowding = pd.DataFrame(list_rows,columns = ['SYSTEM','period','ivtt','effective_ivtt_ukdft','effective_ivtt_metrolinx', 'effective_ivtt_metrolinx_max2pt5'])
transit_crowding_filename = os.path.join(os.getcwd(), "metrics", "transit_crowding.csv")
df_crowding.to_csv(transit_crowding_filename, header=True, index=False)


print("Wrote transit_crowding.csv into %s/OUTPUT/metrics folder"%(sys.argv[1]))

