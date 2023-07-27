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


# for calculating number of full time workers by industry, and num of full time workers with telecommutable jobs
# -------
# read in the destination choice size coefficients (for the relationship between income and industry)
SizeCoeff_df = pd.read_csv(os.path.join(os.getcwd(), 'ctramp', 'model', 'DestinationChoiceSizeCoefficients.csv'), index_col=False, sep=",")

# read in the input on % of jobs that can be performed at home by industry
WFHbyIndustry_df = pd.read_csv(os.path.join(os.getcwd(), 'ctramp','core_summaries', 'wfh_by_industry.csv'), index_col=False, sep=",", nrows=7)


# for the super district level summary
# ------
# read in the taz-superdistrict correspondence
#tazSD_df = pd.read_csv(os.path.join(os.getcwd(),'landuse', 'tazData.csv'), index_col=False, sep=",")

# read in the land use data about job types
# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
tazData_df = pd.read_csv(os.path.join(os.getcwd(),"landuse", "tazData.csv"), index_col=False, sep=",")

tazSD_df = tazData_df[['ZONE','SD','COUNTY']]
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
# data processing -  calculate percent no work tours
# -----------------------

# group only by work location and income
TelecommuteByWrkLoc_df = TelecommuteByIncome_df.groupby(['WorkLocation','incQ'], as_index=False).sum()

# calculate percent telecommute
TelecommuteByWrkLoc_df['percent_NoWorkTours'] = TelecommuteByWrkLoc_df['num_NoWorkTours'] / TelecommuteByWrkLoc_df['num_ftworkers_wWrkLoc']


# -----------------------
# data processing - calculate number of full time workers by industry, and num of full time workers with telecommutable jobs
# -----------------------

# keep only if the purpose is for work
SizeCoeff_df = SizeCoeff_df.loc[SizeCoeff_df['purpose'] == 'work']

# code income quantile
SizeCoeff_df['incQ'] = 0
SizeCoeff_df.loc[SizeCoeff_df['segment']=="low", 'incQ'] = 1
SizeCoeff_df.loc[SizeCoeff_df['segment']=="med", 'incQ'] = 2
SizeCoeff_df.loc[SizeCoeff_df['segment']=="high", 'incQ'] = 3
SizeCoeff_df.loc[SizeCoeff_df['segment']=="very high", 'incQ'] = 4

# add suffix to the column name
SizeCoeff_df.rename(columns={"RETEMPN": "RETEMPN_SizeCoeff"}, inplace=True)
SizeCoeff_df.rename(columns={"FPSEMPN": "FPSEMPN_SizeCoeff"}, inplace=True)
SizeCoeff_df.rename(columns={"HEREMPN": "HEREMPN_SizeCoeff"}, inplace=True)
SizeCoeff_df.rename(columns={"OTHEMPN": "OTHEMPN_SizeCoeff"}, inplace=True)
SizeCoeff_df.rename(columns={"AGREMPN": "AGREMPN_SizeCoeff"}, inplace=True)
SizeCoeff_df.rename(columns={"MWTEMPN": "MWTEMPN_SizeCoeff"}, inplace=True)

# merge in the size coeff
TelecommuteEligible_df= pd.merge(TelecommuteByWrkLoc_df, SizeCoeff_df[['incQ', 'RETEMPN_SizeCoeff', 'FPSEMPN_SizeCoeff', 'HEREMPN_SizeCoeff', 'OTHEMPN_SizeCoeff', 'AGREMPN_SizeCoeff', 'MWTEMPN_SizeCoeff']], left_on='incQ', right_on='incQ', how='left')

