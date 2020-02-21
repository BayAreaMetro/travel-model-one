

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
