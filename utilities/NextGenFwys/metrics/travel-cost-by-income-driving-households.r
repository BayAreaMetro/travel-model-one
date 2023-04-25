#
# Summarize transportation costs by the following new segmentation of households:
#   incQ, incQ_lable: income group
#   home_taz: taz of household
#   hhld_travel: household type, one of [auto_and_transit, auto_no_transit, transit_no_auto, no_auto_no_transit]
#      for segmentation purposes,
#         auto trips include personal auto trips (but *not* taxi, TNC) and drive-to-transit trips
#         transit trips include walk-to-transit trips and drive-to-transit trips
#         so a household with a single drive-to-transit trip is in auto_and_transit
# Data columns:
#   num_hhlds:          number of households
#   num_persons:        number of persons in those households
#   num_auto_trips:     number of auto trips taken by those households
#   num_transit_trips:  number of transit trips taken by those households
#     (Note the same classifications of auto and transit apply as were used in the segmentation
#      so there IS double counting -- a drive-to-transit trip is counted twice)
#   total_hhld_autos:   total number of household autos for these households
#   total_hhd_income:   total household income for these households (in 2000 dollars)
#   total_auto_cost:    total daily auto cost for these trips (in 2000 cents)
#   total_transit_cost: total daily transit cost for these trips (in 2000 cents)
# 
# Note: Initial implementation only reports a single cost; detailed costs are more complicated.
# TODO: break up auto_cost into the following -- this will involve reading detailed skims
#   total trip op cost
#   total trip parking cost
#   total trip bridge toll cost
#   total trip value toll cost
#
#
# See asana task: Calculate daily driving cost breakdown per household for driving households
# https://app.asana.com/0/0/1204292931632605/f
#
# Input:   %TARGET_DIR%\updated_output\trips.rdata
# Output:  %TARGET_DIR%\core_summaries\travel-cost-by-income-driving-households.csv
#
#

COMPUTERNAME <- Sys.getenv("COMPUTERNAME")
if (startsWith(COMPUTERNAME, "MODEL2D") | startsWith(COMPUTERNAME, "MODEL2D")) {
    # modeling machines have R_LIB setup
    .libPaths(Sys.getenv("R_LIB"))
}

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
# print(str(trips))
# select only columns we need
trips <- select(trips, hh_id, person_id, incQ, incQ_label, home_taz, income, autos, trip_mode, cost)

# join on lookup
trips <- left_join(trips, LOOKUP_MODE)
# print(head(trips))

# separate cost into auto cost versus transit fare
# Note: from SkimsDatabase.JOB, drive to transit costs are fare driven
trips <- mutate(trips,
    transit_cost = ifelse(is_transit, cost, 0),
    auto_cost    = ifelse(is_transit==FALSE, cost, 0)  # Note: Taxi/TNC included here
)

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
print("hhld_trips_summary head: ")
print(head(hhld_trips_summary))

# join back to trips and summarize trip costs
trips <- left_join(trips, hhld_trips_summary)
# print(head(trips))

# need autos / income summary by household by income, home_taz, hhld_travel(segment)
hhld_autos_income_summary <- group_by(trips, hh_id, incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise( 
        hhld_autos  = max(autos),  # max, min, avg -- should all be the same
        hhld_income = max(income)  # max, min, avg -- should all be the same
    )
# zero out negative household income
hhld_autos_income_summary <- mutate(hhld_autos_income_summary,
    hhld_income = ifelse(hhld_income < 0, 0, hhld_income)
)
print("hhld_autos_income_summary:")
print(head(hhld_autos_income_summary))
# summarize again to aggregate for households
hhld_autos_income_summary <- group_by(hhld_autos_income_summary, 
    incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise( 
        total_hhld_autos  = sum(hhld_autos),
        total_hhld_income = sum(hhld_income)
    )
print("hhld_autos_income_summary:")
print(head(hhld_autos_income_summary))

# everything is a total so divide by sampleshare
trip_summary <- group_by(trips, incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise(
        num_hhlds           = n_distinct(hh_id)     / SAMPLESHARE,
        num_persons         = n_distinct(person_id) / SAMPLESHARE,
        num_auto_trips      = sum(is_auto)          / SAMPLESHARE,
        num_transit_trips   = sum(is_transit)       / SAMPLESHARE,
        total_auto_cost     = sum(auto_cost)        / SAMPLESHARE,
        total_transit_cost  = sum(transit_cost)     / SAMPLESHARE,
        total_cost          = sum(cost)             / SAMPLESHARE
    )

print("trip_summary: ")
print(trip_summary)

# join with hhld_autos_summary
trip_summary <- left_join(trip_summary, hhld_autos_income_summary) %>%
    mutate(total_hhld_autos = total_hhld_autos / SAMPLESHARE,
           total_hhld_income = total_hhld_income/SAMPLESHARE)

write.csv(trip_summary, file = OUTPUT_FILE, row.names = FALSE, quote = F)
print(paste("Wrote",nrow(trip_summary),"rows to",OUTPUT_FILE))

