
# This script reads cdapResults, filters person type 1, does 1- M/(1-0.142). Output a single value.


import pandas as pd

import os.path
from os import path

# -----------------------
# read inputs
# -----------------------
# read in cdap results
cdapResults_df = pd.read_csv(os.path.join(os.getcwd(), "main", "cdapResults.csv"), index_col=False, sep=",")

# -----------------------
# data processing
# -----------------------
# select full-time workers
ftworkers_df = cdapResults_df.loc[cdapResults_df['PersonType'] == 1]
# count number of rows
total_ftworkers = len(ftworkers_df.index)
# print "total ft workers = " + str(total_ftworkers)

# select full time workers with the Mandatory pattern
ftworkersM_df = ftworkers_df.loc[ftworkers_df['ActivityString'] == 'M']
# count number of rows
total_ftworkersM = len(ftworkersM_df.index)
# print "total ft workers with the Mandatory pattern = " + str(total_ftworkersM)

# calculate the percentage of full-time workers making a mandatory tour, P(going to work)
P_GoingToWork = float(total_ftworkersM) / float(total_ftworkers)
print ("percent of ft workers making a mandatory tour = " + str(P_GoingToWork))

# calculate telecommute level
# see discussion on Asana:
# https://app.asana.com/0/403262763383022/1168279114282314
# P(going to work) = P(not taking personal time or sick time) x P(not teleworking)
# From 2015 ACS 5-year, P(telecommuting) = 5.8% (see M:\Development\Travel Model One\Calibration\Version 1.5.0\04 Coordinated Daily Activity Pattern\WorkedFromHome.xlsx)
# From the IPA run 2015_TM152_IPA_16, P(going to work) =80.8%
# Solving Ffor P(taking personal time or sick time):
# 80.8% = (1-P(taking personal time or sick time) x (1-5.8%)
# P(taking personal time or sick time) = 1 - (80.8% / (1-5.8%)) = 14.2%

# Assume P(taking personal time or sick time) remains constant over time
# Solving for  P(telecommuting) for the model run
# P(telecommuting) = 1 - (P(going to work) / P(not taking personal time or sick time)
P_Telecommuting = 1 - (P_GoingToWork / (1-0.142))
print ("Telecommuting level = " + str(P_Telecommuting))

# -----------------------
# output a single number to the QAQC file
# -----------------------
# constructing DataFrame from a dictionary
Telecommute_df = pd.DataFrame({"Telecommute_Level":[P_Telecommuting]})

output_filename = "QAQC/PBA50_QAQC.csv"
#if os.path.exists(os.path.join(os.getcwd(), "QAQC", "PBA50_QAQC.csv"):
# if path.exists("B:/Projects/2035_TM152_DBP_Plus_08_TelecommuteX2/QAQC/PBA50_QAQC.csv"):
if path.exists(output_filename):
    QAQC_df = pd.read_csv(os.path.join(os.getcwd(), "QAQC", "PBA50_QAQC.csv"), index_col=False, sep=",")
    QAQC_df = pd.merge(QAQC_df, Telecommute_df, left_index=True, right_index=True)
    QAQC_df.to_csv(output_filename, header=True, index=False)
else:
    Telecommute_df.to_csv(output_filename, header=True, index=False)
