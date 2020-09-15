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
print "total rows in input file, wsLocResults = " + str(CountRows_wsLocResults)

# read in the person file (it contains activity pattern information)
personData_df = pd.read_csv(os.path.join(os.getcwd(), 'main', "personData_" + str(ITER) + ".csv"), index_col=False, sep=",")

CountRows_personData = len(personData_df.index)
print "total rows in input file, personData = " + str(CountRows_personData)

# read in the land use data about job types
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
tazData_df = pd.read_csv(os.path.join(os.getcwd(), 'INPUT', "landuse", "tazData.csv"), index_col=False, sep=",")

# -----------------------
# data processing - generates a core summary output of people with jobs/work locations who don't do work tours by income quantile
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

# keep only those who are full time workers
wsLocResults_df = wsLocResults_df.loc[wsLocResults_df['EmploymentCategory'] == 'Full-time worker']
CountRows_wsLocResults = len(wsLocResults_df.index)
print "total rows in wsLocResults, after dropping all non-ftworkers = " + str(CountRows_wsLocResults)

# the field WorkLocation is 0 if no usual work location
# keep only those who have a usual work location
HaveWorkLocation_df = wsLocResults_df.loc[wsLocResults_df['WorkLocation'] != 0]
CountRows_HaveWorkLocation = len(HaveWorkLocation_df.index)
print "total rows in HaveWorkLocation = " + str(CountRows_HaveWorkLocation)

# keep only those who do not make a work tour
HaveWorkLocation_NoTour_df = HaveWorkLocation_df.loc[HaveWorkLocation_df['imf_choice'] == 0]
CountRows_HaveWorkLocation_NoTour = len(HaveWorkLocation_NoTour_df.index)
print "total rows in HaveWorkLocation, and with no mandatory tour = " + str(CountRows_HaveWorkLocation_NoTour)

# group by income quantile
TelecommuteByIncome_df = HaveWorkLocation_NoTour_df.groupby(['HomeTAZ','WorkLocation','incQ'], as_index=False).sum()

# keep only the relevant columns
TelecommuteByIncome_df = TelecommuteByIncome_df[['HomeTAZ','WorkLocation','incQ', 'frequency']]

# rename frequency to num_NoWorkTours
TelecommuteByIncome_df.rename(columns={"frequency": "num_NoWorkTours"}, inplace=True)

# -----------------------
# data processing -  add total number of full time workers with usual work location to the output file
# -----------------------
HaveWorkLocation_df = HaveWorkLocation_df.groupby(['HomeTAZ','WorkLocation','incQ'], as_index=False).sum()

# keep only the relevant columns
HaveWorkLocation_df = HaveWorkLocation_df[['HomeTAZ','WorkLocation','incQ', 'frequency']]

# rename frequency to num_ftworkers_wWrkLoc
HaveWorkLocation_df.rename(columns={"frequency": "num_ftworkers_wWrkLoc"}, inplace=True)

# add total number of full time workers with usual work location to the output dataframe
TelecommuteByIncome_df  = pd.merge(TelecommuteByIncome_df, HaveWorkLocation_df[['HomeTAZ','WorkLocation','incQ', 'num_ftworkers_wWrkLoc']], left_on=['HomeTAZ','WorkLocation','incQ'], right_on=['HomeTAZ','WorkLocation','incQ'], how='right')

# -----------------------
# data processing -  calculate percent telecommute
# -----------------------

# group only by work location and income
TelecommuteByWrkLoc_df = TelecommuteByIncome_df.groupby(['WorkLocation','incQ'], as_index=False).sum()

# calculate percent telecommute
TelecommuteByWrkLoc_df['percent_NoWorkTours'] = TelecommuteByWrkLoc_df['num_NoWorkTours'] / TelecommuteByWrkLoc_df['num_ftworkers_wWrkLoc']


# -----------------------
# data processing -  add in some TAZ data information
# -----------------------
# types of employment
# RETEMPN	Retail trade employment
# FPSEMPN	Financial and professional services employment
# HEREMPN	Health, educational and recreational service employment
# AGREMPN	Agricultural and natural resources employment
# MWTEMPN	Manufacturing, wholesale trade and transportation employment
# OTHEMPN	Other employment (NAICS-based)
# add types of employment to the output dataframe
TelecommuteByWrkLoc_df  = pd.merge(TelecommuteByWrkLoc_df, tazData_df[['ZONE','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN','AGREMPN','MWTEMPN']], left_on=['WorkLocation'], right_on=['ZONE'], how='left')

# keep only the relevant columns
TelecommuteByWrkLoc_df = TelecommuteByWrkLoc_df[['WorkLocation','incQ','num_NoWorkTours','num_ftworkers_wWrkLoc','percent_NoWorkTours','RETEMPN','FPSEMPN','HEREMPN','OTHEMPN','AGREMPN','MWTEMPN']]


# -----------------------
# generates output 1
# -----------------------

# add model run id to the output dataframe for Tableau (so we can use wildcard union)
run_id = os.path.basename(os.getcwd())
TelecommuteByWrkLoc_df['run_directory'] = run_id

output_filename = "core_summaries/TelecommuteByWorkLocation.csv"
TelecommuteByWrkLoc_df.to_csv(output_filename, header=True, index=False)

# re. the "no work tours" terminology:
# note that P(not going to work) = P(taking personal time or sick time) x P(teleworking)
# And we had in https://app.asana.com/0/403262763383022/1168279114282314, we had P(taking personal time or sick time) = 1 - (80.8% / (1-5.8%)) = 14.2%
