# build crosswalks between TAZ and Growth Geographies. 
# Some crosswalks are inputs for strategies, e.g. parking strategies (https://app.asana.com/0/1204085012544660/1206586796423943/f); some are inputs for performance metrics (https://app.asana.com/0/0/1206455080725775/f).

import geopandas as gpd 
import pandas as pd
import numpy as np 
import fiona
import os, logging

# I/O

SQMETER_TO_SQMILE = 3.861e-7

# input
TAZ_INPUT_FILE = r'M:\Data\GIS layers\TM1_taz\bayarea_rtaz1454_rev1_WGS84.shp'

BOX_DIR = r'C:\Users\{}\Box\Modeling and Surveys\Urban Modeling\Bay Area UrbanSim\p10 Datasets for PBA2050plus\raw_data_to_build_parcels_geography'.format(os.getenv('USERNAME'))
GG_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'PBA50Plus_Growth_Geographies_120823.shp')
TRA_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'PBA50_Plus_TRA_v2_121123.shp')
HRA_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'HRA_final_2023_shapefile', 'final_2023_public.shp')
EPC_INPUT_FILE = r'M:\Application\RTP2025_Equity_Performances\EquityPriorityCommunities\DRAFT_Equity_Priority_Communities_-_Plan_Bay_Area_2050_Plus_(ACS_2022).geojson'

# output
OUTPUT_M_DIR = r'M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT'
TAZ_GG_TRA_CROSSWALK_FILE = os.path.join(OUTPUT_M_DIR , 'parking_strategy', 'TAZ_GG_TRA_crosswalk.csv')
# ['TAZ1454', 'area_sqmi', 'area_within_GG', 'pct_area_within_GG', 'area_within_GG_TRA123', 'pct_area_within_GG_TRA123']
TAZ_HRA_CROSSWALK_FILE = os.path.join(OUTPUT_M_DIR , 'metrics', 'taz_hra_crosswalk.csv')
# ['taz1454', 'district', 'county', 'taz_hra']
TAZ_EPC_CROSSWALK_FILE = os.path.join(OUTPUT_M_DIR , 'metrics', 'taz_epc_crosswalk.csv')
# ['taz', 'in_set']
QAQC_DIR = os.path.join(OUTPUT_M_DIR, 'QAQC')

# other - PBA50 data for comparison and QAQC
TAZ_GG_TRA_CROSSWALK_PBA50_FILE = r'M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\parking_strategy\TAZ_intersect_GG_TRA.xlsx'
GEOGRAPHIES_PBA50_DIR = r'M:\Data\GIS layers\Blueprint Land Use Strategies\Final Blueprint_DRAFT GROWTH GEOGRAPHIES_09032020'
GG_INPUT_PBA50_FILE = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_DRAFT_GG-Upzoning Area_v1a.shp')
TRA_INPUT_PBA50_FILE1 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA1.shp')
TRA_INPUT_PBA50_FILE2 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA2.shp')
TRA_INPUT_PBA50_FILE3 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA3.shp')

LOG_FILE = os.path.join(OUTPUT_M_DIR, 'build_TAZ_GrowthGeographies_crosswalk.log')

# set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
logger.addHandler(ch)
# file handler
fh = logging.FileHandler(LOG_FILE, mode='w')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
logger.addHandler(fh)


## TAZ input files
logging.info('read TAZ file from {}'.format(TAZ_INPUT_FILE))
TAZ_gdf = gpd.read_file(TAZ_INPUT_FILE)
logging.debug(TAZ_gdf.head())
# calculate area of each TAZ
logger.info('crs: {}'.format(TAZ_gdf.crs))
TAZ_gdf_proj = TAZ_gdf.to_crs('EPSG:26910')
# logger.info('convert ')
TAZ_gdf_proj['TAZ_m2'] = TAZ_gdf_proj['geometry'].area


## TAZ-GG crosswalk: calculate area within GG for each TAZ 
logging.info('read GG file from {}'.format(GG_INPUT_FILE))
gg_gdf = gpd.read_file(GG_INPUT_FILE)
logging.debug(gg_gdf.head())
gg_gdf['gg_50plus'] = 'GG'
logger.info('crs: {}'.format(gg_gdf.crs))
gg_gdf_proj = gg_gdf.to_crs('EPSG:26910')

# method 1: clip
taz_gg_clip = gpd.clip(TAZ_gdf_proj, gg_gdf_proj)
print(taz_gg_clip.shape[0])
logging.debug('check no duplicated TAZ: {}'.format(taz_gg_clip.shape[0] == taz_gg_clip['TAZ1454'].nunique()))
taz_gg_clip.head()
# calculate the area of TAZ+GG for each TAZ
taz_gg_clip['tazGG_m2'] = taz_gg_clip['geometry'].area
taz_gg_clip.head()
# calculate the percent of TAZ that is gg
taz_gg_clip['taz_gg_ratio'] = taz_gg_clip['tazGG_m2'] / taz_gg_clip['TAZ_m2']
# merge it baack with all TAZs and fill na (TAZs that don't overlap with GG) 
taz_gg_crosswalk = TAZ_gdf_proj[['SUPERD', 'TAZ1454', 'area_sqmi', 'TAZ_m2']].merge(
    taz_gg_clip[['SUPERD', 'TAZ1454', 'tazGG_m2', 'taz_gg_ratio']],
    on=['SUPERD', 'TAZ1454'], how='left')
