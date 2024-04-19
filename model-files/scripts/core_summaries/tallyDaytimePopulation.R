#
# See Script day time population as part of growth patterns metrics
# https://app.asana.com/0/1182463234225195/1207094912644751/f
#
# This script will summarize people who spend time in a TAZ (not in their home) over X hours
#

library(dplyr)
options(width = 180)

# 3 hours
TAZ_DURATION_THRESHOLD <- 3

summarize_duration_activity <- function(person_trips, person_id_tibble) {
  # used with group_modify.
  # person_id_tibble = tibble with hh_id, person_id, person_num
  # person_trips is the list of trips
  
  # sort by depart_hour
  person_trips <- person_trips %>% arrange(depart_hour)
  person_trips <- person_trips %>% mutate(
    next_depart_hour = lead(depart_hour),
    taz_duration     = next_depart_hour - depart_hour
  )
  # DEBUG output
  if (FALSE) {
    print(person_id_tibble)
    print("DEBUG person_trips:")
    print(select(person_trips,
                 tour_id, stop_id,
                 orig_taz, orig_purpose,
                 dest_taz, dest_purpose,
                 depart_hour, next_depart_hour, taz_duration))
  }
  # only keep those with taz_duration > THRESHOLD
  person_trips <- person_trips %>% 
    filter(!is.na(taz_duration)) %>%
    filter(taz_duration > TAZ_DURATION_THRESHOLD) %>%
    # and drop dest_purpose = Home, that's not really activity
    filter(dest_purpose != "Home")

  # print(person_trips)
  return(person_trips)
}

############# main #############################################################
main <- function() {
  
  UPDATED_OUTPUT <- "updated_output"
  RESULTS_DIR    <- "core_summaries"
  if (file.exists("OUTPUT")) {
    UPDATED_OUTPUT <- file.path("OUTPUT", "updated_output")
    RESULTS_DIR    <- file.path("OUTPUT", "core_summaries")
  }   

  # start by reading trips
  load(file.path(UPDATED_OUTPUT, "trips.rdata"))
  print(paste("Read ",prettyNum(nrow(trips),big.mark=","),"from trips.rdata"))

  # keep only columns of interest
  trips <- trips %>% select(
    hh_id, person_id, person_num,
    ptype_label, incQ_label, # add wfh_choice if available
    home_taz, trip_mode, sampleRate,
    orig_taz, orig_purpose, dest_taz, dest_purpose,
    depart_hour
  )
  print(head(trips))
  
  # test mode - don't commit
  trips <- trips %>% filter(hh_id < 10000)

  # group_by person and summarize duration activity
  activity_duration_df <- trips %>% 
    group_by(hh_id, person_id, person_num) %>%
    group_modify(summarize_duration_activity) %>%
    mutate(num_trips = 1.0/sampleRate)

  # summarize this
  activity_duration_summary_df <- activity_duration_df %>% group_by(
    ptype_label, incQ_label, home_taz, dest_taz, dest_purpose, taz_duration
  ) %>% summarise(num_trips = sum(num_trips))
  
  # save it
  write.table(activity_duration_summary_df, 
              file.path(RESULTS_DIR,"ActivityDurationSummary.csv"),
              sep=",", row.names=FALSE)
  print(paste("Wrote",nrow(activity_duration_summary_df),"to",file.path(RESULTS_DIR,"ActivityDurationSummary.csv")))
}

main()