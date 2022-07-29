# Script to read trip.rdata files from two model runs, clean the tables, and 
# append them to a single csv output table.
#
# Requires directories for the two model runs and the output table to be defined
# externally as MODEL_RUN_DIR1, MODEL_RUN_DIR2, and OUTPUT_DIR.

library(dplyr)

# Load and clean trips table from first model run
MODEL_RUN_DIR1 <- Sys.getenv("MODEL_RUN_DIR1")
MODEL_RUN_DIR1 <- gsub("\\\\","/",MODEL_RUN_DIR1) # switch slashes around

trips_path1 <- paste(MODEL_RUN_DIR1, "OUTPUT", "updated_output", 
                     "trips.rdata", sep = "/")
model_run1 <- gsub("^.*?NextGenFwys/","",MODEL_RUN_DIR1)
load(trips_path1)
trips1 <- get("trips")
trips1 <- trips1 %>% select('orig_taz', 'dest_taz', 'trip_mode',
                            'timeperiod_label', 'incQ_label')
trips1$model_run <- rep(model_run1, nrow(trips1))

print(paste(model_run1,"successfully loaded and cleaned.", sep = " "))

# Load and clean trips table from second model run
MODEL_RUN_DIR2 <- Sys.getenv("MODEL_RUN_DIR2")
MODEL_RUN_DIR2 <- gsub("\\\\","/",MODEL_RUN_DIR2) # switch slashes around

trips_path2 <- paste(MODEL_RUN_DIR2, "OUTPUT", "updated_output",
                    "trips.rdata", sep = "/")
model_run2 <- gsub("^.*?NextGenFwys/","",MODEL_RUN_DIR2)
load(trips_path2)
trips2 <- get("trips")
trips2 <- trips2 %>% select('orig_taz', 'dest_taz', 'trip_mode',
                           'timeperiod_label', 'incQ_label')
trips2$model_run <- rep(model_run2, nrow(trips2))

print(paste(model_run2,"successfully loaded and cleaned.", sep = " "))

# Append second trips table to first
output_tb <- rbind(trips1, trips2)

# Save combined table to csv
OUTPUT_DIR <- Sys.getenv("OUTPUT_DIR")
OUTPUT_DIR <- gsub("\\\\","/",OUTPUT_DIR) # switch slashes around

write.csv(output_tb, paste(OUTPUT_DIR, "trips_tb_combined.csv", sep = "/"))

