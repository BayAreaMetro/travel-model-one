# Core Summaries

# Overhead
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

library(scales)
library(dplyr)
library(reshape2)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
JUST_MES     <- Sys.getenv("JUST_MES")    # Run for just-mes only?

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

if (JUST_MES=="1") {
  MAIN_DIR    <- file.path(TARGET_DIR,"main",          "just_mes")
  RESULTS_DIR <- file.path(TARGET_DIR,"core_summaries","just_mes")
  UPDATED_DIR <- file.path(TARGET_DIR,"updated_output","just_mes")
} else {
  MAIN_DIR    <- file.path(TARGET_DIR,"main"           )
  RESULTS_DIR <- file.path(TARGET_DIR,"core_summaries")
  UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")
}

# read means-based cost factors
MBT_factors <- readLines(file.path(TARGET_DIR,"ctramp/scripts/block/hwyParam.block"))
MBF_factors <- readLines(file.path(TARGET_DIR,"ctramp/scripts/block/trnParam.block"))

MBT_Q1_line <- grep("Means_Based_Tolling_Q1Factor",MBT_factors,value=TRUE)
MBT_Q1_string <- substr(MBT_Q1_line,32,39)
MBT_Q1_factor <- as.numeric(MBT_Q1_string)
MBT_Q2_line <- grep("Means_Based_Tolling_Q2Factor",MBT_factors,value=TRUE)
MBT_Q2_string <- substr(MBT_Q2_line,32,39)
MBT_Q2_factor <- as.numeric(MBT_Q2_string)

MBF_Q1_line <- grep("Means_Based_Fare_Q1Factor",MBF_factors,value=TRUE)
MBF_Q1_string <- substr(MBF_Q1_line,29,36)
MBF_Q1_factor <- as.numeric(MBF_Q1_string)
MBF_Q2_line <- grep("Means_Based_Fare_Q2Factor",MBF_factors,value=TRUE)
MBF_Q2_string <- substr(MBF_Q2_line,29,36)
MBF_Q2_factor <- as.numeric(MBF_Q2_string)


# write results in TARGET_DIR/core_summaries
if (!file.exists(RESULTS_DIR)) {
  dir.create(RESULTS_DIR)
}
# write tables in TARGET_DIR/updated_output
if (!file.exists(UPDATED_DIR)) {
  dir.create(UPDATED_DIR)
}
SAMPLESHARE <- as.numeric(SAMPLESHARE)

cat("TARGET_DIR  = ",TARGET_DIR, "\n")
cat("ITER        = ",ITER,       "\n")
cat("SAMPLESHARE = ",SAMPLESHARE,"\n")
cat("JUST_MES    = ",JUST_MES,   "\n")

# Overhead
## Lookups

# For time periods, see https://github.com/BayAreaMetro/modeling-website/wiki/TimePeriods
# For counties, see https://github.com/BayAreaMetro/modeling-website/wiki/TazData
# For walk_subzones, see https://github.com/BayAreaMetro/modeling-website/wiki/Household

######### time periods
LOOKUP_TIMEPERIOD    <- data.frame(timeCodeNum=c(1,2,3,4,5),
                                   timeperiod_label=c("Early AM","AM Peak","Midday","PM Peak","Evening"),
                                   timeperiod_abbrev=c("EA","AM","MD","PM","EV"))
# no factors -- joins don't work
LOOKUP_TIMEPERIOD$timeCodeNum       <- as.integer(LOOKUP_TIMEPERIOD$timeCodeNum)
LOOKUP_TIMEPERIOD$timeperiod_label  <- as.character(LOOKUP_TIMEPERIOD$timeperiod_label)
LOOKUP_TIMEPERIOD$timeperiod_abbrev <- as.character(LOOKUP_TIMEPERIOD$timeperiod_abbrev)

######### counties
LOOKUP_COUNTY        <- data.frame(COUNTY=c(1,2,3,4,5,6,7,8,9),
                                   county_name=c("San Francisco","San Mateo","Santa Clara","Alameda",
                                                 "Contra Costa","Solano","Napa","Sonoma","Marin"))
LOOKUP_COUNTY$COUNTY      <- as.integer(LOOKUP_COUNTY$COUNTY)
LOOKUP_COUNTY$county_name <- as.character(LOOKUP_COUNTY$county_name)

######### walk subzones
LOOKUP_WALK_SUBZONE  <- data.frame(walk_subzone=c(0,1,2),
                                   walk_subzone_label=c("Cannot walk to transit (more than two-thirds of a mile away)",
                                                        "Short-walk to transit (less than one-third of a mile)",
                                                        "Long-walk to transit (between one-third and two-thirds of a mile)"))
LOOKUP_WALK_SUBZONE$walk_subzone <- as.integer(LOOKUP_WALK_SUBZONE$walk_subzone)

######### person types
LOOKUP_PTYPE         <- data.frame(ptype=c(1,2,3,4,5,6,7,8),
                                   ptype_label=c("Full-time worker","Part-time worker","College student","Non-working adult",
                                                 "Retired","Driving-age student","Non-driving-age student",
                                                 "Child too young for school"))
LOOKUP_PTYPE$ptype   <- as.integer(LOOKUP_PTYPE$ptype)

# Data Reads: Land Use

# The land use file: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
tazData           <- read.table(file=file.path(TARGET_DIR,"landuse","tazData.csv"), header=TRUE, sep=",")
names(tazData)    <- toupper(names(tazData))
tazData           <- select(tazData, ZONE, SD, COUNTY, PRKCST, OPRKCST)
tazData           <- left_join(tazData, LOOKUP_COUNTY, by=c("COUNTY"))
names(tazData)[names(tazData)=="ZONE"] <- "taz"


# Data Reads: Household files

## Read the household files and land use file

# There are two household files:

# * the model input file from the synthesized household/population (https://github.com/BayAreaMetro/modeling-website/wiki/PopSynHousehold)
# * the model output file (https://github.com/BayAreaMetro/modeling-website/wiki/Household)

input.pop.households <- read.table(file = file.path(TARGET_DIR,"popsyn","hhFile.csv"),
                                   header=TRUE, sep=",")
input.ct.households  <- read.table(file = file.path(MAIN_DIR,paste0("householdData_",ITER,".csv")),
                                   header=TRUE, sep = ",")

## Join them

# Rename/drop some columns and join them on household id. Also join with tazData to get the super district and county.

# drop random number fields
input.ct.households  <- select(input.ct.households, -ao_rn, -fp_rn, -cdap_rn,
  -imtf_rn, -imtod_rn, -immc_rn, -jtf_rn, -jtl_rn, -jtod_rn, -jmc_rn, -inmtf_rn,
  -inmtl_rn, -inmtod_rn, -inmmc_rn, -awf_rn, -awl_rn, -awtod_rn, -awmc_rn, -stf_rn, -stl_rn)

# in case households aren't numeric - make the columns numeric
for(i in names(input.pop.households)){
  input.pop.households[[i]] <- as.numeric(input.pop.households[[i]])
}

# rename
names(input.pop.households)[names(input.pop.households)=="HHID"] <- "hh_id"

households <- inner_join(input.pop.households, input.ct.households, "hh_id")
households <- inner_join(households, tazData, "taz")
# wrap as a d data frame tbl so it's nicer for printing
households <- tbl_df(households)
# clean up
remove(input.pop.households, input.ct.households)


## Recode a few new variables

# Create the following new household variables:
#  * income quartiles (`incQ`)
#  * worker categories (`workers`)
#  * dummy for households with children that don't drive (`kidsNoDr`)
#  * auto sufficiency (`autoSuff`)
#  * walk subzone label (`walk_subzone_label`)

# incQ are Income Quartiles
LOOKUP_INCQ          <- data.frame(incQ=c(1,2,3,4),
                                   incQ_label=c("Less than $30k","$30k to $60k","$60k to $100k","More than $100k"))
LOOKUP_INCQ$incQ     <- as.integer(LOOKUP_INCQ$incQ)

households    <- mutate(households, incQ=1*(income<30000) +
                                         2*((income>=30000)&(income<60000)) +
                                         3*((income>=60000)&(income<100000)) +
                                         4*(income>=100000))
households    <- left_join(households, LOOKUP_INCQ, by=c("incQ"))

# workers are hworkers capped at 4
households    <- mutate(households, workers=4*(hworkers>=4) + hworkers*(hworkers<4))
WORKER_LABELS <- c("Zero", "One", "Two", "Three", "Four or more")

# auto sufficiency
LOOKUP_AUTOSUFF          <- data.frame(autoSuff=c(0,1,2),
                                autoSuff_label=c("Zero automobiles","Automobiles < workers","Automobiles >= workers"))
