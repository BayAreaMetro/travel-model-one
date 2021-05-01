#Synthetic Population Spatial Sampler Routine
#Ben Stabler, ben.stabler@rsginc.com, 08/29/16
#Modified by Justin Culp, justin.culp@rsginc.com 09/12/17
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
#
# This file samples households and persons from an input synthetic population. The sampling is based on 
# a file of sample rates by TAZ. Input and output files are specified via command line arguments
# 
# Input files:
#    
#   Argument 1:    Sample rate file.    'landuse/sampleRateByTaz.csv'
#   Argument 2:    Household file.      'landuse/households.csv'
#   Argument 3:    Person file.         'landuse/persons.csv'
#
# Output files
#   Argument 4:    Household file.      'landuse/households_sample.csv'
#   Argument 5:    Person file.         'landuse/persons.csv'
#

import os, sys, ast
import pandas as pd
import numpy as np
import random

#Calculate Sample Rates
def calcSampleRate(skimFile, tazFile, outFileName, home_county_array):
    skim_df = pd.read_csv(skimFile)
    zones = pd.read_csv(tazFile)

    home_county = home_county_array

    skim_df.columns = ['ORIGIN', 'DESTINATION', 'DISTANCE']
    skim_df['DESTINATION'] = skim_df['DESTINATION'].astype(str).astype(int)
    solpa_counties = zones[zones['COUNTY'].isin([6,7])]
    solano_napa_dest = pd.merge(skim_df, solpa_counties[['ZONE', 'COUNTY']], left_on = 'DESTINATION', right_on = 'ZONE', how = 'inner')
    dist_solpa = pd.DataFrame(solano_napa_dest.groupby('ORIGIN')['DISTANCE'].min())

    for index, row in zones.iterrows():
        zone = row['ZONE']
        county = row['COUNTY']

        if county in home_county:
            zones.at[index, 'sampleRate'] =  3.0
        else:
            dist = dist_solpa.at[int(zone), 'DISTANCE']
            if dist < 3:
                zones.at[index, 'sampleRate'] = 1.0
            elif dist >= 3 and dist < 5:
                zones.at[index, 'sampleRate'] = 0.5
            elif dist >= 5 and dist < 10:
                zones.at[index, 'sampleRate'] = 0.4
            elif dist >= 10 and dist < 15:
                zones.at[index, 'sampleRate'] = 0.3
            elif dist >= 15 and dist < 20:
                zones.at[index, 'sampleRate'] = 0.2
            elif dist >= 20 and dist < 40:
                zones.at[index, 'sampleRate'] = 0.1
            elif dist >= 40 and dist < 10000:
                zones.at[index, 'sampleRate'] = 0.05

    write_df = zones[['ZONE', 'sampleRate']]
    write_df.columns = ['TAZ', 'SampleRate']
    write_df.to_csv(outFileName, index=False)


# Define working functions
def sample_hhs(group):

	#sample using the taz sample rate with replacement and a stable group seed
    seed = int(group['TAZ'].min()*100 + group['hhincbin'].min()*10 + group['hhsizebin'].min())
    sample = group.sample(frac=group.SampleRate.min(), replace=True, random_state=seed)
    
    if len(sample)==0:
        sample = group.sample(n=1, replace=True, random_state=seed)
        effectiveRate = 1.0 * len(sample)/len(group)
        print("TAZ %i hhincbin %s hhsizebin %s sample rate %.2f effective rate %.2f" % (group.TAZ.min(), group.hhincbin.min(), group.hhsizebin.min(), group.SampleRate.min(), effectiveRate))
    else:
        #set hh expansion factor based on actual sample size since sampling is lumpy
        #sample.hhexpfac = 1.0 / (len(sample)*1.0/len(group)) 
        effectiveRate = 1.0 * len(sample)/len(group)		
        print("TAZ %i hhincbin %s hhsizebin %s sample rate %.2f effective rate %.2f" % (group.TAZ.min(), group.hhincbin.min(), group.hhsizebin.min(), group.SampleRate.min(), effectiveRate))
    
    # replace the target sample rate with the actual sample rate
    sample['SampleRate'] = effectiveRate
    
    return(sample)


def runPopSampler(tazSampleRateFileName, hhFileName, perFileName):
    # Read in TAZ sample rate table as pandas dataframe
    sampleRates = pd.read_csv(tazSampleRateFileName, delimiter=',')
    
    # Read in pop syn household table as pandas dataframe
    households = pd.read_csv(hhFileName, delimiter=',')
    
    # Read in popsyn persons table as pandas dataframe
    persons = pd.read_csv(perFileName, delimiter=',')
    
    #join sample rate by home taz
    households = pd.merge(households, sampleRates, left_on='TAZ', right_on='TAZ')
	
    #bin hhs by income and size
    incbins = [-99999, 50000, 100000, households['HINC'].max()+1]
    households['hhincbin'] = pd.cut(households['HINC'], incbins, labels=False) # Double check household income field
    sizebins = [-1, 1, 2, 3, households['PERSONS'].max()+1]
    households['hhsizebin'] = pd.cut(households['PERSONS'], sizebins, labels=False) # Double check household size field
    
   #group hhs by taz, hhincbin, hhsizebin and sample and reset index
    hhsGrouped = households.groupby(['TAZ', 'hhincbin', 'hhsizebin'])
    new_households = hhsGrouped.apply(sample_hhs)
	
	
    new_households = new_households.reset_index(drop=True)
    
    #update ids and expand persons
    new_households['hhno_new'] = range(1,len(new_households)+1)
    new_persons = pd.merge(persons, new_households[["HHID","hhno_new", "SampleRate"]], left_on="HHID", right_on="HHID", )
    new_households['HHID'] = new_households['hhno_new'].astype(np.int32)
    new_persons['HHID'] = new_persons['hhno_new'].astype(np.int32)
    
       #delete added fields
    del new_households['hhno_new']
#    del new_households['TAZ_SEQ']
#    del new_households['SampleRate']
    del new_households['hhincbin']
    del new_households['hhsizebin']
    del new_persons['hhno_new']
    #del new_households['ORIG_TAZ']
#    del new_households['ORIG_MAZ']
	
	#sort data
    new_households.sort_values('HHID', ascending=True, inplace=True)
    new_persons.sort_values(['HHID','PERID'], ascending=[True,True], inplace=True)
	
	#reset perid to sequential number
    new_persons['PERID'] = range(1,len(new_persons)+1)

    # Write new households file to output data folder
    new_households.to_csv(hhFileName, sep=',', index=False)
        
    # Write new persons file to output data folder
    new_persons.to_csv(perFileName, sep=',', index=False)
   

# Run main
if __name__== "__main__":

	#Get argument inputs
	taz_sample_rate_file = sys.argv[1] #'sampleRateByTaz.csv'
	hh_file_name = sys.argv[2] #'households.csv'
	per_file_name = sys.argv[3] #'persons.csv'
	skim_file_name = sys.argv[4] #HWYSKMMD.csv
	taz_file_name = sys.argv[5] #tazData.csv
	select_counties = ast.literal_eval(sys.argv[6])

	print(taz_sample_rate_file)
	print(hh_file_name)
	print(per_file_name)

	calcSampleRate(skim_file_name, taz_file_name, taz_sample_rate_file, select_counties)
	runPopSampler(taz_sample_rate_file, hh_file_name, per_file_name)
	
	print "*** Finished ***"