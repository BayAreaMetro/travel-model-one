# Author: jmh
# Date: 06 2022
# Description: This script takes input network and TAZ files and writes
# out a TAZ density file for CT-RAMP.
#
# Inputs:
#   hwy\taz_nodes.csv: A file with fields N, X, Y, one record per TAZ. Non-Sequential node numbers.
#   hwy\intersection_nodes.csv: A file with fields X and Y, one record per 3+ leg intersection. 
#   landuse\taz_data.csv: A file with fields TAZ,TAZ_ORIGINAL,emp_total,HH,POP,ACRES,ret_reg,ret_loc.
#
# Outputs:
#   landuse\TAZ_density.csv: A TAZ file with fields:
#       TAZ             Sequential TAZ 
#       TAZ_ORIGINAL    Non-sequential TAZ
#       TotInt          Total intersections within 1/2 mile of TAZ
#       EmpDen          Employment per acre within 1/2 mile of TAZ
#       RetDen          Retail employment per acre within 1/2 mile of TAZ
#       DUDen           Households per acre within 1/2 mile of TAZ
#       PopDen          Population per acre within 1/2 mile of TAZ
#       intDenBin       Intersection density bin (1 through 3 where 3 is the highest)
#       empDenBin       Employment density bin (1 through 3 where 3 is the highest)
#       duDenBin        Houseold density bin (1 through 3 where 3 is the highest)
#   landuse\taz_data_withDensity.csv: landuse\taz_data.csv joined with landuse\taz_density.csv on TAZ_ORIGINAL
#   
# Requires: Basic python 2.7.x, pandas
#

# Import modules
import os, csv, datetime, sys, math
import pandas as pd, numpy as np
from shutil import copyfile

# Variables: Input
inTazNodes          = "hwy/taz_nodes.csv"
inIntersectionNodes = "hwy/intersection_nodes.csv"
inTazData           = "landuse/tazData.csv"
outDensityData      = "landuse/taz_density.csv"
outTazData          = "landuse/taz_data_withdensity.csv"
start_time          = datetime.datetime.now()

print inTazNodes
print inIntersectionNodes
print inTazData
print outDensityData

# Open intersection file as pandas table
intersections = pd.read_csv(inIntersectionNodes)
print("Read {} intersections from {}".format(len(intersections), inIntersectionNodes))

# add columns to intersections dataframe
intersections['taz_x'] = 0
intersections['taz_y'] = 0
intersections['distance'] = 0
intersections['count'] = 0

# Open taz node file
readTazNodeFile = open(inTazNodes, 'r')

# Create file reader
reader = csv.DictReader(readTazNodeFile)

# iterate through file and store count of intersections within 1/2 mile of XY coordinates
max_dist_fact = 0.5 # 1/2 mile radius from centroid
max_dist = 5280 * max_dist_fact

max_dist_popempden = 5280 * 5 # 5 miles radius to approximate a zip code (note: avg zip code size in US is 90 sq mi)

int_cnt = []
taz_x = []
taz_y = []
taz_nonseq = []

n = 0
for row in reader:
    taz_n = int(row['TAZ_ORIGINAL'])
    x = float(row['TAZ_X'])
    y = float(row['TAZ_Y'])
    taz_x.append(x)
    taz_y.append(y)
    taz_nonseq.append(taz_n)
    
    intersections['taz_x'] = x
    intersections['taz_y'] = y
    intersections['count'] = 0
    
    intersections['distance'] = intersections.eval("((X-taz_x)**2 + (Y-taz_y)**2)**0.5")    
    int_cnt.append(len(intersections[intersections.distance <= max_dist]))
    if((n % 1000) == 0):
        print ("Counting Intersections for TAZ ", taz_n, " : ", int_cnt[n]) 
    n = n + 1
     
readTazNodeFile.close()

# read in taz data as pandas dataframe
tazData = pd.read_csv(inTazData)

# create dataset and pandas dataframe of taz xy and intersection count
interDataSet = list(zip(taz_nonseq, taz_x, taz_y, int_cnt))
tazIntersections = pd.DataFrame(data=interDataSet,columns=['ZONE', 'TAZ_X','TAZ_Y','INTER_CNT'])

# merge the taz xys with the taz data 
tazData = pd.merge(tazData,tazIntersections,how='inner',on='ZONE')
tazData['dest_x'] = 0
tazData['dest_y'] = 0
tazData['distance'] = 0
tazData.sort_values(by='ZONE')