# calculate number of full time workers by industry
TelecommuteEligible_df['ftworkers_RETEMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['RETEMPN_SizeCoeff']
TelecommuteEligible_df['ftworkers_FPSEMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['FPSEMPN_SizeCoeff']
TelecommuteEligible_df['ftworkers_HEREMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['HEREMPN_SizeCoeff']
TelecommuteEligible_df['ftworkers_OTHEMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['OTHEMPN_SizeCoeff']
TelecommuteEligible_df['ftworkers_AGREMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['AGREMPN_SizeCoeff']
TelecommuteEligible_df['ftworkers_MWTEMPN'] = TelecommuteEligible_df['num_ftworkers_wWrkLoc']*TelecommuteEligible_df['MWTEMPN_SizeCoeff']

# process the input on % of jobs that can be performed at home by industry
WFHbyIndustry_df=WFHbyIndustry_df.set_index('naics_mtc')

RETEMPN_PercentEligible = WFHbyIndustry_df.at['retempn','share']
FPSEMPN_PercentEligible = WFHbyIndustry_df.at['fpsempn','share']
HEREMPN_PercentEligible = WFHbyIndustry_df.at['herempn','share']
OTHEMPN_PercentEligible = WFHbyIndustry_df.at['othempn','share']
AGREMPN_PercentEligible = WFHbyIndustry_df.at['agrempn','share']
MWTEMPN_PercentEligible = WFHbyIndustry_df.at['mwtempn','share']

# calculate number of full time workers with telecommutable jobs
TelecommuteEligible_df['ftworkers_eligible_RETEMPN'] = TelecommuteEligible_df['ftworkers_RETEMPN']*RETEMPN_PercentEligible
TelecommuteEligible_df['ftworkers_eligible_FPSEMPN'] = TelecommuteEligible_df['ftworkers_FPSEMPN']*FPSEMPN_PercentEligible
TelecommuteEligible_df['ftworkers_eligible_HEREMPN'] = TelecommuteEligible_df['ftworkers_HEREMPN']*HEREMPN_PercentEligible
TelecommuteEligible_df['ftworkers_eligible_OTHEMPN'] = TelecommuteEligible_df['ftworkers_OTHEMPN']*OTHEMPN_PercentEligible
TelecommuteEligible_df['ftworkers_eligible_AGREMPN'] = TelecommuteEligible_df['ftworkers_AGREMPN']*AGREMPN_PercentEligible
TelecommuteEligible_df['ftworkers_eligible_MWTEMPN'] = TelecommuteEligible_df['ftworkers_MWTEMPN']*MWTEMPN_PercentEligible

# -----------------------
# data processing -  add in super district information
# -----------------------
TelecommuteEligible_df  = pd.merge(TelecommuteEligible_df, tazSD_df, left_on=['WorkLocation'], right_on=['ZONE'], how='left')

# home zone

output_filename1 = "core_summaries/num_ftworkers_with_telecommutable_jobs.csv"
TelecommuteEligible_df.to_csv(output_filename1, header=True, index=False)

# -----------------------
# data processing -  create a super district summary
# -----------------------
# aggregate by SD
TelecommuteEligibleBySD_df = TelecommuteEligible_df.groupby('SD', as_index=False).sum()

# keep only the relevant columns
TelecommuteEligibleBySD_df = TelecommuteEligibleBySD_df[['SD','ftworkers_RETEMPN','ftworkers_FPSEMPN', 'ftworkers_HEREMPN','ftworkers_OTHEMPN','ftworkers_AGREMPN','ftworkers_MWTEMPN',
                                                         'ftworkers_eligible_RETEMPN', 'ftworkers_eligible_FPSEMPN', 'ftworkers_eligible_HEREMPN', 'ftworkers_eligible_OTHEMPN', 'ftworkers_eligible_AGREMPN', 'ftworkers_eligible_MWTEMPN',
                                                         'num_NoWorkTours', 'num_ftworkers_wWrkLoc']]


# -----------------------
# data processing - calculate telecommute level
# doing this at the SD level because we'll get negative values if we apply this formula to a very fine geography
# -----------------------
# see discussion on Asana:
# https://app.asana.com/0/403262763383022/1168279114282314
# P(going to work) = P(not taking personal time or sick time) x P(not teleworking)
# From 2015 ACS 5-year, P(telecommuting) = 5.8% (see M:\Development\Travel Model One\Calibration\Version 1.5.0\04 Coordinated Daily Activity Pattern\WorkedFromHome.xlsx)
# From the IPA run 2015_TM152_IPA_16, P(going to work) =80.8%
# Solving Ffor P(taking personal time or sick time):
# 80.8% = (1-P(taking personal time or sick time) x (1-5.8%)
# P(taking personal time or sick time) = 1 - (80.8% / (1-5.8%)) = 14.2%

# P(telecommute) = 1 - (P_GoingToWork / (1-0.142))
TelecommuteEligibleBySD_df['P_telecommute'] = 1 - ((1-(TelecommuteEligibleBySD_df['num_NoWorkTours'] / TelecommuteEligibleBySD_df['num_ftworkers_wWrkLoc']))/(1-0.142))

TelecommuteEligibleBySD_df['num_telecommuters'] = TelecommuteEligibleBySD_df['num_ftworkers_wWrkLoc']*TelecommuteEligibleBySD_df['P_telecommute']

TelecommuteEligibleBySD_df['numEligible_numTele_diff'] = ((TelecommuteEligibleBySD_df['ftworkers_eligible_RETEMPN']
                                                       + TelecommuteEligibleBySD_df['ftworkers_eligible_FPSEMPN']
                                                       + TelecommuteEligibleBySD_df['ftworkers_eligible_HEREMPN']
                                                       + TelecommuteEligibleBySD_df['ftworkers_eligible_OTHEMPN']
                                                       + TelecommuteEligibleBySD_df['ftworkers_eligible_AGREMPN']
                                                       + TelecommuteEligibleBySD_df['ftworkers_eligible_MWTEMPN'])
                                                       - TelecommuteEligibleBySD_df['num_telecommuters'])

# -----------------------
# data processing - add in some TAZ data information
# -----------------------
# types of employment
# RETEMPN	Retail trade employment
# FPSEMPN	Financial and professional services employment
# HEREMPN	Health, educational and recreational service employment
# AGREMPN	Agricultural and natural resources employment
# MWTEMPN	Manufacturing, wholesale trade and transportation employment
# OTHEMPN	Other employment (NAICS-based)

# add suffix to the column names in the tazData
tazData_df.rename(columns={"RETEMPN": "RETEMPN_TazData"}, inplace=True)
tazData_df.rename(columns={"FPSEMPN": "FPSEMPN_TazData"}, inplace=True)
tazData_df.rename(columns={"HEREMPN": "HEREMPN_TazData"}, inplace=True)
tazData_df.rename(columns={"OTHEMPN": "OTHEMPN_TazData"}, inplace=True)
tazData_df.rename(columns={"AGREMPN": "AGREMPN_TazData"}, inplace=True)
tazData_df.rename(columns={"MWTEMPN": "MWTEMPN_TazData"}, inplace=True)

# aggregate by SD
tazDataBySD_df =  tazData_df.groupby('SD', as_index=False).sum()

# add types of employment to the output dataframe
#TelecommuteEligiblebySD_df  = pd.merge(TelecommuteEligiblebySD_df, tazDataBySD_df[['ZONE','RETEMPN_TazData','FPSEMPN_TazData','HEREMPN_TazData','OTHEMPN_TazData','AGREMPN_TazData','MWTEMPN_TazData']], left_on=['WorkLocation'], right_on=['ZONE'], how='left')
TelecommuteEligibleBySD_df = pd.merge(TelecommuteEligibleBySD_df, tazDataBySD_df[['SD','RETEMPN_TazData','FPSEMPN_TazData','HEREMPN_TazData','OTHEMPN_TazData','AGREMPN_TazData','MWTEMPN_TazData']], left_on=['SD'], right_on=['SD'], how='left')

# -----------------------
# final touches for the SuperDistrict summary
# -----------------------

# dedup the taz-SD correspondence file
#TODO: Get 'SD_NUM_NAME', 'COUNTY_NUM_NAME'
tazSDbySD_df = tazSD_df.drop_duplicates(subset=['SD'], keep='last')

# add in SD name
TelecommuteEligibleBySD_df = pd.merge(TelecommuteEligibleBySD_df, tazSDbySD_df[['SD']], left_on=['SD'], right_on=['SD'], how='left')

# add model run id to the output dataframe for Tableau (so we can use wildcard union)
run_id = os.path.basename(os.getcwd())
TelecommuteEligibleBySD_df['run_directory'] = run_id

# reorder the columns
TelecommuteEligibleBySD_df = TelecommuteEligibleBySD_df[['SD','SD_NUM_NAME', 'COUNTY_NUM_NAME',
                                                         'ftworkers_RETEMPN','ftworkers_FPSEMPN', 'ftworkers_HEREMPN','ftworkers_OTHEMPN','ftworkers_AGREMPN','ftworkers_MWTEMPN',
                                                         'ftworkers_eligible_RETEMPN', 'ftworkers_eligible_FPSEMPN', 'ftworkers_eligible_HEREMPN', 'ftworkers_eligible_OTHEMPN', 'ftworkers_eligible_AGREMPN', 'ftworkers_eligible_MWTEMPN',
                                                         'RETEMPN_TazData','FPSEMPN_TazData','HEREMPN_TazData','OTHEMPN_TazData','AGREMPN_TazData','MWTEMPN_TazData',
                                                         'num_NoWorkTours', 'num_ftworkers_wWrkLoc', 'P_telecommute','num_telecommuters', 'numEligible_numTele_diff','run_directory']]

output_filename2 = "core_summaries/TelecommuteEligibleBySD.csv"
TelecommuteEligibleBySD_df.to_csv(output_filename2, header=True, index=False)



# -----------------------
# data processing -  create a summary by SuperDistrict and by income
# I have a slight preference for looking at the SuperDistrict summary (without income disaggregation), because of the 14.2% assumption, but am keeping this here for now
# -----------------------
# aggregate by SD
TelecommuteEligibleBySDByInc_df = TelecommuteEligible_df.groupby(['SD','incQ'], as_index=False).sum()

# keep only the relevant columns
TelecommuteEligibleBySDByInc_df = TelecommuteEligibleBySDByInc_df[['SD','incQ','ftworkers_RETEMPN','ftworkers_FPSEMPN', 'ftworkers_HEREMPN','ftworkers_OTHEMPN','ftworkers_AGREMPN','ftworkers_MWTEMPN',
                                                         'ftworkers_eligible_RETEMPN', 'ftworkers_eligible_FPSEMPN', 'ftworkers_eligible_HEREMPN', 'ftworkers_eligible_OTHEMPN', 'ftworkers_eligible_AGREMPN', 'ftworkers_eligible_MWTEMPN',
                                                         'num_NoWorkTours', 'num_ftworkers_wWrkLoc']]

# calculate telecommute level
# P(telecommute) = 1 - (P_GoingToWork / (1-0.142))
TelecommuteEligibleBySDByInc_df['P_telecommute'] = 1 - ((1-(TelecommuteEligibleBySDByInc_df['num_NoWorkTours'] / TelecommuteEligibleBySDByInc_df['num_ftworkers_wWrkLoc']))/(1-0.142))

TelecommuteEligibleBySDByInc_df['num_telecommuters'] = TelecommuteEligibleBySDByInc_df['num_ftworkers_wWrkLoc']*TelecommuteEligibleBySDByInc_df['P_telecommute']

TelecommuteEligibleBySDByInc_df['numEligible_numTele_diff'] = ((TelecommuteEligibleBySDByInc_df['ftworkers_eligible_RETEMPN']
                                                       + TelecommuteEligibleBySDByInc_df['ftworkers_eligible_FPSEMPN']
                                                       + TelecommuteEligibleBySDByInc_df['ftworkers_eligible_HEREMPN']
                                                       + TelecommuteEligibleBySDByInc_df['ftworkers_eligible_OTHEMPN']
                                                       + TelecommuteEligibleBySDByInc_df['ftworkers_eligible_AGREMPN']
                                                       + TelecommuteEligibleBySDByInc_df['ftworkers_eligible_MWTEMPN'])
                                                       - TelecommuteEligibleBySDByInc_df['num_telecommuters'])

output_filename3 = "core_summaries/TelecommuteEligibleBySDByinc.csv"
TelecommuteEligibleBySDByInc_df.to_csv(output_filename3, header=True, index=False)

# -----------------------
# generates other output 1 - telecommute by work location (at TAZ level)
# -----------------------

# add model run id to the output dataframe for Tableau (so we can use wildcard union)
#run_id = os.path.basename(os.getcwd())
#TelecommuteByWrkLoc_df['run_directory'] = run_id

#output_filename11 = "core_summaries/TelecommuteByWorkLocation.csv"
#TelecommuteByWrkLoc_df.to_csv(output_filename11, header=True, index=False)


# -----------------------
# generates other output 2 (origins and destinations)
# -----------------------

#output_filename12 = "core_summaries/TelecommuteByIncomeByOD.csv"
#TelecommuteByIncome_df.to_csv(output_filename12, header=True, index=False)
