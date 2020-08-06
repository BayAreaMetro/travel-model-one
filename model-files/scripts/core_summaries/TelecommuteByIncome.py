# This script generates a core summary output of people with jobs/work locations who don't do work tours by income quantile
# Input : main\wsLocResults_%ITER%.csv, and
#         main\personData_%ITER%.csv,
# Output: core_summaries\TelecommuteByIncome.csv,

import pandas as pd

import os.path
from os import path

# -----------------------
# read inputs
# -----------------------

# read in the Mandatory Locations file
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/MandatoryLocation
ITER = os.getenv('ITER')
wsLocResults_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "wsLocResults_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_wsLocResults = len(wsLocResults_df.index)
print "total rows in wsLocResults = " + str(CountRows_wsLocResults)

# read in the person file (it contains activity pattern information)
personData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "personData_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_personData = len(personData_df.index)
print "total rows in personData = " + str(CountRows_personData)

# -----------------------
# data processing
# -----------------------

# determine income quantile
wsLocResults_df['incQ'] = 0
wsLocResults_df.loc[                                       wsLocResults_df['Income'] <  30000, 'incQ'] = 1
wsLocResults_df.loc[ (wsLocResults_df['Income'] >= 30000)&(wsLocResults_df['Income'] <  60000),'incQ'] = 2
wsLocResults_df.loc[ (wsLocResults_df['Income'] >= 60000)&(wsLocResults_df['Income'] < 100000),'incQ'] = 3
wsLocResults_df.loc[  wsLocResults_df['Income'] >= 100000                                     ,'incQ'] = 4

# merge in the activity pattern and individual mandatory tour frequency information
wsLocResults_df = pd.merge(wsLocResults_df, personData_df[['person_id','activity_pattern','imf_choice', 'sampleRate']], left_on='PersonID', right_on='person_id', how='left')

# compute the inverse of sample share (so the results represent the full population)
wsLocResults_df['frequency'] = 1 / wsLocResults_df['sampleRate']

# the field WorkLocation is 0 if no usual work location
# keep only those who have a usual work location
HaveWorkLocation_df = wsLocResults_df.loc[wsLocResults_df['WorkLocation'] != 0]

# keep only those who do not make a work tour
HaveWorkLocation_NoTour_df = HaveWorkLocation_df.loc[HaveWorkLocation_df['imf_choice'] == 0]

# group by income quantile
TelecommuteByIncome_df = HaveWorkLocation_NoTour_df.groupby(['incQ'], as_index=False).sum()

# keep only the income quantile and frequency columns
TelecommuteByIncome_df = TelecommuteByIncome_df[['incQ', 'frequency']]

output_filename = "core_summaries/TelecommuteByIncome.csv"
TelecommuteByIncome_df.to_csv(output_filename, header=True, index=False)
