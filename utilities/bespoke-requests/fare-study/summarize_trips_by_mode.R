#
# Aggregate/summarize by mode
# Input:  updated_data/trips_with_skims.rds
# Output: updated_data/tris_by_mode_summaries.rds
#
library(tidyverse)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
    
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")

trips_with_skims <- readRDS(file=file.path(UPDATED_DIR, "trips_with_skims.rds"))

print(str(trips_with_skims))

trip_summary <- trips_with_skims %>% 
                group_by(trip_mode) %>%
                summarize(trips    = n(),
                          fare     = mean(fare,     na.rm=TRUE),
                          ivt      = mean(ivt,      na.rm=TRUE),
                          distance = mean(distance, na.rm=TRUE),
                          # transit specific
                          walktime = mean(walktime, na.rm=TRUE),
                          boards   = mean(boards,   na.rm=TRUE)) %>%
                mutate(revenue=trips*fare)

print(paste("Saving trip_mode_summary.csv with",nrow(trip_summary),"rows"))
write.csv(trip_summary, file=file.path(UPDATED_DIR, "trip_summary.csv"), row.names=FALSE)
