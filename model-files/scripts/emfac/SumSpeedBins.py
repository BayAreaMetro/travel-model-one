# Script to create the necessary files for EMFAC
# Will creae the csv files SumSpeedBinsAll_sums.csv, HourlyTotalCounty.csv and ShareSpeedBinsAll_sums.csv
# From the output files CreateSpeedBinsWithinZones_sums.csv and CreateSpeedBinsBetweenZones_sums.csv of CreateSpeedBinsBetweenZns3.job and CreateSpeedBinsWithinZns2.job
# Will replace SumSpeedBins1.awk
import os
#from dbfread import DBF
import csv
#import copy
import pandas as pd

import argparse,collections,csv,os,sys


#parser = argparse.ArgumentParser()
#parser.add_argument("csv", help="Input csv files")

#args = parser.parse_args()

## Not sure how to read the 2 files separately
#csvfile   = open(args.csv)
#csvreader = csv.reader(csvfile)

## Add the file names here
#CountiesBins_df = pd.read_table(os.path.join(os.getcwd(), ), sep=",")
#Inter_df = pd.read_table(os.path.join(os.getcwd(), ), sep=",")
#Intra_df = pd.read_table(os.path.join(os.getcwd(), ), sep=",")


# Read the csv files output from the Cube process

CountiesBins_df = pd.read_table(os.path.join(os.getcwd(), "CreateSpeedBinsBetweenZones_sums.csv"), sep=",")
Inter_df = pd.read_table(os.path.join(os.getcwd(), "CreateSpeedBinsBetweenZones_sums.csv"), sep=",")
Intra_df = pd.read_table(os.path.join(os.getcwd(), "CreateSpeedBinsWithinZones_sums.csv"), sep=",")


# Iaking out the blank spaces on headers

col_rename = {}
for colname in CountiesBins_df.columns.values.tolist(): col_rename[colname] = colname.strip()
CountiesBins_df.rename(columns=col_rename, inplace=True)

col_rename1 = {}
for colname in Inter_df.columns.values.tolist(): col_rename1[colname] = colname.strip
Inter_df.rename(columns=col_rename, inplace=True)

col_rename2 = {}
for colname in Intra_df.columns.values.tolist(): col_rename2[colname] = colname.strip
Intra_df.rename(columns=col_rename, inplace=True)


# Dropping unecessary columns
CountiesBins_df = CountiesBins_df.drop(['hour01','hour02','hour03','hour04','hour05','hour06','hour07','hour08','hour09','hour10','hour11','hour12','hour13','hour14','hour15','hour16','hour17','hour18','hour19','hour20','hour21','hour22','hour23','hour24'],1)
Inter_df = Inter_df.drop(['countyName','arbCounty','speedBin'],1)
Intra_df = Intra_df.drop(['countyName','arbCounty','speedBin'],1)

#print(CountiesBins_df)

#print(Inter_df)

#print(Intra_df)

# Maybe is easier to start with the "SumSpeedBinsAll_sums.csv"
# This is the sum of the 'CreateSpeedBinsBetweenZones_sums.csv' and 'CreateSpeedBinsWithinZones_sums.csv'
# It is a straight sum. Output keeps the total by speed bins and county and hour

SUM_df = (Inter_df.add(Intra_df))

SumSpeedBins_df = pd.concat([CountiesBins_df,SUM_df], axis=1)


SumSpeedBins_df.to_csv(r'SumSpeedBinsAll_sums.csv', index = False, header=True)

# Need to create a file with the sum of the 2 input files. 
# This output file is named "HourlyTotalCounty.csv"
# 

HourlyTotalCounty_df = SumSpeedBins_df.drop(['speedBin'],1)

# Ths groups the counites in alphabetical order. Does it matter? Gawk orders the file by ARB county number. But I couldn't do it using the groupby. Maybe there is a parameter to do it

HourlyTotalCounty_df =  HourlyTotalCounty_df.groupby(['countyName','arbCounty']).sum()

HourlyTotalCounty_df.to_csv(r'HourlyTotalCounty.csv',header=True)


# Create the file ShareSpeedBinsAll_sums.csv
# I'm sure this can be simplified

# Ended up reading the file created in the previous step. I couldn't read the county name and arb county number from the previous dataframe HourlyTotalCounty_df,
# which is the reason I went through this long process.
# I was trying to divide the SumSpeedBins_df by HourlyTotalCounty_df with a list, but as mentioned couldn't read the county name and arb county number
#
# Need to add the Placeholder rows

Temp1_df = pd.read_table(os.path.join(os.getcwd(), "HourlyTotalCounty.csv"), sep=",")

Temp1_df.columns = ['countyName','arbCounty','hour01a','hour02a','hour03a','hour04a','hour05a','hour06a','hour07a','hour08a','hour09a','hour10a','hour11a','hour12a','hour13a','hour14a','hour15a','hour16a','hour17a','hour18a','hour19a','hour20a','hour21a','hour22a','hour23a','hour24a']

# Merge the aggreagte values by county and hour with SumSpeedBins_df to have them all in a single file with the speed bins column
Shares1_df = pd.merge(SumSpeedBins_df, Temp1_df, on=['countyName','arbCounty'])


Temp2_df = Shares1_df.drop(['countyName','arbCounty','speedBin','hour01a','hour02a','hour03a','hour04a','hour05a','hour06a','hour07a','hour08a','hour09a','hour10a','hour11a','hour12a','hour13a','hour14a','hour15a','hour16a','hour17a','hour18a','hour19a','hour20a','hour21a','hour22a','hour23a','hour24a'],1)
Temp3_df = Shares1_df.drop(['countyName','arbCounty','speedBin','hour01','hour02','hour03','hour04','hour05','hour06','hour07','hour08','hour09','hour10','hour11','hour12','hour13','hour14','hour15','hour16','hour17','hour18','hour19','hour20','hour21','hour22','hour23','hour24'],1)
Temp3_df.columns = ['hour01','hour02','hour03','hour04','hour05','hour06','hour07','hour08','hour09','hour10','hour11','hour12','hour13','hour14','hour15','hour16','hour17','hour18','hour19','hour20','hour21','hour22','hour23','hour24']


Shares_df = (Temp2_df.div(Temp3_df))

ShareSpeedBinsAll_sums_df = pd.concat([CountiesBins_df,Shares_df], axis=1)

ShareSpeedBinsAll_sums_df.to_csv(r'ShareSpeedBinsAll_sums.csv',header=True)

