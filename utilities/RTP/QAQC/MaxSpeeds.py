# Script that calculates maximum congested speeds from avgload5period.csv

import os
#from dbfread import DBF
import csv
#import copy
import pandas as pd

# Reads avgload5period.csv
# To do: Check the location of the file nad verify it can read it
Cspd_df = pd.read_csv("avgload5period.csv", sep=",")

# Strip whitespace from column headers
Cspd_df.columns = Cspd_df.columns.str.strip()

# select only columns of interest
Cspd_df = Cspd_df[['cspdEA','cspdAM','cspdMD','cspdPM','cspdEV']]


print(Cspd_df)

# Calculate maximum congested speeds for each time period
MaxCSpd = Cspd_df.max()

# Take this out on final version
print MaxCSpd

# Output: File with the congested speeds by time period
# To Do: Take out dtype line. Also check the location where to write the file
s = open("Max Speeds.txt","w+")
s.write("\nMaximum Congested speeds for run :\n\n%s" %MaxCSpd)
s.close()