import pandas as pd
import numpy as np
from simpledbf import Dbf5
import os
import sys

USAGE = """

python routeLinkMSA AM|MD|PM|EV|EA trnAssignIter VolumeDiffCondition

 For trnAssignIter=1, just aggregates the assignment files across submodes into trnlink[timeperiod]_ALLMSA.csv
 
 For trnAssignIter>1,
   1. Read in previous iteration's aggregated assignment dbf (MSA'd)
   2. Read in current iteration's raw volumes
   3. Checks if the volumes have changed little (e.g. total change over total vol < VolumeDiffCondition)
   4.   If they're unchanged, then we're converged; do nothing
   5.   Otherwise, continue; MSA this iteration's volumes and output new trnlink[timeperiod]_ALLMSA.csv

 Keeps running log in RouteLinkMSALog.csv
 
"""

if len(sys.argv) != 4:
    print (USAGE)
    exit(1)


timeperiod              = sys.argv[1]
trnAssignIter           = int(sys.argv[2])
volDiffCond             = float(sys.argv[3])

subdir                  = "Subdir"+str(trnAssignIter)
routeFileName           = os.path.join(subdir, "trnlink{}_ALLMSA.csv".format(timeperiod))


if trnAssignIter == 0:
    prevTad = False
else:
    prevSubdir              = "Subdir"+str(trnAssignIter-1)
    prevRouteFileName       = os.path.join(prevSubdir, "trnlink{}_ALLMSA.dbf".format(timeperiod))    
    # Read the MSA assignment from the previous iteration
    prevTad_dbf = Dbf5(os.path.join(prevRouteFileName))
    prevTad = prevTad_dbf.to_dataframe()

modes = ['wlk_com_wlk','drv_com_wlk','drv_com_wlk', 'wlk_com_drv', 'wlk_hvy_wlk', 'drv_hvy_wlk', 'wlk_hvy_drv', 'wlk_lrf_wlk',
        'drv_lrf_wlk', 'wlk_lrf_drv', 'wlk_exp_wlk', 'drv_exp_wlk', 'wlk_exp_drv', 'wlk_loc_wlk' ,'drv_loc_wlk',
        'wlk_loc_drv']

combined_df_dict = {}

for mode_ in modes:

    filename = 'trnlink'+timeperiod.lower()+'_'+mode_
    suplinks=['*1','*2','*3','*4','*5','*6','*7','*8','*9']

    _csv = pd.read_csv(os.path.join(filename + '.csv'), names=["A","B","TIME","MODE", #"FREQ",
                                                                    "PLOT", #"COLOR",
                                                                    "STOP_A","STOP_B","DIST",
                                                                    "NAME", #"SEQ",
                                                                    "OWNER",
                                                                    "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB",
                                                                    "BA_VOL","BA_BRDA","BA_XITA","BA_BRDB","BA_XITB",'MATRIX'])

    _dbf = Dbf5(os.path.join(filename + '.dbf'))
    _dbf = _dbf.to_dataframe()[['FREQ','SEQ', 'COLOR']]
    
    _csv['id'] = _csv.index
    _dbf['id'] = _dbf.index
    
    _csv['FREQ'] = _csv['id'].map(dict(zip(_dbf['id'], _dbf['FREQ'])))
    _csv['SEQ'] = _csv['id'].map(dict(zip(_dbf['id'], _dbf['SEQ'])))
    _csv['COLOR'] = _csv['id'].map(dict(zip(_dbf['id'], _dbf['COLOR'])))

    _csv = _csv[~_csv['NAME'].isin(suplinks)]

    _csv=_csv[_csv['SEQ'].notnull()]

    _csv.drop(columns='id', inplace=True)

    combined_df_dict[mode_] = _csv
    print("Read ", filename)

    del(_csv)
    del(_dbf)


mode_df = pd.concat(combined_df_dict.values(), ignore_index=True)



agg_function = {'TIME': 'mean',
                'PLOT': 'mean',
                'STOP_A': 'mean',
                'STOP_B': 'mean',
                'DIST': 'mean',
                'FREQ': 'mean',
                'SEQ': 'mean',
                'AB_VOL': 'sum',
                'AB_BRDA': 'sum',
                'AB_XITA': 'sum',
                'AB_BRDB': 'sum',
                'AB_XITB': 'sum',
                'BA_VOL': 'sum',
                'BA_BRDA': 'sum',
                'BA_XITA': 'sum',
                'BA_BRDB': 'sum',
                'BA_XITB': 'sum',
                'NAME': 'first',
                'OWNER': 'first',
                'MATRIX': 'first',
                'COLOR': 'first'}

