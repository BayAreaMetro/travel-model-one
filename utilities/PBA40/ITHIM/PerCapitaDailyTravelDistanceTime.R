
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
# we only need some columns
trips <- select(trips, hh_id, person_id, trip_mode, orig_purpose, dest_purpose, 
                distance, time, amode, active, timeCode, orig_taz, dest_taz)

# read popsyn persons rather than simulated because we need everyone, even if they don't travel
persons <- tbl_df(read.table(file = file.path(TARGET_DIR,"popsyn","personFile.csv"),
                             header=TRUE, sep=","))
persons <- select(persons, HHID, PERID, AGE, SEX) %>%
                  rename(hh_id=HHID, person_id=PERID, age=AGE) %>%
                  mutate(gender=ifelse(SEX==1,'m','f')) %>% select(-SEX)

# add age groups (0-4, 5-14, 15-29, 30-44, 45-59, 60-69, 70-79, 80+)
persons <- mutate(persons, age_group='?')
persons$age_group[(persons$age <= 4)                    ] <- ' 0- 4'
persons$age_group[(persons$age >= 5)&(persons$age <= 14)] <- ' 5-14'
persons$age_group[(persons$age >=15)&(persons$age <= 29)] <- '15-29'
persons$age_group[(persons$age >=30)&(persons$age <= 44)] <- '30-44'
persons$age_group[(persons$age >=45)&(persons$age <= 59)] <- '45-59'
persons$age_group[(persons$age >=60)&(persons$age <= 69)] <- '60-69'
persons$age_group[(persons$age >=70)&(persons$age <= 79)] <- '70-79'
persons$age_group[(persons$age >=80)                    ] <- '80+'

#################### 1: Total Daily Travel Distance - Walk and Bike #################### 

# We only need active modes (walk and bike and transit with walk) by age and sex
active_trips <- trips[trips$amode != 0,]

# This includes transit trips with walk links
# https://github.com/MetropolitanTransportationCommission/travel-model-one/blob/v05_sgr/model-files/scripts/core_summaries/CoreSummaries.R
# amode: 1=walk, 2=bike, 3=wTrnW, 4=dTrnW, 5=wTrnD
active_trips <- mutate(active_trips, active_mode=ifelse(amode==2,'bike','walk'))
# for walk and bike trips, active_distance = distance
# # for transit trips, this should be based on active time (distance includes transit modes)
active_trips <- mutate(active_trips, active_distance=ifelse(amode < 3, distance, active*(3.0/60.0)))

# add age, age_group and gender
active_trips <- left_join(active_trips, persons)

# we want daily - so sum to person by mode_group
active_trips_by_person_mode <- group_by(select(active_trips, hh_id, person_id, age_group, gender, trip_mode, distance, time, 
                                               active_mode, active, active_distance), 
                                        hh_id, person_id, age_group, gender, active_mode)
daily_active_trips <- tbl_df(dplyr::summarise(active_trips_by_person_mode,
                                       daily_trips=n(), 
                                       daily_distance=sum(active_distance),
                                       daily_time=sum(active)))

# sum -- denominator is not just people who make active trips
percapita_active_summary  <- rbind(
  dplyr::summarise(group_by(daily_active_trips, age_group, gender, active_mode),
                            sum_daily_travelers = n(),
                            sum_daily_distance  = sum(daily_distance),
                            sum_daily_time      = sum(daily_time)),
  
  # non-age-sex-stratified version
  dplyr::summarise(group_by(daily_active_trips, active_mode),
                            sum_daily_travelers = n(),
                            sum_daily_distance  = sum(daily_distance),
                            sum_daily_time      = sum(daily_time)) %>% 
    mutate(age_group="", gender=""))

# these are from trips so they need to be scaled by sample share
percapita_active_summary$sum_daily_travelers <- percapita_active_summary$sum_daily_travelers/SAMPLESHARE
percapita_active_summary$sum_daily_distance  <- percapita_active_summary$sum_daily_distance /SAMPLESHARE
percapita_active_summary$sum_daily_time      <- percapita_active_summary$sum_daily_time     /SAMPLESHARE

walk_summary <- percapita_active_summary[percapita_active_summary$active_mode == 'walk',]
bike_summary <- percapita_active_summary[percapita_active_summary$active_mode == 'bike',]

# this one is from popsyn so it's not sampled
person_age_sex_summary <- rbind(
  dplyr::summarise(group_by(persons, age_group, gender), total_pop=n()),
  dplyr::summarise(persons, total_pop=n()) %>%
    mutate(age_group="", gender=""))

