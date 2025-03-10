USAGE = """

  Joins network link shapefile to TAZ (or any other) shapefile and determines correspondence between link => shape, portion of link
  Note that some links may span more than one shape; in this case, the link will be included multiple times, one for each shape.
  Therefore, (A, B, TAZ1454) is unique, but (A, B) is not.

  Links that intersect one or more shapes are corresponded to those shapes; if the link doesn't fully intersect
  with the shapefile, then the remainer of the link (e.g. over water) is corresponded to the shape with the largest
  share.
  Links that don't intersect any shape are corresponded to the nearest shape, with merge_type == 'nearest'.

  So in the resulting output, it will be true that the entirety of the link corresponds to one or more shapes.
  In other words,
    number of links in input = sum(linktaz_share) in output
    sum(link_mi) int input   = sum(linktaz_mi) in output
  
  Output csv has the following columns:
  * A             = A node
  * B             = B node
  * TAZ1454       = taz
  * link_mi       = total link length in miles (calculated by geopandas so may differ from DISTANCE)
  * linktaz_mi    = link intersect this taz length in miles (calculated by geoapandas)
  * linktaz_share = share of the link in this taz (e.g. linktaz_mi / link_mi)
  * merge_type    = 'intersect' or 'nearest'

  Note that linktaz_mi and linktaz_share columns are called this by default, but the column names can 
  be specified to be different using the arguments.

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

    # read network_links shapefile; don't worry about other (non-geometry) columns beyond A,B
    network_links = gpd.read_file(my_args.link_shapefile, columns=['A','B'])
    network_links.to_crs(2227, inplace=True)  # EPSG:2227 is Bay Area's local coordinate system - NAD83 / California zone 3 (ftUS)
    print(f"Read {len(network_links):,} links from {my_args.link_shapefile}")

    # assert A,B are unique
    assert not network_links.duplicated(subset=['A', 'B']).any()

    # calculate link length
    LENGTH_FIELD = "link_mi"
    network_links[LENGTH_FIELD] = network_links['geometry'].length/5280 # 1 mile = 5,280 feet
    print(f"sum(network_links[{LENGTH_FIELD}]) = {sum(network_links[LENGTH_FIELD]):,.2f}")

    # read shapefile (use TAZ_SHAPEFILE if not specified)
    input_shapefile = TAZ_SHAPEFILE
    if (my_args.shapefile): input_shapefile = my_args.shapefile
    my_shapefile = gpd.read_file(input_shapefile, columns=[my_args.shp_id])
    my_shapefile.to_crs(2227, inplace=True)     # EPSG:2227 is Bay Area's local coordinate system - NAD83 / California zone 3 (ftUS)
    print(f"Read {len(my_shapefile):,} links from {input_shapefile}")

    # intersect
    link_intersect_taz = gpd.overlay(network_links, my_shapefile, how='intersection')
    print(f"After intersecting links with shapefile, have {len(link_intersect_taz):,} rows")

    # Some links did not intersect; for example those on the region periphery and bridge
    # links.  For these, do special handling to get the nearest TAZ
    check_df = pandas.merge(
        left=network_links,
        right=link_intersect_taz[['A','B',my_args.shp_id]],
        how='outer',
        on=['A','B'],
        indicator=True,
        validate='one_to_many'
    )
    print(f"check_df for intersect failure: {check_df._merge.value_counts()=}")
    unjoined_df = check_df.loc[check_df._merge=='left_only']
    print(f"unjoined_df len={len(unjoined_df):,} type={type(unjoined_df)}\n{unjoined_df}")
    # for these, do nearest
    nearest_shp = gpd.sjoin_nearest(unjoined_df[['A','B','geometry',LENGTH_FIELD]], my_shapefile, how='inner')
    # columns are: A, B, geometry, LENGTH_FIELD, index_right, my_args.shp_id
    print(f"nearest_shp:\n{nearest_shp}")
    nearest_shp['merge_type'] = 'nearest'

    # merge nearest results with overlay/intersect results
    link_intersect_taz['merge_type'] = 'intersect'
    link_intersect_taz = pandas.concat([link_intersect_taz, nearest_shp])
    print(f"link_intersect_taz after merging with nearest_shp has {len(link_intersect_taz):,} rows, type={type(link_intersect_taz)}")
    print(f"{link_intersect_taz['merge_type'].value_counts()=}")
    print(f"duplicate A,B,{my_args.shp_id}:\n{link_intersect_taz[link_intersect_taz.duplicated(subset=['A','B',my_args.shp_id], keep=False)]}")

    # calculate length of these links
    link_intersect_taz[my_args.linkshp_mi] = link_intersect_taz['geometry'].length/5280 # 1 mile = 5,280 feet

    # drop other fields and create simplified pandas dataframe
    fields = ["A","B",my_args.shp_id,LENGTH_FIELD,my_args.linkshp_mi,'merge_type']
    links_df = link_intersect_taz[fields].copy().reset_index(drop=True)

    # divide lengths to get proportion
    links_df[my_args.linkshp_share] = links_df[my_args.linkshp_mi]/links_df[LENGTH_FIELD]
    print(f"links_df has {len(links_df):,} rows; head:\n{links_df.head()}")

    # Finally, some links intersect 1 or more TAZs but then the remainder are over the water.
    # Let's attribute the remainder distance to the TAZ with the biggest share

    # first, find row for A,B with largest value of my_args.linkshp_share
    linkshp_share_idx = links_df.groupby(['A','B'])[my_args.linkshp_share].idxmax()
    print(f"linkshp_share_idx=\n{linkshp_share_idx}")
    max_linkshp_share_df = links_df.loc[ linkshp_share_idx.reset_index(drop=True) ]
    # columns are A,B,my_args.shp_id,link_mi,linktaz_mi,merge_type,my_args.linkshp_share
    print(f"max_linkshp_share_df=\n{max_linkshp_share_df}")
    # A,B is unique
    assert not max_linkshp_share_df.duplicated(subset=['A', 'B']).any()

    # now find total linkshp_share and number of shapes (e.g. TAZs) for each link
    total_linkshp_share_df = links_df.groupby(['A','B']).agg(
        linkshp_share_sum = pandas.NamedAgg(column=my_args.linkshp_share, aggfunc="sum"),
        shp_id_count      = pandas.NamedAgg(column=my_args.shp_id, aggfunc="nunique")
    ).reset_index(drop=False)
    print(f"total_linkshp_share_df=\n{total_linkshp_share_df}")

    # put them together
    linkshp_share_df = pandas.merge(
        left=total_linkshp_share_df,
        right=max_linkshp_share_df,
        how='outer',
        on=['A','B'],
        indicator=True,
        validate='one_to_one'
    )
    # make sure A,B,shp_id are unique
    assert not linkshp_share_df.duplicated(subset=['A', 'B',my_args.shp_id]).any()
    assert(linkshp_share_df._merge == 'both').all()

    # look at links that didn't all map - and allocate the unmapped portion to the biggest shp
    linkshp_share_df = linkshp_share_df.loc[linkshp_share_df.linkshp_share_sum < 1.0]
    linkshp_share_df['add_share' ] = 1.0 - linkshp_share_df.linkshp_share_sum
    linkshp_share_df['add_length'] = (linkshp_share_df[my_args.linkshp_mi] / linkshp_share_df[my_args.linkshp_share])*linkshp_share_df.add_share

    print(f"linkshp_share_df=\n{linkshp_share_df}")
    print(f"{linkshp_share_df['_merge'].value_counts()=}")

    # select only relevant columns and join to result
    linkshp_share_df = linkshp_share_df[['A','B',my_args.shp_id,'add_share','add_length']]
    links_df = pandas.merge(
        left=links_df,
        right=linkshp_share_df,
        how='left',
        on=['A','B',my_args.shp_id],
        indicator=True,
        validate='one_to_one'
    )
    print(f"links to update:\n{links_df.loc[ links_df._merge=='both']}")
    links_df.loc[ links_df._merge=='both', my_args.linkshp_share ] = links_df[my_args.linkshp_share] + links_df.add_share
    links_df.loc[ links_df._merge=='both', my_args.linkshp_mi    ] = links_df[my_args.linkshp_mi]    + links_df.add_length
    links_df.drop(columns=['add_share','add_length','_merge'], inplace=True)
    print(f"sum(links_df[{my_args.linkshp_mi}]) = {sum(links_df[my_args.linkshp_mi]):,.2f}")

    # write it
    links_df.to_csv(my_args.link_to_taz_csv, index=False)
    print(f"Wrote to {my_args.link_to_taz_csv}")
