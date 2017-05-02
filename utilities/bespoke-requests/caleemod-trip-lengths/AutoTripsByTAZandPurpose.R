
# Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))
library(plyr) # this must be first
library(dplyr)
library(reshape2)

# For RStudio, these can be set in the .Rprofile
MODEL_RUN    <- "2010_06_003"
TARGET_DIR   <- paste0("M:/Application/Model One/RTP2017/Scenarios/",MODEL_RUN,"/OUTPUT")
ITER         <- "3"
SAMPLESHARE  <- "1.00"
OUTPUT_DIR   <- "M:/Data/CalEEMod"

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
OUTPUT_DIR   <- gsub("\\\\","/",OUTPUT_DIR) # switch slashes around


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
trips <- select(trips, hh_id, person_id, home_taz, tour_purpose, trip_mode, num_participants, distance)

# we want: home taz, purpose -> vehicle trips, vehicle trip dist

# get the auto trips only
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

# sum them to origin, destination, taz, WorkLocation
auto_trips_summary <- summarise(group_by(auto_trips, home_taz, tour_purpose),
                             vmt           = sum(vmt),
                             trips         = sum(trips),
                             vehicle_trips = sum(vehicle_trips))
remove(auto_trips)

# save it
OUTFILE <- paste0("AutoTripsByTAZandPurpose_",MODEL_RUN,".csv")
write.table(auto_trips_summary, file.path(OUTPUT_DIR,OUTFILE), sep=",", row.names=FALSE)
