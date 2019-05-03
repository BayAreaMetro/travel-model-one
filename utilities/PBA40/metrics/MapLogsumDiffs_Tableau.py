import os
from dbfread import DBF
import dbf
import csv
import copy
import pandas as pd
import sys
from pandas import DataFrame
from shutil import copyfile

USAGE = """

  python \\mainmodel\MainModelShare\travel-model-one-master\utilities\PBA40\metrics\MapLogsumDiffs_Tableau.py 1_Crossings3\2050_TM151_PPA_RT_00_1_Crossings3_01

  Reads logsums (work and shop) by market segment for project and base  (sources baseID from PPAMasterInput).
  Reads population by market segment.
  Creates csvs with logsums for baseline and project at individual level and total population by market segment
  Creates tableau workbooks that reads these csvs (by copying over tableau workbooks from M:\Application\Model One\Mock Futures\Logsum_sidebyside)

  Outputs:
  Logsum_map_marketsegments.twb represents "raw" logsums
  Logsum_map_population.twb represents "consumer surplus" (?) but it's not calculated using rule of one-half


"""
proj_name = sys.argv[1].split('\\')[1]

# reading logsums by market segment for project
#os.chdir(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT','logsums'))
logsums_work_df = pd.read_table(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "person_workDCLogsum.csv"), sep=",")
logsums_shop_df = pd.read_table(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'logsums', "tour_shopDCLogsum.csv"), sep=",")

# reading logsums by market segment for corresponding base
baseid = proj_name[0:20]
print("Baseline project is %s" %baseid)
logsums_work_df_base = pd.read_table(os.path.join(os.getcwd(), baseid, 'OUTPUT', 'logsums', "person_workDCLogsum.csv"), sep=",")
logsums_shop_df_base = pd.read_table(os.path.join(os.getcwd(), baseid, 'OUTPUT', 'logsums', "tour_shopDCLogsum.csv"), sep=",")

# creating logsums df by market segment for tableau
logsums_work_df['workDCLogsum_base_noCEM'] =   logsums_work_df_base['workDCLogsum']
logsums_work_df['workDCLogsum_proj_noCEM'] = 	logsums_work_df['workDCLogsum']
logsums_work_df = logsums_work_df.drop('workDCLogsum', 1)

logsums_shop_df['dcLogsum_base_noCEM'] =   logsums_shop_df_base['dcLogsum']
logsums_shop_df['dcLogsum_proj_noCEM'] = 	logsums_shop_df['dcLogsum']
logsums_shop_df = logsums_shop_df.drop('dcLogsum', 1)


# reading accessibility markets
markets_df = pd.read_table(os.path.join(os.getcwd(), sys.argv[1], 'OUTPUT', 'core_summaries', "AccessibilityMarkets.csv"), sep=",")
markets_df_base = pd.read_table(os.path.join(os.getcwd(), baseid, 'OUTPUT', 'core_summaries', "AccessibilityMarkets.csv"), sep=",")

# creating unique IDs for each market based on taz, walk subzone, autos, AVs and income
markets_df['id'] = markets_df['taz'].map(str) + '_' + markets_df['walk_subzone'].map(str) + '_' + markets_df['autoSuff'].map(str) + '_' + \
					markets_df['hasAV'].map(str) + '_' + markets_df['incQ'].map(str)
markets_df_base['id'] = markets_df_base['taz'].map(str) + '_' + markets_df_base['walk_subzone'].map(str) + '_' + markets_df_base['autoSuff'].map(str) + '_' + \
					markets_df_base['hasAV'].map(str) + '_' + markets_df_base['incQ'].map(str)

# getting the total pop for each market and getting rid of unnecessary columns
markets_df = markets_df.rename(columns={'num_workers_students': 'work_proj', 'num_persons': 'shop_proj'})
markets_df_base = markets_df_base.rename(columns={'num_workers_students': 'work_base', 'num_persons': 'shop_base'})
markets_df = markets_df[['id','work_proj','shop_proj']]
markets_df_base = markets_df_base[['id','work_base','shop_base']]

# merging total populations of base and project, which will have both work and shop (total four populations per market segment ID)
markets_df = pd.merge(markets_df, markets_df_base, on = 'id', how = 'outer')

# creating similar IDs for logsums to be able to merge with markets
logsums_pop_work_df = logsums_work_df
logsums_pop_shop_df = logsums_shop_df
logsums_pop_work_df['id'] = logsums_pop_work_df['taz'].map(str) + '_' + logsums_pop_work_df['walk_subzone'].map(str) + \
							'_' + logsums_pop_work_df['autos'].map(str) + '_' +  logsums_pop_work_df['autonomousVehicles'].map(str) + \
							'_' + logsums_pop_work_df['income_group'].map(str)
logsums_pop_shop_df['id'] = logsums_pop_shop_df['taz'].map(str) + '_' + logsums_pop_shop_df['walk_subzone'].map(str) + \
							'_' + logsums_pop_shop_df['autos'].map(str) + '_' +  logsums_pop_shop_df['autonomousVehicles'].map(str) + \
							'_' + logsums_pop_shop_df['income_group'].map(str)


