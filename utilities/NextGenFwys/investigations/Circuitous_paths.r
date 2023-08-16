#--------------------------------------------------------------------------------------------------------
#
# this script is created for the circuitous non-tolled paths investigation
# Are there long intercounty trips that would have been taken on freeways but are now along circuitous non-tolled paths, and is this especially affecting Q1?
# https://app.asana.com/0/0/1205198178220493/f 
# 
#--------------------------------------------------------------------------------------------------------
library(dplyr)

# Specify run_ids
#--------------------------------------------------------------------------------------------------------
run_id_base  <- "2035_TM152_NGF_NP10_Path4_02"
run_id_build <- "2035_TM152_NGF_NP10_Path1a_02"


# load the trip file of the base run
#--------------------------------------------------------------------------------------------------------
trip_file_base    <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios/", run_id_base, "OUTPUT/updated_output/trips.rdata")
load(trip_file_base)

# the data frame comes with a name - trips. Rename.
trips_base_df <- trips
rm(trips)

#-----------------------------------------
# some extra steps because I don't remember how the trip table looks like:
# what are the variables in this data frame? List them.
variable_names <- names(trips_base_df)

# Print the variable names as a list, one variable name per row
for (variable in variable_names) {
      cat(variable, "\n")
}
#-----------------------------------------

# keep only the variables orig_taz, timeperiod_label, incQ_label, distance, time
# this simplified the dataframe so I won't run into problems when joining base with build
trips_base_df <- trips_base_df %>%
  select(orig_taz, dest_taz, timeperiod_label, incQ_label, trip_mode, distance, time)

# keep only the "drive alone, no toll" trips 
# keep only the AM trips
# keep only the lowerest income group 
trips_base_df <- trips_base_df %>%
  filter(trip_mode == 1) %>%
  filter(timeperiod_label == "AM Peak") %>%
  filter(incQ_label == "Less than $30k")

# create a database of OD time and distance for the base run
OD_TimeDist_base_df <- trips_base_df %>%
  group_by(orig_taz, dest_taz) %>%
  summarise(distance = mean(distance),
            time = mean(time),
            trip_count = n()) %>%
  arrange(desc(trip_count))



# load the trip file of the build run
#--------------------------------------------------------------------------------------------------------
trip_file    <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios/", run_id_build, "OUTPUT/updated_output/trips.rdata")
load(trip_file)

# the data frame comes with a name - trips. Rename.
trips_df <- trips
rm(trips)

# keep only the variables orig_taz, timeperiod_label, incQ_label, distance, time
# this simplified the dataframe so I won't run into problems when joining base with build
trips_df <- trips_df %>%
  select(orig_taz, dest_taz, timeperiod_label, incQ_label, trip_mode, distance, time)

# keep only the "drive alone, no toll" trips 
# keep only the AM trips
# keep only the lowerest income group 
trips_df <- trips_df %>%
  filter(trip_mode == 1) %>%
  filter(timeperiod_label == "AM Peak") %>%
  filter(incQ_label == "Less than $30k")

# create a database of OD time and distance for the build run
OD_TimeDist_build_df <- trips_df %>%
  group_by(orig_taz, dest_taz) %>%
  summarise(distance = mean(distance),
            time = mean(time),
            trip_count = n()) %>%
  arrange(desc(trip_count))

# note that the build run has fewer unqiue OD pairs
# the base has 75763 unqiue OD pairs
# the build has 63142 unqiue OD pairs 

# join the two data frames based on ODs
#--------------------------------------------------------------------------------------------------------
# note that the build run has fewer unqiue OD pairs. Use outer join.
joined_df <- full_join(OD_TimeDist_base_df, OD_TimeDist_build_df, 
                        by = c("orig_taz" = "orig_taz", "dest_taz" = "dest_taz"), 
                        suffix = c("_base", "_build"))

# the joint database has 100027 records

# calculate the change in distance between base and build
# identify the ones with large changes
#--------------------------------------------------------------------------------------------------------
joined_df$distance_diff <- joined_df$distance_build - joined_df$distance_base
joined_df$time_diff <- joined_df$time_build - joined_df$time_base

#sort the database
joined_df <- joined_df %>%
  arrange(desc(distance_diff))


# write out the file
#--------------------------------------------------------------------------------------------------------
OUTFILE1 <- file.path("L:\\Application\\Model_One\\NextGenFwys\\Investigations\\Circuitous_paths\\OD_TimeDist.csv")
write.csv(joined_df, OUTFILE1, row.names = FALSE)

# to do: maybe join this file with taz names csv on Petrale.

