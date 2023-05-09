# ---
# title: "Trip Distance by Mode, Tour Purpose, Origin Superdistrict, Destination Superdistrict"
# author: "David Ory"
# output: 
#   html_document:
#     theme: cosmo
#     toc: yes
# ---
# 
## Administration

#### Purpose
# Prepares a bespoke summary of travel model output.  Specifically, calculates the average trip length by travel mode, tour purpose, origin superdistrict, and destination superdistrict. 

#### Outputs
# 1.  A CSV file with the following columns:
#    * trip_mode - Trip mode number
#    * mode_name - Trip mode string
#    * tour_purpose - Tour purpose (see http://analytics.mtc.ca.gov/foswiki/Main/IndividualTrip)
#    * orig_sd - Trip origin superdistrict
#    * dest_sd - Trip destination superdistrict
#    * simulated trips - Number of trips simulated in the model run
#    * estimated trips - Total estimated number of trips in the model run (so simulated expanded by sampling weight)
#    * mean_distance - Mean distance for the trips in this category

## Procedure

#### Overhead
library(tidyverse)
library(sf)
library(foreign)


#### Remote file locations

# this should be set by caller
project <- 'Blueprint'
project <- 'NGF'

RUN_SET     <- Sys.getenv("RUN_SET")
MODEL_DIR   <- Sys.getenv("MODEL_DIR")
MODEL_DIR <- "2035_TM152_NGF_NP10_Path2a_02_10pc"
TRN_LINK <- "network_trn_links.shp"

if (project == 'Blueprint') {
  TARGET_DIR <- file.path("M:/Application/Model One/RTP2021",RUN_SET,MODEL_DIR,"OUTPUT","shapefile",'network_trn_links.shp')
} else if (project == 'NGF') {
  TARGET_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios",MODEL_DIR,"OUTPUT","shapefile",'network_trn_links.shp')
}

if (project == 'Blueprint') {
  OUTPUT_DIR <- file.path("M:/Application/Model One/RTP2021",RUN_SET,MODEL_DIR,"OUTPUT","bespoke")
} else if (project == 'NGF') {
  OUTPUT_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios",MODEL_DIR,"OUTPUT",'shapefile')
}

NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios",MODEL_DIR,"OUTPUT","shapefile",'network_links.dbf')
cat("MODEL_DIR     = ",MODEL_DIR, "\n")
cat("TARGET_DIR    = ",TARGET_DIR, "\n")
cat("OUTPUT_DIR    = ",OUTPUT_DIR, "\n")
cat("NETWORK_DIR   = ",NETWORK_DIR, "\n")


network_trn_links <- read_sf(TARGET_DIR)
network_links <- read.dbf(NETWORK_DIR)


# Select and join
BRT_links <- 
  network_links %>%
  select(A ,B, DISTANCE, BRT) %>%
  filter(BRT  !=  0)


output <- 
  network_trn_links %>%
  left_join(BRT_links, by=c('A'='A', 'B'='B')) %>%
  select(A, B, NAME, SEQ, NAMESEQAB, BRT, DIST_EA, DIST_AM, DIST_MD, DIST_PM, DIST_EV)

#### Write to disk
if (!file.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR)
}
F_OUTPUT = file.path(OUTPUT_DIR, "network_trn_links_for_metrics.shp")
st_write(output, "L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP10_Path2a_02_10pc/OUTPUT/shapefile/network_trn_links_for_metrics.shp")