LOOKUP_AUTOSUFF$autoSuff <- as.integer(LOOKUP_AUTOSUFF$autoSuff)

households    <- mutate(households, autoSuff=1*((autos>0)&(autos<hworkers)) +
                                             2*((autos>0)&(autos>=hworkers)))
households    <- left_join(households, LOOKUP_AUTOSUFF, by=c("autoSuff"))

# walk subzone label
households    <- left_join(households, LOOKUP_WALK_SUBZONE, by=c("walk_subzone"))

# Data Reads: Person files

# There are two person files:
# * the model input file from the synthesized household/population (https://github.com/BayAreaMetro/modeling-website/wiki/PopSynPerson)
# * the model output file (https://github.com/BayAreaMetro/modeling-website/wiki/Person)

## Read the person files
input.pop.persons    <- read.table(file = file.path(TARGET_DIR,"popsyn","personFile.csv"),
                                   header=TRUE, sep=",")
input.ct.persons     <- read.table(file = file.path(MAIN_DIR,paste0("personData_",ITER,".csv")),
                                   header=TRUE, sep = ",")

## Join them

# Rename
names(input.pop.persons)[names(input.pop.persons)=="HHID"] <- "hh_id"
names(input.pop.persons)[names(input.pop.persons)=="PERID"] <- "person_id"

# in case households aren't numeric - make the columns numeric
for(i in names(input.pop.persons)){
  input.pop.persons[[i]] <- as.numeric(input.pop.persons[[i]])
}

# Inner join so persons must be present in both.  So only simulated persons stay.
persons              <- inner_join(input.pop.persons, input.ct.persons, by=c("hh_id", "person_id"))
# Get incQ from Households
persons              <- left_join(persons, select(households, hh_id, incQ, incQ_label), by=c("hh_id"))

# Person type label
persons              <- left_join(persons, LOOKUP_PTYPE, by=c("ptype"))

# wrap as a d data frame tbl so it's nicer for printing
persons              <- tbl_df(persons)
# clean up
remove(input.pop.persons, input.ct.persons)

# kidsNoDr is 1 if the household has children in the household that don't drive (pre-school age or school age)
# calculate for persons and transfer to households as a binary
persons              <- mutate(persons, kidsNoDr=ifelse((ptype==7)|(ptype==8),1,0))
kidsNoDr_hhlds       <- summarise(group_by(select(persons, hh_id, kidsNoDr), hh_id), kidsNoDr=max(kidsNoDr))
households           <- left_join(households, kidsNoDr_hhlds)
remove(kidsNoDr_hhlds)

# Tours

## Read Individual Tours

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTour

indiv_tours     <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("indivTourData_",ITER,".csv")),
                                     header=TRUE, sep=","))
indiv_tours     <- mutate(indiv_tours, tour_id=paste0("i",substr(tour_category,1,2),tour_id))

# Add income from household table
indiv_tours     <- left_join(indiv_tours, select(households, hh_id, income, incQ, incQ_label), by=c("hh_id"))
indiv_tours     <- mutate(indiv_tours, num_participants=1)

# Add in County, Superdistrict, Parking Cost from TAZ Data for the tour destination
indiv_tours     <- left_join(indiv_tours,
                             mutate(tazData, dest_taz=taz, dest_COUNTY=COUNTY, dest_county_name=county_name,
                                    dest_SD=SD, PRKCST, OPRKCST) %>%
                               select(dest_taz, dest_COUNTY, dest_county_name, dest_SD, PRKCST, OPRKCST),
                             by=c("dest_taz"))

# Add free-parking choice from persons table
indiv_tours   <- left_join(indiv_tours, select(persons, person_id, fp_choice), by=c("person_id"))

# Compute the tour parking rate
indiv_tours   <- mutate(indiv_tours, parking_rate=ifelse(tour_category=='MANDATORY',PRKCST,OPRKCST))

# Free parking for work tours if fp_choice==1
indiv_tours   <- mutate(indiv_tours, parking_rate=ifelse((substr(tour_purpose,0,4)=='work')*(fp_choice==1),0.0,parking_rate))

## Data Reads: Joint Tours

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTour

joint_tours    <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("jointTourData_",ITER,".csv")),
                                    header=TRUE, sep=","))
joint_tours     <- mutate(joint_tours, tour_id=paste0("j",substr(tour_category,1,2),tour_id))

# Add Income from household table
joint_tours    <- left_join(joint_tours, select(households, hh_id, income, incQ, incQ_label), by=c("hh_id"))

# Add in County, Superdistrict, Parking Cost from TAZ Data for the tour destination
joint_tours     <- left_join(joint_tours,
                             mutate(tazData, dest_taz=taz, dest_COUNTY=COUNTY, dest_county_name=county_name,
                                    dest_SD=SD, PRKCST, OPRKCST) %>%
                               select(dest_taz, dest_COUNTY, dest_county_name, dest_SD, PRKCST, OPRKCST),
                             by=c("dest_taz"))

# Add parking rate
joint_tours    <- mutate(joint_tours, parking_rate=OPRKCST)

## Function to add Cost to Tours or Trips

# Function `add_cost`: attaches the cost skims for the given time period abbreviation `this_timeperiod`
# to the given tours data.frame (note: this can be the trips data frame). Joining is done on the columns
# `orig_taz`, `dest_taz`, and `timeCode`.

# The function fills in values to the column `cost` and `cost_fail` for the given time
# period based on the column `costMode`.

# Pass `reverse_od` as TRUE to do return trip; this uses the dest taz as the origin and the origin
# taz as the dest, and it uses wTrnD cost rather than dTrnW.

# Tallies failed costs (expected cost but -999 found) in the field cost_fail

add_cost <- function(this_timeperiod, input_trips_or_tours, reverse_od = FALSE) {

  # separate the relevant and irrelevant tours/trips
  relevant <- input_trips_or_tours %>%
    filter(timeCode == this_timeperiod)

  irrelevant <- input_trips_or_tours %>%
    filter(timeCode != this_timeperiod)

  # read in the relevant skim
  skim_file <- file.path(TARGET_DIR,"database",paste0("CostSkimsDatabase",this_timeperiod,".csv"))
  costSkims <- read.table(file = skim_file, header=TRUE, sep=",")

  # standardize column names, reversing if needed
  if (reverse_od) {
    costSkims <- costSkims %>%
      rename(orig_taz = dest, dest_taz = orig)
  } else {
      costSkims <- costSkims %>%
        rename(orig_taz = orig, dest_taz = dest)
  }

  # Left join tours to the skims
  relevant <- left_join(relevant, costSkims, by=c("orig_taz","dest_taz"))

  # assign cost value if we can to new column cost2
  relevant <- relevant %>%
    mutate(cost2 = (costMode == 1) * da +
             (costMode == 2 & incQ == 1) * daToll * MBT_Q1_factor + (costMode == 2 & incQ == 2) * daToll * MBT_Q2_factor + (costMode == 2 & incQ >= 3) * daToll +
             (costMode == 3) * s2 +
             (costMode == 4 & incQ == 1) * s2Toll * MBT_Q1_factor + (costMode == 4 & incQ == 2) * s2Toll * MBT_Q2_factor + (costMode == 4 & incQ >= 3) * s2Toll +
             (costMode == 5) * s3 +
             (costMode == 6 & incQ == 1) * s3Toll* MBT_Q1_factor + (costMode == 6 & incQ == 2) * s3Toll* MBT_Q2_factor + (costMode == 6 & incQ >= 3) * s3Toll +
             (costMode == 7) * 0.0 +
             (costMode == 8) * 0.0 +
             (costMode == 9 & incQ == 1) * wTrnW * MBF_Q1_factor + (costMode == 9 & incQ == 2) * wTrnW * MBF_Q2_factor + (costMode == 9 & incQ >= 3) * wTrnW +
             (costMode == 10 & incQ == 1) * (1 - reverse_od) * dTrnW * MBF_Q1_factor + (costMode == 10 & incQ == 2) * (1 - reverse_od) * dTrnW * MBF_Q2_factor + (costMode == 10 & incQ >= 3) * (1 - reverse_od) * dTrnW +
             (costMode == 10 & incQ == 1) * (reverse_od) * wTrnD * MBF_Q1_factor + (costMode == 10 & incQ == 2) * (reverse_od) * wTrnD * MBF_Q2_factor + (costMode == 10 & incQ >= 3) * (reverse_od) * wTrnD +
             (costMode == 11 & incQ == 1) * wTrnD * MBF_Q1_factor + (costMode == 11 & incQ == 2) * wTrnD * MBF_Q2_factor + (costMode == 11 & incQ >= 3) * wTrnD)


  # re-code missing as zero and set a failure indicator
  relevant <- relevant %>%
    mutate(cost2 = ifelse(cost2 < -990, 0, cost2)) %>%
    mutate(cost_fail2 = ifelse(cost2 < -990 ,1 ,0))

  print(paste("For",
              this_timeperiod,
              "assigned",
              prettyNum(sum(!is.na(relevant$cost2)),big.mark=","),
              "costs, with",
              prettyNum(sum(!is.na(relevant$cost2)&(relevant$cost2>0)),big.mark=","),
              "nonzero values"))

  # re-code na as zero
  relevant$cost2[is.na(relevant$cost2)]           <- 0
  relevant$cost_fail2[is.na(relevant$cost_fail2)] <- 0

  # set the cost variable
  relevant <- relevant %>%
    mutate(cost = cost + cost2) %>%
    mutate(cost_fail = cost_fail + cost_fail2)

  print(paste("  -> total nonzero costs:",
              prettyNum(sum(relevant$cost!=0),big.mark=",")))

  # clean-up
  relevant <- relevant %>%
    select(-da, -daToll, -s2, -s2Toll, -s3, -s3Toll, -wTrnW, -dTrnW, -wTrnD, -cost2, -cost_fail2)

  return_list <- rbind(relevant, irrelevant)

  return(return_list)

}

