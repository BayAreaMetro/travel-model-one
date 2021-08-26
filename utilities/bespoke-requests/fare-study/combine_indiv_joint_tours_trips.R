# Simplified version of CoreSummaries.R, this script simply:
#
# 1) merges individual and joint tour files into a single file, updated_data/tours.rds
#   - each joint tour is represented once, with num_participants > 1
#   - adds columns num_participants, tour_participants from joint file
#   - drops columns person_type, atWork_freq
#   - adds columns income, incQ, incQ_label, (home) taz, (home) SD, (home) COUNTY, (home) county_name from household file / tazdata
#   - adds column fp_choice (free parking choice) from person file
#   - adds columns PRKCST, OPRKCST from tazdata for tour destination
#   - recodes simple_purpose categories based on tour_purpose
#   - calculates parking_rate based on tour_category, fp_choice
#   - calculates duration based on tour duration, parking_cost based on duration
#
# 2) merges individual and joint trip files into a single file, updated_data/trips.rds
#   - each joint trip is represented once *per participant*, so each trip is a person trip
#   - adds columns num_participants, tour_participants from joint file
#   - adds columns income, incQ, incQ_label, home_taz, from household file
#   - adds columns ptype, ptype_label, fp_choice from person file
#   - recodes columns timeCodeNum, timperiod_label, timeCode from depart_hour
#   - adds columns autoSuff, autoSuff_label based on household workers, and number of household autos
#   - adds column skims_mode based on trip_mode, selecting between drive-transit-walk or walk-transit-drive if the orig_purpose or dest_purpose is Home
#
# Required subfolders of the root folder where this will be run:
# "main" - only the files for the specified iteration are needed.  
# "popsyn"
# "landuse"
# "CTRAMP\scripts\block"

datestampr <- function(myusername = FALSE) {
    # returns something like 20210819_1723_lzorn
    # ignores args other than myusername

    datestampr <- format(Sys.time(), "%Y%m%d_%H%M")
    if (myusername) {
        datestampr <- paste0(datestampr,"_",Sys.getenv("USERNAME"))
    }
    return(datestampr)
}

library(scales)
library(tidyverse)
library(reshape2)
library(crayon)

  # Simplified version of CoreSummaries.R
  #
  # Required subfolders of the root folder where this will be run:
  # "main" - only the files for the specified iteration are needed.  
  # "popsyn"
  # "landuse"
  # "CTRAMP\scripts\block"
  
  # Core Summaries
  # Overhead
  
    datestring <- datestampr(myusername=FALSE)
    print(datestring)
    mylogfilename <- paste0("JoinSkimsStr_", datestring,".txt")
    sink()
    sink(mylogfilename, split=TRUE)
    cat(yellow(paste0("A log of the output will be saved to ", mylogfilename, ". \n \n")))
	
# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
	
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)


MAIN_DIR    <- file.path(TARGET_DIR,"main"           )
RESULTS_DIR <- file.path(TARGET_DIR,"core_summaries")
UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")

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