taz_gg_crosswalk['taz_gg_ratio'].fillna(0, inplace=True)
taz_gg_crosswalk['tazGG_m2'].fillna(0, inplace=True)


# method 2: overlay
taz_gg_overlay = gpd.overlay(TAZ_gdf_proj, gg_gdf_proj, how='intersection')
print(taz_gg_overlay.shape[0])
taz_gg_overlay.head()
taz_gg_overlay['tazGG_m2'] = taz_gg_overlay['geometry'].area
taz_gg_overlay.head()
# calculate the percent of TAZ that is gg
taz_gg_overlay['taz_gg_ratio_overlay'] = taz_gg_overlay['tazGG_m2'] / taz_gg_overlay['TAZ_m2']
# merge it baack with all TAZs and fill na (TAZs that don't overlap with GG) 
taz_gg_overlay_crosswalk = TAZ_gdf_proj[['SUPERD', 'TAZ1454', 'area_sqmi', 'TAZ_m2']].merge(
    taz_gg_overlay[['SUPERD', 'TAZ1454', 'tazGG_m2', 'taz_gg_ratio_overlay']],
    on=['SUPERD', 'TAZ1454'], how='left')
taz_gg_overlay_crosswalk['taz_gg_ratio_overlay'].fillna(0, inplace=True)
taz_gg_overlay_crosswalk['tazGG_m2'].fillna(0, inplace=True)


## TAZ-GG/TRA crosswalk: calculate area within GG and TRA for each TAZ
logging.info('read TRA file from {}'.format(TRA_INPUT_FILE))
tra_gdf = gpd.read_file(TRA_INPUT_FILE)
logging.debug(tra_gdf.head())
logging.debug(tra_gdf['PBA50_Geo'].value_counts(dropna=False))

logger.info('crs: {}'.format(tra_gdf.crs))
tra_gdf_proj = tra_gdf.to_crs('EPSG:26910')

# combine TRA 1/2/3 categories and dissolve into TRA
tra_gdf_proj['tra_50plus'] = ''
tra_gdf_proj.loc[tra_gdf_proj['PBA50_Geo'].notnull(), 'tra_50plus'] = 'tra'
tra_dissolve_gdf = tra_gdf_proj.dissolve(by='tra_50plus').reset_index()
# GG and TRA
gg_tra_gdf = gpd.overlay(gg_gdf_proj, tra_dissolve_gdf)
# clip TAZ with GG+TRA
taz_ggtra_clip = gpd.clip(TAZ_gdf_proj, gg_tra_gdf)

logging.debug('check no duplicated TAZ: {}'.format(taz_ggtra_clip.shape[0] == taz_ggtra_clip['TAZ1454'].nunique()))
taz_ggtra_clip.head()
# calculate the area of TAZ + GG+TRA
taz_ggtra_clip['tazGGtra_m2'] = taz_ggtra_clip['geometry'].area
taz_ggtra_clip.head()
# calculate the percent of TAZ that is gg_tra
taz_ggtra_clip['taz_ggtra_ratio'] = taz_ggtra_clip['tazGGtra_m2'] / taz_ggtra_clip['TAZ_m2']
# merge it baack with all TAZs and fill na (TAZs that don't overlap with GG+TRA) 
taz_ggtra_crosswalk = TAZ_gdf_proj[['SUPERD', 'TAZ1454', 'area_sqmi', 'TAZ_m2']].merge(
    taz_ggtra_clip[['SUPERD', 'TAZ1454', 'tazGGtra_m2', 'taz_ggtra_ratio']],
    on=['SUPERD', 'TAZ1454'], how='left')
taz_ggtra_crosswalk['taz_ggtra_ratio'].fillna(0, inplace=True)
taz_ggtra_crosswalk['tazGGtra_m2'].fillna(0, inplace=True)

## combine GG and GG+TRA into one table
logging.info('combine GG and GG+TRA into one table')
taz_gg_ggtra_crosswalk = taz_gg_crosswalk.merge(
    taz_ggtra_crosswalk,
    on=['SUPERD', 'TAZ1454', 'area_sqmi', 'TAZ_m2'],
    how='outer')
logging.debug('check merge: {} rows, {} unique TAZ id'.format(
    taz_gg_ggtra_crosswalk.shape[0], taz_gg_ggtra_crosswalk['TAZ1454'].nunique()
))
logging.debug(taz_gg_ggtra_crosswalk.head())