## Function to add Distance to Tours or Trips

# Function `add_distance`: attaches the distance skims the given time period abbreviation `this_timeperiod`
# to the given tours data frame (note: this can be the trips data frame). Joining is done on the columns
# `orig_taz`, `dest_taz`, and `timeCode`. The function fills in values to the column `distance` for the given
# time period based on the column `distance_mode`.

add_distance <- function(this_timeperiod, input_trips_or_tours) {

  # separate the relevant and irrelevant tours/trips
  relevant <- input_trips_or_tours %>%
    filter(timeCode == this_timeperiod)

  irrelevant <- input_trips_or_tours %>%
    filter(timeCode != this_timeperiod)

  # Read the relevant skim table
  skim_file <- file.path(TARGET_DIR,"database",paste0("DistanceSkimsDatabase",this_timeperiod,".csv"))
  distSkims <- read.table(file = skim_file, header=TRUE, sep=",")

  # rename columns for join
  distSkims <- distSkims %>%
    rename(orig_taz = orig, dest_taz = dest)

  # Left join tours to the skims
  relevant <- left_join(relevant, distSkims, by=c("orig_taz","dest_taz"))

  # Assign distance value
  relevant <- relevant %>%
    mutate(distance2 = 0.0)

  relevant <- relevant %>%
    mutate(distance2 = (distance_mode == 1) * da +
             (distance_mode == 2) * daToll +
             (distance_mode == 3) * s2     +
             (distance_mode == 4) * s2Toll +
             (distance_mode == 5) * s3     +
             (distance_mode == 6) * s3Toll +
             (distance_mode == 7) * walk   +
             (distance_mode == 8) * bike   +
             (distance_mode >= 9) * pmin(da, daToll))


  relevant <- relevant %>%
    mutate(distance2 = ifelse(distance2 < -990.0, 0, distance2))

  print(paste("For",
              this_timeperiod,
              "assigned",
              prettyNum(sum(!is.na(relevant$distance2)),big.mark=","),
              "distances, with",
              prettyNum(sum(!is.na(relevant$distance2)&(relevant$distance2>0)),big.mark=","),
              "nonzero values"))

  relevant$distance2[is.na(relevant$distance2)] <- 0

  relevant <- relevant %>%
    mutate(distance = distance + distance2)

  print(paste("  -> total nonzero distances:",prettyNum(sum(relevant$distance!=0),big.mark=",")))

  relevant <- relevant %>%
    select(-da, -daToll, -s2, -s2Toll, -s3, -s3Toll, -walk, -bike, -distance2)

  return_list <- rbind(relevant, irrelevant)

  return(return_list)
}

## Function to add Time to Tours or Trips

# Function `add_time`: attaches the time skims for the given time period `this_timeperiod`
# to the given tours data.frame (note: this can be the trips data frame).  Joining is done on the
# columns `orig_taz`, `dest_taz`, and `timeCode`.
#
# Fills in values to the column `time` for the given time period based on the column `costMode`.
#
# Pass `reverse_od` as TRUE to do return trip; this uses the dest taz as the origin and the origin
# taz as the dest, and it uses wTrnD time rather than dTrnW.
#
# Tallies failed times (expected time but -999 found) in the field `time_fail`.

add_time <- function(this_timeperiod, input_trips_or_tours, reverse_od=FALSE) {

  # separate the relevant and irrelevant tours/trips
  relevant <- input_trips_or_tours %>%
    filter(timeCode == this_timeperiod)

  irrelevant <- input_trips_or_tours %>%
    filter(timeCode != this_timeperiod)

  # read in the relevant skim
  skim_file <- file.path(TARGET_DIR,"database", paste0("TimeSkimsDatabase", this_timeperiod,".csv"))
  timeSkims   <- read.table(file = skim_file, header = TRUE, sep = ",")

  # standardize column names, reversing if needed
  if (reverse_od) {
    timeSkims <- timeSkims %>%
      rename(orig_taz = dest, dest_taz = orig)
  } else {
    timeSkims <- timeSkims %>%
      rename(orig_taz = orig, dest_taz = dest)
  }


  # join the skims and relevant trips/tours
  relevant <- left_join(relevant, timeSkims, by=c("orig_taz","dest_taz"))

  # assign the new time
  relevant <- relevant %>%
    mutate(time2 = (costMode == 1) * da +
             (costMode == 2) * daToll +
             (costMode == 3) * s2 +
             (costMode == 4) * s2Toll +
             (costMode == 5) * s3 +
             (costMode == 6) * s3Toll +
             (costMode == 7) * walk +
             (costMode == 8) * bike +
             (costMode == 9) * wTrnW +
             (costMode == 10) * (1 - reverse_od) * dTrnW +
             (costMode == 10) * (reverse_od) * wTrnD)

  # re-code missing as zero and set a failure indicator
  relevant <- relevant %>%
    mutate(time2 = ifelse(time2 < -990, 0, time2)) %>%
    mutate(time_fail2 = ifelse(time2 < -990 ,1 ,0))

  print(paste("For",
              this_timeperiod,
              "assigned",
              prettyNum(sum(!is.na(relevant$time2)),big.mark=","),
              "times, with",
              prettyNum(sum(!is.na(relevant$time2)&(relevant$time2>0)),big.mark=","),
              "nonzero values"))

  # re-code na as zero
  relevant$time2[is.na(relevant$time2)] <- 0
  relevant$time2[is.na(relevant$time_fail2)] <- 0

  # set the time variable
  relevant <- relevant %>%
    mutate(time = time + time2) %>%
    mutate(time_fail = time_fail + time_fail2)

  print(paste("  -> total nonzero times:",prettyNum(sum(relevant$time!=0),big.mark=",")))

  relevant <- relevant %>%
    select(-da, -daToll, -s2, -s2Toll, -s3, -s3Toll, -walk, -bike, -wTrnW, -dTrnW, -wTrnD, -time2, -time_fail2)

  return_list <- rbind(relevant, irrelevant)

  return(return_list)
}


## Function to add Active travel time to tours

# Function `add_active`: attaches the active skims of the given time period `this_timeperiod`
# to the given trip data.frame (joining on the columns `orig_taz`, `dest_taz`, and `timeCode`).
#
# Fills in values to the column `active` for the given time period.

add_active <- function(this_timeperiod, input_trips_or_tours) {

  # separate the relevant and irrelevant tours/trips
  relevant <- input_trips_or_tours %>%
    filter(timeCode == this_timeperiod)

  irrelevant <- input_trips_or_tours %>%
    filter(timeCode != this_timeperiod)

  # read in the relevant skim
  skim_file <- file.path(TARGET_DIR,"database", paste0("ActiveTimeSkimsDatabase", this_timeperiod,".csv"))
  activeSkims <- read.table(file = skim_file,header=TRUE, sep=",")

  # standarize column names
  activeSkims <- activeSkims %>%
    rename(orig_taz = orig, dest_taz = dest)

  # left join the skims
  relevant <- left_join(relevant, activeSkims, by=c("orig_taz","dest_taz"))

  # assign active2
  relevant <- relevant %>%
    mutate(active2 = (amode == 1) * walk +
             (amode == 2) * bike +
             (amode == 3) * wTrnW +
             (amode == 4) * dTrnW +
             (amode == 5) * wTrnD)

  relevant <- relevant %>%
    mutate(active2 = ifelse(active2 < -990.0, 0, active2))

  print(paste("For",
              this_timeperiod,
              "assigned",
              prettyNum(sum(!is.na(relevant$active2)),big.mark=","),
              "active times, with",
              prettyNum(sum(!is.na(relevant$active2)&(relevant$active2>0)),big.mark=","),
              "nonzero values"))

  relevant$active2[is.na(relevant$active2)] <- 0

  relevant <- relevant %>%
    mutate(active = active + active2)

  print(paste("  -> total nonzero active times:",
              prettyNum(sum(relevant$active!=0),big.mark=",")))

  relevant <- relevant %>%
    select(-walk, -bike, -wTrnW, -dTrnW, -wTrnD, -active2)

  return_list <- rbind(relevant, irrelevant)

  return(return_list)
}

