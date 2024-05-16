USAGE = """
  python shapefile_move_timeperiod_to_rows.py

  Moves the timeperiod from columns to rows for a given shapefile.
  This is useful for transit shapefiles to join to to transit_crowding_complete.csv
  
"""

import argparse, os, re, sys
import geopandas as gpd
import pandas as pd

if __name__ == '__main__':

    pd.options.display.width = 1000
    pd.options.display.max_rows = 1000
    pd.options.display.max_columns = 30
    parser = argparse.ArgumentParser(description = USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_shapefile', type=str, help="Input shapefile")
    parser.add_argument('output_shapefile', type=str, help="Input shapefile")
    my_args = parser.parse_args()

    network_shp = gpd.read_file(my_args.input_shapefile)
    print(f"Read {len(network_shp):,} rows from {my_args.input_shapefile}")
    print(f"network_shp.dtypes:\n{network_shp.dtypes}")

    timeperiod_re = re.compile(r"^(.*)_(EA|AM|MD|PM|EV)$")
    stubnames = []  # Wide format variables assumed to start with this
    i = []          # Columns to use as id-variables
    for colname in network_shp.columns.tolist():
        match_obj = timeperiod_re.match(colname)
        print(f"colname {colname}: match_obj:{match_obj}")

        # use as id variable
        if match_obj == None:
            i.append(colname)
            continue
        # matches
        if match_obj.group(1) not in stubnames:
            stubnames.append(match_obj.group(1))
            continue
    print(f"stubnames: {stubnames}")
    print(f"i: {i}")

    # pull out the geometry along with the other id fields
    assert('geometry' in i)
    id_gdf = network_shp[i]
    print('type(id_gdf): {type(id_gdf)}')
    i.remove('geometry')
    print(f"i updated:{i}")
  
    # do the transformation
    network_long_shp = pd.wide_to_long(
        network_shp,
        stubnames=stubnames,
        i=i,
        j="timeperiod",
        sep="_",
        suffix="(EA|AM|MD|PM|EV)"
    ).reset_index(drop=False)
    print(network_long_shp.columns)

    network_long_shp = pd.merge(
        left=id_gdf,
        right=network_long_shp,
        how='left'
    )
    print(f"type(network_long_shp): {type(network_long_shp)}")
    network_long_shp.to_file(my_args.output_shapefile)
    print(f"Wrote {len(network_long_shp):,} rows to {my_args.output_shapefile}")