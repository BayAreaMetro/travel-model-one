#
# tallyParking.R
#
# Tallies parking metrics for tours and trips using richer (CoreSummaries-produced) tour and trip data
# Run from model directory after CoreSummaries.R
# 
# Creates:
#  parking_costs_tour.csv, with columns
#  1) work_nonwork, either "Non-Work" or "Work"
#  2) incQ * incQ_label, income "quartile".  incQ is one of 1-4, and incQ_label is the human-readable version.
#     Note that these are in $2000
#  3) orig_county, tour origin county
#  4) dest_county, tour destination county
#  5) num_tours, number of tours in the parking_category from the given county to the givne county
#  6) parking_cost, total (summed) tour-based parking costs for these tours, in $2000
#  Note that the sum of parking_cost for work = sum(parking_cost x freq) from CommuteByEmploymentLocation
#
# parking_costs_tour_destTaz.csv, with columns
#  1) simple_purpose, one of "work","school","college","at work",non-work"
#  2) incQ * incQ_label, income "quartile".  incQ is one of 1-4, and incQ_label is the human-readable version.
#     Note that these are in $2000
#  3) dest_taz, tour destination TAZ
#  4) parking_rate, Hourly parking rate for this tour (year 2000 cents). One of PRKCST or OPRKCST, depending on tour purpose.
#     If work tour and person has free parking, then this is zero
#  5) num_tours, number of tours in the parking_category from the given county to the given county
#  6) parking_cost, total (summed) tour-based parking costs for these tours, in $2000
#
# parking_costs_trip_destTaz.csv, with columns
#  1) simple_purpose, one of "work","school","college","at work",non-work"
#  2) incQ * incQ_label, income "quartile".  incQ is one of 1-4, and incQ_label is the human-readable version.
#     Note that these are in $2000
#  3) trip_mode, mode for the trips
#  4) dest_taz, trip destination TAZ
#  5) num_trips, number of trips for the above variables
#  6) parking_cost, total (summed) trip-based parking costs for these trips, in $2000
#
# parking_costs_trip_distBins.csv, with columns
# 1) simple_purpose, one of "work","school","college","at work",non-work"
# 2) incQ * incQ_label, income "quartile".  incQ is one of 1-4, and incQ_label is the human-readable version.
#     Note that these are in $2000
# 3) trip_mode, mode for the trips
# 4) distance_bin, in (X,Y] format
# 5) num_trips, number of trips for the above variables
# 5) parking_cost, total (summed) trip-based parking costs for these trips, in $2000
#

library(dplyr)

# read tours and tazdata
TAZDATA_FILE      <- file.path("landuse","tazData.csv")
tazData           <- read.table(file=TAZDATA_FILE, header=TRUE, sep=",")
names(tazData)    <- toupper(names(tazData))
print(paste("Read",nrow(tazData),"rows from",TAZDATA_FILE))

COST_SHARE_SR2 <- 1.75
COST_SHARE_SR3 <- 2.50

load("updated_output/tours.rdata")

# filter to auto tours
tours <- filter(tours, (tour_mode >= 1)&(tour_mode <= 6))

# add orig_COUNTY
tours <- left_join(tours, rename(select(tazData, ZONE, COUNTY), orig_taz=ZONE, orig_COUNTY=COUNTY), by="orig_taz")

# CoreSummaries.R created parking_cost (in cents in 2000$),
# which includes free parking for fp_choice work tours
# and split cost for individual tours with SR2/SR3 tour_mode

# convert to $2000 dollars
tours <- mutate(tours, parking_cost = parking_cost*0.01)

# parking_cost is already included so just summarize
tours <- mutate(tours, work_nonwork=ifelse(substr(tour_purpose,1,5)=='work_','Work','Non-Work'))

# account for sampleRate
tours <- mutate(tours, 
                num_tours         = 1.0/sampleRate, # expand each tour to multiple tours
                parking_cost      = parking_cost/sampleRate)

# summarize by work/nonwork, income quartile, origin county and destination county
tour_parking_summary <- group_by(tours, work_nonwork, incQ, incQ_label, orig_COUNTY, dest_COUNTY) %>% 
  summarise(num_tours         = sum(num_tours),
            parking_cost      = sum(parking_cost))

tour_parking_file <- file.path("metrics","parking_costs_tour.csv")
write.table(tour_parking_summary, tour_parking_file, sep=",", row.names=FALSE)
print(paste("Wrote",nrow(tour_parking_summary),"to",tour_parking_file))

# summarize by simple_purpose, income quartile, destination taz, parking_rate
tour_parking_summary <- group_by(tours, simple_purpose, incQ, incQ_label, dest_taz, parking_rate) %>% 
  summarise(num_tours         = sum(num_tours),
            parking_cost      = sum(parking_cost))

tour_parking_file <- file.path("metrics","parking_costs_tour_destTaz.csv")
write.table(tour_parking_summary, tour_parking_file, sep=",", row.names=FALSE)
print(paste("Wrote",nrow(tour_parking_summary),"to",tour_parking_file))

# switch to trips
remove(tours)

load("updated_output/trips.rdata")

# find first and last stop in the tour
print("Finding first and last stop for each tour leg")
first_last_stop <- group_by(trips, hh_id, person_id, tour_id, inbound) %>% 
  summarise(first_stop = min(stop_id),
            last_stop  = max(stop_id))