# Data Reads: Trips

## Read Individual Trips and recode a few variables

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip

indiv_trips     <- read.table(file=file.path(MAIN_DIR, paste0("indivTripData_",ITER,".csv")), header=TRUE, sep=",")
indiv_trips     <- select(indiv_trips, hh_id, person_id, tour_id, orig_taz, dest_taz,
                          trip_mode, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate) %>%
                   mutate(tour_id = paste0("i",substr(tour_category,1,2),tour_id))

## Data Reads: Joint Trips and recode a few variables

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip
joint_trips     <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("jointTripData_",ITER,".csv")),
                                     header=TRUE, sep=","))
joint_trips     <- select(joint_trips, hh_id, tour_id, orig_taz, dest_taz, trip_mode,
                          num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate) %>%
                   mutate(tour_id = paste0("j",substr(tour_category,1,2),tour_id))

print(paste("Read",prettyNum(nrow(joint_trips),big.mark=","),
            "joint trips or ",prettyNum(sum(joint_trips$num_participants),big.mark=","),
            "joint person trips"))

## Add `num_participants` to joint_tours
joint_tours     <- left_join(joint_tours,
                             unique(select(joint_trips, hh_id, tour_id, num_participants)),
                             by=c("hh_id","tour_id"))

## Combine individual tours and joint tours together

tours <- rbind(select(indiv_tours, -person_id, -person_num, -person_type, -atWork_freq, -fp_choice),
               select(joint_tours, -tour_composition, -tour_participants))

# done with this -- joint_tours will be used for unwinding joint trips and then released
if (JUST_MES!="1") {
  remove(indiv_tours)
}

# add residence TAZ info
tours <- left_join(tours, select(households, hh_id, taz, SD, COUNTY, county_name),
                   by=c("hh_id"))

# add simple_purpose, duration, parking cost to tours table
add_tour_attrs <- function(ftours) {
  # add simple_purpose
  ftours <- mutate(ftours, simple_purpose='non-work')
  ftours$simple_purpose[ftours$tour_purpose=='work_low'       ] <- 'work'
  ftours$simple_purpose[ftours$tour_purpose=='work_med'       ] <- 'work'
  ftours$simple_purpose[ftours$tour_purpose=='work_high'      ] <- 'work'
  ftours$simple_purpose[ftours$tour_purpose=='work_very high' ] <- 'work'

  ftours$simple_purpose[ftours$tour_purpose=='school_grade'   ] <- 'school'
  ftours$simple_purpose[ftours$tour_purpose=='school_high'    ] <- 'school'

  ftours$simple_purpose[ftours$tour_purpose=='university'     ] <- 'college'

  ftours$simple_purpose[ftours$tour_purpose=='atwork_business'] <- 'at work'
  ftours$simple_purpose[ftours$tour_purpose=='atwork_eat'     ] <- 'at work'
  ftours$simple_purpose[ftours$tour_purpose=='atwork_maint'   ] <- 'at work'

  # Calculate the duration
  ftours   <- mutate(ftours, duration=end_hour-start_hour+0.5)

  # Parking cost is based on tour duration
  ftours   <- mutate(ftours, parking_cost=parking_rate*duration)
  # Distribute costs across shared ride modes (same value used in skims, assignment) for indiv tours
  ftours   <- mutate(ftours,
                     parking_cost=ifelse((num_participants==1)&((tour_mode==3)|(tour_mode==4)),
                                        parking_cost/1.75,parking_cost))
  ftours   <- mutate(ftours,
                     parking_cost=ifelse((num_participants==1)&((tour_mode==5)|(tour_mode==6)),
                                         parking_cost/2.50,parking_cost))
  # Set the transit parking cost to zero
  ftours   <- mutate(ftours, parking_cost=ifelse(tour_mode>6,0.0,parking_cost))
  return(ftours)
}

tours <- add_tour_attrs(tours)

## Convert joint trips to joint person trips

# Getting the tour participants person nums from the joint_tours table, and unwind it so that each joint tour
# becomes a row per partipant.  Returns table of person-tours, with columns hh_id, tour_id, person_num, person_id
get_joint_tour_persons <- function(joint_tours, persons) {
  # tour participants are person ids separated by spaces -- create a table of hh_id, person_num for them
  joint_tour_persons <- data.frame(hh_id=numeric(), tour_id=numeric(), person_num=numeric())
  # unwind particpants into table with cols hh_id, tour_id, person_num1, person_num2, ...
  participants   <- strsplit(as.character(joint_tours$tour_participants)," ")
  max_peeps      <- max(sapply(participants,length))
  participants   <- lapply(participants, function(X) c(X,rep(NA, max_peeps-length(X))))
  participants   <- data.frame(t(do.call(cbind, participants)))
  participants   <- mutate(participants, hh_id=joint_tours$hh_id, tour_id=joint_tours$tour_id)
  # melt the persons so they are each on their own row
  for (peep in 1:max_peeps) {
    jtp <- melt(participants, id.var=c("hh_id","tour_id"), measure.vars=paste0("X",peep), na.rm=TRUE)
    jtp <- mutate(jtp, person_num=value)
    jtp <- select(jtp, hh_id, tour_id, person_num)
    joint_tour_persons <- rbind(joint_tour_persons, jtp)
  }
  joint_tour_persons <- transform(joint_tour_persons, person_num=as.numeric(person_num))
  # sort by hh_id
  joint_tour_persons <- joint_tour_persons[with(joint_tour_persons, order(hh_id, tour_id)),]
  # merge with the persons to get the person_id
  joint_tour_persons <- left_join(joint_tour_persons, select(persons, hh_id, person_num, person_id), by=c("hh_id","person_num"))

  return(joint_tour_persons)
}

joint_tour_persons <- get_joint_tour_persons(joint_tours, persons)

# create and write person-tours for just-mes
if (JUST_MES=="1") {
  joint_tours <- left_join(joint_tour_persons, joint_tours)
  indiv_tours$tour_participants <- as.character(indiv_tours$person_num)
  person_tours <- rbind(select(indiv_tours, -person_type, -atWork_freq, -fp_choice),
                        select(joint_tours, -tour_composition))
  person_tours <- add_tour_attrs(person_tours)

  save(person_tours, file=file.path(UPDATED_DIR, "person_tours.rdata"))
  write.table(person_tours, file=file.path(UPDATED_DIR, "person_tours.csv"), sep=",", row.names=FALSE)
  remove(indiv_tours, person_tours)
}

# attach persons to the joint_trips
joint_person_trips <- inner_join(joint_trips, joint_tour_persons, by=c("hh_id", "tour_id"))
# select out person_num and the person table columns
joint_person_trips <- select(joint_person_trips, hh_id, person_id, tour_id, orig_taz, dest_taz, trip_mode,
                             num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, avAvailable, sampleRate)
# cleanup
remove(joint_tours,joint_trips,joint_tour_persons)

## Combine Individual Trips and Joint Person Trips
indiv_trips        <- mutate(indiv_trips,        num_participants=1) %>% select(-tour_category)
trips <- tbl_df(rbind(indiv_trips, joint_person_trips))
print(paste("Combined",prettyNum(nrow(indiv_trips),big.mark=","),
            "individual trips with",prettyNum(nrow(joint_person_trips),big.mark=","),
            "joint trips to make",prettyNum(nrow(trips),big.mark=",")," total trips"))
remove(indiv_trips,joint_person_trips)

## Add Variables to Trips

# Add some variable to trips, such as:
#   * `timeCode`, a recoding of the `depart_hour` for joining skims
#   * `home_taz` from household table
#   * `incQ` and label from the household table
#   * `autoSuff` and label from the household table
#   * `walk_subzone` and label from the household table
#   * `ptype` and label from persons

