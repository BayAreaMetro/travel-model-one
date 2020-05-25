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

# Get model run sampleshare for later weighting of trips

sampleshare <- as.numeric(Sys.getenv("sampleshare"))
weight      <- 1/sampleshare

# Occupancy Assumptions for TNC single and shared vehicles
# https://github.com/BayAreaMetro/travel-model-one/blob/master/config/params_PBA50_Blueprint2050.properties#L116

single.da.share = 0.53      # Share of single-passenger rides for non-shared TNCs
single.s2.share = 0.29      # Share of 2-passenger rides for non-shared TNCs
single.s3.share = 0.18      # Share of 3plus-passenger rides for non-shared TNCs

shared.da.share = 0.09      # Share of single-passenger rides for shared TNCs
shared.s2.share = 0.29      # Share of 2-passenger rides for shared TNCs
shared.s3.share = 0.62      # Share of 2-passenger rides for shared TNCs

# Average occupancy for 3-plus rides, single and shared TNC trips
# https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/metrics/sumAutoTimes.job#L192

single3p        = 3.60      # Average occupancy for 3-plus passenger non-shared TNCs
shared3p        = 3.83      # Average occupancy for 3-plus passenger shared TNCs

# PMT to VMT conversion factors for single and shared TNC trips

single_factor   = single.da.share*1 + single.s2.share*2 + single.s3.share*single3p
shared_factor   = shared.da.share*1 + shared.s2.share*2 + shared.s3.share*shared3p

# Bring in trips and subset needed variables, filter only TNC trips

load(trips_location)

trips_TNC <- trips %>% 
  select(trip_mode,distance) %>%                # Mode and distance are only needed variables
  filter(trip_mode %in% c(20,21))               # TNC single-party and shared, respecively

# Summarize totals by TNC mode, applying weight that corrects for sampleshare

temp1 <- trips_TNC %>%                                   
  group_by(trip_mode) %>%                               # Sum trips by TNC mode
  summarize(pmt=sum(distance*weight)) %>%               # Apply weight from sampleshare
  spread(trip_mode,pmt) %>%                             # List to matrix format
  rename(TNC_Single_PMT="20",TNC_Shared_PMT="21")       # Rename variable names from mode values

# Calculate VMT from PMT

final <- temp1 %>% mutate(
  TNC_Single_VMT = TNC_Single_PMT/single_factor,        # Single PMT divided by single factor = single VMT
  TNC_Shared_VMT = TNC_Shared_PMT/shared_factor,        # Shared PMT divided by shared factor = shared VMT
  TNC_Total_VMT  = TNC_Single_VMT + TNC_Shared_VMT,     # Combined total of single and shared TNC VMT
  ZPV_VMT        = TNC_Total_VMT*0.7                    # ZPV factor for TNC VMT
) %>% 
  mutate_if(is.numeric, round,0)                        # Round all numeric values to ones place

write.csv(final,OUTPUT_FILE,row.names = FALSE,quote=T)