# get the xy columns and node numbers for iterating
taz_x_seq = tazData['TAZ_X'].tolist()
taz_y_seq = tazData['TAZ_Y'].tolist()
taz_seqn = tazData['ZONE'].tolist()
taz_nonseqn = tazData['ZONE'].tolist()

# create writer
writeTazDensityFile = open(outDensityData, "wb")
writer = csv.writer(writeTazDensityFile, delimiter=',')
outHeader = ["ZONE","TotInt","EmpDen","RetEmpDen","DUDen","PopDen","IntDenBin","EmpDenBin","DuDenBin","PopEmpDenPerMi"]
writer.writerow(outHeader)

# iterate through TAZs and calculate density terms
i = 0
while i < len(taz_seqn):
    origSeqTaz = taz_seqn[i]
    origNonSeqTaz = taz_nonseqn[i]
    interCount = int_cnt[i]
    totEmp=0
    totRet=0
    totHH=0
    totPop=0
    totAcres=0
    empDen=0
    retDen=0
    duDen=0
    popDen=0
    intDenBin = 0
    empDenBin = 0
    duDenBin = 0

    #added for TNC\Taxi wait times
    totPopWaitTime = 0
    totEmpWaitTime = 0
    totAcreWaitTime = 0    
    popEmpWaitTimeDen = 0
    
    tazData['dest_x'] = taz_x_seq[i]
    tazData['dest_y'] = taz_y_seq[i]

    if((i ==0) or (i % 100) == 0):
        print ("Calculating Density Variables for TAZ ", origNonSeqTaz)
 
     
    #sum the variables for all tazs within the max distance
    tazData['distance'] = tazData.eval("((TAZ_X - dest_x)**2 + (TAZ_Y-dest_y)**2)**0.5")    
    totEmp = tazData.loc[tazData['distance'] < max_dist, 'TOTEMP'].sum()
    totRet = tazData.loc[tazData['distance'] < max_dist, 'RETEMPN'].sum() 
    totHH = tazData.loc[tazData['distance'] < max_dist, 'TOTHH'].sum()
    totPop = tazData.loc[tazData['distance'] < max_dist, 'TOTPOP'].sum()
    totAcres = tazData.loc[tazData['distance'] < max_dist, 'TOTACRE'].sum()
    
    # TNC\Taxi wait time density fields
    totPopWaitTime = tazData.loc[tazData['distance'] < max_dist_popempden, 'TOTPOP'].sum()
    totEmpWaitTime = tazData.loc[tazData['distance'] < max_dist_popempden, 'TOTEMP'].sum()
    totAcreWaitTime = tazData.loc[tazData['distance'] < max_dist_popempden, 'TOTACRE'].sum()
    
    # calculate density variables
    if(totAcres>0):
        empDen = totEmp/totAcres
        retDen = totRet/totAcres
        duDen = totHH/totAcres
        popDen = totPop/totAcres

    if(totAcreWaitTime>0):
        popEmpWaitTimeDen = (totPopWaitTime + totEmpWaitTime)/(totAcreWaitTime * 0.0015625)
    
    # calculate bins based on sandag bin ranges
    if (interCount < 80):
        intDenBin=1
    elif (interCount < 130):
        intDenBin=2
    else:
        intDenBin=3
		
    if (empDen < 10):
        empDenBin=1
    elif (empDen < 30):
        empDenBin=2
    else:
        empDenBin=3
		
    if (duDen < 5):
        duDenBin=1
    elif (duDen < 10):
        duDenBin=2
    else:
        duDenBin=3
    
    i = i + 1
 
    
    #write out results to csv file
    outList = [origNonSeqTaz,interCount,empDen,retDen,duDen,popDen,intDenBin,empDenBin,duDenBin,popEmpWaitTimeDen]
    writer.writerow(outList)

writeTazDensityFile.close()

# read the data back in as a pandas table
densityData = pd.read_csv(outDensityData)   

# merge with taz data
tazData = pd.merge(tazData,densityData,how='inner',on='ZONE')

# drop unnecessary fields
tazData.drop('INTER_CNT', axis=1, inplace=True)
tazData.drop('dest_x', axis=1, inplace=True)
tazData.drop('dest_y', axis=1, inplace=True)
tazData.drop('distance', axis=1, inplace=True)

# write the data back out
tazData.to_csv(outTazData, index=False)

end_time = datetime.datetime.now()
duration = end_time - start_time

print "*** Finished in {} minutes ***".format(duration.total_seconds()/60.0)
