USAGE = """

Create crosswalk between TAZ and Census geographies (e.g. tract, block, etc.), or between TAZ / Tract and other geographies (e.g. Growth Geographies, TRA).
It is based on "largest area within" method, i.e. if a TAZ falls into multiple Census Tracts, it is assigned to the Tract with the largest intersection area with the TAZ.

Args:
    base_geo_file: full directory of the base spatial layer
    base_geo_name: short name of the base layer, e.g. 'TAZ1454', 'Tract20', 'TRA'
    base_geo_unique_ID: unique ID of the base geography, e.g. 'TAZ1454', 'GEOID'
    overlay_geo_file: full directory of the overlay spatial layer
    overlay_geo_name: short name of the base layer, e.g. 'TAZ1454', 'Tract20', 'TRA'
    overlay_geo_unique_ID: unique ID of the overlay geography, e.g. 'TAZ1454', 'GEOID'
    output_dir: directory of the output
    --scenario: optional, plan scenario, e.g. 'DBP','FBP','NP','EIR1','EIR2'

Output: 
    [base_geo_name]_[overlay_geo_name]_crosswalk_[scenario].csv. With fields:
        * base_geo_unique_ID
        * base_sq_m: size of each base polygon in square-meter
        * overlay_geo_unique_ID + overlay_geo_name
        * intersection_sq_m: size of the intersection between each base polygon and the matched overlay polygon (the one with the largest intersection)
        * area_share: the ratio of the intersection's area to the total area for each base polygon. 
        * scen: scenario
    It should have the same record count as the base layer.

Example call: 
    python TAZ_Census_otherGeographies_overlay_crosswalk.py "M:/Data/Census/Geography/tl_2020_06_tract/tl_2020_06_tract_bayarea.shp" "tract2020" "GEOID" "C:/Users/ywang/Box/Modeling and Surveys/Urban Modeling/Bay Area UrbanSim/p10 Datasets for PBA2050plus/raw_data_to_build_parcels_geography/pba50plus_GrowthGeographies_p10tagging/PBA50Plus_Growth_Geographies_120823.shp" "ggPBA50plus" "gg_id" "M:/Application/PBA50Plus_Data_Processing/crosswalks/interim" --scenario DBP

"""

import pandas as pd
import numpy as np
import geopandas as gpd
import argparse, os, sys, logging, time

today = time.strftime('%Y_%m_%d')
analysis_crs = "EPSG:26910"

# Note: project_to_analysis_crs() and geo_assign_fields() are based on https://github.com/BayAreaMetro/dvutils/blob/7f4831064e12aa238ed0836b2f4faea7da43dfac/utils_analytics.py#L2530,
# with minor modifications.
def project_to_analysis_crs(geo_df):
    """Checks for whether a GeoDataFrame is in the analysis CRS (EPSG:26910) and reprojects if not.

    Args:
        geo_df (geopandas GeoDataFrame): A geopandas GeoDataFrame needs to be reprojected for
            spatial analysis

    Returns:
        geopandas GeoDataFrame: A geopandas GeoDataFrame in the analysis CRS (EPSG:26910)
    """
    if geo_df.crs != analysis_crs:
        logger.debug("GeoDataFrame must be in EPSG:26910. Reprojecting:")
        try:
            geo_df = geo_df.to_crs(analysis_crs)
        except:
            logger.debug("Error reprojecting, correct geometries and re-run.")
            return
    return geo_df


