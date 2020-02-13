

USAGE = """

This scripts produces a correspondence between AADT measurements in the HPMS shapefile to the links in the Travel Model network.

Requires arcpy, so use arcgis version of python
e.g. set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts

HPMS shapefile can be downloaded from FHWA's site:
https://www.fhwa.dot.gov/policyinformation/hpms/shapefiles.cfm

The fields in the shapefile is documented in the HPMS field manual (https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/page04.cfm)
Note that the AADT recorded in the shapefile are "bi-directional" (see: https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/page05.cfm)

"""

import arcpy
import pandas as pd
from simpledbf import Dbf5

arcpy.env.workspace = r"M:\Data\Traffic\HPMS\2015\Test9"
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


# Separate the free flow network into N, E, S, W
arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_N.shp", "ROUTEDIR = 'N'")
arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_E.shp", "ROUTEDIR = 'E'")
arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_S.shp", "ROUTEDIR = 'S'")
arcpy.conversion.FeatureClassToFeatureClass(INPUT_TM1shapefile, "", "freeflow_links_freeway_W.shp", "ROUTEDIR = 'W'")
# note: only freeway routes are coded with direction in the TM1 network; there are 49 freeway routes in TM1


# use spatial join to find the nearest links, use a search distance of 0.25 miles
# 0.25 miles is just what I judge to be reasonable to use. Ideally we could do some test to see if the results are sensitive to this value.
# syntax: SpatialJoin(target_features, join_features, out_feature_class, {join_operation}, {join_type}, {field_mapping}, {match_option}, {search_radius}, {distance_field_name})

target_features = "HPMS_BayArea_aadt_SHS.shp"

join_features = "freeflow_links_freeway_N.shp"
out_feature_class = "SpatialJoin_N.shp"
arcpy.SpatialJoin_analysis(target_features, join_features, out_feature_class, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "0.25 Miles", '')

join_features = "freeflow_links_freeway_E.shp"
out_feature_class = "SpatialJoin_E.shp"
arcpy.SpatialJoin_analysis(target_features, join_features, out_feature_class, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "0.25 Miles", '')

join_features = "freeflow_links_freeway_S.shp"
out_feature_class = "SpatialJoin_S.shp"
arcpy.SpatialJoin_analysis(target_features, join_features, out_feature_class, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "0.25 Miles", '')

join_features = "freeflow_links_freeway_W.shp"
out_feature_class = "SpatialJoin_W.shp"
arcpy.SpatialJoin_analysis(target_features, join_features, out_feature_class, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "0.25 Miles", '')

# Select the rows with matched route number
arcpy.conversion.FeatureClassToFeatureClass("SpatialJoin_N.shp", "", "HPMS_to_TM_N.shp", "route_numb = ROUTENUM")
arcpy.conversion.FeatureClassToFeatureClass("SpatialJoin_E.shp", "", "HPMS_to_TM_E.shp", "route_numb = ROUTENUM")
arcpy.conversion.FeatureClassToFeatureClass("SpatialJoin_S.shp", "", "HPMS_to_TM_S.shp", "route_numb = ROUTENUM")
arcpy.conversion.FeatureClassToFeatureClass("SpatialJoin_W.shp", "", "HPMS_to_TM_W.shp", "route_numb = ROUTENUM")

# switch to dbf processing
dbf_FwyNorth = Dbf5('HPMS_to_TM_N.dbf')
df_FwyNorth = dbf_FwyNorth.to_dataframe()

dbf_FwyEast = Dbf5('HPMS_to_TM_E.dbf')
df_FwyEast = dbf_FwyEast.to_dataframe()

dbf_FwySouth = Dbf5('HPMS_to_TM_S.dbf')
df_FwySouth = dbf_FwySouth.to_dataframe()

dbf_FwyWest = Dbf5('HPMS_to_TM_W.dbf')
df_FwyWest = dbf_FwyWest.to_dataframe()

# Union N+E and S+W (so, one file contains freeway segments going either north or east; and one file contains freeway segments going either South or West)
# the goal is to be able to sum up the volume of N+S and E+W by joining the objectID in later steps
df_FwyNorthEast = df_FwyNorth.append(df_FwyEast)
df_FwySouthWest = df_FwySouth.append(df_FwyWest)

# inner join because we only want the freeway segments where we get volumes for both directions
df_FwyBiDirection = pd.merge(df_FwyNorthEast, df_FwySouthWest, left_on='OBJECTID', right_on='OBJECTID', how='inner', suffixes=('_NE', '_SW'))

#keep only the relevant columns
df_FwyBiDirection = df_FwyBiDirection[['OBJECTID', 'route_numb_NE', 'route_numb_SW', 'aadt_NE', 'aadt_SW', 'A_NE', 'B_NE', 'A_SW', 'B_SW']]

output_filename = "HPMS_to_TM.csv"
df_FwyBiDirection.to_csv(output_filename, header=True, index=False)
