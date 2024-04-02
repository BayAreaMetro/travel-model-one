USAGE = """

  Joins network link shapefile to TAZ (or any other) shapefile and determines correspondence between link => shape, portion of link
  Note that some links may span more than one shape.

  Output csv has the following columns:
  * A             = A node
  * B             = B node
  * TAZ1454       = taz
  * link_mi       = total link length in miles (calculated by arcpy so may differ from DISTANCE)
  * linktaz_mi    = link intersect this taz length in miles (calculated by arcpy)
  * linktaz_share = share of the link in this taz (e.g. linktaz_mi / link_mi)

  Requires GeoPandas. 
  TODO: Add geopandas to tm15-python310 environment (https://github.com/BayAreaMetro/modeling-website/wiki/SetupConfiguration)

  Example usage:
  PS [M_dir for model run]\OUTPUT\shapefile> python X:\\travel-model-one-master\\utilities\\cube-to-shapefile\\correspond_link_to_TAZ.py 
    network_links.shp network_links_TAZ.csv

  Developed for task: Calculate metrics for emissions and fatalities at TAZ level
  https://app.asana.com/0/13098083395690/1195902248890525/f

"""

import argparse, os
import geopandas as gpd
import numpy,pandas

TAZ_SHAPEFILE = "M:\\Data\\GIS layers\\TM1_taz\\bayarea_rtaz1454_rev1_WGS84.shp"

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('link_shapefile',  type=str, help="Input link shapefile")
    parser.add_argument('link_to_taz_csv', type=str, help="Output link to taz csv")
    parser.add_argument('--shapefile',     type=str, help="TAZ or non-TAZ shapefile")
    parser.add_argument('--shp_id',        type=str, default="TAZ1454",       help="ID from shapefile")
    parser.add_argument('--linkshp_mi',    type=str, default="linktaz_mi",    help="Column name for link intersect this shape in miles")
    parser.add_argument('--linkshp_share', type=str, default="linktaz_share", help="Column name for share of the link intersecting this shape")
    my_args = parser.parse_args()

    # read network_links shapefile 
    network_links = gpd.read_file(my_args.link_shapefile)
    
    # calculate link length
    network_links  = network_links.to_crs(2227)  # EPSG:2227 is Bay Area's local coordinate system - NAD83 / California zone 3 (ftUS)
    length_field = "link_mi"
    network_links[length_field] = network_links['geometry'].length/5280 # 1 mile = 5,280 feet
    print(network_links)

    # read taz shapefile
    taz_feature = "tazs"
    my_shapefile = gpd.read_file(TAZ_SHAPEFILE)  
    my_shapefile = my_shapefile.to_crs(2227)     # EPSG:2227 is Bay Area's local coordinate system - NAD83 / California zone 3 (ftUS)
    print(my_shapefile)

    # intersect
    link_taz_feature = "link_intersect_taz"
    link_intersect_taz = gpd.overlay(network_links, my_shapefile, how='intersection')
    print(link_intersect_taz)

    # calculate length of these links
    length_taz_field = my_args.linkshp_mi
    link_intersect_taz[length_taz_field] = link_intersect_taz['geometry'].length/5280 # 1 mile = 5,280 feet

    # bring into pandas
    fields = ["A","B",my_args.shp_id,length_field,length_taz_field]
    print(fields)
    links_df = pandas.DataFrame(link_intersect_taz, columns=fields)

    # divide lengths to get proportion
    links_df[my_args.linkshp_share] = links_df[length_taz_field]/links_df[length_field]
    print("links_df has {} rows; head:\n{}".format(len(links_df), links_df.head()))

    # write it
    links_df.to_csv(my_args.link_to_taz_csv, index=False)
    print("Wrote to {}".format(my_args.link_to_taz_csv))