input.pop.households <- read.table(file = file.path(TARGET_DIR,"popsyn","hhFile.2015.csv"),
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
print(paste("Read household files; have",prettyNum(nrow(households),big.mark=","),"rows"))

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
input.pop.persons    <- read.table(file = file.path(TARGET_DIR,"popsyn","personFile.2015.csv"),
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
print(paste("Read persons files; have",prettyNum(nrow(persons),big.mark=","), "rows"))


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
indiv_tours     <- mutate(indiv_tours, tour_id=paste0("i",substr(tour_purpose,1,4),tour_id))

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
joint_tours     <- mutate(joint_tours, tour_id=paste0("j",substr(tour_purpose,1,4),tour_id))

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

# Data Reads: Trips

## Read Individual Trips and recode a few variables

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/IndividualTrip

indiv_trips     <- read.table(file=file.path(MAIN_DIR, paste0("indivTripData_",ITER,".csv")), header=TRUE, sep=",")
indiv_trips     <- select(indiv_trips, hh_id, person_id, person_num, tour_id, orig_taz, orig_walk_segment, dest_taz, dest_walk_segment,
                          trip_mode, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate, inbound) %>%
                   mutate(tour_id = paste0("i",substr(tour_purpose,1,4),tour_id))
print(paste("Read",prettyNum(nrow(indiv_trips),big.mark=","),"individual trips"))

## Data Reads: Joint Trips and recode a few variables

# The fields are documented here: https://github.com/BayAreaMetro/modeling-website/wiki/JointTrip
joint_trips     <- tbl_df(read.table(file=file.path(MAIN_DIR, paste0("jointTripData_",ITER,".csv")),
                                     header=TRUE, sep=","))
joint_trips     <- select(joint_trips, hh_id, tour_id, orig_taz, orig_walk_segment, dest_taz, dest_walk_segment, trip_mode,
                          num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, tour_category, avAvailable, sampleRate, inbound) %>%
                   mutate(tour_id = paste0("j",substr(tour_purpose,1,4),tour_id))

print(paste("Read",prettyNum(nrow(joint_trips),big.mark=","),
            "joint trips or ",prettyNum(sum(joint_trips$num_participants),big.mark=","),
            "joint person trips"))

## Add `num_participants` to joint_tours
joint_tours     <- left_join(joint_tours,
                             unique(select(joint_trips, hh_id, tour_id, num_participants)),
                             by=c("hh_id","tour_id"))

## Combine individual tours and joint tours together, keeping person_id, person_num, tour_participants for both
tours <- rbind(select(mutate(indiv_tours, tour_participants=as.character(person_num)), -person_type, -atWork_freq),
               select(mutate(joint_tours, person_id=0, person_num=0, fp_choice=0), -tour_composition))
print(paste("Combined indiv_tours (",prettyNum(nrow(indiv_tours),big.mark=","),"rows ) and joint_tours (",
      prettyNum(nrow(joint_tours),big.mark=","),"rows) into",
      prettyNum(nrow(tours),big.mark=","),"tours with columns",toString(colnames(tours))))
print(head(select(tours,hh_id,person_id,person_num,tour_id,num_participants,tour_participants),10))
print(tail(select(tours,hh_id,person_id,person_num,tour_id,num_participants,tour_participants),10))


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

  # Calculate the duration consistently with MtcModeChoiceDMU.java
  # https://github.com/BayAreaMetro/travel-model-one/blob/15dc6cdfd04e828cf319c21a4b7077ad3c7ca3e6/core/projects/mtc/src/java/com/pb/mtc/ctramp/MtcModeChoiceDMU.java#L83
  ftours   <- mutate(ftours, duration=end_hour-start_hour+1.0)

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
# becomes a row per partipant.  
# Inputs: joint_tours has columns tour_participants, hh_id, tour_id
#         persons has hh_id, person_num, person_id
# Returns table of person-tours, with columns hh_id, tour_id, tour_participants person_num, person_id
get_joint_tour_persons <- function(joint_tours, persons) {
  # tour participants are person ids separated by spaces -- create a table of hh_id, person_num for them
  joint_tour_persons <- data.frame(hh_id=numeric(), tour_id=numeric(), person_num=numeric())
  # unwind particpants into table with cols hh_id, tour_id, person_num1, person_num2, ...
  participants   <- strsplit(as.character(joint_tours$tour_participants)," ")
  max_peeps      <- max(sapply(participants,length))
  participants   <- lapply(participants, function(X) c(X,rep(NA, max_peeps-length(X))))
  participants   <- data.frame(t(do.call(cbind, participants)))
  participants   <- mutate(participants, hh_id=joint_tours$hh_id, tour_id=joint_tours$tour_id, tour_participants=joint_tours$tour_participants)
  print("get_join_tour_persons; head(participants):")
  print(head(participants))
  # melt the persons so they are each on their own row
  for (peep in 1:max_peeps) {
    jtp <- melt(participants, id.var=c("hh_id","tour_id","tour_participants"), measure.vars=paste0("X",peep), na.rm=TRUE)
    jtp <- mutate(jtp, person_num=value)
    jtp <- select(jtp, hh_id, tour_id, tour_participants, person_num)
    joint_tour_persons <- rbind(joint_tour_persons, jtp)
  }
  joint_tour_persons <- transform(joint_tour_persons, person_num=as.numeric(person_num))
  # sort by hh_id
  joint_tour_persons <- joint_tour_persons[with(joint_tour_persons, order(hh_id, tour_participants, tour_id)),]
  # merge with the persons to get the person_id
  joint_tour_persons <- left_join(joint_tour_persons, select(persons, hh_id, person_num, person_id), by=c("hh_id","person_num"))

  print("get_join_tour_persons; head(joint_tour_persons):")
  print(head(joint_tour_persons))
  return(joint_tour_persons)
}

joint_tour_persons <- get_joint_tour_persons(joint_tours, persons)

# attach persons to the joint_trips
joint_person_trips <- inner_join(joint_trips, joint_tour_persons, by=c("hh_id", "tour_id"))
# select out person_num and the person table columns
#joint_person_trips <- select(joint_person_trips, hh_id, person_id, tour_id, tour_participants, orig_taz, dest_taz, trip_mode,
#                             num_participants, tour_purpose, orig_purpose, dest_purpose, depart_hour, stop_id, avAvailable, sampleRate, inbound)

print(paste("Created joint_person_trips with",prettyNum(nrow(joint_person_trips),big.mark=","),"rows from",
      prettyNum(nrow(joint_trips),big.mark=","),"rows from joint_trips and",
      prettyNum(nrow(joint_tour_persons),big.mark=","),"rows from joint_tour_persons"))

# cleanup
remove(joint_trips,joint_tour_persons)

## Combine Individual Trips and Joint Person Trips
indiv_trips <- mutate(indiv_trips, num_participants=1, tour_participants=as.character(person_num))
print(toString(colnames(joint_person_trips)))
print(toString(colnames(indiv_trips)))
trips <- tbl_df(rbind(indiv_trips, joint_person_trips))
print(paste("Combined",prettyNum(nrow(indiv_trips),big.mark=","),
            "individual trips with",prettyNum(nrow(joint_person_trips),big.mark=","),
            "joint trips to make",prettyNum(nrow(trips),big.mark=",")," total trips with columns",toString(colnames(trips))))

remove(indiv_trips,joint_person_trips)

## Add Variables to Trips

# Add some variable to trips, such as:
#   * `timeCode`, a recoding of the `depart_hour` for joining skims
#   * `home_taz` from household table
#   * `incQ` and label from the household table
#   * `autoSuff` and label from the household table
#   * `walk_subzone` and label from the household table
#   * `ptype` and label, `fp_choice` from persons

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
                   select(persons, hh_id, person_id, ptype, ptype_label, fp_choice),
                   by=c("hh_id","person_id"))

		# need to reconcile this...

		# trip_mode	trip_mode_name
		# 1	Drive alone (single-occupant vehicles), not eligibile to use value toll facilities
		# 2	Drive alone (single-occupant), eligible to use value toll facilities
		# 3	Shared ride 2 (two-occupant vehicles), not eligibile to use value toll facilities
		# 4	Shared ride 2 (two-occupant vehicles), eligible to use value toll facilities
		# 5	Shared ride 3+ (three-or-more-occupant vehicles), not eligibile to use value toll facilities
		# 6	Shared ride 3+ (three-of-more occupant vehicles), eligible to use value toll facilities
		# 7	Walk the entire way (no transit, no bicycle)
		# 8	Bicycle the entire way (no transit)
		# 9	Walk to local bus
		# 10	Walk to light rail or ferry
		# 11	Walk to express bus
		# 12	Walk to heavy rail
		# 13	Walk to commuter rail
		# 14	Drive to local bus
		# 15	Drive to light rail or ferry
		# 16	Drive to express bus
		# 17	Drive to heavy rail
		# 18	Drive to commuter rail
		# 19	Taxi (added in Travel Model 1.5)
		# 20	TNC (Transportation Network Company, or ride-hailing services) - Single party (added in Travel Model 1.5)
		# 21	TNC - Shared e.g. sharing with strangers (added in Travel Model 1.5)
		
		# to this: 
		# da
		# daToll
		# s2
		# s2Toll
		# s3
		# s3Toll
		# walk
		# bike
		# wComW
		# wHvyW
		# wExpW
		# wLrfW
		# wLocW
		# wTrnW
		# dComW
		# dHvyW
		# dExpW
		# dLrfW
		# dLocW
		# dTrnW
		# wComD
		# wHvyD
		# wExpD
		# wLrfD
		# wLocD
		# wTrnD

		trips <- trips %>%
		  mutate(
		    
		    skims_mode = case_when(
		      
		      trip_mode == 1 ~ "da",
		      trip_mode == 2 ~ "daToll",
		      trip_mode == 3 ~ "s2",
		      trip_mode == 4 ~ "s2Toll",	 
		      trip_mode == 5 ~ "s3",
		      trip_mode == 6 ~ "s3Toll",	
		      trip_mode == 7 ~ "walk",
		      trip_mode == 8 ~ "bike",		        
		      trip_mode == 9 ~ "wLocW",	
		      trip_mode == 10 ~ "wLrfW",	
		      trip_mode == 11 ~ "wExpW",	
		      trip_mode == 12 ~ "wHvyW",	
		      trip_mode == 13 ~ "wComW",	
		      trip_mode == 14 & (orig_purpose == 'Home') ~ "dLocW",	
		      trip_mode == 15 & (orig_purpose == 'Home') ~ "dLrfW",	
		      trip_mode == 16 & (orig_purpose == 'Home') ~ "dExpW",	
		      trip_mode == 17 & (orig_purpose == 'Home') ~ "dHvyW",	
		      trip_mode == 18 & (orig_purpose == 'Home') ~ "dComW",
		      trip_mode == 14 & (dest_purpose == 'Home') ~ "wLocD",	
		      trip_mode == 15 & (dest_purpose == 'Home') ~ "wLrfD",	
		      trip_mode == 16 & (dest_purpose == 'Home') ~ "wExpD",	
		      trip_mode == 17 & (dest_purpose == 'Home') ~ "wHvyD",	
		      trip_mode == 18 & (dest_purpose == 'Home') ~ "wComD",	        
		      trip_mode == 19 ~ "Taxi",
		      trip_mode == 20 ~ "TNCa",
		      trip_mode == 21 ~ "TNCs",
		      TRUE ~ "Other"
		      
		    )
		    
		  )		  

num_tours       <- nrow(tours)
num_tours_dist  <- nrow( distinct(tours, hh_id, tour_participants, tour_id))
print(paste("num_tours",      prettyNum(num_tours,big.mark=",")))
print(paste("num_tours_dist", prettyNum(num_tours_dist,big.mark=",")))

## Add Tour Duration to Trips
print(paste("Before adding tour duration to trips -- have",prettyNum(nrow(trips),big.mark=","),"rows"))
# this will only work for individual tours since person_id is set
trips <- left_join(trips, select(tours, hh_id, tour_participants, tour_id, duration), by=c("hh_id", "tour_participants", "tour_id")) %>% 
  rename(tour_duration=duration)
print(paste("After adding tour duration to trips -- have",prettyNum(nrow(trips),big.mark=","),"rows"))

## Cleanup and save tours, trips and households
print(paste("Saving trips.rds with",prettyNum(nrow(trips),big.mark=","),"rows and",ncol(trips),"columns"))
saveRDS(trips, file=file.path(UPDATED_DIR, "trips.rds"))

print(paste("Saving tours.rds with",prettyNum(nrow(tours),big.mark=","),"rows and",ncol(tours),"columns"))
saveRDS(tours, file=file.path(UPDATED_DIR, "tours.rds"))
remove(tours)

print(paste("Saving households.rds with",prettyNum(nrow(households),big.mark=","),"rows and",ncol(households),"columns"))
save(households, file=file.path(UPDATED_DIR, "households.rds"))
remove(households)				
