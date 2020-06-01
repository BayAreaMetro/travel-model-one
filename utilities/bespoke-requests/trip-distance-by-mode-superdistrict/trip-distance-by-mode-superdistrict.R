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
library(dplyr)

#### Mode look-up table
LOOKUP_MODE <- data.frame(trip_mode = c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21),
                          mode_name = c("Drive alone - free", "Drive alone - pay", 
                                        "Shared ride two - free", "Shared ride two - pay",
                                        "Shared ride three - free", "Shared ride three - pay",
                                        "Walk", "Bike",
                                        "Walk  to local bus", "Walk to light rail or ferry", "Walk to express bus", 
                                        "Walk to heavy rail", "Walk to commuter rail",
                                        "Drive  to local bus", "Drive to light rail or ferry", "Drive to express bus", 
                                        "Drive to heavy rail", "Drive to commuter rail",
                                        "Taxi", "TNC", "TNC shared"))

SAMPLING_RATE = 0.500

#### Remote file locations

# this should be set by caller
RUN_SET     <- Sys.getenv("RUN_SET")
MODEL_DIR   <- Sys.getenv("MODEL_DIR")
TARGET_DIR  <- file.path("M:/Application/Model One/RTP2021",RUN_SET,MODEL_DIR,"OUTPUT")
OUTPUT_DIR  <- file.path("M:/Application/Model One/RTP2021",RUN_SET,MODEL_DIR,"OUTPUT","bespoke")

cat("MODEL_DIR     = ",MODEL_DIR, "\n")
cat("TARGET_DIR    = ",TARGET_DIR, "\n")
cat("OUTPUT_DIR    = ",OUTPUT_DIR, "\n")
cat("SAMPLING_RATE = ",SAMPLING_RATE,"\n")

load(file.path(TARGET_DIR, "updated_output", "trips.rdata"))
zonal_df <- read.table(file = file.path(TARGET_DIR, "..", "INPUT", "landuse", "tazData.csv"), header=TRUE, sep=",")

# Select and join
working <- trips %>%
  select(hh_id, tour_purpose, distance, trip_mode, orig_taz, dest_taz)

origin <- zonal_df %>%
  select(orig_taz = ZONE, orig_sd = SD)

destination <- zonal_df %>%
  select(dest_taz = ZONE, dest_sd = SD)

output <- left_join(working, origin, by = c("orig_taz"))
output <- left_join(output, destination, by = c("dest_taz"))

# Reduce
summarized <- output %>%
  group_by(trip_mode, tour_purpose, orig_sd, dest_sd) %>%
  summarize(simulated_trips = n(), mean_distance = mean(distance))

summarized <- left_join(summarized, LOOKUP_MODE, by = c("trip_mode"))

summarized <- summarized %>%
  mutate(estimated_trips = simulated_trips / SAMPLING_RATE) %>%
  select(trip_mode, mode_name, tour_purpose, orig_sd, dest_sd, simulated_trips, estimated_trips, mean_distance)

#### Write to disk
if (!file.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR)
}
F_OUTPUT = file.path(OUTPUT_DIR, "trip-distance-by-mode-superdistrict.csv")
write.csv(summarized, file = F_OUTPUT, row.names = FALSE, quote = F)