mode_df_grouped = mode_df.groupby(['A','B','MODE']).agg(agg_function).reset_index()
print ('Grouped')
mode_df_grouped['A'] = mode_df_grouped['A'].astype(str)
mode_df_grouped['B'] = mode_df_grouped['B'].astype(str)
mode_df_grouped['AB'] = mode_df_grouped['A']+'_'+mode_df_grouped['B']
mode_df_grouped['SEQ'] = mode_df_grouped['SEQ'].apply(lambda x: str(int(x)))

mode_df_grouped['ABNAMESEQ'] = mode_df_grouped['A']+'_'+mode_df_grouped['B']+'_'+mode_df_grouped['NAME']+'_'+mode_df_grouped['SEQ']
print ('ABNAMESEQ created')
LAMBDA       = float(1.0/float(trnAssignIter+1))
totVol       = 0
totalDeltaVol= 0

if prevTad:

    mode_df_grouped     =   mode_df_grouped.merge(prevTad, on='ABNAMESEQ', how='left', suffixes=('','_prev'))

    for col in ['AB_VOL', 'AB_BRDA', 'AB_XITA', 'AB_BRDB', 'AB_XITB', 'BA_VOL','BA_BRDA', 'BA_XITA', 'BA_BRDB', 'BA_XITB']:

        mode_df_grouped[col]    = (LAMBDA*mode_df_grouped[col]) +((1.0-LAMBDA)*mode_df_grouped[col+'_prev'])

    mode_df_grouped['deltaVol'] = abs(mode_df_grouped["AB_VOL"]-mode_df_grouped["AB_VOL_prev"])

    totVol       = mode_df_grouped["AB_VOL"].sum()
    totalDeltaVol= mode_df_grouped['deltaVol'].sum()

criteriaMet = False
pctDiffVol = totalDeltaVol/(totVol+0.001)
if prevTad and pctDiffVol < volDiffCond:
    criteriaMet = True

# Might two different try do do this at the same time?
f = open("RouteLinkMSALog.csv","a")
f.write("%d,%s,%f,%f,%d\n" % (trnAssignIter,timeperiod,mode_df_grouped["AB_VOL"].sum(),pctDiffVol,criteriaMet))
f.close()

# write the link sum aggregates if it's the last one
linkSumFileName = None
if criteriaMet:
    linkSumFileName=routeFileName.replace(".csv", "_linksum.csv")
    
#read supplemental files

system_file = pd.read_csv('../transitLineToVehicle.csv') #'Name', 'System','Stripped', 'Line', 'FullLineName', 'AM Vehicle Type','PM Vehicle Type', 'OP Vehicle Type'
vehicletype_file = pd.read_csv('../transitPrefixToVehicle.csv') #'Prefix', 'System', 'VehicleType'
capacity_file = pd.read_csv('../transitVehicleToCapacity.csv') #'VehicleType	100%Capacity	85%Capacity	VehicleCategory	SimpleDelayPerStop	ConstDelayPerStop	DelayPerBoard	DelayPerAlight
print ('Extra files read')
if timeperiod == 'AM':
    system_file['VehicleType'] = system_file[ 'AM Vehicle Type']
elif timeperiod == 'PM':
    system_file['VehicleType'] = system_file[ 'PM Vehicle Type']
else:
    system_file['VehicleType'] = system_file[ 'OP Vehicle Type']


HOURS_PER_TIMEPERIOD = {# https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
                        "EA":3.0,
                        "AM":4.0,
                        "MD":5.0,
                        "PM":4.0,
                        "EV":8.0 }

TIMEPERIOD_FACTOR = {}

for tp in ["AM", "MD", "PM", "EV", "EA"]:
    TIMEPERIOD_FACTOR[tp] = 1.0/HOURS_PER_TIMEPERIOD[tp]

muni_peaking = {"AM":0.45, # 0.39 / 0.85 (Muni peaking factor from 2010 APC / Muni's capacity ratio)
                "MD":1/HOURS_PER_TIMEPERIOD["MD"],
                "PM":0.45,
                "EV":0.2,
                "EA":1/HOURS_PER_TIMEPERIOD["EA"]}   

