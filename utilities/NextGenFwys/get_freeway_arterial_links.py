"""
Reads a roadway network shapefile file (exported from model output)
Filters to tolled freeway links (toll > 990000 in 2035_TM152_NGF_NP02_BPALTsegmented_03_SimpleTolls01 network) and 
  arterial links of interest (based on their presence in NetworkProjects named NGF_*_Art_*)
Saves resulting file to L:\\Application\\Model_One\\NextGenFwys\\across_runs_union\\freeway_arterial_links.csv
  with columns 'A', 'B', 'DISTANCE', 'Project', 'TollClass', 'link_tag' (one of 'freeway' or 'arterial')
Also saves get_freeway_arterial_links_[YYYY_MM_DD].log
"""

import pandas as pd
# import numpy
# import geopandas as gpd
from simpledbf import Dbf5
import os, sys, logging, time

today = time.strftime("%Y_%m_%d")

############ I/O
## INPUT
# Network that contains all-lane tolling
RUN_OUTPUT_DIR = "L:\\Application\\Model_One\\NextGenFwys\\Scenarios\\2035_TM152_NGF_NP02_BPALTsegmented_03_SimpleTolls01\\OUTPUT"
NETWORK_DIR = os.path.join(RUN_OUTPUT_DIR, "shapefile")

ROADWAY_FILE = os.path.join(NETWORK_DIR, "network_links.dbf")

TRN_LINKS_RAW_FILE = os.path.join(RUN_OUTPUT_DIR, "trn", "trnlink.csv")

# NextGenFwy arterial projects
# NOTE: these are coded as indivdiual NetworkProject named "NGF_XXX_Art_XXX";
# Within each NetworkProject, file "mod_links_tollclass_direction.csv" file contains the tolled links.
ART_PROJ_DIR = "M:\\Application\\Model One\\NetworkProjects"

## OUTPUT
# freeway and tolled arterial links
DATA_OUTPUT_DIR             = "L:\\Application\\Model_One\\NextGenFwys\\across_runs_union"
FREEWAY_ARTERIAL_LINKS_FILE = os.path.join(DATA_OUTPUT_DIR, "freeway_arterial_links.csv")
LOG_FILE                    = os.path.join(DATA_OUTPUT_DIR, "get_freeway_arterial_links_{}.log".format(today))


############ setup logging
# create logger
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

# console handler
ch = logging.StreamHandler()
ch.setLevel("INFO")
ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"))
logger.addHandler(ch)

# file handler
fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setLevel("DEBUG")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"))
logger.addHandler(fh)


############ Get Freeway and Arterial Links

## get all-lane tolling nodes
# load roadway network
logger.info("loading roadway network {}".format(ROADWAY_FILE))
dbf = Dbf5(ROADWAY_FILE)
network_links_df = dbf.to_dataframe()
# keep only needed fields
network_links_df = network_links_df[["A", "B", "TOLLCLASS", "PROJ", "DISTANCE"]]

# tag all-lane-tolling links
network_links_df.loc[network_links_df.TOLLCLASS > 990000, "freeway"] = True
logger.info(
    "{:,} freeway links, containing the following {} toll classes: {}".format(
        network_links_df.loc[network_links_df["freeway"] == True].shape[0],
        network_links_df.loc[network_links_df["freeway"] == True].TOLLCLASS.nunique(),
        sorted(network_links_df.loc[network_links_df["freeway"] == True].TOLLCLASS.unique())))

logger.info(network_links_df.head())

## get links on tolled arterials
# create a dataframe to store the node pairs
artierial_links_df = pd.DataFrame()

# loop through arterial projects to get the links, and append to the df above
logger.info("getting links of tolled arterials")
# tally number of projects
n = 0
for proj in os.listdir(ART_PROJ_DIR):
    if ("NGF" in proj) and ("_Art_" in proj):
        logger.info(proj)
        try:
            mod_links_df = pd.read_csv(os.path.join(ART_PROJ_DIR, proj, "mod_links_tollclass_direction.csv"))
            artierial_links_df = pd.concat([artierial_links_df, mod_links_df])
            n = n+1
        except:
            logger.info("mod_links_tollclass_direction.csv does not exist!")

logger.info(
    "finished processing all tolled arterials, {} NetworkProjects, {:,} links, containing the following {} toll classes: {}".format(
        n,
        artierial_links_df.shape[0],
        artierial_links_df['_Tollclass'].nunique(),
        sorted(artierial_links_df['_Tollclass'].unique())))

# add a NGF tag
artierial_links_df['arterial'] = True

## merge arterial link tag to roadway link df
logger.info("merging freeway and tolled-arterial links")
network_links_df = network_links_df.merge(artierial_links_df, on=['A', 'B'], how='left')

# consolidate fields
network_links_df.loc[network_links_df['freeway'] == True, 'link_tag']  = 'freeway'
network_links_df.loc[network_links_df['freeway'] == True, 'Project']   = network_links_df['PROJ']
network_links_df.loc[network_links_df['freeway'] == True, 'TollClass'] = network_links_df['TOLLCLASS']

network_links_df.loc[network_links_df['arterial'] == True, 'link_tag']  = 'arterial'
network_links_df.loc[network_links_df['arterial'] == True, 'Project']   = network_links_df['_Project']
network_links_df.loc[network_links_df['arterial'] == True, 'TollClass'] = network_links_df['_Tollclass']

# keep only freeway and arterial links with needed fields
freeway_arterial_links_df = network_links_df.loc[
    network_links_df['link_tag'].isin(['freeway', 'arterial'])
    ][[
        'A', 'B', 'DISTANCE', 'Project', 'TollClass', 'link_tag'
]]

logger.info(
    'finished merging, {:,} links total: \n{}'.format(
        freeway_arterial_links_df.shape[0], freeway_arterial_links_df.head()
    ))

# export
freeway_arterial_links_df.to_csv(FREEWAY_ARTERIAL_LINKS_FILE, index=False)
logger.info("exported to {}".format(FREEWAY_ARTERIAL_LINKS_FILE))
