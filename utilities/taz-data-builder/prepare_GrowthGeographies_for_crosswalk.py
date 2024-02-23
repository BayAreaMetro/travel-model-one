# create intersection of Growth Geography and TRAs for PBA50+.

import geopandas as gpd 
import pandas as pd
import numpy as np
import os, logging

analysis_crs = "EPSG:26910"

# I/O

## input
TAZ_INPUT_FILE = r'M:\Data\GIS layers\TM1_taz\bayarea_rtaz1454_rev1_WGS84.shp'

# PBA50plus
BOX_DIR = r'C:\Users\{}\Box\Modeling and Surveys\Urban Modeling\Bay Area UrbanSim\p10 Datasets for PBA2050plus\raw_data_to_build_parcels_geography'.format(os.getenv('USERNAME'))
GG_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'PBA50Plus_Growth_Geographies_120823.shp')
TRA_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'PBA50_Plus_TRA_v2_121123.shp')

# PBA50
GEOGRAPHIES_PBA50_DIR = r'M:\Data\GIS layers\Blueprint Land Use Strategies\Final Blueprint_DRAFT GROWTH GEOGRAPHIES_09032020'
GG_INPUT_PBA50_FILE = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_DRAFT_GG-Upzoning Area_v1a.shp')
TRA_INPUT_PBA50_FILE1 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA1.shp')
TRA_INPUT_PBA50_FILE2 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA2.shp')
TRA_INPUT_PBA50_FILE3 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA3.shp')

## output
OUTPUT_M_DIR = r'M:\Application\PBA50Plus_Data_Processing\Draft_Blueprint_Growth_Geographies'
QAQC_DIR = os.path.join(OUTPUT_M_DIR, 'QAQC')
GG_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_tra_pba50plus.shp')
GG_TRA_SHAPE_PBA50_FILE = os.path.join(QAQC_DIR, 'gg_tra_pba50.shp')

LOG_FILE = os.path.join(QAQC_DIR, 'prepare_GrowthGeographies_for_crosswalk.log')

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

#### PBA50+
## Growth geographies
logging.info('read GG file from {}'.format(GG_INPUT_FILE))
gg_gdf = gpd.read_file(GG_INPUT_FILE)
logging.debug(gg_gdf.head())
gg_gdf['gg_50plus'] = 'GG'
logger.info('crs: {}'.format(gg_gdf.crs))
gg_gdf_proj = gg_gdf.to_crs(analysis_crs)
# write out for QAQC
gg_gdf_proj.to_file(os.path.join(QAQC_DIR, 'GG_pba50plus.shp'))

## TRAs
logging.info('read TRA file from {}'.format(TRA_INPUT_FILE))
tra_gdf = gpd.read_file(TRA_INPUT_FILE)
logging.debug(tra_gdf.head())
logging.debug(tra_gdf['PBA50_Geo'].value_counts(dropna=False))

logger.info('crs: {}'.format(tra_gdf.crs))
tra_gdf_proj = tra_gdf.to_crs(analysis_crs)

# combine TRA 1/2/3 categories and dissolve into TRA
tra_gdf_proj['tra_50plus'] = ''
tra_gdf_proj.loc[tra_gdf_proj['PBA50_Geo'].notnull(), 'tra_50plus'] = 'tra'
tra_dissolve_gdf = tra_gdf_proj.dissolve(by='tra_50plus').reset_index()
# write out for QAQC
tra_gdf_proj.to_file(os.path.join(QAQC_DIR, 'tra_pba50plus.shp'))

# GG and TRA
gg_tra_gdf = gpd.overlay(gg_gdf_proj, tra_dissolve_gdf)

# write out GG-TRA intersection
logger.info('write out GG_TRA intersection geography to {}'.format(GG_TRA_SHAPE_FILE))
gg_tra_gdf[['gg_50plus', 'tra_50plus', 'geometry']].to_file(GG_TRA_SHAPE_FILE)


#### PBA50
# GG
logging.info('read GG file from {}'.format(GG_INPUT_PBA50_FILE))
gg_pba50_gdf = gpd.read_file(GG_INPUT_PBA50_FILE)
logging.debug(gg_pba50_gdf.head())

gg_pba50_gdf['gg_50'] = 'GG'
logger.info('crs: {}'.format(gg_pba50_gdf.crs))
gg_pba50_gdf_proj = gg_pba50_gdf.to_crs(analysis_crs)
# write out for QAQC
gg_pba50_gdf_proj.to_file(os.path.join(QAQC_DIR, 'GG_pba50.shp'))

# TRAs
tra1_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE1)
tra2_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE2)
tra3_pba50_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE3)

tra1_pba50_gdf_proj = tra1_pba50_gdf.to_crs(analysis_crs)
tra2_pba50_gdf_proj = tra2_pba50_gdf.to_crs(analysis_crs)
tra3_pba50_gdf_proj = tra3_pba50_gdf.to_crs(analysis_crs)

tra12_pba50_gdf = tra1_pba50_gdf_proj.union(tra2_pba50_gdf_proj)
tra123_pba50_gdf = tra12_pba50_gdf.union(tra3_pba50_gdf_proj)
tra_pba50_gdf = gpd.GeoDataFrame(geometry=tra123_pba50_gdf)
tra_pba50_gdf['tra_50'] = 'tra'
# write out for QAQC
tra_pba50_gdf.to_file(os.path.join(QAQC_DIR, 'tra_pba50.shp'))

# GG and TRA
gg_tra_pba50_gdf = gpd.overlay(gg_pba50_gdf_proj, tra_pba50_gdf)

# write out GG-TRA intersection
logger.info('write out GG_TRA_pba50 intersection geography to {}'.format(GG_TRA_SHAPE_PBA50_FILE))
gg_tra_pba50_gdf[['gg_50', 'tra_50', 'geometry']].to_file(GG_TRA_SHAPE_PBA50_FILE)