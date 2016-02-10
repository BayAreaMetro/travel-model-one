
# Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))
library(plyr) # this must be first
library(dplyr)
library(reshape2)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

SAMPLESHARE <- as.numeric(SAMPLESHARE)

cat("TARGET_DIR  = ",TARGET_DIR,"\n")
cat("ITER        = ",ITER,"\n")
cat("SAMPLESHARE = ",SAMPLESHARE,"\n")

updated_trips = file.path(TARGET_DIR,"updated_output","trips.rdata")
if (!file.exists(updated_trips)) {
  stop(paste("Can't find file",updated_trips))
}
load(updated_trips)

updated_persons = file.path(TARGET_DIR, "updated_output", "persons.rdata")
if (!file.exists(updated_persons)) {
  stop(paste("Can't find file",updated_persons))
}
load(updated_persons)

# 1: Per Capita Mean Daily Travel Distance

# add mode groups: drive alone, shared ride 2, shared ride 3+, bus, rail, walk, bicycle
trips <- mutate(trips, mode_group='?')
trips$mode_group[trips$trip_mode== 1] <- 'drive alone'        # da
trips$mode_group[trips$trip_mode== 2] <- 'drive alone'        # da pay
trips$mode_group[trips$trip_mode== 3] <- 'shared ride 2'      # sr2
trips$mode_group[trips$trip_mode== 4] <- 'shared ride 2'      # sr2 pay
trips$mode_group[trips$trip_mode== 5] <- 'shared ride 3+'     # sr3
trips$mode_group[trips$trip_mode== 6] <- 'shared ride 3+'     # sr3 pay
trips$mode_group[trips$trip_mode== 7] <- 'walk'               # walk
trips$mode_group[trips$trip_mode== 8] <- 'bicycle'            # bike
trips$mode_group[trips$trip_mode== 9] <- 'bus'                # walk to local bus
trips$mode_group[trips$trip_mode==10] <- 'rail'               # walk to light rail or ferry
trips$mode_group[trips$trip_mode==11] <- 'bus'                # walk to express bus
trips$mode_group[trips$trip_mode==12] <- 'rail'               # walk to BART
trips$mode_group[trips$trip_mode==13] <- 'rail'               # walk to commuter rail
trips$mode_group[trips$trip_mode==14] <- 'bus'                # drive to local bus
trips$mode_group[trips$trip_mode==15] <- 'rail'               # drive to light rail or ferry
trips$mode_group[trips$trip_mode==16] <- 'bus'                # drive to express bus
trips$mode_group[trips$trip_mode==17] <- 'rail'               # drive to BART
trips$mode_group[trips$trip_mode==18] <- 'rail'               # drive to commuter rail

# add age and gender
trips <- left_join(trips, select(persons, hh_id, person_id, age, gender))

# we want daily - so sum to person by mode_group
trips_by_person_mode <- group_by(select(trips, hh_id, person_id, age, gender, mode_group, distance, time), 
                                 hh_id, person_id, age, gender, mode_group)
daily_trips <- tbl_df(dplyr::summarise(trips_by_person_mode,
                                       daily_trips=n(), 
                                       daily_distance=sum(distance),
                                       daily_time=sum(time)))

# total shared ride daily distance and time - we'll have to split it between car passengers and drivers
sr2_dist <- sum(daily_trips$daily_distance[daily_trips$mode_group=='shared ride 2' ])
sr3_dist <- sum(daily_trips$daily_distance[daily_trips$mode_group=='shared ride 3+'])
sr2_time <- sum(daily_trips$daily_time[daily_trips$mode_group=='shared ride 2'])
sr3_time <- sum(daily_trips$daily_time[daily_trips$mode_group=='shared ride 3+'])

# ITHIM mode groups: car-driver, car-passenger, motorcycle, truck, bus, rail, walk, bicycle
daily_trips <- mutate(daily_trips, ITHIM_mode=mode_group)
daily_trips$ITHIM_mode[daily_trips$mode_group=='drive alone'] <- 'car_driver'

# too young to drive
daily_trips$ITHIM_mode[(daily_trips$mode_group=='shared ride 2' )&(daily_trips$age<16)] <- 'car_passenger'
daily_trips$ITHIM_mode[(daily_trips$mode_group=='shared ride 3+')&(daily_trips$age<16)] <- 'car_passenger'
# we'll split these later
daily_trips$ITHIM_mode[(daily_trips$mode_group=='shared ride 2' )&(daily_trips$age>=16)] <- 'car_sr2'
daily_trips$ITHIM_mode[(daily_trips$mode_group=='shared ride 3+')&(daily_trips$age>=16)] <- 'car_sr3'

