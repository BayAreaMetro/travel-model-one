#########################################################
# this script prepares inputs for the "create simple tolls process" 
# see more in: https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/NextGenFwys/Create_simple_toll_plan.py
#
# originally, the create simple tolls process is designed to use the network_links.shp from a full model run
# and the network_links.shp itself is an export of the Cube file avgload5period.net
# in order to save model run time, we may want to use the avgload5period.net from the toll calibration process
# however, the tolldaea, tolldam, etc in avgload5period.net is actually set only in the first iteration (not updated during toll calibration)
# ie their values do not reflect the tolls used in the toll calibration iterations
# the tolldaea, tolldaam, etc need to be read from withTolls.net instead

# this is a makeshift script so we can use avgload5period.net from toll calibration instead of a full run 
# it replaces tolldaea, tolldaam, etc in network_links.shp with values from withTolls.net
# before running this script, there are some manual steps, namely:
# copying withTolls.net to a location on the L drive and export it to shape
# (we'll see if it's worth cleaning this script up)

# example call: python CopyTolldaFromWithTolls.py
# user needs to specify input 1, input 2 and output_dir below
#
#########################################################

import os
import pandas as pd
import geopandas as gpd

# input 1
withTolls_gdf="L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP07_Path1b_01_TollCalibration01/OUTPUT/shapefile_withTolls.net/withTolls.shp"
withTolls_gdf=gpd.read_file("L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP07_Path1b_01_TollCalibration01/OUTPUT/shapefile_withTolls.net/withTolls.shp")

# review the variable names
# withTolls_gdf.info()

# keep only the variables that are needed
withTolls_gdf = withTolls_gdf[['A','B','TOLLEA_DA','TOLLAM_DA','TOLLMD_DA','TOLLPM_DA', 'TOLLEV_DA']] 

withTolls_gdf.rename(columns = {'TOLLEA_DA':'TOLLEA_DA_withTolls'}, inplace = True)
withTolls_gdf.rename(columns = {'TOLLAM_DA':'TOLLAM_DA_withTolls'}, inplace = True)
withTolls_gdf.rename(columns = {'TOLLMD_DA':'TOLLMD_DA_withTolls'}, inplace = True)
withTolls_gdf.rename(columns = {'TOLLPM_DA':'TOLLPM_DA_withTolls'}, inplace = True)
withTolls_gdf.rename(columns = {'TOLLEV_DA':'TOLLEV_DA_withTolls'}, inplace = True)

# input 2
# the loaded network from a dynamic tolling run, in which the all-lane tolling system is represented as many short segments (100+)
project_dir ="L:/Application/Model_One/NextGenFwys/" 
modelrun_with_DynamicTolling = "2035_TM152_NGF_NP07_Path1b_01_TollCalibration01"
loadednetwork_100psegs_shp_gdf = gpd.read_file(os.path.join(project_dir, "Scenarios", modelrun_with_DynamicTolling, "OUTPUT", "shapefile", "network_links.shp")) 

loadednetwork_100psegs_shp_gdf = pd.merge(loadednetwork_100psegs_shp_gdf,
                             withTolls_gdf,
                             how='left',
                             left_on=['A','B'], 
                             right_on = ['A','B'],
                             indicator=False)

# review the variable names
# for column_headers in loadednetwork_100psegs_shp_gdf.columns: 
#    print(column_headers)


# replace the values
loadednetwork_100psegs_shp_gdf['TOLLEA_DA'] = loadednetwork_100psegs_shp_gdf['TOLLEA_DA_withTolls']
loadednetwork_100psegs_shp_gdf['TOLLAM_DA'] = loadednetwork_100psegs_shp_gdf['TOLLAM_DA_withTolls']
loadednetwork_100psegs_shp_gdf['TOLLMD_DA'] = loadednetwork_100psegs_shp_gdf['TOLLMD_DA_withTolls']
loadednetwork_100psegs_shp_gdf['TOLLPM_DA'] = loadednetwork_100psegs_shp_gdf['TOLLPM_DA_withTolls']
loadednetwork_100psegs_shp_gdf['TOLLEV_DA'] = loadednetwork_100psegs_shp_gdf['TOLLEV_DA_withTolls']

# print the gdf out
output_dir ='L:/Application/Model_One/NextGenFwys/INPUT_DEVELOPMENT/Static_toll_plans/Static_toll_P1b_V1'
loadednetwork_100psegs_shp_gdf.to_file(os.path.join(output_dir,'network_links_100plusSeg.shp'))