# join
walk_summary <- join(walk_summary, person_age_sex_summary)
bike_summary <- join(bike_summary, person_age_sex_summary)

# convert to final format
walk_summary <- mutate(walk_summary, 'Per Capita Mean Daily Travel Time'    =sum_daily_time/total_pop)
walk_summary <- mutate(walk_summary, 'Per Capita Mean Daily Travel Distance'=sum_daily_distance/total_pop)
walk_summary <- rename(walk_summary, Mode=active_mode)
walk_summary <- select(walk_summary, -sum_daily_travelers, -sum_daily_time, -sum_daily_distance, -total_pop)

bike_summary <- mutate(bike_summary, 'Per Capita Mean Daily Travel Time'    =sum_daily_time/total_pop)
bike_summary <- mutate(bike_summary, 'Per Capita Mean Daily Travel Distance'=sum_daily_distance/total_pop)
bike_summary <- rename(bike_summary, Mode=active_mode)
bike_summary <- select(bike_summary, -sum_daily_travelers, -sum_daily_time, -sum_daily_distance, -total_pop)

summary <- rbind(melt(walk_summary) %>% rename(Parameter=variable),
                 melt(bike_summary) %>% rename(Parameter=variable))

remove(active_trips, active_trips_by_person_mode, daily_active_trips, percapita_active_summary, person_age_sex_summary)

####################  2: Total Daily Travel Distance - Transit #################### 

transit_trips <- trips[(trips$trip_mode >= 9),]
transit_trips <- mutate(transit_trips, trn_mode = ifelse((trip_mode>=9)&(trip_mode<=13), 'wTrnW','?')) %>%
  mutate(trn_mode = ifelse((trip_mode>=14)&(trip_mode<=18)&(orig_purpose=='Home'), 'dTrnW', trn_mode)) %>%
  mutate(trn_mode = ifelse((trip_mode>=14)&(trip_mode<=18)&(dest_purpose=='Home'), 'wTrnD', trn_mode))

# join transit trip with ITHIM skims
add_ithim_skims <- function(this_timeperiod, input_trips) {
  # separate the relevant and irrelevant tours/trips
  relevant   <- input_trips %>% filter(timeCode == this_timeperiod)
  irrelevant <- input_trips %>% filter(timeCode != this_timeperiod)
  
  # read in the relevant skim
  skim_file   <- file.path(TARGET_DIR,"database",paste0("IthimSkimsDatabase",this_timeperiod,".csv"))
  ithim_skims <- read.table(file=skim_file, header=TRUE, sep=",")
  # standardize column names
  ithim_skims <- ithim_skims %>% rename(orig_taz=orig, dest_taz=dest)
  
  # Left join tours to the skims
  relevant <- left_join(relevant, ithim_skims, by=c("orig_taz","dest_taz"))
  # assign values if we can
  relevant <- relevant %>% 
    mutate(ivtB=(trn_mode=='wTrnW')*ivtB_wTrnW +
                (trn_mode=='dTrnW')*ivtB_dTrnW +
                (trn_mode=='wTrnD')*ivtB_wTrnD) %>%
    mutate(ivtR=(trn_mode=='wTrnW')*ivtR_wTrnW +
                (trn_mode=='dTrnW')*ivtR_dTrnW +
                (trn_mode=='wTrnD')*ivtR_wTrnD) %>%
    mutate(distB=(trn_mode=='wTrnW')*distB_wTrnW +
                 (trn_mode=='dTrnW')*distB_dTrnW +
                 (trn_mode=='wTrnD')*distB_wTrnD) %>%
    mutate(distR=(trn_mode=='wTrnW')*distR_wTrnW +
                 (trn_mode=='dTrnW')*distR_dTrnW +
                 (trn_mode=='wTrnD')*distR_wTrnD) %>%
    mutate(ddist=(trn_mode=='dTrnW')*ddist_dTrnW +
                 (trn_mode=='wTrnD')*ddist_wTrnD) %>%
    mutate(dtime=(trn_mode=='dTrnW')*dtime_dTrnW +
                 (trn_mode=='wTrnD')*dtime_wTrnD)
  
  # re-code missing as zero
  relevant <- relevant %>%
    mutate(ivtB = ifelse(ivtB < -990, 0, ivtB)) %>%
    mutate(ivtR = ifelse(ivtR < -990, 0, ivtR)) %>%
    mutate(distB = ifelse(distB < -990, 0, distB)) %>%
    mutate(distR = ifelse(distR < -990, 0, distR)) %>%
    mutate(ddist = ifelse(ddist < -990, 0, distB)) %>%
    mutate(dtime = ifelse(dtime < -990, 0, distR)) %>%
    mutate(ivt_trn  = ivtB+ivtR) %>%
    mutate(dist_trn = distB + distR)

  print(paste("For", 
              this_timeperiod, 
              "assigned", 
              prettyNum(sum(!is.na(relevant$ivt_trn)),big.mark=","),
              "ivts and ",
              prettyNum(sum(!is.na(relevant$dist_trn)),big.mark=","),
              "dists"))
  
  print(paste("  -> Total zero ivts:",
              prettyNum(sum(relevant$ivt_trn==0),big.mark=",")))
  print(paste("  -> Total zero dists:",
              prettyNum(sum(relevant$dist_trn==0),big.mark=",")))
  # clean-up
  relevant <- relevant %>% select(-walk_wTrnW,-ivtB_wTrnW,-ivtR_wTrnW,-wait_wTrnW,-distB_wTrnW,-distR_wTrnW,
                                  -walk_wTrnD,-ivtB_wTrnD,-ivtR_wTrnD,-wait_wTrnD,-distB_wTrnD,-distR_wTrnD,-dtime_wTrnD,-ddist_wTrnD,
                                  -walk_dTrnW,-ivtB_dTrnW,-ivtR_dTrnW,-wait_dTrnW,-distB_dTrnW,-distR_dTrnW,-dtime_dTrnW,-ddist_dTrnW)
  
  return_list <- rbind(relevant, irrelevant)
  return(return_list)
}