trips <- mutate(trips,
                timeCodeNum=1*(depart_hour<6) +                                       # EA
                            2*((depart_hour>5)&(depart_hour<10)) +                    # AM
                            3*((depart_hour>9)&(depart_hour<15)) +                    # MD
                            4*((depart_hour>14)&(depart_hour<19)) +                   # PM
                            5*((depart_hour>18))                                      # EV
                )
trips <- left_join(trips, LOOKUP_TIMEPERIOD, by=c("timeCodeNum"))
trips <- select(mutate(trips, timeCode=timeperiod_abbrev), -timeperiod_abbrev)
trips <- left_join(trips,
                   mutate(households, home_taz=taz) %>%
                     select(hh_id, incQ, incQ_label, autoSuff, autoSuff_label,
                            home_taz, walk_subzone, walk_subzone_label),
                   by=c("hh_id"))
trips <- left_join(trips,
                   select(persons, hh_id, person_id, ptype, ptype_label),
                   by=c("hh_id","person_id"))

## Add Trip Distance to Trips

# Use `add_distance` to add trip distance to trips.
trips <- mutate(trips,
                distance=0.0,
                distance_mode=trip_mode) # use trip_mode for distance

for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  trips <- add_distance(timeperiod, trips)
}
trips <- tbl_df(trips)
trips <- select(trips, -distance_mode)

## Add Active Travel time to Trips

# code the Active Mode
trips <- trips %>%
  mutate(amode = 0) %>%
  mutate(amode = ifelse(trip_mode == 7, 1, amode)) %>%
  mutate(amode = ifelse(trip_mode == 8, 2, amode)) %>%
  mutate(amode = ifelse((trip_mode >= 9) & (trip_mode <= 13), 3, amode)) %>%
  mutate(amode = ifelse((trip_mode >= 14) & (trip_mode <= 18) & (orig_purpose == 'Home'), 4, amode)) %>%
  mutate(amode = ifelse((trip_mode >= 14) & (trip_mode <= 18) & (dest_purpose == 'Home'), 5, amode)) %>%
  mutate(wlk_trip = ifelse(amode == 1, 1, 0)) %>%
  mutate(bik_trip = ifelse(amode == 2, 1, 0)) %>%
  mutate(wtr_trip = ifelse(amode == 3, 1, 0)) %>%
  mutate(dtr_trip = ifelse(amode == 4, 1, 0)) %>%
  mutate(dtr_trip = ifelse(amode == 5, 1 + amode, 0)) %>%
  mutate(active = 0.0)

# go go gadget: Add active transportation time to trips
for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  trips <- add_active(timeperiod, trips)
}
trips <- tbl_df(trips)

## Add Travel Cost and Travel Time to Trips
trips <- trips %>%
  mutate(costMode = 0) %>%
  mutate(costMode = ifelse(trip_mode <= 8, trip_mode, costMode)) %>%
  mutate(costMode = ifelse((trip_mode >= 9) & (trip_mode <=13), 9, costMode)) %>%
  mutate(costMode = ifelse((trip_mode >= 14) & (trip_mode <=18) & (orig_purpose == 'Home'), 10, costMode)) %>%
  mutate(costMode = ifelse((trip_mode >= 14) & (trip_mode <=18) & (dest_purpose == 'Home'), 11, costMode)) %>%
  mutate(cost = 0) %>%
  mutate(cost_fail = 0) %>%
  mutate(time = 0) %>%
  mutate(time_fail = 0)

for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  trips <- add_cost(timeperiod, trips)
  trips <- add_time(timeperiod, trips)
}
trips <- tbl_df(trips)

# Mandatory Locations

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/MandatoryLocation
mandatory_locations <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("wsLocResults_",ITER,".csv")),
                                         header=TRUE, sep=","))

# Summaries

## Active Transportation Summary
# we only want some variables - sum them to hh_id/person_id
trips_melt  <- tbl_df(melt(select(trips, hh_id, person_id, wlk_trip, bik_trip, wtr_trip, dtr_trip, active),
                           id.vars=c("hh_id","person_id")))
trips_dcast <- tbl_df(dcast(trips_melt, hh_id+person_id ~ variable, fun.aggregate=sum))
# left join with persons --> one row per person!
trips_by_person <- left_join(select(persons, hh_id, person_id, ptype, activity_pattern, value_of_time),
                             trips_dcast, by=c("hh_id","person_id"))

# we're done with these
remove(trips_melt,trips_dcast)

# append autos, taz, COUNTY from households
trips_by_person <- left_join(trips_by_person, select(households, hh_id, autos, taz, county_name), by=c("hh_id"))
# recode zeroAuto
trips_by_person <- mutate(trips_by_person,
                          zeroAuto=(autos==0),
                          atHomeA=is.na(active))
# set NAs to zero
trips_by_person$wlk_trip[is.na(trips_by_person$wlk_trip)] <- 0
trips_by_person$bik_trip[is.na(trips_by_person$bik_trip)] <- 0
trips_by_person$wtr_trip[is.na(trips_by_person$wtr_trip)] <- 0
trips_by_person$dtr_trip[is.na(trips_by_person$dtr_trip)] <- 0
trips_by_person$active[is.na(trips_by_person$active)] <- 0

trips_by_person <- mutate(trips_by_person, more15=(active>=15), more30=(active>=30))

# summarize
active_summary <- summarise(group_by(trips_by_person, taz, county_name, ptype, zeroAuto),
                            freq     = n(),
                            active   = mean(active),
                            more15   = mean(more15),
                            more30   = mean(more30),
                            wlk_trip = mean(wlk_trip),
                            bik_trip = mean(bik_trip),
                            wtr_trip = mean(wtr_trip),
                            dtr_trip = mean(dtr_trip),
                            atHomeA  = mean(atHomeA))

# scale by sampleshare
active_summary$freq <- active_summary$freq / SAMPLESHARE

write.table(active_summary, file.path(RESULTS_DIR,"ActiveTransport.csv"), sep=",", row.names=FALSE)
model_summary <- active_summary  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"ActiveTransport.rdata"))
remove(active_summary, trips_by_person)

## Activity Pattern Summary

actpatt_summary <- summarise(group_by(persons, type, activity_pattern, imf_choice, inmf_choice, incQ_label), freq=n())
actpatt_summary$freq <- actpatt_summary$freq / SAMPLESHARE
write.table(actpatt_summary, file.path(RESULTS_DIR,"ActivityPattern.csv"), sep=",", row.names=FALSE)
model_summary <- actpatt_summary  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"ActivityPattern.rdata"))
remove(actpatt_summary)

## Auto Ownership Summaries

# summarise
autoown_summary <- summarise(group_by(households, SD, COUNTY, county_name, autos,
                                      incQ, incQ_label, walk_subzone, walk_subzone_label, workers, kidsNoDr), freq=n())
autoown_summary$freq <- autoown_summary$freq / SAMPLESHARE
write.table(autoown_summary, file.path(RESULTS_DIR,"AutomobileOwnership.csv"), sep=",", row.names=FALSE)
model_summary <- autoown_summary  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"AutomobileOwnership.rdata"))

### Auto Ownership Summary By County
auto_labels <- c("Zero automobiles", "One automobile", "Two automobiles",
                 "Three automobiles", "Four or more automobiles")

## Commute By Employment Location Summaries
commute_tours   <- select(tours, hh_id, orig_taz, dest_taz, dest_COUNTY, dest_county_name, dest_SD,
                          tour_purpose, start_hour, end_hour, tour_mode, income, incQ, incQ_label, parking_cost)
# select out non-work travel
commute_tours   <- subset(commute_tours, (tour_purpose!="atwork_business" & tour_purpose!="atwork_eat"     &
                                          tour_purpose!="atwork_maint"    & tour_purpose!="eatout"         &
                                          tour_purpose!="escort_kids"     & tour_purpose!="escort_no kids" &
                                          tour_purpose!="othdiscr"        & tour_purpose!="othmaint"       &
                                          tour_purpose!="school_grade"    & tour_purpose!="school_high"    &
                                          tour_purpose!="shopping"        & tour_purpose!="social"         &
                                          tour_purpose!="university"))