# and merge it back in, set stopIsFirst and stopIsLast
trips <- left_join(trips, first_last_stop, by=c("hh_id","person_id","tour_id","inbound"))
trips <- mutate(trips, stopIsFirst = (stop_id==first_stop),
                stopIsLast  = (stop_id==last_stop))

# add simple_purpose from tour_purpose
trips <- mutate(trips, simple_purpose=case_when(
  tour_purpose=='work_low'       ~ 'work',
  tour_purpose=='work_med'       ~ 'work',
  tour_purpose=='work_high'      ~ 'work',
  tour_purpose=='work_very_high' ~ 'work',
  tour_purpose=='school_grade'   ~ 'school',
  tour_purpose=='school_high'    ~ 'school',
  tour_purpose=='university'     ~ 'college',
  tour_purpose=='atwork_business'~ 'at work',
  tour_purpose=='atwork_eat'     ~ 'at work',
  tour_purpose=='atwork_maint'   ~ 'at work',
  TRUE ~ 'non-work'))

# replication originDuration/destDuration from TripModeChoice UEC
trips <- mutate(trips,
                originDuration = case_when(
                  (inbound==0)&(stopIsFirst) ~ 0.0,           # if origin is at home
                  (inbound==1)&(stopIsFirst) ~ tour_duration, # if origin is tour primary destination
                  (stopIsFirst==FALSE)       ~ 1.0            # if origin is intermediate stop
                ),
                destDuration = case_when(
                  (inbound==1)&(stopIsLast) ~ 0.0,            # if destination is at home
                  (inbound==0)&(stopIsLast) ~ tour_duration,  # if destination is tour primary destination
                  (stopIsLast==FALSE)       ~ 1.0             # if destination is intermediate stop
                ))
# replication of originHourlyParkingCost and destHourlyParkingCost -- looks like these are always PKCST
trips <- left_join(trips, rename(select(tazData, ZONE, PRKCST), orig_taz=ZONE, orig_PRKCST=PRKCST), by="orig_taz")
trips <- left_join(trips, rename(select(tazData, ZONE, PRKCST), dest_taz=ZONE, dest_PRKCST=PRKCST), by="dest_taz")

trips <- mutate(trips, 
                originParkingCost=originDuration*orig_PRKCST,
                destParkingCost  =destDuration  *dest_PRKCST,
                totalParkingCost =(originParkingCost+destParkingCost)/2.0)

# divide out costs for SR2 and SR3 (note: for tours, CoreSummaries.R does this but for the trips version, it's here)
# no special treatment for joint trips
trips <- mutate(trips,
                totalParkingCost = case_when(
                  (trip_mode==3)|(trip_mode==4) ~ totalParkingCost/COST_SHARE_SR2,
                  (trip_mode==5)|(trip_mode==6) ~ totalParkingCost/COST_SHARE_SR3,
                  TRUE ~ totalParkingCost
                ))

# convert to $2000 dollars
trips <- mutate(trips, totalParkingCost = totalParkingCost*0.01)

# zero out for non auto trips
trips <- mutate(trips, totalParkingCost=ifelse(trip_mode>6,0,totalParkingCost))
# zero out for work tours if person has fp_choice
trips <- mutate(trips, totalParkingCost=ifelse((substr(tour_purpose,0,4)=='work')&(fp_choice==1),0.0,totalParkingCost))

# account for sampleRate
trips <- mutate(trips, 
                num_trips        = 1.0/sampleRate, # expand each tour to multiple tours
                totalParkingCost = totalParkingCost/sampleRate)

#trips_debug <- filter(trips, hh_id < 10) %>% 
#  select(hh_id, person_id, tour_id, tour_purpose, num_participants, inbound, stop_id, orig_purpose, dest_purpose, first_stop, stopIsFirst, last_stop, stopIsLast)
#trips_debug <- trips_debug[with(trips_debug, order(hh_id, person_id, tour_id, inbound, stop_id)), ]

# summarize by simple_purpose, income quartile, trip mode, destination taz
trip_parking_summary <- group_by(trips, simple_purpose, incQ, incQ_label, trip_mode, dest_taz) %>% 
  summarise(num_trips         = sum(num_trips),
            parking_cost      = sum(totalParkingCost))

trip_parking_file <- file.path("metrics","parking_costs_trip_destTaz.csv")
write.table(trip_parking_summary, trip_parking_file, sep=",", row.names=FALSE)
print(paste("Wrote",nrow(trip_parking_summary),"to",trip_parking_file))

# define distance bins
bins <- seq(0,9.5,0.5)
bins <- append(bins, seq(10,49,1))
bins <- append(bins, seq(50,150,5))

trips['distance_bin'] <- cut(trips$distance, bins)

# summarize by simple_purpose, income quartile, trip mode, distance bin
trip_parking_summary <- group_by(trips, simple_purpose, incQ, incQ_label, trip_mode, distance_bin) %>% 
  summarise(num_trips         = sum(num_trips),
            parking_cost      = sum(totalParkingCost))

trip_parking_file <- file.path("metrics","parking_costs_trip_distBins.csv")
write.table(trip_parking_summary, trip_parking_file, sep=",", row.names=FALSE)
print(paste("Wrote",nrow(trip_parking_summary),"to",trip_parking_file))
