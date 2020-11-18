# TNC_AV.R
# Script to output TNC and AV PMT and VMT
# SI

# Import libraries

suppressMessages(library(tidyverse))
library(reshape2)
options(width = 180)

# Set up directories

USERNAME            <- Sys.getenv("USERNAME")
BOX_BASE_DIR        <- file.path("C:/Users", USERNAME, "Box/Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation")
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         FinalBlueprint="M:/Application/Model One/RTP2021/Blueprint")
OUTPUT_DIR          <- file.path(BOX_BASE_DIR, "Final Blueprint/OffModel_FBP/ModelData")
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - TNC_AV.csv")

# this is the currently running script
SCRIPT     <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/TNC_AV.R"
# the model runs are RTP/ModelRuns.csv
model_runs          <- read.table(file.path(dirname(SCRIPT),"..","..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# filter to the current runs
model_runs          <- model_runs[ which(model_runs$status == "current"), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# Read trips.rdata for respective scenarios and summarize important variables, appending each new scenario
# Start with empty data frame

tripdata_df          <- data.frame()

for (i in 1:nrow(model_runs)) {
  
    if (model_runs[i,"year"]<2015){next}  # TNCs don't exist in years prior to 2015, so skip those model runs to avoid conflicts
    MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
    print(paste("Processing",model_runs[i,"directory"]))

# Bring in parameters file, search for TNC occupancy assumptions and TNC zero-passenger vehicle multiplier
# Grep Fn separates string into two, extracts the second element (after the equals sign,the parameter of interest)
  
    param_file <- file.path(MODEL_DATA_BASE_DIR,model_runs[i,"directory"],"INPUT","params.properties")
    params <- readLines(param_file)
    
    single.da.share  <- as.numeric(str_split_fixed(grep("TNC.single.da.share",params,value=TRUE),"=",n=2)[2])
    single.s2.share  <- as.numeric(str_split_fixed(grep("TNC.single.s2.share",params,value=TRUE),"=",n=2)[2])
    single.s3.share  <- as.numeric(str_split_fixed(grep("TNC.single.s3.share",params,value=TRUE),"=",n=2)[2])
    
    shared.da.share  <- as.numeric(str_split_fixed(grep("TNC.shared.da.share",params,value=TRUE),"=",n=2)[2])
    shared.s2.share  <- as.numeric(str_split_fixed(grep("TNC.shared.s2.share",params,value=TRUE),"=",n=2)[2])
    shared.s3.share  <- as.numeric(str_split_fixed(grep("TNC.shared.s3.share",params,value=TRUE),"=",n=2)[2])
      
    single.s3.occ    <- as.numeric(str_split_fixed(grep("TNC.single.s3.occ",params,value=TRUE),"=",n=2)[2])
    shared.s3.occ    <- as.numeric(str_split_fixed(grep("TNC.shared.s3.occ",params,value=TRUE),"=",n=2)[2])
    
    # print(paste("single.s3.occ:",single.s3.occ,"; shared.s3.occ:",shared.s3.occ))

    if (is.na(single.s3.occ)) {
      single.s3.occ <- 3.6
      print(paste("  TNC.single.s3.occ not found in",param_file,"; assuming",single.s3.occ))
    }
    if (is.na(shared.s3.occ)) {
      shared.s3.occ <- 3.83
      print(paste("  TNC.shared.s3.occ not found in",param_file,"; assuming",shared.s3.occ))
    }

    TNC_ZPV_fac      <- as.numeric(str_split_fixed(grep("TNC_ZPV_fac",params,value=TRUE),"=",n=2)[2])

    
# PMT to VMT conversion factors for single and shared TNC trips
    
    single_factor   = single.da.share*1 + single.s2.share*2 + single.s3.share*single.s3.occ
    shared_factor   = shared.da.share*1 + shared.s2.share*2 + shared.s3.share*shared.s3.occ
    print(paste("  single_factor=", single_factor, "and shared_factor=",shared_factor))

# Now bring in trip file for respective scenarios and perform summaries, then append and repeat until done
    
    trip_file          <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","updated_output","trips.rdata")
    load(trip_file)

    if ("sampleRate" %in% colnames(trips) == FALSE) {
      print(paste("sampleRate not found in",trip_file,"; assuming 0.5"))
      trips['sampleRate'] = 0.5
    }

    trip_file_df       <- trips %>%                         # "trips" comes from native name of loaded .rdata dataset
      select(trip_mode,distance,sampleRate) %>%             # Mode, distance, and sampleRate are only needed variables
      filter(trip_mode %in% c(20,21)) %>%                   # TNC single-party and shared, respectively
      group_by(trip_mode) %>%                               # Sum trips by TNC mode
      summarize(pmt=sum(distance*1/sampleRate)) %>%         # Apply weight, which is the inverse of sampleRate
      spread(trip_mode,pmt) %>%                             # List to matrix format
      rename(TNC_Single_PMT="20",TNC_Shared_PMT="21") %>%   # Rename variable names from mode values
      mutate(                                               # Add VMT values
          TNC_Single_VMT = TNC_Single_PMT/single_factor,        # Single PMT divided by single factor = single VMT
          TNC_Shared_VMT = TNC_Shared_PMT/shared_factor,        # Shared PMT divided by shared factor = shared VMT
          TNC_Total_VMT  = TNC_Single_VMT + TNC_Shared_VMT,     # Combined total of single and shared TNC VMT
          ZPV_VMT        = TNC_Total_VMT*TNC_ZPV_fac            # Zero passenger vehicle factor for TNC VMT
        ) %>% 
      mutate_if(is.numeric, round,0) %>%                    # Round all numeric values to ones place
      mutate(
           year      = model_runs[i,"year"],                # Now append scenario variables
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
    
  tripdata_df        <- rbind(tripdata_df, trip_file_df)    # Accumulate data frames into a single one
}

# Remove large trip files, then output file

rm(trips, trip_file_df)

# columns are: year, category, directory, variable, value
summary_melted_df <- melt(tripdata_df, id.vars=c("year","category","directory"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","variable","value")]
# print(summary_melted_df)

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)





