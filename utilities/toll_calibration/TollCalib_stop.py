# TollCalibration.py
# Script that reads in the average speed by facility of two successive iterations, calculate the sum of square differences of the two
# Outputs a csv file indicating calibration should stop when


import os

# from dbfread import DBF
import csv

# import copy
import pandas as pd

print(os.environ["ITER"])

# Iterations
iter0 = int(os.environ["ITER"]) - 1
iter1 = os.environ["ITER"]

# Read files

AvgSpeedIter0_df = pd.read_table(
    os.path.join(os.getcwd(), "el_gp_avg_speed_iter" + str(iter0) + ".csv"), sep=","
)
AvgSpeedIter1_df = pd.read_table(
    os.path.join(os.getcwd(), "el_gp_avg_speed_iter" + str(iter1) + ".csv"), sep=","
)

# Deleting unnecessary columns
AvgSpeedIter0_df = AvgSpeedIter0_df.drop(
    [
        "TOLLCLASS",
        "Case_AM",
        "Case_MD",
        "Case_PM",
        "facility_name",
        "tollam_da",
        "tollmd_da",
        "tollpm_da",
        "tollam_da_new",
        "tollmd_da_new",
        "tollpm_da_new",
    ],
    1,
)
AvgSpeedIter1_df = AvgSpeedIter1_df.drop(
    [
        "TOLLCLASS",
        "Case_AM",
        "Case_MD",
        "Case_PM",
        "facility_name",
        "tollam_da",
        "tollmd_da",
        "tollpm_da",
        "tollam_da_new",
        "tollmd_da_new",
        "tollpm_da_new",
    ],
    1,
)

# Subtract one matrix from the other. Square of the resulting matrix
SSD_df = (AvgSpeedIter0_df.subtract(AvgSpeedIter1_df)).pow(2)
# print(SSD_df)

# Add all elemnts in the matrix
Totalmat = SSD_df.values.sum()

count_row = AvgSpeedIter0_df.shape[0]

# NormTotalmat = Totalmat/count_row

s = open("Results.txt", "a+")
s.write("\nSSD for iterations %s - %s = %s" % (iter0, iter1, Totalmat))
s.close()

# Create the file to stop the script once the Total < 20

if Totalmat <= 20:
    # s = open("stop.txt","w+")
    with open("Stop.csv", mode="w") as csvfile:
        csvwriter = csv.writer(csvfile)

        csvwriter.writerow(["SSD", "Status"])
        csvwriter.writerow([Totalmat, "Stop"])