transit_trips <- mutate(transit_trips, ivtB=0, ivtR=0, distB=0, distR=0, ddist=0, dtime=0, ivt_trn=0, dist_trn=0)
transit_trips <- add_ithim_skims('EA', transit_trips)
transit_trips <- add_ithim_skims('AM', transit_trips)
transit_trips <- add_ithim_skims('MD', transit_trips)
transit_trips <- add_ithim_skims('PM', transit_trips)
transit_trips <- add_ithim_skims('EV', transit_trips)

# summarise and add total population as denominators
trn_summary_rail <- tbl_df(dplyr::summarise(transit_trips,
                                            sum_daily_distance=sum(distR),
                                            sum_daily_time=sum(ivtR))) %>% 
  mutate(Mode='rail', total_pop=nrow(persons))
trn_summary_bus  <- tbl_df(dplyr::summarise(transit_trips,
                                            sum_daily_distance=sum(distB),
                                            sum_daily_time=sum(ivtB))) %>%
  mutate(Mode='bus', total_pop=nrow(persons))
trn_summary_drive <- tbl_df(dplyr::summarise(transit_trips,
                                             sum_daily_distance=sum(ddist),
                                             sum_daily_time=sum(dtime))) %>% 
  mutate(Mode='drive to transit')

# these are from trips so they need to be scaled by sample share
trn_summary_rail$sum_daily_distance  <- trn_summary_rail$sum_daily_distance  /SAMPLESHARE
trn_summary_rail$sum_daily_time      <- trn_summary_rail$sum_daily_time      /SAMPLESHARE
trn_summary_bus$sum_daily_distance   <- trn_summary_bus$sum_daily_distance   /SAMPLESHARE
trn_summary_bus$sum_daily_time       <- trn_summary_bus$sum_daily_time       /SAMPLESHARE
trn_summary_drive$sum_daily_distance <- trn_summary_drive$sum_daily_distance /SAMPLESHARE
trn_summary_drive$sum_daily_time     <- trn_summary_drive$sum_daily_time     /SAMPLESHARE

# convert to final format
trn_summary_rail <- mutate(trn_summary_rail, 'Per Capita Mean Daily Travel Time'    =sum_daily_time/total_pop)
trn_summary_rail <- mutate(trn_summary_rail, 'Per Capita Mean Daily Travel Distance'=sum_daily_distance/total_pop)
trn_summary_bus  <- mutate(trn_summary_bus,  'Per Capita Mean Daily Travel Time'    =sum_daily_time/total_pop)
trn_summary_bus  <- mutate(trn_summary_bus,  'Per Capita Mean Daily Travel Distance'=sum_daily_distance/total_pop)

trn_summary_rail <- select(trn_summary_rail, -sum_daily_time, -sum_daily_distance, -total_pop) %>%
  mutate(age_group='', gender='')
trn_summary_bus  <- select(trn_summary_bus,  -sum_daily_time, -sum_daily_distance, -total_pop) %>%
  mutate(age_group='', gender='')

