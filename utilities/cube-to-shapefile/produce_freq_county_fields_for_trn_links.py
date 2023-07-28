USAGE = """

  Joins network_trn_links shapefile to county and network_trn_lines shapefile. 
  For links intersecting with multiple counties, it is joined to whichever county most part of the link intersects with

  Output shapefile is called network_trn_links_by_county_freq.shp has the all columns from network_trn_links.shp and the follownig additional columns:
  * coname: county name            
  * FREQ_EA             
  * FREQ_AM           
  * FREQ_MD     
  * FREQ_PM    
  * FREQ_EV

  Requires GeoPandas. 
  TODO: Add geopandas to tm15-python310 environment (https://github.com/BayAreaMetro/modeling-website/wiki/SetupConfiguration)

  Developed for task: Add transit VRH and transit boarding by county to Transit tableau
  https://app.asana.com/0/1200580945030144/1205086281493905/f

"""

import argparse, os
import geopandas as gpd
import numpy,pandas

TAZ_SHAPEFILE = "M:\\Data\\GIS layers\\TM1_taz\\bayarea_rtaz1454_rev1_WGS84.shp"

if __name__ == '__main__':
    # STEP 1: read files
    # read network_trn_links.shp
    TRN_LINKS_SHPFILE = gpd.read_file('network_trn_links.shp')
    print(TRN_LINKS_SHPFILE)
   
    # read county shapefile: the shapefile is downloaded from https://opendata.mtc.ca.gov/datasets/MTC::san-francisco-bay-region-counties-1/explore
    COUNTY_SHPFILE    = gpd.read_file("X:/travel-model-one-master/utilities/geographies/region_county.shp")
    # for some reason, the original data downloaded from MTC data portal doesn't have county name. The "coname" column is all NULL
    # fill "coname" field with county name
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 10, 'coname'] = 'Sonoma' 
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 11, 'coname'] = 'San Francisco'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 12, 'coname'] = 'Marin'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 13, 'coname'] = 'Napa'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 14, 'coname'] = 'Solano'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 15, 'coname'] = 'Contra Costa'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 16, 'coname'] = 'Santa Clara'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 17, 'coname'] = 'Alameda'
    COUNTY_SHPFILE.loc[COUNTY_SHPFILE['objectid'] == 18, 'coname'] = 'San Mateo'
    # project the county shapefile to transit link shapefile
    COUNTY_SHPFILE    = COUNTY_SHPFILE.to_crs(TRN_LINKS_SHPFILE.crs)
    COUNTY_SHPFILE    = COUNTY_SHPFILE[['coname', 'geometry']]

    # read network_trn_lines.shp
    TRN_LINES_SHPFILE = gpd.read_file("network_trn_lines.shp")

    # STEP 2: join network_trn_links.shp with the county shapefile
    # for links intersecting with multiple counties, it is joined to whichever county most part of the link intersects with
    TRN_LINKS_SHPFILE_COUNTY = gpd.overlay(TRN_LINKS_SHPFILE, COUNTY_SHPFILE, how='intersection')
    # calculate length of the intersectd links
    TRN_LINKS_SHPFILE_COUNTY['linkcounty_mi'] = TRN_LINKS_SHPFILE_COUNTY['geometry'].length/5280
    # sort all links by name, seq, and length
    TRN_LINKS_SHPFILE_COUNTY = TRN_LINKS_SHPFILE_COUNTY.sort_values(by = ['NAME', 'SEQ', 'linkcounty_mi'], ascending = [True, True, False])
    # remove repeat links of each line
    TRN_LINKS_SHPFILE_COUNTY = TRN_LINKS_SHPFILE_COUNTY.drop_duplicates(subset=['NAME', 'SEQ', 'A', 'B'])
    # remove column linkcounty_mi
    TRN_LINKS_SHPFILE_COUNTY = TRN_LINKS_SHPFILE_COUNTY.drop(['linkcounty_mi'], axis=1)
    print("TRN_LINKS_SHPFILE_COUNTY")
    print(TRN_LINKS_SHPFILE_COUNTY)

    # STEP 3: join network_trn_links.shp with network_trn_lines.shp to get FREQ information
    TRN_LINES_SHPFILE = TRN_LINES_SHPFILE[['NAME', 'FREQ_EA', 'FREQ_AM', 'FREQ_MD', 'FREQ_PM', 'FREQ_EV']]
    TRN_LINKS_SHPFILE_COUNTY_FREQ = TRN_LINKS_SHPFILE_COUNTY.merge(TRN_LINES_SHPFILE, on='NAME', how='left')
    print("TRN_LINKS_SHPFILE_COUNTY_FREQ")
    print(TRN_LINKS_SHPFILE_COUNTY_FREQ)

    # export
    TRN_LINKS_SHPFILE_COUNTY_FREQ.to_file("network_trn_links_by_county_freq.shp")




