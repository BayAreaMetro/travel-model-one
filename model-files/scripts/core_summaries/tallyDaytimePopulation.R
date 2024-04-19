#
# See Script day time population as part of growth patterns metrics
# https://app.asana.com/0/1182463234225195/1207094912644751/f
#
# This script will summarize people who spend time in a TAZ (not in their home) over X hours
# Input: 
#   [OUTPUT]/updated_output/trips.rdata
# Output:
#   [OUTPUT]/core_summaries/ActivityDurationSummary.csv with columns:
#   --- index columns ---
#     dest_taz: trip destination TAZ
#     desT_purpose_simple: one of work, university/school, other
#     taz_duration: int, representing hours
#   --- value columns --- or the trips going to the given dest_taz for the given purpose and the given taz_duration:
#     avg_distance: the average distance of that trip
#     num_persons: the number of persons who made trips
#     num_trips: the number of persons who made trips
#
library(dplyr)
library(data.table)
options(width = 180)

# 3 hours
TAZ_DURATION_THRESHOLD <- 3

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
    depart_hour, distance
  )

  # Convert df to data.table for fast sort
  trips_dt <- as.data.table(trips)
  setorder(trips_dt, person_id, depart_hour)
  print("Sorted trips_dt:")
  print(head(trips_dt))
  # convert back to data.frame
  trips <- as.data.frame(trips_dt)
  print("Converted to data frame")
  rm(trips_dt)

  trips <- trips %>% mutate(
    next_person_id   = lead(person_id),
    next_depart_hour = lead(depart_hour),
    taz_duration     = next_depart_hour - depart_hour,
    trip_mode_simple = case_when(
      trip_mode <= 6 ~ 'auto',
      trip_mode == 7 ~ 'walk',
      trip_mode == 8 ~ 'bike',
      ((trip_mode >= 9) & (trip_mode <= 18)) ~ 'transit',
      trip_mode >= 19 ~ 'auto'),
    dest_purpose_simple = case_when(
      dest_purpose == "Home"           ~ "Home",
      dest_purpose == "work_low"       ~ "work",
      dest_purpose == "work_med"       ~ "work",
      dest_purpose == "work_high"      ~ "work",
      dest_purpose == "work_very high" ~ "work",
      dest_purpose == "work"           ~ "work",
      dest_purpose == "Work"           ~ "work",
      dest_purpose == "university"     ~ "university/school",
      dest_purpose == "school_high"    ~ "university/school",
      dest_purpose == "school_grade"   ~ "university/school",
      TRUE                             ~ "other"),
  )
  # print(table(trips$dest_purpose, trips$dest_purpose_simple))

  print("Before filtering:")
  print(head(select(trips, -ptype_label, -incQ_label), 20))

  trips <- trips %>% 
    filter(next_person_id == person_id) %>%
    filter(taz_duration >= TAZ_DURATION_THRESHOLD) %>%
    # and drop dest_purpose = Home, that's not really activity
    filter(dest_purpose != "Home")
  print("After filtering:")
  print(head(select(trips, -ptype_label, -incQ_label), 20))

  print(paste("Number of trips:", prettyNum(nrow(trips),big.mark=",")))
  print(paste("Number of persons:", prettyNum(n_distinct(trips$person_id),big.mark=",")))

  # summarize this
  # also available: incQ_label, home_taz, ptype_label
  activity_duration_summary_df <- trips %>% group_by(
    dest_taz, dest_purpose_simple, taz_duration
  ) %>% summarise(
      avg_distance = mean(distance),
      sampleRate   = first(sampleRate), 
      num_persons  = n_distinct(person_id),
      num_trips    = n()
    ) %>% mutate(
      num_persons  = num_persons/sampleRate,
      num_trips    = num_trips/sampleRate
    ) %>% select(-sampleRate)
  print(paste("Done with group_by and summarise; nrows:",
    prettyNum(nrow(activity_duration_summary_df),big.mark=",")))

  # save it
  write.table(activity_duration_summary_df, 
              file.path(RESULTS_DIR,"ActivityDurationSummary.csv"),
              sep=",", row.names=FALSE)
  print(paste("Wrote",file.path(RESULTS_DIR,"ActivityDurationSummary.csv")))
}

main()