# TODO: add this to all tours, not just commute?
# The cost database contains simplified transit modes, build a cross-walk from the full modes;
commute_tours   <- mutate(commute_tours,
                          costMode  =(tour_mode<=8)*tour_mode +         # auto, walk, bike all in the skims
                                     # All walk to transit sub modes get best path walk to transit skim
                                     (tour_mode>=9)*(tour_mode<=13)*9 +
                                     # All drive transit walk sub modes get the best path
                                     # drive transit walk skim (tours start at home)
                                     (tour_mode>=14)*(tour_mode<=18)*10,
                          timeCodeHwNum=(start_hour<6)*1 +                  # EA
                                        (start_hour>5)*(start_hour<10)*2 +  # AM
                                        (start_hour>9)*(start_hour<15)*3 +  # MD
                                        (start_hour>14)*(start_hour<19)*4 + # PM
                                        (start_hour>18)*5,                  # EV
                          timeCodeWhNum=(end_hour<6)*1 +                  # EA
                                        (end_hour>5)*(end_hour<10)*2 +    # AM
                                        (end_hour>9)*(end_hour<15)*3 +    # MD
                                        (end_hour>14)*(end_hour<19)*4 +   # PM
                                        (end_hour>18)*5                   # EV
                          )
# add timeCodeHw and timeCodeWh (character abbreviation versions)
commute_tours   <- left_join(commute_tours,
                             select(mutate(LOOKUP_TIMEPERIOD,
                                           timeCodeHwNum=timeCodeNum, timeCodeHw=timeperiod_abbrev),
                                    timeCodeHwNum, timeCodeHw))
commute_tours   <- left_join(commute_tours,
                             select(mutate(LOOKUP_TIMEPERIOD,
                                           timeCodeWhNum=timeCodeNum, timeCodeWh=timeperiod_abbrev),
                                    timeCodeWhNum, timeCodeWh))

# Initialize for home-work cost lookup
commute_tours   <- mutate(commute_tours, timeCode=timeCodeHw, cost=0.0, cost_fail=0)
# Add home-work cost to tours
for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  commute_tours <- add_cost(timeperiod, commute_tours, reverse_od=FALSE)
}
# That set it as cost, so rename
commute_tours   <- mutate(commute_tours, hwCost=cost)
# Add distance to tours
commute_tours   <- mutate(commute_tours, distance=0.0, distance_mode=tour_mode)
for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  commute_tours <- add_distance(timeperiod, commute_tours)
}

# Add time
commute_tours   <- mutate(commute_tours, time=0.0, time_fail=0)
for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  commute_tours <- add_time(timeperiod, commute_tours)
}


# Initialize for work-home cost lookup.
commute_tours   <- mutate(commute_tours, timeCode=timeCodeWh, cost=0.0)
# Add work-home cost to tours
for (timeperiod in LOOKUP_TIMEPERIOD$timeperiod_abbrev) {
  commute_tours <- add_cost(timeperiod, commute_tours, reverse_od=TRUE)
}
# That set it as cost, so rename
commute_tours   <- mutate(commute_tours, whCost=cost)
# Save cost as the average of hwCost and whCost
commute_tours   <- mutate(commute_tours, cost=0.5*(hwCost+whCost))

commute_tours   <- mutate(commute_tours, totCost=cost+parking_cost)

# tours with failures should be dropped from the mean
commute_tours$totCost[commute_tours$cost_fail>0] <- NA
commute_tours$cost[commute_tours$cost_fail>0]    <- NA
commute_tours$time[commute_tours$time_fail>0]    <- NA

# summarise
commute_summary <- summarise(group_by(commute_tours, dest_COUNTY, dest_county_name, dest_SD, tour_mode),
                             freq         = n(),
                             totCost      = mean(totCost, na.rm=TRUE),
                             cost         = mean(cost,    na.rm=TRUE),
                             parking_cost = mean(parking_cost),
                             distance     = mean(distance),
                             cost_fail    = sum(cost_fail))
commute_summary$freq <- commute_summary$freq / SAMPLESHARE
write.table(commute_summary, file.path(RESULTS_DIR,"CommuteByEmploymentLocation.csv"),
            sep=",", row.names=FALSE)
model_summary <- commute_summary  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"CommuteByEmploymentLocation.rdata"))
remove(commute_summary)


## Commute By Income Summaries
commute_inc_summary_byjob <- summarise(group_by(commute_tours, dest_COUNTY, dest_county_name, dest_SD, dest_taz,
                                                tour_mode, incQ, incQ_label),
                                       freq         = n(),
                                       totCost      = mean(totCost, na.rm=TRUE),
                                       cost         = mean(cost,    na.rm=TRUE),
                                       parking_cost = mean(parking_cost),
                                       distance     = mean(distance),
                                       duration     = mean(time,    na.rm=TRUE),
                                       cost_fail    = sum(cost_fail),
                                       time_fail    = sum(time_fail))
commute_inc_summary_byjob$freq <- commute_inc_summary_byjob$freq / SAMPLESHARE
write.table(commute_inc_summary_byjob, file.path(RESULTS_DIR,"CommuteByIncomeJob.csv"), sep=",", row.names=FALSE)
model_summary <- commute_inc_summary_byjob  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"CommuteByIncomeJob.rdata"))

# The COUNTY and super district are by destination right now; add residence
commute_tours   <- left_join(commute_tours,
                             mutate(tazData, orig_taz=taz, res_COUNTY=COUNTY, res_county_name=county_name,
                                    res_SD=SD) %>%
                               select(orig_taz, res_COUNTY, res_county_name, res_SD),
                             by=c("orig_taz"))
commute_inc_summary_byres <- summarise(group_by(commute_tours, res_COUNTY, res_county_name, res_SD, orig_taz,
                                                tour_mode, incQ, incQ_label),
                                       freq         = n(),
                                       totCost      = mean(totCost, na.rm=TRUE),
                                       cost         = mean(cost,    na.rm=TRUE),
                                       parking_cost = mean(parking_cost),
                                       distance     = mean(distance),
                                       duration     = mean(time,    na.rm=TRUE),
                                       cost_fail    = sum(cost_fail),
                                       time_fail    = sum(time_fail))
commute_inc_summary_byres$freq <- commute_inc_summary_byres$freq / SAMPLESHARE
write.table(commute_inc_summary_byres, file.path(RESULTS_DIR,"CommuteByIncomeHousehold.csv"), sep=",", row.names=FALSE)
model_summary <- commute_inc_summary_byres  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"CommuteByIncomeHousehold.rdata"))
remove(commute_tours, commute_inc_summary_byjob, commute_inc_summary_byres)

## Journey To Work Summary

# select out non-work travel
work_locations <- subset(mandatory_locations, WorkLocation != 0)
# add home county
work_locations <- left_join(work_locations,
                            mutate(tazData,HomeTAZ=taz, homeCOUNTY=COUNTY, home_county_name=county_name) %>%
                              select(HomeTAZ,homeCOUNTY,home_county_name),
                            by=c("HomeTAZ"))
# add work county
work_locations <- left_join(work_locations,
                            mutate(tazData,WorkLocation=taz, workCOUNTY=COUNTY, work_county_name=county_name) %>%
                              select(WorkLocation,workCOUNTY,work_county_name),
                            by=c("WorkLocation"))

journeytowork_summary <- summarise(group_by(work_locations,
                                            homeCOUNTY, home_county_name, HomeTAZ,
                                            WorkLocation, workCOUNTY, work_county_name),
                                   freq   = n(),
                                   Income = mean(Income))
journeytowork_summary$freq <- journeytowork_summary$freq / SAMPLESHARE
write.table(journeytowork_summary,
            file.path(RESULTS_DIR,"JourneyToWork.csv"), sep=",", row.names=FALSE)
model_summary <- journeytowork_summary  # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR,"JourneyToWork.rdata"))
remove(mandatory_locations, work_locations, journeytowork_summary, model_summary)

## Time of Day Summary
timeofday_summary <- summarise(group_by(tours,SD,COUNTY,county_name,
                                        simple_purpose,tour_mode,start_hour,end_hour),
                               freq              = n(),
                               num_participants  = sum(num_participants))
timeofday_summary$freq             <- timeofday_summary$freq / SAMPLESHARE
timeofday_summary$num_participants <- timeofday_summary$num_participants / SAMPLESHARE
write.table(timeofday_summary,
            file.path(RESULTS_DIR,"TimeOfDay.csv"), sep=",", row.names=FALSE)
model_summary <- timeofday_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "TimeOfDay.rdata"))

# another table -- who's touring?
persons_touring <- data.frame(hour=numeric(), simple_purpose=character(), persons_touring=numeric())
for (h in min(timeofday_summary$start_hour):max(timeofday_summary$end_hour)) {
  touring_at_hour <- subset(timeofday_summary,
                         (timeofday_summary$start_hour<=h)&(timeofday_summary$end_hour>=h))
  touring_at_hour <- summarise(group_by(touring_at_hour, simple_purpose), persons_touring=sum(num_participants))
  touring_at_hour <- mutate(touring_at_hour, hour=h)
  persons_touring <- rbind(persons_touring, touring_at_hour)
}
write.table(persons_touring, file.path(RESULTS_DIR,"TimeOfDay_personsTouring.csv"), sep=",", row.names=FALSE)
model_summary <- persons_touring
save(model_summary, file=file.path(RESULTS_DIR, "TimeOfDay_personsTouring.rdata"))
remove(timeofday_summary, persons_touring, h, touring_at_hour)


