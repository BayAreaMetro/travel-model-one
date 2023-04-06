USAGE = """
Prepare network shapefile for visualizing in Tableau with overlapping links offset based on direction. 
Does two things:
- convert to crs 4326
- extract the X and Y of each link's A, B nodes

Example call: python prepare_link_shp_for_tableau_offset.py L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\2035_TM152_NGF_NP02_BPALTsegmented_03_SimpleTolls01\\OUTPUT\\shapefile network_links.shp

Args: 
    links.shp: network links shapefile

Returns:
    links_withXY.shp: network links shapefile with crs 4326, and four additional columns: 'A_X', 'A_Y', 'B_X', 'B_Y'  
"""

import geopandas as gpd
import argparse, os, logging, time
from datetime import datetime

TARGET_CRS = 4326

# get date for the logging file
today = time.strftime("%Y_%m_%d")


def linestring_to_points(line):
    """
    extracts points from a linestring
    """
    return line['geometry'].coords


if __name__ == '__main__':

    # process one run at a time
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument('folder_dir', help='Provide the location of the file')
    parser.add_argument('network_links_shp', help='Provide the network links shapefile')

    args = parser.parse_args()

    # INPUT
    RAW_LINK_FILE = args.network_links_shp
    FILE_DIR = args.folder_dir
    # OUTPUT
    LINK_WITH_XY_FILE = RAW_LINK_FILE.split('.shp')[0] + '_withXY.shp'
    LOG_FILE = os.path.join(FILE_DIR, "prepare_link_shp_for_tableau_offset_{}.log".format(today))

    # set up logging
    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel('DEBUG')

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel('INFO')
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(ch)
    # file handler
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel('DEBUG')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'))
    logger.addHandler(fh)

    # load the data
    logger.info('start loading the network data')
    raw_link_gdf = gpd.read_file(os.path.join(FILE_DIR, RAW_LINK_FILE))
    logger.info('finished loading the network data')
    logger.info('raw data crs: {}'.format(raw_link_gdf.crs))
    logger.info('data has {:,} rows'.format(raw_link_gdf.shape[0]))
    logger.info(raw_link_gdf.head())

    # convert to 4326
    logger.info('converting to crs 4326')
    link_gdf = raw_link_gdf.to_crs(TARGET_CRS)

    # extract points from linestring
    logger.info('extracting points from linestring')
    link_gdf['points'] = link_gdf.apply(lambda l: linestring_to_points(l), axis=1)

    # extract X, Y of A/B nodes
    logger.info('adding X Y')
    link_gdf['A_point'] = link_gdf['points'].apply(lambda x: x[0])
    link_gdf['B_point'] = link_gdf['points'].apply(lambda x: x[1])
    link_gdf['A_X'] = link_gdf['A_point'].apply(lambda x: x[0])
    link_gdf['A_Y'] = link_gdf['A_point'].apply(lambda x: x[1])
    link_gdf['B_X'] = link_gdf['B_point'].apply(lambda x: x[0])
    link_gdf['B_Y'] = link_gdf['B_point'].apply(lambda x: x[1])
    # double check
    logger.info(link_gdf[['A', 'B', 'geometry', 'A_point', 'B_point', 'A_X', 'A_Y', 'B_X', 'B_Y']].head())

    # check column types
    coltypes_before = raw_link_gdf.dtypes
    coltypes_after = link_gdf.dtypes
    for colname in list(raw_link_gdf):
        logger.debug('{}: {} --> {}'.format(colname, coltypes_before[colname], coltypes_after[colname]))
    
    # check memory usage
    logger.debug('memory usage of old file: {}'.format(raw_link_gdf.memory_usage(index=True).sum()))
    logger.debug('memory usage of new file: {}'.format(link_gdf.memory_usage(index=True).sum()))
    logger.debug('memory usage of new columns :{}'.format(link_gdf[['A_X', 'A_Y', 'B_X', 'B_Y']].memory_usage(index=True).sum()))

    # export
    logger.info('Start writing out')
    link_gdf[list(raw_link_gdf) + ['A_X', 'A_Y', 'B_X', 'B_Y']].to_file(
        os.path.join(FILE_DIR, LINK_WITH_XY_FILE)
    )
    logger.info('wrote {} to {}'.format(LINK_WITH_XY_FILE, FILE_DIR) )