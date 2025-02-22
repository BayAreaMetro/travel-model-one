USAGE = """

Create intersection of Growth Geography and TRAs for PBA50+.

"""

import geopandas as gpd
import fiona
import pandas as pd
import numpy as np
import os, logging, time, argparse

analysis_crs = "EPSG:26910"
today = time.strftime('%Y_%m_%d')

# I/O

## input
TAZ_INPUT_FILE = r'M:\Data\GIS layers\TM1_taz\bayarea_rtaz1454_rev1_WGS84.shp'

# PBA50plusDBP - Draft Blueprint
BOX_DIR = r'C:\Users\{}\Box\Modeling and Surveys\Urban Modeling\Bay Area UrbanSim\p10 Datasets for PBA2050plus\raw_data_to_build_parcels_geography'.format(os.getenv('USERNAME'))
PPA_INPUT_FILE = os.path.join(BOX_DIR, 'pba50plus_GrowthGeographies_p10tagging', 'pba50plus_GrowthGeographies_p10tagging.gdb')
GG_INPUT_FILE = r'M:\Application\PBA50Plus_Data_Processing\Draft_Blueprint_Growth_Geographies\raw_and_interim_data\PBA50Plus_Growth_Geographies_120823.shp'
TRA_INPUT_FILE = r'M:\Application\PBA50Plus_Data_Processing\Draft_Blueprint_Growth_Geographies\raw_and_interim_data\PBA50_Plus_TRA_v2_121123.shp'

# PBA50plusFBP - Final Blueprint
GG_INPUT_FBP_DIR = r'M:\Application\PBA50Plus_Data_Processing\Final_Blueprint_Growth_Geographies\raw_interim_data\FBP_Discrete_Modeling_GG_v2'
GG_INPUT_FBP_FILE = os.path.join(GG_INPUT_FBP_DIR, 'FBP_2025_GG.shp')
TRA_INPUT_FBP_FILE1 = os.path.join(GG_INPUT_FBP_DIR, 'FBP_Jan2025_TRA1_discrete.shp')
TRA_INPUT_FBP_FILE2 = os.path.join(GG_INPUT_FBP_DIR, 'FBP_Jan2025_TRA2_discrete.shp')
TRA_INPUT_FBP_FILE3 = os.path.join(GG_INPUT_FBP_DIR, 'FBP_Jan2025_TRA3_discrete.shp')
TRA_INPUT_FBP_FILE4 = os.path.join(GG_INPUT_FBP_DIR, 'FBP_Jan2025_TRA4_discrete.shp')
TRA_INPUT_FBP_FILE5 = os.path.join(GG_INPUT_FBP_DIR, 'FBP_Jan2025_TRA5__discrete.shp')
GGnonPPA_INPUT_FBP_FILE = r'M:\Application\PBA50Plus_Data_Processing\Final_Blueprint_Growth_Geographies\raw_interim_data\FBP_Jan2025_GG_no_PPA\FBP_Jan2025_GG_no_PPA.shp'