# merging market populations with logsums, and multiplying

logsums_pop_work_df = pd.merge(logsums_pop_work_df, markets_df, on = 'id', how = 'left')
logsums_pop_work_df['workDCLogsum_pop base'] = logsums_pop_work_df['workDCLogsum_base_noCEM'] * logsums_pop_work_df['work_base']
logsums_pop_work_df['workDCLogsum_pop proj'] = logsums_pop_work_df['workDCLogsum_proj_noCEM'] * logsums_pop_work_df['work_proj']
logsums_pop_work_df['workDCLogsum_base_noCEM'] = logsums_pop_work_df['workDCLogsum_pop base']
logsums_pop_work_df['workDCLogsum_proj_noCEM'] = logsums_pop_work_df['workDCLogsum_pop proj']
logsums_pop_work_df = logsums_pop_work_df.drop(['id','workDCLogsum_pop base','workDCLogsum_pop proj','work_proj','work_base','shop_proj','shop_base'], 1)

logsums_pop_shop_df = pd.merge(logsums_pop_shop_df, markets_df, on = 'id', how = 'left')
logsums_pop_shop_df['dcLogsum_pop base'] = logsums_pop_shop_df['dcLogsum_base_noCEM'] * logsums_pop_shop_df['shop_base']
logsums_pop_shop_df['dcLogsum_pop proj'] = logsums_pop_shop_df['dcLogsum_proj_noCEM'] * logsums_pop_shop_df['shop_proj']
logsums_pop_shop_df['dcLogsum_base_noCEM'] = logsums_pop_shop_df['dcLogsum_pop base']
logsums_pop_shop_df['dcLogsum_proj_noCEM'] = logsums_pop_shop_df['dcLogsum_pop proj']
logsums_pop_shop_df = logsums_pop_shop_df.drop(['id','dcLogsum_pop base','dcLogsum_pop proj','work_proj','work_base','shop_proj','shop_base'], 1)



# creating directory for logsum maps within project folder, with subdirectories for Market Segments and Population
directory = os.path.join(os.getcwd(),sys.argv[1],'logsum_diff_map')
if not os.path.exists(directory):
    os.makedirs(directory)
dir_segments = os.path.join(os.getcwd(),sys.argv[1],'logsum_diff_map','Market Segments')
if not os.path.exists(dir_segments):
    os.makedirs(dir_segments)
dir_population = os.path.join(os.getcwd(),sys.argv[1],'logsum_diff_map', 'Population')
if not os.path.exists(dir_population):
    os.makedirs(dir_population)


# writing logsum diff files by market segment for tableau
logsums_work_filename = os.path.join(os.getcwd(), sys.argv[1],'logsum_diff_map', 'Market Segments',  "person_workDCLogsum_compare.csv")
logsums_work_df.to_csv(logsums_work_filename, header=True, index=False)
print("Wrote person_workDCLogsum.csv into " + dir_segments)
logsums_shop_filename = os.path.join(os.getcwd(), sys.argv[1],'logsum_diff_map', 'Market Segments',  "tour_shopDCLogsum_compare.csv")
logsums_shop_df.to_csv(logsums_shop_filename, header=True, index=False)
print("Wrote tour_shopDCLogsum.csv into " + dir_segments)


# writing logsum diff files for full population for tableau
logsums_pop_work_filename = os.path.join(os.getcwd(), sys.argv[1],'logsum_diff_map', 'Population',  "person_workDCLogsum_cs_compare.csv")
logsums_pop_work_df.to_csv(logsums_pop_work_filename, header=True, index=False)
print("Wrote person_workDCLogsum.csv into " + dir_population)
logsums_pop_shop_filename = os.path.join(os.getcwd(), sys.argv[1],'logsum_diff_map', 'Population',  "tour_shopDCLogsum_cs_compare.csv")
logsums_pop_shop_df.to_csv(logsums_pop_shop_filename, header=True, index=False)
print("Wrote tour_shopDCLogsum.csv into " + dir_population)



# copying the tableau workbooks into these folders, which will source data from the just created csv files

tableau_segments_template ='Logsum_map_marketsegments.twb'
tableau_segments = "M:\\Application\\Model One\\Mock Futures\\Logsum_sidebyside\\" + tableau_segments_template
tableau_segments_filename = 'Logsum_map_marketsegments_' + proj_name + '.twb'
copyfile(tableau_segments, os.path.join(dir_segments, tableau_segments_filename))
print("Copied tableau workbook for market segments into " + dir_segments)


tableau_pop_template ='Logsum_map_population.twb'
tableau_pop = "M:\\Application\\Model One\\Mock Futures\\Logsum_sidebyside\\" + tableau_pop_template
tableau_pop_filename = 'Logsum_map_population_' + proj_name + '.twb'
copyfile(tableau_pop, os.path.join(dir_population, tableau_pop_filename))
print("Copied tableau workbook for full population into " + dir_population)