# this is what we have covered for passengers
sr2_dist_pax <- sum(daily_trips$daily_distance[(daily_trips$mode_group=='shared ride 2' )&(daily_trips$ITHIM_mode=='car_passenger')])
sr3_dist_pax <- sum(daily_trips$daily_distance[(daily_trips$mode_group=='shared ride 3+')&(daily_trips$ITHIM_mode=='car_passenger')])
sr2_time_pax <- sum(daily_trips$daily_time[(daily_trips$mode_group=='shared ride 2' )&(daily_trips$ITHIM_mode=='car_passenger')])
sr3_time_pax <- sum(daily_trips$daily_time[(daily_trips$mode_group=='shared ride 3+')&(daily_trips$ITHIM_mode=='car_passenger')])

# without information about driving/passenger distributions by age, just proportion out sr2 miles and minutes to driver/passenger uniformly
# (desired amount - what we have)/desired amount
sr2_dist_pax_fraction <- ((1.0/2.0)*sr2_dist - sr2_dist_pax)/((1.0/2.0)*sr2_dist)
sr3_dist_pax_fraction <- ((2.5/3.5)*sr3_dist - sr2_dist_pax)/((2.5/3.5)*sr3_dist)
sr2_time_pax_fraction <- ((1.0/2.0)*sr2_time - sr2_time_pax)/((1.0/2.0)*sr2_time)
sr3_time_pax_fraction <- ((2.5/3.5)*sr3_time - sr2_time_pax)/((2.5/3.5)*sr2_time)

# add age groups (0-4, 5-14, 15-29, 30-44, 45-59, 60-69, 70-79, 80+)
daily_trips <- mutate(daily_trips, age_group='?')
daily_trips$age_group[(daily_trips$age <= 4)                        ] <- ' 0- 4'
daily_trips$age_group[(daily_trips$age >= 5)&(daily_trips$age <= 14)] <- ' 5-14'
daily_trips$age_group[(daily_trips$age >=15)&(daily_trips$age <= 29)] <- '15-29'
daily_trips$age_group[(daily_trips$age >=30)&(daily_trips$age <= 44)] <- '30-44'
daily_trips$age_group[(daily_trips$age >=45)&(daily_trips$age <= 59)] <- '45-59'
daily_trips$age_group[(daily_trips$age >=60)&(daily_trips$age <= 69)] <- '69-69'
daily_trips$age_group[(daily_trips$age >=70)&(daily_trips$age <= 79)] <- '70-90'
daily_trips$age_group[(daily_trips$age >=80)                        ] <- '80+'

by_age_gender_mode <- group_by(daily_trips, age_group, gender, ITHIM_mode)

percapita_summary  <- dplyr::summarise(by_age_gender_mode,
                                mean_daily_trips    = mean(daily_trips),
                                mean_daily_distance = mean(daily_distance),
                                mean_daily_time     = mean(daily_time),
                                sum_daily_travelers = n(),
                                sum_daily_distance  = sum(daily_distance),
                                sum_daily_time      = sum(daily_time))

# we need to fix the auto modes - pull them out
auto_summary <- percapita_summary[(percapita_summary$ITHIM_mode=='car_driver'   )|
                                  (percapita_summary$ITHIM_mode=='car_passenger')|
                                  (percapita_summary$ITHIM_mode=='car_sr2'      )|
                                  (percapita_summary$ITHIM_mode=='car_sr3'      ),]
auto_pers <- select(auto_summary, age_group, gender, ITHIM_mode, sum_daily_travelers)
auto_dist <- select(auto_summary, age_group, gender, ITHIM_mode, sum_daily_distance)
auto_time <- select(auto_summary, age_group, gender, ITHIM_mode, sum_daily_time)

# make ITHIM_mode into columns
auto_dist2      <- dcast(auto_dist, age_group + gender ~ ITHIM_mode, fun.aggregate = sum, fill=0)
auto_time2      <- dcast(auto_time, age_group + gender ~ ITHIM_mode, fun.aggregate = sum, fill=0)
auto_dist_pers2 <- dcast(auto_pers, age_group + gender ~ ITHIM_mode, fun.aggregate = sum, fill=0)
auto_time_pers2 <- dcast(auto_pers, age_group + gender ~ ITHIM_mode, fun.aggregate = sum, fill=0)