## Trip Distance Summary
tripdist_summary          <- summarise(group_by(trips, autoSuff, autoSuff_label, incQ, incQ_label, timeCode,
                                                timeperiod_label, trip_mode, tour_purpose),
                                       freq         = n(),
                                       distance     = mean(distance))
tripdist_summary$freq <- tripdist_summary$freq / SAMPLESHARE
write.table(tripdist_summary, file.path(RESULTS_DIR,"TripDistance.csv"), sep=",", row.names=FALSE)
model_summary <- tripdist_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "TripDistance.rdata"))
remove(tripdist_summary, model_summary)

## Cleanup and save persons
save(persons, file=file.path(UPDATED_DIR, "persons.rdata"))
if (JUST_MES=="1") { write.table(persons, file=file.path(UPDATED_DIR, "persons.csv"), sep=",", row.names=FALSE) }
remove(persons)

## Travel Cost Summary

# split trip cost into trip_cost_indiv, trip_cost_joint
trips       <- mutate(trips,
                      trip_cost_indiv = (num_participants==1)*cost,
                      trip_cost_joint = (num_participants>1)*cost/num_participants
                      )

# we only want some variables - sum them to hh_id
trips_melt  <- tbl_df(melt(select(trips, hh_id, trip_cost_indiv, trip_cost_joint, cost_fail),
                           id.vars=c("hh_id")))
trips_dcast <- tbl_df(dcast(trips_melt, hh_id ~ variable, fun.aggregate=sum))
# left join with household --> one row per household!
costs_by_household <- left_join(select(households, hh_id, SD, COUNTY, county_name,
                                       PERSONS, incQ, incQ_label, autos),
                             trips_dcast, by=c("hh_id"))

# we're done with these
remove(trips_melt,trips_dcast)

# recode people = PERSONS capped at 6
costs_by_household <- mutate(costs_by_household, people=ifelse(PERSONS>6,6,PERSONS))

# fill in NA
costs_by_household$trip_cost_indiv[is.na(costs_by_household$trip_cost_indiv)] <- 0
costs_by_household$trip_cost_joint[is.na(costs_by_household$trip_cost_joint)] <- 0
costs_by_household$cost_fail[is.na(costs_by_household$cost_fail)] <- 0

# parking cost is in tours
tours       <- mutate(tours,
                      pcost_indiv = (num_participants==1)*parking_cost,
                      pcost_joint = (num_participants>1)*parking_cost)
# sum them to hh_id
tours_melt  <- tbl_df(melt(select(tours, hh_id, pcost_indiv, pcost_joint),
                           id.vars=c("hh_id")))
tours_dcast <- tbl_df(dcast(tours_melt, hh_id ~ variable, fun.aggregate=sum))

# add to costs_by_household
costs_by_household <- left_join(costs_by_household, tours_dcast, by=c("hh_id"))

# fill in NA
costs_by_household$pcost_indiv[is.na(costs_by_household$pcost_indiv)] <- 0
costs_by_household$pcost_joint[is.na(costs_by_household$pcost_joint)] <- 0

costs_by_household <- mutate(costs_by_household,
                             total_cost=trip_cost_indiv+trip_cost_joint+
                                        pcost_indiv+pcost_joint)
remove(tours_melt, tours_dcast)

# write summary
travelcost_summary  <- summarise(group_by(costs_by_household, SD, COUNTY, county_name,
                                          people, incQ, incQ_label, autos),
                                 freq            = n(),
                                 total_cost      = mean(total_cost),
                                 trip_cost_indiv = mean(trip_cost_indiv),
                                 trip_cost_joint = mean(trip_cost_joint),
                                 cost_fail       = sum(cost_fail),
                                 pcost_indiv     = mean(pcost_indiv),
                                 pcost_joint     = mean(pcost_joint))
travelcost_summary$freq <- travelcost_summary$freq / SAMPLESHARE
write.table(travelcost_summary, file.path(RESULTS_DIR,"TravelCost.csv"), sep=",", row.names=FALSE)
model_summary <- travelcost_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "TravelCost.rdata"))
remove(costs_by_household,travelcost_summary,model_summary)

## Per Trip Travel Time Summary
triptime_summary <- summarise(group_by(trips, incQ, incQ_label, trip_mode, tour_purpose),
                              freq             = n(),
                              num_participants = sum(num_participants),
                              trvlTime         = mean(time),
                              time_fail        = sum(time_fail))
triptime_summary$freq             <- triptime_summary$freq / SAMPLESHARE
triptime_summary$num_participants <- triptime_summary$num_participants / SAMPLESHARE
write.table(triptime_summary, file.path(RESULTS_DIR,"PerTripTravelTime.csv"), sep=",", row.names=FALSE)
model_summary <- triptime_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "PerTripTravelTime.rdata"))
remove(triptime_summary, model_summary)

## Cleanup and save tours, trips and households
save(trips, file=file.path(UPDATED_DIR, "trips.rdata"))
if (JUST_MES=="1") {
  write.table(trips, file=file.path(UPDATED_DIR, "trips.csv"), sep=",", row.names=FALSE)
  ## Need a version for mapping.  These are links, so we need to split into points.
  ## No intermediate stop: rows with stop_id == -1
  trips_dest_noint <- trips[ which(trips$stop_id==-1), ] %>%
    mutate(stop_id=0) %>%
    select(-orig_taz, -orig_purpose) %>%
    rename(taz = dest_taz, purpose = dest_purpose)
  trips_orig_noint <- trips[ which(trips$stop_id==-1), ] %>%
    select(-dest_taz, -dest_purpose) %>%
    rename(taz = orig_taz, purpose = orig_purpose)
  ## Intermediate stops: rows with stop_id > 0
  trips_orig_int <- trips[ which(trips$stop_id==0), ] %>%
    mutate(stop_id=-1) %>%
    select(-dest_taz, -dest_purpose) %>%
    rename(taz= orig_taz, purpose = orig_purpose)
  trips_dest_int <- trips[ which(trips$stop_id>=0), ] %>%
    select(-orig_taz, -orig_purpose) %>%
    rename(taz = dest_taz, purpose = dest_purpose)
  # put them together and sort
  trip_points <- rbind(trips_dest_noint, trips_orig_noint, trips_orig_int, trips_dest_int) %>%
    select(-incQ,-incQ_label,-autoSuff,-autoSuff_label,-home_taz,-walk_subzone,-walk_subzone_label,
           -ptype,-ptype_label,-amode,-wlk_trip,-bik_trip,-wtr_trip,-dtr_trip)
  trip_points <- trip_points[order(trip_points$hh_id,
                                   trip_points$person_id,
                                   trip_points$tour_id,
                                   trip_points$depart_hour,
                                   trip_points$stop_id),]
  write.table(trip_points, file=file.path(UPDATED_DIR, "trip_points.csv"), sep=",", row.names=FALSE)
}
remove(trips)

save(tours, file=file.path(UPDATED_DIR, "tours.rdata"))
if (JUST_MES=="1") { write.table(tours, file=file.path(UPDATED_DIR, "tours.csv"), sep=",", row.names=FALSE) }
remove(tours)

save(households, file=file.path(UPDATED_DIR, "households.rdata"))
if (JUST_MES=="1") { write.table(households, file=file.path(UPDATED_DIR, "households.csv"), sep=",", row.names=FALSE) }
remove(households)


## Vehicle Miles Traveled

# maybe don't save/load but just keep it?  I started having memory problems though...
load(file=file.path(UPDATED_DIR,"trips.rdata"))
auto_trips <- subset(trips, trip_mode<=6)
remove(trips)

auto_trips <- mutate(auto_trips,
                     vmt_indiv=(num_participants==1)*(trip_mode==1)*distance +
                               (num_participants==1)*(trip_mode==2)*distance +
                               (num_participants==1)*(trip_mode==3)*(distance/2.0) +
                               (num_participants==1)*(trip_mode==4)*(distance/2.0) +
                               (num_participants==1)*(trip_mode==5)*(distance/3.25) +
                               (num_participants==1)*(trip_mode==6)*(distance/3.25),
                     vmt_joint=(num_participants>1)*(distance/num_participants),
                     vmt=vmt_indiv+vmt_joint,
                     person_trips=1,
                     vehicle_trips =((num_participants==1)*(trip_mode==1)*1.0 +
                                     (num_participants==1)*(trip_mode==2)*1.0 +
                                     (num_participants==1)*(trip_mode==3)*(1.0/2.0) +
                                     (num_participants==1)*(trip_mode==4)*(1.0/2.0) +
                                     (num_participants==1)*(trip_mode==5)*(1.0/3.25) +
                                     (num_participants==1)*(trip_mode==6)*(1.0/3.25) +
                                     (num_participants>1)*(1.0/num_participants)))

