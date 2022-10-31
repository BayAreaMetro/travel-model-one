# This script adds income information to the trip lists (individual trips and joint trips)
# Input : main\indivTripData_%ITER%.csv, 
#         main\jointTripData_%ITER%.csv, and
#         main\householdData_%ITER%.csv
# Output: main\indivTripData_inc_%ITER%.csv, and
#         main\jointTripData_inc_%ITER%.csv
# The output would be used by PreAssign.job

import pandas as pd

import os.path
from os import path

import gc # Garbage Collector interface

# -----------------------
# attach income to the individual trip list
# -----------------------

ITER = os.getenv('ITER')

# read in the household data file (it contains income information)
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/Household
householdData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "householdData_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_householdData = len(householdData_df.index)
print "total rows in input file, householdData = " + str(CountRows_householdData)

# read in the individual trip file
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip
indivTripData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "indivTripData_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_indivTripData = len(indivTripData_df.index)
print "total rows in input file, indivTripData = " + str(CountRows_indivTripData)


# attach income to the trip list
indivTripData_inc_df = pd.merge(indivTripData_df, householdData_df[['hh_id','income']], left_on='hh_id', right_on='hh_id', how='left')

# determine income quantile
indivTripData_inc_df['incQ'] = 0
indivTripData_inc_df.loc[                                            indivTripData_inc_df['income'] <  30000, 'incQ'] = 1
indivTripData_inc_df.loc[ (indivTripData_inc_df['income'] >= 30000)&(indivTripData_inc_df['income'] <  60000),'incQ'] = 2
indivTripData_inc_df.loc[ (indivTripData_inc_df['income'] >= 60000)&(indivTripData_inc_df['income'] < 100000),'incQ'] = 3
indivTripData_inc_df.loc[  indivTripData_inc_df['income'] >= 100000                                          ,'incQ'] = 4

# print out a trip list with income info
output_filename1 = "main/indivTripData_incALL_" + str(ITER) + ".csv"
indivTripData_inc_df.to_csv(output_filename1, header=True, index=False)
print "Finish adding the income varaible to the trip file for individual travel."

# print out a trip list for each income group
indivTripData_incQ1_df = indivTripData_inc_df.loc[indivTripData_inc_df['incQ'] == 1]
output_filenameQ1 = "main/indivTripData_incQ1_" + str(ITER) + ".csv"
indivTripData_incQ1_df.to_csv(output_filenameQ1, header=True, index=False)

indivTripData_incQ2_df = indivTripData_inc_df.loc[indivTripData_inc_df['incQ'] == 2]
output_filenameQ2 = "main/indivTripData_incQ2_" + str(ITER) + ".csv"
indivTripData_incQ2_df.to_csv(output_filenameQ2, header=True, index=False)

indivTripData_incQ3_df = indivTripData_inc_df.loc[indivTripData_inc_df['incQ'] == 3]
output_filenameQ3 = "main/indivTripData_incQ3_" + str(ITER) + ".csv"
indivTripData_incQ3_df.to_csv(output_filenameQ3, header=True, index=False)

indivTripData_incQ4_df = indivTripData_inc_df.loc[indivTripData_inc_df['incQ'] == 4]
output_filenameQ4 = "main/indivTripData_incQ4_" + str(ITER) + ".csv"
indivTripData_incQ4_df.to_csv(output_filenameQ4, header=True, index=False)

print "Finish printing out a trip list each income group for individual travel."

# -----------------------
# release memory
# https://stackoverflow.com/questions/39100971/how-do-i-release-memory-used-by-a-pandas-dataframe
# -----------------------

del [[indivTripData_df,indivTripData_inc_df]]
gc.collect()
indivTripData_df=pd.DataFrame()
indivTripData_inc_df=pd.DataFrame()

# -----------------------
# attach income to the joint trip list
# -----------------------

# read in the joint trip file
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip
jointTripData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "jointTripData_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_jointTripData = len(jointTripData_df.index)
print "total rows in input file, jointTripData = " + str(CountRows_jointTripData)


# attach income to the trip list
jointTripData_inc_df = pd.merge(jointTripData_df, householdData_df[['hh_id','income']], left_on='hh_id', right_on='hh_id', how='left')

# determine income quantile
jointTripData_inc_df['incQ'] = 0
jointTripData_inc_df.loc[                                            jointTripData_inc_df['income'] <  30000, 'incQ'] = 1
jointTripData_inc_df.loc[ (jointTripData_inc_df['income'] >= 30000)&(jointTripData_inc_df['income'] <  60000),'incQ'] = 2
jointTripData_inc_df.loc[ (jointTripData_inc_df['income'] >= 60000)&(jointTripData_inc_df['income'] < 100000),'incQ'] = 3
jointTripData_inc_df.loc[  jointTripData_inc_df['income'] >= 100000                                          ,'incQ'] = 4


output_filename2 = "main/jointTripData_incALL_" + str(ITER) + ".csv"
jointTripData_inc_df.to_csv(output_filename2, header=True, index=False)
print "Finish adding the income varaible to the trip file for joint travel."

# print out a trip list for each income group
jointTripData_incQ1_df = jointTripData_inc_df.loc[jointTripData_inc_df['incQ'] == 1]
output_filenameQ1 = "main/jointTripData_incQ1_" + str(ITER) + ".csv"
jointTripData_incQ1_df.to_csv(output_filenameQ1, header=True, index=False)

jointTripData_incQ2_df = jointTripData_inc_df.loc[jointTripData_inc_df['incQ'] == 2]
output_filenameQ2 = "main/jointTripData_incQ2_" + str(ITER) + ".csv"
jointTripData_incQ2_df.to_csv(output_filenameQ2, header=True, index=False)

jointTripData_incQ3_df = jointTripData_inc_df.loc[jointTripData_inc_df['incQ'] == 3]
output_filenameQ3 = "main/jointTripData_incQ3_" + str(ITER) + ".csv"
jointTripData_incQ3_df.to_csv(output_filenameQ3, header=True, index=False)

jointTripData_incQ4_df = jointTripData_inc_df.loc[jointTripData_inc_df['incQ'] == 4]
output_filenameQ4 = "main/jointTripData_incQ4_" + str(ITER) + ".csv"
jointTripData_incQ4_df.to_csv(output_filenameQ4, header=True, index=False)

print "Finish printing out a trip list each income group for joint travel."