summary <- rbind(summary,
                 melt(trn_summary_rail) %>% rename(Parameter=variable),
                 melt(trn_summary_bus)  %>% rename(Parameter=variable))

remove(add_ithim_skims, transit_trips, trn_summary_bus, trn_summary_rail)
# note: we'll use trn_summary_drive later

####################  3: Total Daily Travel Distance - Auto #################### 

# drop walk and bike
auto_trips <- trips[(trips$trip_mode <=6),]

# we don't care about toll vs no-toll
auto_trips <- mutate(auto_trips, mode_group='?')
auto_trips$mode_group[auto_trips$trip_mode== 1] <- 'drive alone'        # da
auto_trips$mode_group[auto_trips$trip_mode== 2] <- 'drive alone'        # da pay
auto_trips$mode_group[auto_trips$trip_mode== 3] <- 'shared ride 2'      # sr2
auto_trips$mode_group[auto_trips$trip_mode== 4] <- 'shared ride 2'      # sr2 pay
auto_trips$mode_group[auto_trips$trip_mode== 5] <- 'shared ride 3+'     # sr3
auto_trips$mode_group[auto_trips$trip_mode== 6] <- 'shared ride 3+'     # sr3 pay

# we want daily - so sum to person by mode_group
auto_trips_by_person_mode <- group_by(select(auto_trips, hh_id, person_id, mode_group, distance, time), 
                                      hh_id, person_id, mode_group)

auto_daily_trips <- tbl_df(dplyr::summarise(auto_trips_by_person_mode,
                                            daily_trips=n(), 
                                            daily_distance=sum(distance),
                                            daily_time=sum(time)))

# total shared ride daily distance and time - we'll have to split it between car passengers and drivers
sr2_dist <- sum(auto_daily_trips$daily_distance[auto_daily_trips$mode_group=='shared ride 2' ])
sr3_dist <- sum(auto_daily_trips$daily_distance[auto_daily_trips$mode_group=='shared ride 3+'])
sr2_time <- sum(auto_daily_trips$daily_time[auto_daily_trips$mode_group=='shared ride 2'])
sr3_time <- sum(auto_daily_trips$daily_time[auto_daily_trips$mode_group=='shared ride 3+'])

# ITHIM mode groups: car-driver, car-passenger
auto_daily_trips <- mutate(auto_daily_trips, ITHIM_mode=mode_group)
auto_daily_trips$ITHIM_mode[auto_daily_trips$mode_group=='drive alone'] <- 'car_driver'

# too young to drive
auto_daily_trips <- left_join(auto_daily_trips, select(persons, hh_id, person_id, age))
auto_daily_trips$ITHIM_mode[(auto_daily_trips$mode_group=='shared ride 2' )&(auto_daily_trips$age<16)] <- 'car_passenger'
auto_daily_trips$ITHIM_mode[(auto_daily_trips$mode_group=='shared ride 3+')&(auto_daily_trips$age<16)] <- 'car_passenger'
# we'll split these later
auto_daily_trips$ITHIM_mode[(auto_daily_trips$mode_group=='shared ride 2' )&(auto_daily_trips$age>=16)] <- 'car_sr2'
auto_daily_trips$ITHIM_mode[(auto_daily_trips$mode_group=='shared ride 3+')&(auto_daily_trips$age>=16)] <- 'car_sr3'

# this is what we have covered for passengers
sr2_dist_pax <- sum(auto_daily_trips$daily_distance[(auto_daily_trips$mode_group=='shared ride 2' )&(auto_daily_trips$ITHIM_mode=='car_passenger')])
sr3_dist_pax <- sum(auto_daily_trips$daily_distance[(auto_daily_trips$mode_group=='shared ride 3+')&(auto_daily_trips$ITHIM_mode=='car_passenger')])
sr2_time_pax <- sum(auto_daily_trips$daily_time[(auto_daily_trips$mode_group=='shared ride 2' )&(auto_daily_trips$ITHIM_mode=='car_passenger')])
sr3_time_pax <- sum(auto_daily_trips$daily_time[(auto_daily_trips$mode_group=='shared ride 3+')&(auto_daily_trips$ITHIM_mode=='car_passenger')])

# without information about driving/passenger distributions by age, just proportion out sr2 miles and minutes to driver/passenger uniformly
# (desired amount - what we have)/desired amount
sr2_dist_pax_fraction <- ((1.0/2.0)*sr2_dist - sr2_dist_pax)/((1.0/2.0)*sr2_dist)
sr3_dist_pax_fraction <- ((2.5/3.5)*sr3_dist - sr2_dist_pax)/((2.5/3.5)*sr3_dist)
sr2_time_pax_fraction <- ((1.0/2.0)*sr2_time - sr2_time_pax)/((1.0/2.0)*sr2_time)
sr3_time_pax_fraction <- ((2.5/3.5)*sr3_time - sr2_time_pax)/((2.5/3.5)*sr2_time)