TIMEPERIOD_FACTOR[20]  = muni_peaking # muni cable car
TIMEPERIOD_FACTOR[21]  = muni_peaking # muni local bus
TIMEPERIOD_FACTOR[110] = muni_peaking # muni LRT

def tp_factor(vehcap, mode):
    if vehcap == 0:
        return 0
    else:
        if mode in  TIMEPERIOD_FACTOR.keys():
            return TIMEPERIOD_FACTOR[mode][timeperiod]
        else:
            return TIMEPERIOD_FACTOR[timeperiod]

mode_df_grouped['SYSTEM'] = mode_df_grouped['NAME'].map(dict(zip(system_file['Name'], system_file['System'])))
mode_df_grouped['FULLNAME'] = mode_df_grouped['NAME'].map(dict(zip(system_file['Name'], system_file['FullLineName'])))
mode_df_grouped['VEHTYPE'] = mode_df_grouped['NAME'].map(dict(zip(system_file['Name'], system_file['VehicleType'])))
mode_df_grouped['VEHCAP'] = mode_df_grouped['VEHTYPE'].map(dict(zip(capacity_file['VehicleType'], capacity_file['100%Capacity']))).fillna(0)

mode_df_grouped["PERIODCAP"] = HOURS_PER_TIMEPERIOD[timeperiod]* 60.0 * mode_df_grouped['VEHCAP']/mode_df_grouped["FREQ"].fillna(0)
mode_df_grouped["tp_factor"] = mode_df_grouped.apply(lambda x: tp_factor(x['VEHCAP'], x['MODE']), axis=1)
mode_df_grouped["LOAD"] = mode_df_grouped["AB_VOL"]* mode_df_grouped['tp_factor'] * mode_df_grouped["FREQ"] / (60.0 * mode_df_grouped["VEHCAP"])
mode_df_grouped['FREQ_INV'] = 1/mode_df_grouped['FREQ']

aggregate_table = mode_df_grouped.groupby(['A','B','AB']).agg({'DIST':'first',
                                                                'VEHCAP':'sum',
                                                                'AB_VOL':'sum',
                                                                'AB_BRDA':'sum',
                                                                'AB_BRDB':'sum',
                                                                'AB_XITA':'sum',
                                                                'AB_XITB':'sum',
                                                                'BA_VOL':'sum',
                                                                'BA_BRDA':'sum',
                                                                'BA_BRDB':'sum',
                                                                'BA_XITA':'sum',
                                                                'BA_XITB':'sum',
                                                                'PERIODCAP':'sum',
                                                                'LOAD':'max',
                                                                'FREQ_INV':'sum'}).reset_index()


aggregate_table['FREQ'] =np.where(aggregate_table['FREQ_INV']>0,
                                  1/aggregate_table['FREQ_INV'],
                                  0)
aggregate_table["LOAD_2"] = np.where(aggregate_table["PERIODCAP"]>0,
                                    aggregate_table["AB_VOL"] / aggregate_table["PERIODCAP"],
                                    0)

aggregate_table['MAXLOAD'] =np.where(aggregate_table['LOAD']>aggregate_table['LOAD_2'],
                                    aggregate_table['LOAD'],
                                    aggregate_table['LOAD_2'])

aggregate_table = aggregate_table[['A','B', 'AB', 'FREQ', 'DIST', 'VEHCAP', 'PERIODCAP', 'LOAD', 'MAXLOAD','AB_VOL','AB_BRDA', 'AB_XITA', 'AB_BRDB', 'AB_XITB', 'BA_VOL','BA_BRDA', 'BA_XITA', 'BA_BRDB', 'BA_XITB']]

mode_df_grouped['GROUP']=""

assignment_table = mode_df_grouped[['A', 'B','TIME', 'MODE', 'FREQ', 'PLOT',"COLOR", 'STOP_A', 'STOP_B', 'DIST',  'NAME',
       'SEQ', 'OWNER','AB','ABNAMESEQ','FULLNAME','SYSTEM','GROUP',"VEHTYPE", "VEHCAP","PERIODCAP","LOAD",
       'AB_VOL', 'AB_BRDA', 'AB_XITA', 'AB_BRDB', 'AB_XITB', 'BA_VOL','BA_BRDA', 'BA_XITA', 'BA_BRDB', 'BA_XITB']]                


assignment_table.to_csv(routeFileName, index=False)
aggregate_table.to_csv(linkSumFileName, index=False)