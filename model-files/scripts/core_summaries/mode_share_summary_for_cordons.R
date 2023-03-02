# this script is to summarize the mode share between cordons (Treasury Island, SF, OK, and SJ)
# Input needed: model run output trip.radta, tazdata.csv with cordon information

library(tidyverse)
library(foreign)
library(readxl)

#### load files ####

# create path
#change it for each model run
WORK_DIR        <- "L:/Application/Model_One/NextGenFwys/NetworkProject_Development/NGF_Path3a"
#change it for each model run
MODEL           <- "2035_TM152_NGF_NP07_Path3a_01_Toll_189SJ_189OAK"
#change it for each model run
MODEL_DIR_01    <- "L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP07_Path3a_01_Toll_189SJ_189OAK" 
TRIP_RDATA_PATH <- paste(MODEL_DIR_01, "OUTPUT", "updated_output" , "trips.rdata", sep = "/")
CORDON_PATH     <- "L:/Application/Model_One/NextGenFwys/INPUT_DEVELOPMENT/PopSyn_n_LandUse/2035_cordon/landuse/tazdata.csv"
OUTPUT_NAME     <- paste("trips_cordon_mode_summary_",MODEL, ".csv", sep ="")
OUTPUT_PATH     <- paste(WORK_DIR, OUTPUT_NAME, sep = "/")

# read files
TRIP_RDATA      <- load(TRIP_RDATA_PATH)
CORDON          <- read.csv(CORDON_PATH)


#### process cordon data ####

# four cordons are considered: SF, Treasury Island, OK, and SJ
# 9  - Treasury Island;
# 10 - SF;
# 11 - OK;
# 12 - SJ

# County Name
CORDON$COUNTY_NAME <- NA
CORDON$COUNTY_NAME[CORDON$COUNTY ==  1] <- "San Francisco County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  2] <- "San Mateo County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  3] <- "Santa Clara County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  4] <- "Alameda County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  5] <- "Contra Costa County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  6] <- "Solano County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  7] <- "Napa County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  8] <- "Sonoma County"
CORDON$COUNTY_NAME[CORDON$COUNTY ==  9] <- "Marin County"

# Cordon Name
CORDON$CORDON_NAME <- NA
CORDON$CORDON_NAME[CORDON$CORDON ==  0] <- "0-No Cordons"
CORDON$CORDON_NAME[CORDON$CORDON ==  9] <- "9-Treasury Island Cordon"
CORDON$CORDON_NAME[CORDON$CORDON == 10] <- "10-San Francisco Cordon"
CORDON$CORDON_NAME[CORDON$CORDON == 11] <- "11-Oakland Cordon"
CORDON$CORDON_NAME[CORDON$CORDON == 12] <- "12-San Jose Cordon"

CORDON <-
  CORDON %>%
  mutate(CORDON_NAME = ifelse(CORDON == 0, paste(CORDON_NAME, COUNTY_NAME, sep = ", "), CORDON_NAME))


#### Process trip data ####
# four column needed - 
 # Orig_cordon
 # Dest_cordon
 # trip_mode
 # number of trips
trips_cordon <-
  trips %>%
  select(hh_id, person_id, person_num, tour_id, orig_taz, dest_taz, trip_mode, tour_purpose, tour_category, cost, costMode, cost_fail) %>%
  left_join(CORDON %>% select(ZONE, CORDON_NAME, COUNTY_NAME, CORDON),
            by = c("orig_taz" = "ZONE")) %>%
  rename(CORDON_NAME_orig = CORDON_NAME,
         COUNTY_NAME_orig = COUNTY_NAME,
         CORDON_orig      = CORDON) %>%
  left_join(CORDON %>% select(ZONE, CORDON_NAME, COUNTY_NAME, CORDON),
            by = c("dest_taz" = "ZONE")) %>%
  rename(CORDON_NAME_dest = CORDON_NAME,
         COUNTY_NAME_dest = COUNTY_NAME,
         CORDON_dest      = CORDON)

trips_cordon_mode_summary <- 
  trips_cordon %>%
  group_by(CORDON_NAME_orig,
           CORDON_NAME_dest,
           trip_mode) %>%
  summarise(num_of_trips = n()) %>%
  mutate(model_run = MODEL)

trips_cordon_mode_summary$trip_mode_description <- NA
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 1]  <- "Drive alone free"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 2]  <- "Drive alone toll"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 3]  <- "Shared ride 2 free"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 4]  <- "Shared ride 2 toll"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 5]  <- "Shared ride 3+ free"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 6]  <- "Shared ride 3+ toll"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 7]  <- "Walk"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 8]  <- "Bicycle"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 9]  <- "Walk to local bus"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 10] <- "Walk to light rail or ferry"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 11] <- "Walk to express bus"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 12] <- "Walk to heavy rail"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 13] <- "Walk to commuter rail"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 14] <- "Drive to local bus"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 15] <- "Drive to light rail or ferry"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 16] <- "Drive to express bus"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 17] <- "Drive to heavy rail"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 18] <- "Drive to commuter rail"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 19] <- "Taxi"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 20] <- "TNC, single party"
trips_cordon_mode_summary$trip_mode_description[trips_cordon_mode_summary$trip_mode == 21] <- "TNC, shared"
#### write the output ####
write.csv(trips_cordon_mode_summary, OUTPUT_PATH, row.names = FALSE)