def geo_assign_fields(id_df, id_field, overlay_df, overlay_fields, return_intersection_area=False, use_half_area_rule=True):
    """Given an id_df and an overlay_df, assigns the overlay fields.

    Methodology:
    Assigns based on the area with the largest intersection with each id_field (where there are
    duplicate assignments).

    Notes:
    - This is primarily used for generating correspondences, such as new parcel id : old parcel id
    - If any overlay_fields also occur in the id_df, append a _y suffix to the overlay field

    Args:
        id_df (geopandas GeoDataFrame): The ID GeoDataFrame
        id_field (str): The name of the ID column in the ID GeoDataFrame
        overlay_df (geopandas GeoDataFrame): The overlay GeoDataFrame
        overlay_fields (list): A list of overlay fields to assign to the ID GeoDataFrame
        return_intersection_area (bool, optional): Flag for whether to return the intersection area
            of the overlay. Defaults to False.
        use_half_area_rule (bool, optional): Flag for whether to add "the intersection area is at least 50% of
            id_df area" condition in the assignment. Defaults to True.

    Returns:
        geopandas GeoDataFrame: The ID GeoDataFrame with the overlay fields assigned by largest
            intersection area
    """
    if id_df.crs != analysis_crs or overlay_df.crs != analysis_crs:
        logger.debug('base geo crs: {}'.format(id_df.crs))
        logger.debug('overlay geo crs: {}'.format(overlay_df.crs))
        logger.debug("Both GeoDataFrames must be in EPSG:26910. Reprojecting:")
        id_df = project_to_analysis_crs(id_df)
        overlay_df = project_to_analysis_crs(overlay_df)

    join_df = gpd.overlay(id_df, overlay_df, how="intersection")
    join_df["intersection_sq_m"] = join_df.geometry.area
    join_df["idx"] = join_df.index

    max_idxs = (
        join_df.groupby(id_field, as_index=False)
        .agg({"intersection_sq_m": "idxmax"})
        .rename(columns={"intersection_sq_m": "idx"})
    )
    join_df = join_df.merge(max_idxs)

    final_fields = [id_field] + overlay_fields

    # calculate intersection area and share of id_df in intersection
    id_df['base_sq_m'] = id_df.geometry.area
    final_assignment = id_df[[id_field, 'base_sq_m']].merge(join_df[final_fields+['intersection_sq_m']], how="left")
    final_assignment['area_share'] = final_assignment['intersection_sq_m'] / final_assignment['base_sq_m']

    # set the assignment to NaN if no more than 50%
    if use_half_area_rule:
        for i in overlay_fields:
            final_assignment.loc[final_assignment['area_share'] < 0.5, i] = np.nan

    if return_intersection_area:
        return final_assignment[final_fields+['base_sq_m', 'intersection_sq_m', 'area_share']]
    else:
        return final_assignment


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter,)
    parser.add_argument('base_geo_file', help='Base geography spatial file with the full directory')
    parser.add_argument('base_geo_name', help='Base geography name, e.g. "TAZ1454"')
    parser.add_argument('base_geo_unique_ID', help='Specify the unique ID of the base geography, e.g. "TAZ1454"')
    parser.add_argument('overlay_geo_file',  help='Overlay geography spatial file with the full directory')
    parser.add_argument('overlay_geo_name', help='Overlay geography name, e.g. "tract2020", "block2010"')
    parser.add_argument('overlay_geo_unique_ID', help='Specify the unique ID of the Overlay geography, e.g. "GEOID"')
    parser.add_argument('output_dir',  help='Output directory')
    # optional input, choices=['DBP','FBP','NP','EIR1','EIR2'] when creating plan-scenario based crosswalk
    parser.add_argument('--scenario', help='Plan scenario')
    args = parser.parse_args()

    # input
    BASE_GEO_FILE = args.base_geo_file
    BASE_NAME = args.base_geo_name
    BASE_GEO_ID = args.base_geo_unique_ID
    OVERLAY_GEO_FILE = args.overlay_geo_file
    OVERLAY_NAME = args.overlay_geo_name
    OVERLAY_GEO_ID = args.overlay_geo_unique_ID
    SCENARIO = args.scenario
    
    # output
    OUTPUT_DIR = args.output_dir
    if SCENARIO is not None:
        OUTPUT_FILE = os.path.join(OUTPUT_DIR, '{}_{}_crosswalk_{}.csv'.format(BASE_NAME, OVERLAY_NAME, SCENARIO))
        LOG_FILE = os.path.join(OUTPUT_DIR, 'create_{}_{}_crossawlk_{}_{}.log'.format(BASE_NAME, OVERLAY_NAME, SCENARIO, today))
    else:
        OUTPUT_FILE = os.path.join(OUTPUT_DIR, '{}_{}_crosswalk.csv'.format(BASE_NAME, OVERLAY_NAME))
        LOG_FILE = os.path.join(OUTPUT_DIR, 'create_{}_{}_crossawlk_{}.log'.format(BASE_NAME, OVERLAY_NAME, today))
        print(LOG_FILE)     

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

    logger.info('overlaying {} onto {}'.format(OVERLAY_NAME, BASE_NAME))

    # loading the input files - base layer
    logger.info('loading base geography data: {}, from {}'.format(BASE_NAME, BASE_GEO_FILE))
    base_geo = gpd.read_file(BASE_GEO_FILE)
    logger.info('{} rows, {} unique {}'.format(base_geo.shape[0], base_geo[BASE_GEO_ID].nunique(), BASE_GEO_ID))
    
    # loading the input files - overlay layer
    logger.info('loading overlay geography data: {}, from {}'.format(OVERLAY_NAME, OVERLAY_GEO_FILE))
    # census_geo = gpd.read_file(r'M:\Data\Census\Geography\tl_2020_06_tract\tl_2020_06_tract_bayarea.shp')
    overlay_geo = gpd.read_file(OVERLAY_GEO_FILE)
    # there are cases when the overlay data doesn't have a unique ID, i.e. only one record (one geography category), then add a field
    if OVERLAY_GEO_ID not in overlay_geo:
        overlay_geo[OVERLAY_GEO_ID] = OVERLAY_NAME
    logger.info('{} rows, {} unique {}'.format(overlay_geo.shape[0], overlay_geo[OVERLAY_GEO_ID].nunique(), OVERLAY_GEO_ID))

    # create crosswalk between base data ID and overlay data ID
    logger.info('creating {} - {} crosswalk'.format(BASE_NAME, OVERLAY_NAME))
    crosswalk = geo_assign_fields(base_geo, BASE_GEO_ID, overlay_geo, [OVERLAY_GEO_ID], return_intersection_area=True, use_half_area_rule=False)
    logger.info('crosswalk created: {} rows, {} unique {}, with header \n{}'.format(
        crosswalk.shape[0], crosswalk[BASE_GEO_ID].nunique(), BASE_GEO_ID, crosswalk.head()))
    # add overlay name to the ID column name for clarity
    crosswalk.rename(columns = {OVERLAY_GEO_ID: OVERLAY_GEO_ID+'_'+OVERLAY_NAME}, inplace=True)
    # add scenario column
    if SCENARIO is not None:
        crosswalk['scen'] = SCENARIO

    # write out
    logger.info('writing out to {}'.format(OUTPUT_FILE))
    crosswalk.to_csv(OUTPUT_FILE, index=False)

   