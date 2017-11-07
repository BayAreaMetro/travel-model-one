
# Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))
library(plyr) # this must be first
library(dplyr)
library(reshape2)

# For RStudio, these can be set in the .Rprofile
MODEL_RUN    <- "2040_06_694"
TARGET_DIR   <- paste0("M:/Application/Model One/RTP2017/Scenarios/",MODEL_RUN,"/OUTPUT")
ITER         <- "3"
SAMPLESHARE  <- "0.50"
OUTPUT_DIR   <- file.path(TARGET_DIR,"bespoke")
OUTFILE      <- "trip-distance-bins-by-mode.csv"

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

# we only need some columns -- trip_mode, distance
trips <- select(trips, hh_id, person_id, trip_mode, distance)
# create distance rounded for bins
trips <- mutate(trips, distance_floor=floor(distance))

# count for each (distance_floor, trip_mode) and factor by SAMPLESHARE
trips_by_dist_mode <- dplyr::count(trips, distance_floor, trip_mode) %>% mutate(n = n/SAMPLESHARE)

write.table(trips_by_dist_mode, file.path(OUTPUT_DIR,OUTFILE), sep=",", row.names=FALSE)