# sum them to hh_id, person_id
auto_trips_dcast <- summarise(group_by(auto_trips, hh_id, person_id),
                              vmt_indiv    = sum(vmt_indiv),
                              vmt_joint    = sum(vmt_joint),
                              vmt          = sum(vmt),
                              person_trips = sum(person_trips),
                              vehicle_trips= sum(vehicle_trips))

# add to persons so we get zero-vmt persons
load(file=file.path(UPDATED_DIR,"persons.rdata"))
persons          <- left_join(persons, auto_trips_dcast, by=c("hh_id","person_id"))
remove(auto_trips_dcast)
persons$vmt_indiv[is.na(persons$vmt_indiv)] <- 0
persons$vmt_joint[is.na(persons$vmt_joint)] <- 0
persons$vmt[is.na(persons$vmt)]             <- 0
persons$person_trips[is.na(persons$person_trips)]   <- 0
persons$vehicle_trips[is.na(persons$vehicle_trips)] <- 0

# add household vars
load(file=file.path(UPDATED_DIR,"households.rdata"))
persons          <- left_join(persons, select(households, hh_id, taz, COUNTY, county_name, SD,
                                              walk_subzone, walk_subzone_label,
                                              autoSuff, autoSuff_label),
                              by=c("hh_id"))
remove(households)

# added new person vars so save it
save(persons, file=file.path(UPDATED_DIR, "persons.rdata"))
if (JUST_MES=="1") { write.table(persons, file=file.path(UPDATED_DIR, "persons.csv"), sep=",", row.names=FALSE) }

vmt_summary      <- summarise(group_by(persons, COUNTY, county_name, SD, taz,
                                       walk_subzone, walk_subzone_label,
                                       ptype, ptype_label,
                                       autoSuff, autoSuff_label),
                              freq             = n(),
                              vmt_indiv        = mean(vmt_indiv),
                              vmt_joint        = mean(vmt_joint),
                              vmt              = mean(vmt),
                              person_trips     = sum(person_trips),
                              vehicle_trips    = sum(vehicle_trips))
vmt_summary$freq          <- vmt_summary$freq / SAMPLESHARE
vmt_summary$person_trips  <- vmt_summary$person_trips / SAMPLESHARE
vmt_summary$vehicle_trips <- vmt_summary$vehicle_trips / SAMPLESHARE
write.table(vmt_summary, file.path(RESULTS_DIR,"VehicleMilesTraveled.csv"), sep=",", row.names=FALSE)
model_summary <- vmt_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "VehicleMilesTraveled.rdata"))
remove(vmt_summary, model_summary)

## by household; remove ptype
vmt_summary      <- summarise(group_by(persons, COUNTY, county_name, SD, taz,
                                       walk_subzone, walk_subzone_label,
                                       autoSuff, autoSuff_label),
                              freq             = n_distinct(hh_id),
                              vmt_indiv        = mean(vmt_indiv),
                              vmt_joint        = mean(vmt_joint),
                              vmt              = mean(vmt),
                              person_trips     = sum(person_trips),
                              vehicle_trips    = sum(vehicle_trips))
vmt_summary$freq          <- vmt_summary$freq / SAMPLESHARE
vmt_summary$person_trips  <- vmt_summary$person_trips / SAMPLESHARE
vmt_summary$vehicle_trips <- vmt_summary$vehicle_trips / SAMPLESHARE
write.table(vmt_summary, file.path(RESULTS_DIR,"VehicleMilesTraveled_households.csv"), sep=",", row.names=FALSE)
model_summary <- vmt_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "VehicleMilesTraveled_households.rdata"))
remove(vmt_summary, model_summary)

# Vehicle Miles Travelef for Climate Action Plans Summary
mandatory_locations <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("wsLocResults_",ITER,".csv")),
                                         header=TRUE, sep=","))
# we only want work_locations to have hh_id, person_id, workLocation
work_locations      <- subset(mandatory_locations, WorkLocation>0)
remove(mandatory_locations)
work_locations      <- mutate(work_locations, hh_id=HHID, person_id=PersonID)
work_locations      <- select(work_locations, hh_id, person_id, WorkLocation)

# attach it to persons
load(file=file.path(UPDATED_DIR, "persons.rdata"))
persons             <- left_join(persons, work_locations, by=c("hh_id", "person_id"))
persons$WorkLocation[is.na(persons$WorkLocation)] <- 0    # change NA to 0
# save, since we added something (WorkLocation)
save(persons, file=file.path(UPDATED_DIR, "persons.rdata"))
if (JUST_MES=="1") { write.table(persons, file=file.path(UPDATED_DIR, "persons.csv"), sep=",", row.names=FALSE) }

# we only care about very specific vars
vmt_persons <- select(persons, hh_id, person_id, taz, COUNTY, county_name, WorkLocation)
remove(persons, work_locations)

# we want: orig_taz, dest_taz, WorkLocation -> #persons, vmt

# get the auto trips again
load(file=file.path(UPDATED_DIR,"trips.rdata"))
auto_trips <- subset(trips, trip_mode<=6)
remove(trips)
auto_trips <- mutate(auto_trips,
                     vmt_indiv=((num_participants==1)*(trip_mode==1)*distance +
                               (num_participants==1)*(trip_mode==2)*distance +
                               (num_participants==1)*(trip_mode==3)*(distance/2.0) +
                               (num_participants==1)*(trip_mode==4)*(distance/2.0) +
                               (num_participants==1)*(trip_mode==5)*(distance/3.25) +
                               (num_participants==1)*(trip_mode==6)*(distance/3.25))/SAMPLESHARE,
                     vmt_joint=(num_participants>1)*(distance/num_participants)/SAMPLESHARE,
                     vmt=(vmt_indiv+vmt_joint),
                     trips=1.0/SAMPLESHARE,
                     vehicle_trips =((num_participants==1)*(trip_mode==1)*1.0 +
                                     (num_participants==1)*(trip_mode==2)*1.0 +
                                     (num_participants==1)*(trip_mode==3)*(1.0/2.0) +
                                     (num_participants==1)*(trip_mode==4)*(1.0/2.0) +
                                     (num_participants==1)*(trip_mode==5)*(1.0/3.25) +
                                     (num_participants==1)*(trip_mode==6)*(1.0/3.25) +
                                     (num_participants>1)*(1.0/num_participants))/SAMPLESHARE)
auto_trips <- select(auto_trips, hh_id, person_id, orig_taz, dest_taz, vmt, vmt_indiv, vmt_joint, trips, vehicle_trips)
auto_trips <- left_join(auto_trips, select(vmt_persons, hh_id, person_id, taz, WorkLocation),
                        by=c("hh_id","person_id"))

# sum them to origin, destination, taz, WorkLocation
auto_trips_odhw <- summarise(group_by(auto_trips, orig_taz, dest_taz, taz, WorkLocation),
                             vmt_indiv     = sum(vmt_indiv),
                             vmt_joint     = sum(vmt_joint),
                             vmt           = sum(vmt),
                             trips         = sum(trips),
                             vehicle_trips = sum(vehicle_trips))
remove(auto_trips)


# save it
write.table(auto_trips_odhw, file.path(RESULTS_DIR,"AutoTripsVMT_perOrigDestHomeWork.csv"), sep=",", row.names=FALSE)
model_summary <- auto_trips_odhw # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "AutoTripsVMT_perOrigDestHomeWork.rdata"))
remove(auto_trips_odhw, model_summary)

# that was trips/vmt - we also want persons
person_hw_summary      <- summarise(group_by(vmt_persons, COUNTY, county_name, taz, WorkLocation),
                                    freq = n())
person_hw_summary$freq <- person_hw_summary$freq / SAMPLESHARE
write.table(person_hw_summary, file.path(RESULTS_DIR,"AutoTripsVMT_personsHomeWork.csv"), sep=",", row.names=FALSE)
model_summary <- person_hw_summary # name it generically for rdata
save(model_summary, file=file.path(RESULTS_DIR, "AutoTripsVMT_personsHomeWork.rdata"))
remove(person_hw_summary, model_summary)