# allocate car-sr2 and car-sr3 distance and times to car-passenger
auto_dist2$car_passenger       <- auto_dist2$car_passenger +
                                  auto_dist2$car_sr2*sr2_dist_pax_fraction +
                                  auto_dist2$car_sr3*sr3_dist_pax_fraction

auto_time2$car_passenger       <- auto_time2$car_passenger +
                                  auto_time2$car_sr2*sr2_time_pax_fraction +
                                  auto_time2$car_sr3*sr3_time_pax_fraction

auto_dist_pers2$car_passenger <- auto_dist_pers2$car_passenger +
                                 auto_dist_pers2$car_sr2*sr2_dist_pax_fraction +
                                 auto_dist_pers2$car_sr3*sr3_dist_pax_fraction

auto_time_pers2$car_passenger <- auto_time_pers2$car_passenger +
                                 auto_time_pers2$car_sr2*sr2_time_pax_fraction +
                                 auto_time_pers2$car_sr3*sr3_time_pax_fraction

# allocate car-sr2 and car-sr3 distance and times to car-driver
auto_dist2$car_driver          <- auto_dist2$car_driver +
                                  auto_dist2$car_sr2*(1.0-sr2_dist_pax_fraction) +
                                  auto_dist2$car_sr3*(1.0-sr3_dist_pax_fraction)

auto_time2$car_driver          <- auto_time2$car_driver +
                                  auto_time2$car_sr2*(1.0-sr2_time_pax_fraction) +
                                  auto_time2$car_sr3*(1.0-sr3_time_pax_fraction)

auto_dist_pers2$car_driver    <- auto_dist_pers2$car_driver +
                                 auto_dist_pers2$car_sr2*(1.0-sr2_dist_pax_fraction) +
                                 auto_dist_pers2$car_sr3*(1.0-sr3_dist_pax_fraction)

auto_time_pers2$car_driver    <- auto_time_pers2$car_driver +
                                 auto_time_pers2$car_sr2*(1.0-sr2_time_pax_fraction) +
                                 auto_time_pers2$car_sr3*(1.0-sr3_time_pax_fraction)
# they're allocated - so drop sr2, sr3
auto_dist2      <- select(auto_dist2,      age_group, gender, car_driver, car_passenger)
auto_time2      <- select(auto_time2,      age_group, gender, car_driver, car_passenger)
auto_dist_pers2 <- select(auto_dist_pers2, age_group, gender, car_driver, car_passenger)
auto_time_pers2 <- select(auto_time_pers2, age_group, gender, car_driver, car_passenger)

# back to original format
auto_dist        <- rename(melt(auto_dist2),      ITHIM_mode=variable, sum_daily_distance=value)
auto_dist_pers   <- rename(melt(auto_dist_pers2), ITHIM_mode=variable, sum_daily_travelers=value)
auto_dist        <- left_join(auto_dist, auto_dist_pers)
auto_dist        <- mutate(auto_dist, mean_daily_distance=ifelse(sum_daily_travelers==0,0,sum_daily_distance/sum_daily_travelers))

auto_time        <- rename(melt(auto_time2),      ITHIM_mode=variable, sum_daily_time=value)
auto_time_pers   <- rename(melt(auto_time_pers2), ITHIM_mode=variable, sum_daily_travelers=value)
auto_time        <- left_join(auto_time, auto_time_pers)
auto_time        <- mutate(auto_time, mean_daily_time=ifelse(sum_daily_travelers==0,0,sum_daily_time/sum_daily_travelers))

auto_dist_time   <- select(left_join(auto_dist, auto_time, c("age_group","gender","ITHIM_mode")), 
                           age_group, gender, ITHIM_mode, mean_daily_distance, mean_daily_time)

# put it back together
percapita_summary_update <- select(percapita_summary, age_group, gender, ITHIM_mode, mean_daily_distance, mean_daily_time)
percapita_summary_update <- percapita_summary_update[(percapita_summary_update$ITHIM_mode!='car_driver'   )&
                                                     (percapita_summary_update$ITHIM_mode!='car_passenger')&
                                                     (percapita_summary_update$ITHIM_mode!='car_sr2'      )&
                                                     (percapita_summary_update$ITHIM_mode!='car_sr3'      ),]
percapita_summary_update <- rbind(percapita_summary_update, auto_dist_time)

write.table(percapita_summary_update, file.path(TARGET_DIR,"metrics","ITHIM","percapita_daily_dist_time.csv"),
            sep=",", row.names=FALSE)
