# Script that calculates maximum congested speeds from avgload5period.csv

import os
#from dbfread import DBF
import csv
#import copy
import pandas as pd

import os.path
from os import path


# Reads avgload5period.csv
# To do: Check the location of the file and verify it can read it
Cspd_df = pd.read_csv("../extractor/avgload5period.csv", sep=",")

# Strip whitespace from column headers
Cspd_df.columns = Cspd_df.columns.str.strip()

# select only columns of interest
Cspd_df = Cspd_df[['cspdEA','cspdAM','cspdMD','cspdPM','cspdEV']]
AMspd_df = Cspd_df[['cspdAM']]

print(Cspd_df)
print (AMspd_df)

# Calculate maximum congested speeds for each time period
MaxCSpd = Cspd_df.max()
MaxAMSpd = AMspd_df['cspdAM'].max()

# Take this out on final version
print MaxCSpd
print MaxAMSpd

# Output: File with the congested speeds by time period
# To Do: Take out dtype line. Also check the location where to write the file
s = open("Max Speeds.txt","w+")
s.write("\nMaximum Congested speeds for run :\n\n%s" %MaxCSpd)
s.close()

# -----------------------
# output AM maximum speed to the QAQC file
# -----------------------
# constructing DataFrame from a dictionary
MaxSpeed_df = pd.DataFrame({"Max_AM_Speed":[MaxAMSpd]})

output_filename = "PBA50_QAQC.csv"
print output_filename
#Test the else
if path.exists(output_filename):
    QAQC_df = pd.read_csv(os.path.join(os.getcwd(), "PBA50_QAQC.csv"), index_col=False, sep=",")
    QAQC_df = pd.merge(QAQC_df, MaxSpeed_df, left_index=True, right_index=True)
    QAQC_df.to_csv(output_filename, header=True, index=False)
else:
    MaxSpeed_df.to_csv(output_filename, header=True, index=False)