# PBA50
GEOGRAPHIES_PBA50_DIR = r'M:\Data\GIS layers\Blueprint Land Use Strategies\Final Blueprint_DRAFT GROWTH GEOGRAPHIES_09032020'
GG_INPUT_PBA50_FILE = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_DRAFT_GG-Upzoning Area_v1a.shp')
TRA_INPUT_PBA50_FILE1 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA1.shp')
TRA_INPUT_PBA50_FILE2 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA2.shp')
TRA_INPUT_PBA50_FILE3 = os.path.join(GEOGRAPHIES_PBA50_DIR, 'Final_Blueprint_TRA3.shp')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('rtp_v', type=str, choices=['RTP2021FBP','RTP2025DBP', 'RTP2025FBP'], help='RTP and version of Growth Geographies data')
    # parser.add_argument('--test', action='store_true', help='If passed, writes output to cwd instead of METRICS_OUTPUT_DIR')
    my_args = parser.parse_args()

    # set up logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    LOG_FILE = 'prepare_GrowthGeographies_for_crosswalk_{}_{}.log'.format(my_args.rtp_v, today)
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    ## output files
    if my_args.rtp_v == 'RTP2021FBP':
        OUTPUT_M_DIR = r'M:\Application\PBA50Plus_Data_Processing\Draft_Blueprint_Growth_Geographies'
        QAQC_DIR = os.path.join(OUTPUT_M_DIR, 'QAQC')
        GG_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_tra_pba50.shp')
    elif my_args.rtp_v == 'RTP2025DBP':
        OUTPUT_M_DIR = r'M:\Application\PBA50Plus_Data_Processing\Draft_Blueprint_Growth_Geographies'
        QAQC_DIR = os.path.join(OUTPUT_M_DIR, 'QAQC')
        GG_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_tra_pba50plus_DBP.shp')
        GG_nonPPA_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_nonPPA_tra_pba50plus_DBP.shp')  
    elif my_args.rtp_v == 'RTP2025FBP':
        OUTPUT_M_DIR = r'M:\Application\PBA50Plus_Data_Processing\Final_Blueprint_Growth_Geographies'
        QAQC_DIR = os.path.join(OUTPUT_M_DIR, 'QAQC')
        GG_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_tra_pba50plus_FBP.shp')
        GG_nonPPA_TRA_SHAPE_FILE = os.path.join(QAQC_DIR, 'gg_nonPPA_tra_pba50plus_FBP.shp')
        
    ## create dissolved or unioned growth geographies based on RTP and growth geographies version
    
    if my_args.rtp_v == 'RTP2021FBP':   # PBA50

        # GG
        logging.info('read GG file from {}'.format(GG_INPUT_PBA50_FILE))
        gg_gdf = gpd.read_file(GG_INPUT_PBA50_FILE)
        logging.debug(gg_gdf.head())

        gg_gdf['gg_50'] = 'GG'
        logger.info('crs: {}'.format(gg_gdf.crs))
        gg_gdf_proj = gg_gdf.to_crs(analysis_crs)
        # write out for QAQC
        gg_gdf_proj.to_file(os.path.join(QAQC_DIR, 'GG_pba50.shp'))

        # TRAs
        tra1_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE1)
        tra2_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE2)
        tra3_gdf = gpd.read_file(TRA_INPUT_PBA50_FILE3)

        tra1_gdf_proj = tra1_gdf.to_crs(analysis_crs)
        tra2_gdf_proj = tra2_gdf.to_crs(analysis_crs)
        tra3_gdf_proj = tra3_gdf.to_crs(analysis_crs)

        tra12_gdf = tra1_gdf_proj.union(tra2_gdf_proj)
        tra123_gdf = tra12_gdf.union(tra3_gdf_proj)
        tra_gdf = gpd.GeoDataFrame(geometry=tra123_gdf)
        tra_gdf['tra_50'] = 'tra'
        # write out for QAQC
        tra_gdf.to_file(os.path.join(QAQC_DIR, 'tra_pba50.shp'))

        # GG and TRA
        gg_tra_gdf = gpd.overlay(gg_gdf_proj, tra_gdf)

        # write out GG-TRA intersection
        logger.info('write out GG_TRA_pba50 intersection geography to {}'.format(GG_TRA_SHAPE_FILE))
        gg_tra_pba50_gdf[['gg_50', 'tra_50', 'geometry']].to_file(GG_TRA_SHAPE_FILE)

    elif my_args.rtp_v == 'RTP2025DBP': # PBA50+ Draft Blueprint

        ## Growth geographies
        logging.info('read GG file from {}'.format(GG_INPUT_FILE))
        gg_gdf = gpd.read_file(GG_INPUT_FILE)
        logging.debug(gg_gdf.head())
        gg_gdf['gg_50plus'] = 'GG'
        logger.info('crs: {}'.format(gg_gdf.crs))
        gg_gdf_proj = gg_gdf.to_crs(analysis_crs)
        # write out for QAQC
        gg_gdf_proj.to_file(os.path.join(QAQC_DIR, 'GG_pba50plusDBP.shp'))

        ## PPAs
        logging.info('getting PPA data from {}'.format(PPA_INPUT_FILE))
        layers = fiona.listlayers(PPA_INPUT_FILE)
        logging.info('the gdb contains the following layers: {}'.format(layers))
        ppa_gdf = gpd.read_file(PPA_INPUT_FILE, driver='fileGDB', layer='PPA_ExportFeatures')

        logger.info('initial crs: {}'.format(ppa_gdf.crs))
        ppa_gdf_proj = ppa_gdf.to_crs(analysis_crs)
        logger.debug(ppa_gdf_proj.head())

        ## TRAs
        logging.info('read TRA file from {}'.format(TRA_INPUT_FILE))
        tra_gdf = gpd.read_file(TRA_INPUT_FILE)
        logging.debug(tra_gdf.head())
        logging.debug(tra_gdf['PBA50_Geo'].value_counts(dropna=False))

        logging.info('crs: {}'.format(tra_gdf.crs))
        tra_gdf_proj = tra_gdf.to_crs(analysis_crs)

        # combine TRA 1/2/3 categories and dissolve into TRA
        logging.info('dissolve TRA categories')
        tra_gdf_proj['tra_50plus'] = ''
        tra_gdf_proj.loc[tra_gdf_proj['PBA50_Geo'].notnull(), 'tra_50plus'] = 'tra'
        tra_dissolve_gdf = tra_gdf_proj.dissolve(by='tra_50plus').reset_index()
        logging.debug('after dissolving, unique TRA values: {}'.format(tra_dissolve_gdf['tra_50plus'].unique()))
        # write out for QAQC
        logging.info('write out dissolved TRA data for QAQC')
        tra_gdf_proj.to_file(os.path.join(QAQC_DIR, 'tra_pba50plusDBP.shp'))

        # generic GG and TRA intersection
        logging.info('create intersection of GG and TRA')
        gg_tra_gdf = gpd.overlay(gg_gdf_proj, tra_dissolve_gdf, how='intersection')

        # for travel model parking policies - need GG & TRA intersection, but without PPA in GG
        logging.info('create GG_nonPPA by clipping PPA out from GG')
        gg_nonPPA_gdf = gg_gdf_proj.overlay(ppa_gdf_proj, how='difference')
        gg_nonPPA_gdf['gg_50plus'] = 'gg_nonPPA'
        logging.info('write out the clipped GG data for QAQC')
        gg_nonPPA_gdf.to_file(os.path.join(QAQC_DIR, 'gg_nonPPA_pba50plusDBP.shp'))
        logging.info('create intersection of GG_nonPPA and TRA')
        gg_nonPPA_tra_gdf = gpd.overlay(gg_nonPPA_gdf, tra_dissolve_gdf, how='intersection')

        # write out GG-TRA intersection
        logger.info('write out GG_TRA intersection geography to {}'.format(GG_TRA_SHAPE_FILE))
        gg_tra_gdf[['gg_50plus', 'tra_50plus', 'geometry']].to_file(GG_TRA_SHAPE_FILE)

        logger.info('write out GG_nonPPA_TRA intersection geography to {}'.format(GG_nonPPA_TRA_SHAPE_FILE))
        gg_nonPPA_tra_gdf[['gg_50plus', 'tra_50plus', 'geometry']].to_file(GG_nonPPA_TRA_SHAPE_FILE)

    elif my_args.rtp_v == 'RTP2025FBP': # PBA50+ Final Blueprint

        ## Growth geographies
        logging.info('read GG file from {}'.format(GG_INPUT_FBP_FILE))
        gg_gdf = gpd.read_file(GG_INPUT_FBP_FILE)
        logging.debug(gg_gdf.head())
        assert gg_gdf.shape[0] == 1
        gg_gdf['gg_50plus'] = 'GG'
        logger.info('crs: {}'.format(gg_gdf.crs))
        gg_gdf_proj = gg_gdf.to_crs(analysis_crs)
        # dissolve
        gg_dissolve_gdf = gg_gdf_proj.dissolve(by='gg_50plus').reset_index()
        assert gg_dissolve_gdf.shape[0] == 1       
        # write out for QAQC
        gg_dissolve_gdf.to_file(os.path.join(QAQC_DIR, 'GG_pba50plusFBP.shp'))
    
        ## Growth geographies within PPA
        logging.info('read GG-nonPPA file from {}'.format(GGnonPPA_INPUT_FBP_FILE))
        gg_nonPPA_gdf = gpd.read_file(GGnonPPA_INPUT_FBP_FILE)
        logging.debug(gg_nonPPA_gdf.head())
        gg_nonPPA_gdf['gg_50plus'] = 'gg_nonPPA'
        logger.info('crs: {}'.format(gg_nonPPA_gdf.crs))
        gg_nonPPA_gdf_proj = gg_nonPPA_gdf.to_crs(analysis_crs)
        # dissolve
        gg_nonPPA_dissolve_gdf = gg_nonPPA_gdf_proj.dissolve(by='gg_50plus').reset_index()
        assert gg_nonPPA_dissolve_gdf.shape[0] == 1

        # write out for QAQC
        gg_nonPPA_dissolve_gdf.to_file(os.path.join(QAQC_DIR, 'gg_nonPPA_pba50plusFBP.shp'))

        # TRAs
        tra1_gdf = gpd.read_file(TRA_INPUT_FBP_FILE1)
        tra2_gdf = gpd.read_file(TRA_INPUT_FBP_FILE2)
        tra3_gdf = gpd.read_file(TRA_INPUT_FBP_FILE3)
        tra4_gdf = gpd.read_file(TRA_INPUT_FBP_FILE4)
        tra5_gdf = gpd.read_file(TRA_INPUT_FBP_FILE5)

        tra1_gdf_proj = tra1_gdf.to_crs(analysis_crs)
        tra2_gdf_proj = tra2_gdf.to_crs(analysis_crs)
        tra3_gdf_proj = tra3_gdf.to_crs(analysis_crs)
        tra4_gdf_proj = tra4_gdf.to_crs(analysis_crs)
        tra5_gdf_proj = tra5_gdf.to_crs(analysis_crs)

        tras_gdf = pd.concat([tra1_gdf_proj, tra2_gdf_proj, tra3_gdf_proj, tra4_gdf_proj, tra5_gdf_proj])
        tras_gdf['tra_50plus'] = 'tra'
        tra_dissolve_gdf = tras_gdf.dissolve(by='tra_50plus').reset_index()
        # write out for QAQC
        logging.info('write out dissolved TRA data for QAQC')
        tras_gdf.to_file(os.path.join(QAQC_DIR, 'tra_pba50plusFBP_before_dissolve.shp'))
        tra_dissolve_gdf.to_file(os.path.join(QAQC_DIR, 'tra_pba50plusFBP_dissolve.shp'))

        # generic GG and TRA intersection
        logging.info('create intersection of GG and TRA')
        logging.info('{} rows left'.format(len(gg_dissolve_gdf)))
        logging.info('{} rows right'.format(len(tra_dissolve_gdf)))
        gg_tra_gdf = gpd.overlay(gg_dissolve_gdf, tra_dissolve_gdf, how='intersection')
        logging.info('{} rows'.format(len(gg_tra_gdf)))
    
        # Growth Geographies and TRAs for travel model parking policies - need GG & TRA intersection, but without PPA in GG
        logging.info('create intersection of GG_nonPPA and TRA')
        logging.info('{} rows left'.format(len(gg_nonPPA_dissolve_gdf)))
        logging.info('{} rows right'.format(len(tra_dissolve_gdf)))
        gg_nonPPA_tra_gdf = gpd.overlay(gg_nonPPA_dissolve_gdf, tra_dissolve_gdf, how='intersection')   
        logging.info('{} rows'.format(len(gg_nonPPA_tra_gdf)))

        # write out GG-TRA intersection
        logger.info('write out GG_TRA intersection geography to {}'.format(GG_TRA_SHAPE_FILE))
        gg_tra_gdf[['gg_50plus', 'tra_50plus', 'geometry']].to_file(GG_TRA_SHAPE_FILE)

        logger.info('write out GG_nonPPA_TRA intersection geography to {}'.format(GG_nonPPA_TRA_SHAPE_FILE))
        gg_nonPPA_tra_gdf[['gg_50plus', 'tra_50plus', 'geometry']].to_file(GG_nonPPA_TRA_SHAPE_FILE)
