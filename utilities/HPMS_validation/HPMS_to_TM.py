

USAGE = """

This scripts produces a correspondence between AADT measurements in the HPMS shapefile to the links in the Travel Model network.

Requires arcpy, so use arcgis version of python
e.g. set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts

HPMS shapefile can be downloaded from FHWA's site:
https://www.fhwa.dot.gov/policyinformation/hpms/shapefiles.cfm

The fields in the shapefile is documented in the HPMS field manual (https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/page04.cfm)
Note that the AADT recorded in the shapefile are "bi-directional" (see: https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/page05.cfm)

"""
import os
import arcpy
import pandas as pd
from simpledbf import Dbf5

arcpy.env.workspace = r"M:\Data\Traffic\HPMS\2015\Test17"
INPUT_TM1shapefile = r"M:\Application\Model One\Networks\TM1_2015_Base_Network\shapefile\freeflow_links.shp"
INPUT_HPMSshapefile = r"M:\Data\Traffic\HPMS\2015\california2015\California_Sections.shp"

# From the HPMS shapefile, select only the road segments that are in the Bay Area
# use the variable "county_cod"
# FIPS county code of the nine Bay Area county
# 06001	Alameda
# 06013	Contra Costa
# 06041	Marin
# 06055	Napa
# 06075	San Francisco
# 06081	San Mateo
# 06085	Santa Clara
# 06095	Solano
# 06097	Sonoma
# Feature Class to Feature Class (Conversion)
# syntax: FeatureClassToFeatureClass(in_features, out_path, out_name, {where_clause}, {field_mapping}, config_keyword)
arcpy.conversion.FeatureClassToFeatureClass(INPUT_HPMSshapefile, "", "HPMS_BayArea.shp", "county_cod = 1 Or county_cod = 13 Or county_cod = 41 Or county_cod = 55 Or county_cod = 75 Or county_cod = 81 Or county_cod = 85 Or county_cod = 95 Or county_cod = 97")

# Trim the HPMS network
# - by selecting only non zero AADT
# - by selecting only state highways (as we use "route_numb" for matching, and there is no route number for lower level facilities)
arcpy.conversion.FeatureClassToFeatureClass("HPMS_BayArea.shp", "", "HPMS_BayArea_aadt_SHS.shp", "aadt > 0 And route_id LIKE '%SHS%'")


# Separate the free flow network into 16 pieces ( [N, E, S, W] x [use = 1, 2, 3, 4])
# e.g. arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_N_Use1.shp", "USE = 1 And ROUTEDIR = 'N'")
# note: only freeway routes are coded with direction in the TM1 network; there are 49 freeway routes in TM1

direction_list = ["N", "E", "S", "W"]
use_list = ["1", "2", "3", "4"]

for d in direction_list:
    for u in use_list:
        arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_" + d + "_Use" + u + ".shp", "USE = " + u + "And ROUTEDIR = '" + d + "'")


# use spatial join to find the nearest links, use a search distance of 0.2 miles
# 0.2 miles is just what I judge to be a reasonable search distance. Ideally we could do some test to see if the results are sensitive to this value.
# syntax: SpatialJoin(target_features, join_features, out_feature_class, {join_operation}, {join_type}, {field_mapping}, {match_option}, {search_radius}, {distance_field_name})


for d in direction_list:
    for u in use_list:

        target_features = "HPMS_BayArea_aadt_SHS.shp"

        join_features = "freeflow_links_freeway_" + d + "_Use" + u + ".shp"
        out_feature_class = "SpatialJoin_" + d + "_Use" + u + ".shp"
        arcpy.SpatialJoin_analysis(target_features, join_features, out_feature_class, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "0.2 Miles", '')

		# Select the rows with matched route number
		# syntax: FeatureClassToFeatureClass(in_features, out_path, out_name, {where_clause}, {field_mapping}, config_keyword)
		# e.g. arcpy.conversion.FeatureClassToFeatureClass("SpatialJoin_N_Use1.shp", "", "HPMS_to_TM_N_Use1.shp", "route_numb = ROUTENUM")
        in_features = out_feature_class
        out_path = ""
        out_name = "HPMS_to_TM_" + d + "_Use" + u + ".shp"
        arcpy.conversion.FeatureClassToFeatureClass(in_features, out_path, out_name, "route_numb = ROUTENUM")

# -------------------------------
# switch to dbf processing (not arcpy)
# -------------------------------
# e.g.
# dbf_Fwy = Dbf5('HPMS_to_TM_N_Use1.dbf')
# x[N1] = dbf_Fwy.to_dataframe()

# use dictionary
x = {}

for d in direction_list:
    for u in use_list:
        dbf_Fwy = Dbf5(arcpy.env.workspace + "\HPMS_to_TM_" + d + "_Use" + u + ".dbf")
        x[d+u] = dbf_Fwy.to_dataframe()


# Union N+E and S+W (so, one file contains freeway segments going either north or east; and one file contains freeway segments going either South or West)
# this reduces the number of dataframes
# the goal is to be able to sum up the volume of N+S and E+W by joining the objectID in later steps
df_FwyNorthEast1 = x['N1'].append(x['E1'])
df_FwySouthWest1 = x['S1'].append(x['W1'])

df_FwyNorthEast2 = x['N2'].append(x['E2'])
df_FwySouthWest2 = x['S2'].append(x['W2'])