auto_summary  <- dplyr::summarise(group_by(auto_daily_trips, ITHIM_mode),
                                  sum_daily_travelers = n(),
                                  sum_daily_distance  = sum(daily_distance),
                                  sum_daily_time      = sum(daily_time))
# these are from trips so they need to be scaled by sample share
auto_summary$sum_daily_travelers <- auto_summary$sum_daily_travelers/SAMPLESHARE
auto_summary$sum_daily_distance  <- auto_summary$sum_daily_distance /SAMPLESHARE
auto_summary$sum_daily_time      <- auto_summary$sum_daily_time     /SAMPLESHARE

# allocate car-sr2 and car-sr3 distance and times to car-passenger
auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_passenger'] <- 
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_passenger'] +
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_sr2']*sr2_dist_pax_fraction +
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_sr3']*sr3_dist_pax_fraction

auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_passenger'] <- 
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_passenger'] +
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_sr2']*sr2_time_pax_fraction +
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_sr3']*sr3_time_pax_fraction

# allocate car-sr2 and car-sr3 distance and times to car-driver
auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_driver'] <- 
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_driver'] +
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_sr2']*(1.0-sr2_dist_pax_fraction) +
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_sr3']*(1.0-sr3_dist_pax_fraction)

auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_driver'] <- 
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_driver'] +
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_sr2']*(1.0-sr2_time_pax_fraction) +
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_sr3']*(1.0-sr3_time_pax_fraction)

# they're allocated - so drop sr2, sr3
auto_summary <- auto_summary[auto_summary$ITHIM_mode!='car_sr2',]
auto_summary <- auto_summary[auto_summary$ITHIM_mode!='car_sr3',]
# and clean up some variables
remove(sr2_dist, sr2_dist_pax, sr2_dist_pax_fraction,
       sr2_time, sr2_time_pax, sr2_time_pax_fraction,
       sr3_dist, sr3_dist_pax, sr3_dist_pax_fraction,
       sr3_time, sr3_time_pax, sr3_time_pax_fraction)

# total population of drivers and passengers
auto_summary <- mutate(auto_summary, total_pop=nrow(persons))

# add drive to transit drive time and drive distance
auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_driver'] <- 
  auto_summary$sum_daily_distance[auto_summary$ITHIM_mode=='car_driver'] +
  trn_summary_drive$sum_daily_distance
auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_driver'] <- 
  auto_summary$sum_daily_time[auto_summary$ITHIM_mode=='car_driver'] +
  trn_summary_drive$sum_daily_time

# convert to final format
auto_summary <- mutate(auto_summary, 'Per Capita Mean Daily Travel Time'    =sum_daily_time/total_pop)
auto_summary <- mutate(auto_summary, 'Per Capita Mean Daily Travel Distance'=sum_daily_distance/total_pop)
auto_summary <- rename(auto_summary, Mode=ITHIM_mode)
auto_summary <- select(auto_summary, -sum_daily_travelers, -sum_daily_time, -sum_daily_distance, -total_pop)
auto_summary <- mutate(auto_summary, age_group='', gender='')

summary <- rbind(summary,
                 melt(auto_summary) %>% rename(Parameter=variable))


####################  Population #################### 

persons_summary <- rbind(
  dplyr::summarise(group_by(persons, age_group, gender),
                   'Population Forecasts'=n()) %>% mutate(Mode=''),
  dplyr::summarise(persons, 'Population Forecasts'=n()) %>% mutate(Mode='', age_group='', gender=''))

summary <- rbind(summary,
                 melt(persons_summary) %>% rename(Parameter=variable))

####################  Units ####################

summary$Units <- ""
summary$Units[summary$Parameter=="Per Capita Mean Daily Travel Distance"] <- "miles"
summary$Units[summary$Parameter=="Per Capita Mean Daily Travel Time"    ] <- "minutes"
summary$Units[summary$Parameter=="Population Forecasts"                 ] <- "people"

summary <- summary[c("age_group","gender","Mode","Units","Parameter","value")]
summary <- summary[order(summary$Parameter),]

####################  4: Write it #################### 

write.table(summary, file.path(TARGET_DIR,"metrics","ITHIM","percapita_daily_dist_time.csv"),
            sep=",", row.names=FALSE)

