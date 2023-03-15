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
import argparse, os

TARGET_CRS = 4326


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

    # load the data
    raw_link_gdf = gpd.read_file(os.path.join(FILE_DIR, RAW_LINK_FILE))
    print('raw data crs: {}'.format(raw_link_gdf.crs))
    print('data has {:,} rows'.format(raw_link_gdf.shape[0]))
    print(raw_link_gdf.head())

    # convert to 4326
    link_gdf = raw_link_gdf.to_crs(TARGET_CRS)

    # extract points from lingstring
    link_gdf['points'] = link_gdf.apply(lambda l: linestring_to_points(l), axis=1)

    # extract X, Y of A/B nodes
    link_gdf['A_point'] = link_gdf['points'].apply(lambda x: x[0])
    link_gdf['B_point'] = link_gdf['points'].apply(lambda x: x[1])
    link_gdf['A_X'] = link_gdf['A_point'].apply(lambda x: x[0])
    link_gdf['A_Y'] = link_gdf['A_point'].apply(lambda x: x[1])
    link_gdf['B_X'] = link_gdf['B_point'].apply(lambda x: x[0])
    link_gdf['B_Y'] = link_gdf['B_point'].apply(lambda x: x[1])
    # double check
    print(link_gdf[['A', 'B', 'geometry', 'A_point', 'B_point', 'A_X', 'A_Y', 'B_X', 'B_Y']].head())
    
    # export
    link_gdf[list(raw_link_gdf) + ['A_X', 'A_Y', 'B_X', 'B_Y']].to_file(
        os.path.join(FILE_DIR, LINK_WITH_XY_FILE)
    )
    print('wrote {} to {}'.format(LINK_WITH_XY_FILE, FILE_DIR) )