df_FwyNorthEast3 = x['N3'].append(x['E3'])
df_FwySouthWest3 = x['S3'].append(x['W3'])

df_FwyNorthEast4 = x['N4'].append(x['E4'])
df_FwySouthWest4 = x['S4'].append(x['W4'])

# add suffix
df_FwyNorthEast1 = df_FwyNorthEast1.add_suffix('_NE1')
df_FwySouthWest1 = df_FwySouthWest1.add_suffix('_SW1')

df_FwyNorthEast2 = df_FwyNorthEast2.add_suffix('_NE2')
df_FwySouthWest2 = df_FwySouthWest2.add_suffix('_SW2')

df_FwyNorthEast3 = df_FwyNorthEast3.add_suffix('_NE3')
df_FwySouthWest3 = df_FwySouthWest3.add_suffix('_SW3')

df_FwyNorthEast4 = df_FwyNorthEast4.add_suffix('_NE4')
df_FwySouthWest4 = df_FwySouthWest4.add_suffix('_SW4')



# for use = 1
# inner join because we only want the freeway segments where we get volumes for both directions
df_FwyBiDirection = pd.merge(df_FwyNorthEast1, df_FwySouthWest1, left_on='OBJECTID_NE1', right_on='OBJECTID_SW1', how='inner')
#keep only the relevant columns
#df_FwyBiDirection = df_FwyBiDirection[['OBJECTID', 'route_numb_NE1', 'route_numb_SW1', 'aadt_NE1', 'aadt_SW1', 'A_NE1', 'B_NE1', 'A_SW1', 'B_SW1']]

# left join the other tables
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwyNorthEast2, left_on='OBJECTID_NE1', right_on='OBJECTID_NE2', how='left')
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwySouthWest2, left_on='OBJECTID_NE1', right_on='OBJECTID_SW2', how='left')
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwyNorthEast3, left_on='OBJECTID_NE1', right_on='OBJECTID_NE3', how='left')
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwySouthWest3, left_on='OBJECTID_NE1', right_on='OBJECTID_SW3', how='left')
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwyNorthEast4, left_on='OBJECTID_NE1', right_on='OBJECTID_NE4', how='left')
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_FwySouthWest4, left_on='OBJECTID_NE1', right_on='OBJECTID_SW4', how='left')

#keep only the relevant columns
df_FwyBiDirection = df_FwyBiDirection[['OBJECTID_NE1', 'route_numb_NE1', 'route_numb_SW1', 'aadt_NE1', 'aadt_SW1', 'A_NE1', 'B_NE1', 'A_SW1', 'B_SW1',  'A_NE2', 'B_NE2','A_SW2', 'B_SW2', 'A_NE3', 'B_NE3', 'A_SW3', 'B_SW3', 'A_NE4', 'B_NE4', 'A_SW4', 'B_SW4' ]]


output_filename = arcpy.env.workspace + "\HPMS_to_TM.csv"
df_FwyBiDirection.to_csv(output_filename, header=True, index=False)

# left join to avgload5period.csv
df_avgload5period = pd.read_csv(os.path.join(arcpy.env.workspace, 'avgload5period.csv'), index_col=False, sep=",")
df_avgload5period['vol5period'] = df_avgload5period['   volEA_tot'] + df_avgload5period['   volAM_tot'] + df_avgload5period['   volMD_tot'] + df_avgload5period['   volPM_tot'] + df_avgload5period['   volEV_tot']
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_NE1','B_NE1'], right_on=['       a','       b'], how='left', suffixes=('', '_TMne1'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_SW1','B_SW1'], right_on=['       a','       b'], how='left', suffixes=('', '_TMsw1'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_NE2','B_NE2'], right_on=['       a','       b'], how='left', suffixes=('', '_TMne2'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_SW2','B_SW2'], right_on=['       a','       b'], how='left', suffixes=('', '_TMsw2'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_NE3','B_NE3'], right_on=['       a','       b'], how='left', suffixes=('', '_TMne3'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_SW3','B_SW3'], right_on=['       a','       b'], how='left', suffixes=('', '_TMsw3'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_NE4','B_NE4'], right_on=['       a','       b'], how='left', suffixes=('', '_TMne4'))
df_FwyBiDirection = pd.merge(df_FwyBiDirection, df_avgload5period[['       a','       b','vol5period']], left_on=['A_SW4','B_SW4'], right_on=['       a','       b'], how='left', suffixes=('', '_TMsw4'))
# force the '_TMne1' suffix
df_FwyBiDirection.rename(columns={'       a': '       a_TMne1','       b': '       b_TMne1', 'vol5period': 'vol5period_TMne1'}, inplace=True)

# sum the volume
df_FwyBiDirection.fillna(0, inplace=True)
df_FwyBiDirection['modelled_daily_volume'] = df_FwyBiDirection['vol5period_TMne1'] + df_FwyBiDirection['vol5period_TMsw1'] + df_FwyBiDirection['vol5period_TMne2'] + df_FwyBiDirection['vol5period_TMsw2'] + df_FwyBiDirection['vol5period_TMne3'] + df_FwyBiDirection['vol5period_TMsw3'] + df_FwyBiDirection['vol5period_TMne4'] + df_FwyBiDirection['vol5period_TMsw4']


output_filename2 = arcpy.env.workspace + "\HPMS_to_TM_avgload5period.csv"
df_FwyBiDirection.to_csv(output_filename2, header=True, index=False)
