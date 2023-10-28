#--------------------------------------------------------------------------------------------------------
#
# this script is created for the circuitous non-tolled paths investigation
# Are there long intercounty trips that would have been taken on freeways but are now along circuitous non-tolled paths, and is this especially affecting Q1?
# https://app.asana.com/0/0/1205198178220493/f 
#
#--------------------------------------------------------------------------------------------------------


# overall approach
#--------------------------------------------------------------------------------------------------------
# use all the trips in build (income Q1, da, am)
# and merge in the skims from base (da, am)


library(dplyr)

# Specify run_ids
#--------------------------------------------------------------------------------------------------------
run_id_build <- "2035_TM152_NGF_NP10_Path1a_02"


# load the trip file of the build run
#--------------------------------------------------------------------------------------------------------
trip_file    <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios/", run_id_build, "OUTPUT/updated_output/trips.rdata")
load(trip_file)

# the data frame comes with a name - trips. Rename.
trips_df <- trips
rm(trips)

# keep selected variables to reduce file size
# this simplified the dataframe so I won't run into problems when joining base with build
trips_df <- trips_df %>%
  select(hh_id, person_id, person_num, tour_purpose, tour_id, orig_taz, dest_taz, timeperiod_label, incQ_label, trip_mode, distance, time)

# keep only the "drive alone, no toll" trips 
# keep only the AM trips
# keep only the lowerest income group 
trips_df <- trips_df %>%
  filter(trip_mode == 1) %>%
  filter(timeperiod_label == "AM Peak") %>%
  filter(incQ_label == "Less than $30k")
# 147494 records

# read in the distance and time skims from the base run
#--------------------------------------------------------------------------------------------------------
skim_file <- file.path("//MODEL2-C/Model2C-Share/Projects/2035_TM152_NGF_NP10_Path4_02/skims/skim_csv/HWYSKMAM.csv")

# Read the CSV file
skim_df <- read.csv(skim_file)

# keep only the variables: orig, dest, TIMEDA and DISTDA
skim_df <- skim_df %>%
  select(orig, dest, TIMEDA, DISTDA)


# join the distance and time skims from the base run to the trip table of the build run
#--------------------------------------------------------------------------------------------------------
joined_df <- left_join(trips_df, skim_df, 
                        by = c("orig_taz" = "orig", "dest_taz" = "dest"), 
                        suffix = c("_build", "_base"))

joined_df <- joined_df %>%
  rename(distance_build = distance,
         time_build = time,
         time_base = TIMEDA,
         distance_base = DISTDA)


# calculate the change in distance between base and build
# identify the ones with large changes
#--------------------------------------------------------------------------------------------------------
joined_df$distance_diff <- joined_df$distance_build - joined_df$distance_base
joined_df$time_diff <- joined_df$time_build - joined_df$time_base


# Categorize data into distance bins and count trips
binned_dist_df <- joined_df %>%
  mutate(bin = cut(
    distance_diff,
    breaks = c(-Inf, seq(0, 0, 1), seq(0.000001, max(distance_diff), 2), Inf),
    include.lowest = TRUE,
    right = FALSE
  )) %>%
  group_by(bin) %>%
  summarise(trip_count = n())
print(binned_dist_df)


# Categorize data into time bins and count trips
binned_time_df <- joined_df %>%
  mutate(bin = cut(
    time_diff,
    breaks = c(-Inf, seq(0, 0, 1), seq(0.000001, 5, 1), seq(5, max(time_diff), 5), Inf),
    include.lowest = TRUE,
    right = FALSE
  )) %>%
  group_by(bin) %>%
  summarise(trip_count = n())
print(binned_time_df)

# output joined_df as a csv file for creating histogram in Tableau
#--------------------------------------------------------------------------------------------------------
OUTFILE1 <- file.path("L:\\Application\\Model_One\\NextGenFwys\\Investigations\\Circuitous_paths\\trips_DaIncQ1AM.csv")
write.csv(joined_df, OUTFILE1, row.names = FALSE)

# output a file that is indexed by ODs for examining extreme cases
#--------------------------------------------------------------------------------------------------------
OD_TimeDist_df <- joined_df %>%
  group_by(orig_taz, dest_taz) %>%
  summarise(distance_diff = mean(distance_diff),
            time_diff = mean(time_diff),
            distance_build = mean(distance_build),
            time_build = mean(time_build),
            distance_base = mean(distance_base),
            time_base = mean(time_base),
            trip_count_build = n()) %>%
  arrange(desc(distance_diff))

OUTFILE2 <- file.path("L:\\Application\\Model_One\\NextGenFwys\\Investigations\\Circuitous_paths\\OD_TimeDistDiff.csv")
write.csv(OD_TimeDist_df, OUTFILE2, row.names = FALSE)

# The Tableau workbook that uses these output files are saved in: 
# L:\Application\Model_One\NextGenFwys\Investigations\Circuitous_paths
