#
# Summarize transportation costs by the following new segmentation of households:
#   income group
#   taz of household
#   household type (driving only, driving + transit, transit only, other)
# Data:
#   number of households
#   number of auto trips
#   number of transit trips
#   total trip op cost
#   total trip parking cost
#   total trip bridge toll cost
#   total trip value toll cost
#   total transit fare cost
# Note: Initial implementation only reports a single cost; detailed costs are more complicated.
#
# See asana task: Calculate daily driving cost breakdown per household for driving households
# https://app.asana.com/0/0/1204292931632605/f
#
# Input:   %TARGET_DIR%\updated_output\trips.rdata
# Output:  %TARGET_DIR%\core_summaries\travel-cost-by-income-driving-households.csv
#
#
# modeling machines have R_LIB setup
.libPaths(Sys.getenv("R_LIB"))

library(dplyr)

#### Mode look-up table
LOOKUP_MODE <- data.frame(
    trip_mode = c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21),
    mode_name = c("Drive alone - free", "Drive alone - pay", 
                  "Shared ride two - free", "Shared ride two - pay",
                  "Shared ride three - free", "Shared ride three - pay",
                  "Walk", "Bike",
                  "Walk to local bus", "Walk to light rail or ferry", "Walk to express bus", 
                  "Walk to heavy rail", "Walk to commuter rail",
                  "Drive to local bus", "Drive to light rail or ferry", "Drive to express bus", 
                  "Drive to heavy rail", "Drive to commuter rail",
                  "Taxi", "TNC", "TNC shared"),
    is_auto =    c(TRUE, TRUE, TRUE, TRUE, TRUE, TRUE,       # DAx2, SR2x2, SR3x2
                   FALSE, FALSE,                             # walk, bike
                   FALSE, FALSE, FALSE, FALSE, FALSE,        # walk to transit
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # drive to transit
                   FALSE, FALSE, FALSE),                     # taxi, tnc; auto=personal vehicle?
    is_transit = c(FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, # DAx2, SR2x2, SR3x2
                   FALSE, FALSE,                             # walk, bike
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # walk to transit
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # drive to transit
                   FALSE, FALSE, FALSE)                      # taxi, tnc; drive=personal vehicle
        
    )
print("LOOKUP_MODE:")
print(LOOKUP_MODE)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
SAMPLESHARE  <- 0.5
OUTPUT_FILE  <- file.path(TARGET_DIR, "core_summaries", "travel-cost-by-income-driving-households.csv")

stopifnot(nchar(TARGET_DIR  )>0)

print(paste0("TARGET_DIR  = ",TARGET_DIR))
print(paste0("SAMPLESHARE = ",SAMPLESHARE))

load(file.path(TARGET_DIR, "updated_output", "trips.rdata"))
print(str(trips))
# select only columns we need
trips <- select(trips, hh_id, person_id, incQ, incQ_label, home_taz, trip_mode, cost)

# join on lookup
trips <- left_join(trips, LOOKUP_MODE)
print(head(trips))

# summarize by household on is_auto, is_transit
hhld_trips_summary <- group_by(trips, hh_id) %>%
    summarise(
        hhld_trips = n(),
        hhld_auto_trips = sum(is_auto),
        hhld_transit_trips = sum(is_transit)
    )

# summarize at household level
hhld_trips_summary <- mutate(hhld_trips_summary,
    hhld_travel = case_when(
        (hhld_auto_trips >  0) & (hhld_transit_trips  > 0) ~ "auto_and_transit",
        (hhld_auto_trips >  0) & (hhld_transit_trips == 0) ~ "auto_no_transit",
        (hhld_auto_trips == 0) & (hhld_transit_trips  > 0) ~ "transit_no_auto",
        (hhld_auto_trips == 0) & (hhld_transit_trips == 0) ~ "no_auto_no_transit"), 
    hhld_travel = factor(hhld_travel, levels=c("auto_and_transit","auto_no_transit", "transit_no_auto","no_auto_no_transit"))
)
print(head(hhld_trips_summary))

# join back to trips and summarize trip costs
trips <- left_join(trips, hhld_trips_summary)
print(head(trips))

trip_summary <- group_by(trips, incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise(
        num_hhlds           = n_distinct(hh_id) / SAMPLESHARE,
        num_persons         = n_distinct(person_id) / SAMPLESHARE,
        num_auto_trips      = sum(is_auto) / SAMPLESHARE,
        num_transit_trips   = sum(is_transit) / SAMPLESHARE,
        total_cost          = sum(cost) / SAMPLESHARE
    )
print(trip_summary)
write.csv(trip_summary, file = OUTPUT_FILE, row.names = FALSE, quote = F)
print(paste("Wrote",nrow(trip_summary),"rows to",OUTPUT_FILE))

