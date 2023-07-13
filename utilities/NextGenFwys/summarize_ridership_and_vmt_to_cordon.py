import copy, os.path, re
import pandas as pd
import dbfread
import csv
import numpy as np
import geopandas as gpd



run_list = ["2035_TM152_NGF_NP10_Path4_02",
            "2035_TM152_NGF_NP10_Path3a_02", "2035_TM152_NGF_NP10_Path3b_02",
            "2035_TM152_NGF_NP10_Path1a_02","2035_TM152_NGF_NP10_Path1b_02",
            "2035_TM152_NGF_NP10_Path2a_02_10pc", "2035_TM152_NGF_NP10_Path2b_02_10pc",
          ]

# 1. SF cordon effect on VMT
# 1.1 VMT on SF links
network_links_df = pd.DataFrame()
for runid in run_list:
    network_links_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/shapefile/network_links.shp'
    network_links      = gpd.read_file(network_links_path)
    # note the runid
    network_links["runid"] = runid
    # add to transit_assignment_df
    network_links_df = pd.concat([network_links_df, network_links])


# Only select SF city links
network_links_sf = network_links_df.loc[
    network_links_df.CITYNAME == 'San Francisco'
]


# Only select SF cordon links
network_links_sf = network_links_df.loc[
    network_links_df.CITYNAME == 'San Francisco'
]
TAZ    = gpd.read_file('X:/travel-model-one-master/utilities/geographies/bayarea_rtaz1454_rev1_WGS84.shp').to_crs(network_links_sf.crs)
TAZ_sf = TAZ.loc[
    ((TAZ.TAZ1454 >= 1) & (TAZ.TAZ1454 <= 41))
    | (TAZ.TAZ1454 == 106)
    | (TAZ.TAZ1454 == 109)
    | (TAZ.TAZ1454 == 110)
]



# spatial join: trn stops intersecting with cordon polygons
network_links_sf["SF_cordon_links"] = network_links_sf.intersects(TAZ_sf.unary_union)
network_links_sf = network_links_sf.loc[
    network_links_sf.SF_cordon_links == True
]


# Prep to summarize VMT on SF links
network_links_sf['VOL_TOT'] = network_links_sf['VOLEA_TOT'] + network_links_sf['VOLAM_TOT'] + network_links_sf['VOLMD_TOT'] + network_links_sf['VOLPM_TOT'] + network_links_sf['VOLEV_TOT']
network_links_sf['VMT']     = network_links_sf['VOL_TOT'] * network_links_sf['DISTANCE']

# Summarize VMT on SF links
network_links_sf_summarize = network_links_sf.groupby(['runid']).agg({'VMT':'sum'}).reset_index()

print(network_links_sf_summarize)


# 1. SF cordon effect on VMT
# 1.2 VMT to-from SF vs. rest
AutoTripsVMT_df = pd.DataFrame()
for runid in run_list:
    AutoTripsVMT_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/core_summaries/AutoTripsVMT_perOrigDestHomeWork.csv'
    AutoTripsVMT      = pd.read_csv(AutoTripsVMT_path)
    # note the runid
    AutoTripsVMT["runid"] = runid
    # add to transit_assignment_df
    AutoTripsVMT_df = pd.concat([AutoTripsVMT_df, AutoTripsVMT])


# Only select trips to and from SF cordon
AutoTripsVMT_from_sf = AutoTripsVMT_df.loc[
    ((AutoTripsVMT_df.orig_taz >= 1) & (AutoTripsVMT_df.orig_taz <= 41))
    | (AutoTripsVMT_df.orig_taz == 106)
    | (AutoTripsVMT_df.orig_taz == 109)
    | (AutoTripsVMT_df.orig_taz == 110)
]

AutoTripsVMT_to_sf = AutoTripsVMT_df.loc[
    ((AutoTripsVMT_df.dest_taz >= 1) & (AutoTripsVMT_df.dest_taz <= 41))
    | (AutoTripsVMT_df.dest_taz == 106)
    | (AutoTripsVMT_df.dest_taz == 109)
    | (AutoTripsVMT_df.dest_taz == 110)
]

AutoTripsVMT_sf = pd.concat([AutoTripsVMT_to_sf, AutoTripsVMT_from_sf])



# Summarize VMT on SF links
AutoTripsVMT_sf_summarize = AutoTripsVMT_sf.groupby(['runid']).agg({'vmt':'sum'}).reset_index()

print(AutoTripsVMT_sf_summarize)


# 2. Mode share
# Conducted in https://app.asana.com/0/0/1204082986821822/f


# 3. SF cordon effect on transit ridership
# summarize transit ridership for routes ending in the SF cordon
# Step 1: use shapefile/network_trn_lines.shp to select routes ending in the SF cordon

# network_trn_lines
network_trn_links = gpd.read_file('L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP10_Path1a_02/OUTPUT/shapefile/network_trn_links.shp')
# The SF Cordon
TAZ    = gpd.read_file('X:/travel-model-one-master/utilities/geographies/bayarea_rtaz1454_rev1_WGS84.shp').to_crs(network_trn_links.crs)
TAZ_sf = TAZ.loc[
    ((TAZ.TAZ1454 >= 1) & (TAZ.TAZ1454 <= 41))
    | (TAZ.TAZ1454 == 106)
    | (TAZ.TAZ1454 == 109)
    | (TAZ.TAZ1454 == 110)
]
# spatial join
network_trn_links_end   = network_trn_links.loc[network_trn_links.groupby('NAME').SEQ.idxmax()].reset_index(drop=True)

network_trn_links_end["SF_cordon_links"] = network_trn_links_end.intersects(TAZ_sf.unary_union)
network_trn_links_end_sf = network_trn_links_end.loc[
    network_trn_links_end.SF_cordon_links == True
]
network_trn_links_end_sf = list(set(network_trn_links_end_sf['NAME']))

network_trn_links_end_sf.remove("*1")
network_trn_links_end_sf.remove("*2")
network_trn_links_end_sf.remove("*5")


# Step 2: 
transit_assignment_df = pd.DataFrame()

for runid in run_list:
    transit_assignment_path = 'L:/Application/Model_One/NextGenFwys/Scenarios/' + runid +'/OUTPUT/trn/trnlinkam_withSupport.dbf'
    transit_assignment      = pd.DataFrame(dbfread.DBF(transit_assignment_path))
    # note the runid
    transit_assignment["runid"] = runid
    # add to transit_assignment_df
    transit_assignment_df = pd.concat([transit_assignment_df, transit_assignment])


transit_assignment_sf = transit_assignment_df.loc[transit_assignment_df['NAME'].isin(network_trn_links_end_sf)]

# sort links by routes and SEQ
transit_assignment_sf = transit_assignment_sf.sort_values(by = ['NAME', 'SEQ'], ascending = [True, True])

# summarize by routes
transit_assignment_sf_summarized = transit_assignment_sf.groupby(['NAME','runid']).agg({'AB_BRDA':'sum','AB_XITA':'sum', 'AB_VOL':'last'}).reset_index()
transit_assignment_sf_summarized['RIDERSHIP'] = transit_assignment_sf_summarized['AB_BRDA'] + transit_assignment_sf_summarized['AB_XITA'] + + transit_assignment_sf_summarized['AB_VOL']
print(transit_assignment_sf_summarized)

# summarize by runs
transit_assignment_sf_summarized = transit_assignment_sf_summarized.groupby(['runid']).agg({'RIDERSHIP':'sum'}).reset_index()
print(transit_assignment_sf_summarized)
