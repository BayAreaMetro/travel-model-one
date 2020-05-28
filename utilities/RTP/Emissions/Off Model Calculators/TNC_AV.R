# TNC_AV.R
# Script to output TNC and AV PMT and VMT
# SI

# Import libraries

suppressMessages(library(tidyverse))

# Set up directories

MODEL_DATA_BASE_DIR <-"M:/Application/Model One/RTP2021/IncrementalProgress"
Box_H               <-file.path(gsub("\\\\","/", Sys.getenv("USERPROFILE")),"Box")
OUTPUT_DIR          <-file.path(Box_H,"Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation/Incremental Progress/ModelData")
OUTPUT_FILE         <-file.path(OUTPUT_DIR, "Model Data - TNC_AV.csv")
trips_location      <-file.path(MODEL_DATA_BASE_DIR,"2035_TM152_IPA_aoc1795_00/OUTPUT/updated_output/trips.rdata") 

# this is the currently running script

SCRIPT     <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/TNC_AV.R"

# the model runs are in the parent folder

model_runs <- read.table(file.path(dirname(SCRIPT),"..","ModelRuns_RTP2021.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# Read trips.rdata for respective scenarios and summarize important variables, appending each new scenario
# Start with empty data frame

tripdata_df          <- data.frame()

for (i in 1:nrow(model_runs)) {
  
# Bring in parameters file, search for TNC occupancy assumptions and TNC zero-passenger vehicle multiplier
# Grep Fn separates string into two, extracts the second element (after the equals sign,the parameter of interest)
  
    params <- readLines(file.path(MODEL_DATA_BASE_DIR,model_runs[i,"directory"],"INPUT","params.properties"))
    
    single.da.share  <- as.numeric(str_split_fixed(grep("TNC.single.da.share",params,value=TRUE),"=",n=2)[2])
    single.s2.share  <- as.numeric(str_split_fixed(grep("TNC.single.s2.share",params,value=TRUE),"=",n=2)[2])
    single.s3.share  <- as.numeric(str_split_fixed(grep("TNC.single.s3.share",params,value=TRUE),"=",n=2)[2])
    
    shared.da.share  <- as.numeric(str_split_fixed(grep("TNC.shared.da.share",params,value=TRUE),"=",n=2)[2])
    shared.s2.share  <- as.numeric(str_split_fixed(grep("TNC.shared.s2.share",params,value=TRUE),"=",n=2)[2])
    shared.s3.share  <- as.numeric(str_split_fixed(grep("TNC.shared.s3.share",params,value=TRUE),"=",n=2)[2])
      
    single.s3.occ    <- as.numeric(str_split_fixed(grep("TNC.single.s3.occ",params,value=TRUE),"=",n=2)[2])
    shared.s3.occ    <- as.numeric(str_split_fixed(grep("TNC.shared.s3.occ",params,value=TRUE),"=",n=2)[2])
    
    TNC_ZPV_fac      <- as.numeric(str_split_fixed(grep("TNC_ZPV_fac",params,value=TRUE),"=",n=2)[2])
    
# PMT to VMT conversion factors for single and shared TNC trips
    
    single_factor   = single.da.share*1 + single.s2.share*2 + single.s3.share*single.s3.occ
    shared_factor   = shared.da.share*1 + shared.s2.share*2 + shared.s3.share*shared.s3.occ    

# Now bring in trip file for respective scenarios and perform summaries, then append and repeat until done
    
    trip_file          <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","updated_output","trips.rdata")
    load(trip_file)                                         
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
    
  tripdata_df        <- rbind(tripdata_df, trip_file_df)    # Append
}

# Remove i and large trip files, output file

rm(i, trips, trip_file_df)

write.csv(tripdata_df,OUTPUT_FILE,row.names = FALSE,quote=T)