logging.info('rename columns')
taz_gg_ggtra_crosswalk.rename(columns = {
    'taz_gg_ratio': 'pct_area_within_GG',
    'taz_ggtra_ratio': 'pct_area_within_GG_TRA123'}, inplace=True)
taz_gg_ggtra_crosswalk_export = taz_gg_ggtra_crosswalk[[
    'TAZ1454', 'area_sqmi', 'pct_area_within_GG', 'pct_area_within_GG_TRA123'
]]
logging.info('write out tag_gg_ggtra crosswalk to {}'.format(TAZ_GG_TRA_CROSSWALK_FILE))
taz_gg_ggtra_crosswalk_export.to_csv(TAZ_GG_TRA_CROSSWALK_FILE, index=False)

## QAQC - compare w/ PBA50 Final Blueprint
taz_gg_ggtra_crosswalk_pba50 = pd.read_excel(
    TAZ_GG_TRA_CROSSWALK_PBA50_FILE,
    sheet_name = 'bayarea_rtaz1454_rev1_WGS84')
taz_gg_ggtra_crosswalk_pba50['version'] = 'PBA50'

# make columns consistent
taz_gg_ggtra_crosswalk['version'] = 'PBA50+ Draft BP'
taz_gg_ggtra_crosswalk['area_within_GG'] = taz_gg_ggtra_crosswalk['tazGG_m2'] * SQMETER_TO_SQMILE
taz_gg_ggtra_crosswalk['area_within_GG_TRA123'] = taz_gg_ggtra_crosswalk['tazGGtra_m2'] * SQMETER_TO_SQMILE

taz_gg_ggtra_crosswalk_comp = pd.concat([
    taz_gg_ggtra_crosswalk_pba50, 
    taz_gg_ggtra_crosswalk[['TAZ1454', 'area_sqmi', 'area_within_GG', 'pct_area_within_GG', 
                            'area_within_GG_TRA123', 'pct_area_within_GG_TRA123']]])
taz_gg_ggtra_crosswalk_comp.to_csv(os.path.join(QAQC_DIR, 'taz_gg_ggtra_crosswalk_comp.csv'), index=False)

# also simplify PBA50 growth geography shapes for easier Tableau QAQC
gg_pba50_gdf = gpd.read_file(GG_INPUT_PBA50_FILE)
logging.debug(gg_pba50_gdf.head())
gg_pba50_gdf['gg_50'] = 'GG'
logger.info('crs: {}'.format(gg_pba50_gdf.crs))
gg_pba50_gdf_proj = gg_pba50_gdf.to_crs('EPSG:26910')
gg_pba50_gdf_proj.to_file(os.path.join(QAQC_DIR, 'GG_pba50.shp'))

tra1_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE1)
tra2_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE2)
tra3_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE3)

tra1_pba50_gdf_proj = tra1_pba50_gdf.to_crs('EPSG:26910')
tra2_pba50_gdf_proj = tra2_pba50_gdf.to_crs('EPSG:26910')
tra3_pba50_gdf_proj = tra3_pba50_gdf.to_crs('EPSG:26910')

tra12_pba50_gdf = tra1_pba50_gdf_proj.union(tra2_pba50_gdf_proj)
tra123_pba50_gdf = tra12_pba50_gdf.union(tra3_pba50_gdf_proj)
tra_pba50_gdf = gpd.GeoDataFrame(geometry=tra123_pba50_gdf)
tra_pba50_gdf['tra_50'] = 'tra'
tra_pba50_gdf.to_file(os.path.join(QAQC_DIR, 'tra_pba50.shp'))


"""
## TAZ-HRA crosswalk
logging.info('read HRA file from {}'.format(HRA_INPUT_FILE))
hra_gdf = gpd.read_file(HRA_INPUT_FILE)
logging.debug(tra_gdf.head())

logger.info('crs: {}'.format(hra_gdf.crs))
hra_gdf_proj = hra_gdf.to_crs('EPSG:26910')

# simplify the categories
logging.debug(hra_gdf_proj['oppcat'].value_counts(dropna=False))

hra_dict = {'Highest Resource': 'HRA',
            'High Resource': 'HRA'}
hra_gdf_proj['hra_50plus'] = hra_gdf_proj['oppcat'].map(hra_dict)
# TODO: what is the threshold?


## TAZ-EPC crosswalk
logging.info('read EPC file from {}'.format(EPC_INPUT_FILE))
epc_gdf = gpd.read_file(EPC_INPUT_FILE)
logging.debug(epc_gdf.head())

epc_gdf = epc_gdf[['epc_2050p', 'geometry']]
logger.info(epc_gdf.crs)
epc_gdf_proj = epc_gdf.to_crs('EPSG:26910')

# dissolve
epc_dissolve_gdf = epc_gdf_proj.dissolve(by='epc_2050p')
"""
