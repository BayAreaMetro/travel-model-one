USAGE = r"""

  Combines synthetic person and housing records for households and group quarters, as well as the melted summary.

  Inputs:
  (1) hh_gq/output_[model_year]/synthetic_households.csv
  (2) hh_gq/output_[model_year]/synthetic_persons.csv
  (3) hh_gq/output_[model_year]/summary_melt.csv
  (4) group_quarters/data/geo_cross_walk.csv
  (5) hh_gq/data/[model_year]_COUNTY_controls.csv

  Outputs:
  (1) output_[model_year]/synthetic_households.csv
  (2) output_[model_year]/synthetic_persons.csv
  (3) output_[model_year]/summary_melt.csv

  Basic functions:
  (a) Concatenates person and housing records for households and group quarters, creating a
      unique HHID and PERID.
  (b) Add TAZ to group quarters from MAZ (it's not there since there are no TAZ level controls)
  (c) Add MTCCountyID to all
  (c) Fills NaN values with -9
  (d) Downcasts columns to int
  (e) Adds county-level household summaries to summary_melt since they're not there.

"""

import pandas, numpy

# based on: https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold, PopSyn scripts
HOUSING_COLUMNS = {"HHID":"HHID", 
                   "BCMTAZ":"TAZ",
                   #("hinccat1",            "hinccat1"),  # commented out since this is added after hh+gq combine
                   "hh_income_2000":"HINC",
                   "hh_workers_from_esr":"hworkers",
                   "VEH":"VEHICL",
                   "NP":"PERSONS",
                   "HHT":"HHT",
                   "TYPE":"UNITTYPE"}

  # based on: https://github.com/BayAreaMetro/modeling-website/wiki/PopSynPerson, PopSyn scripts
PERSON_COLUMNS = {'HHID':'HHID',
                  "PERID":"PERID",
                  "AGEP":"AGE",
                  "SEX":"SEX",
                  "employ_status":"pemploy",
                  "student_status":"pstudent",
                  "person_type":"ptype"}


geocrosswalk_df = pandas.read_csv("popsyn/geo_crosswalk.csv")
taz_seq = pandas.read_csv("hwy/complete_network_zone_seq.csv")
taz_seq_dict = dict(zip(taz_seq['N'],taz_seq['TAZSEQ']))
taz_county_dict = dict(zip(geocrosswalk_df['BCMTAZ'], geocrosswalk_df['COUNTY']))
table_hhgq = pandas.read_csv("popsyn/synthetic_households.csv")
table_hhgq["HHID"] = table_hhgq.unique_hh_id  # this already starts from 1


table_hhgq = table_hhgq[HOUSING_COLUMNS['TM1'].keys()].rename(columns=HOUSING_COLUMNS)
table_hhgq['hinccat1'] = 0
table_hhgq.loc[                           (table_hhgq.HINC< 20000), 'hinccat1'] = 1
table_hhgq.loc[ (table_hhgq.HINC>= 20000)&(table_hhgq.HINC< 50000), 'hinccat1'] = 2
table_hhgq.loc[ (table_hhgq.HINC>= 50000)&(table_hhgq.HINC<100000), 'hinccat1'] = 3
table_hhgq.loc[ (table_hhgq.HINC>=100000)                           , 'hinccat1'] = 4
# recode -9 HHT to 0
table_hhgq.loc[ table_hhgq.HHT==-9, 'HHT'] = 0
table_hhgq['COUNTY'] = table_hhgq['BCMTAZ'].map(taz_county_dict)
table_hhgq['TAZ']=table_hhgq['TAZ'].map(taz_seq_dict)


for column in ['hworkers','VEHICL','PERSONS','HHT','UNITTYPE','hinccat1', 'HINC']:
    table_hhgq[column]=table_hhgq[column].fillna(0)
    table_hhgq[column]=table_hhgq[column].astype(numpy.int64)
table_hhgq.to_csv("popsyn/hhFile.2015.csv",index=False) 
#table_hhgq[~table_hhgq['TAZ'].isin([592, 652, 4137])].to_csv("output/Run_8/hhFile2015.csv",index=False) 
#table_hhgq[~table_hhgq['TAZ'].isin([592, 652, 4137])].to_csv("output_2015/hhFile.2015.csv",index=False)         

table_personsgq = pandas.read_csv("popsyn/synthetic_persons.csv")
table_personsgq["HHID"]  = table_personsgq.unique_hh_id 
table_personsgq["PERID"] = table_personsgq.index + 1 # start from 1
table_personsgq['OCCP'] = numpy.where(table_personsgq['OCCP']==0, 999, table_personsgq['OCCP'])   
table_personsgq = table_personsgq[PERSON_COLUMNS['TM1'].keys()].rename(columns=PERSON_COLUMNS)

for column in ['AGE', 'SEX', 'pemploy', 'pstudent', 'ptype']:
    table_personsgq[column]=table_personsgq[column].fillna(0)
    table_personsgq[column]=table_personsgq[column].astype(numpy.int64)
table_personsgq.to_csv("popsyn/personFile.2015.csv",index=False)  
#table_personsgq[table_personsgq['HHID'].isin(table_hhgq[~table_hhgq['TAZ'].isin([592, 652, 4137])].HHID.unique())].to_csv("output/Run_8/personFile2015.csv",index=False)  
#table_personsgq[table_personsgq['HHID'].isin(table_hhgq[~table_hhgq['TAZ'].isin([592, 652, 4137])].HHID.unique())].to_csv("output_2015/personFile2015.csv",index=False)  