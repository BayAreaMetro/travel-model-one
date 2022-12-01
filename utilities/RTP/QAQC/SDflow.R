# this script processes the trips.rdata file into a matrix format
# I usually just run this from RStudio
# for commute only for now (although this can be easily changed by modifying the filter)


library(tidyverse)

# remove existing variables from the r environment
rm(list=ls())


# -----------
# user inputs
# -----------

# specify project name
project <- 'Blueprint'
project <- 'NGF'

if (project == 'Blueprint') {
  output_dir <- "M:/Application/Model One/RTP2021/Blueprint/"
} else if (project == 'NGF') {
  output_dir <- "L:/Application/Model_One/NextGenFwys/Scenarios"
}

# specify run id
#run_id <- "2050_TM152_DBP_PlusCrossing_08"
run_id <- "2035_TM152_NGF_NP02"

# specify the modes to calculate. Mode dictionary: https://github.com/BayAreaMetro/modeling-website/wiki/TravelModes#tour-and-trip-modes
# selected_mode <- 1      # Walk to express bus
# selected_mode <- 12      # Walk to BART
# selected_mode <- 16      # Drive to express bus
selected_modes <- c(1, 2, 3, 4, 5, 6)

# specify tour purposes to include
tour_purposes <- c("work_low", "work_med", "work_high", "work_very high", "university", "school_high", "school_grade")

# -----------
# processing the trip file
# -----------

trip_file    <- file.path(output_dir, run_id, "OUTPUT/updated_output", "trips.rdata")
load(trip_file)

taz_superdistrict_county_csv <- "//mainmodel/MainModelShare/travel-model-one-master/utilities/geographies/taz-superdistrict-county.csv"
taz_superdistrict_county_df  <- read.csv(file=taz_superdistrict_county_csv, header=TRUE, sep=",")

superdistrict_county_csv <- "//mainmodel/MainModelShare/travel-model-one-master/utilities/geographies/superdistrict-county.csv"
superdistrict_county_df  <- read.csv(file=superdistrict_county_csv, header=TRUE, sep=",")

print(colnames(trips))

trips <- trips %>% left_join(taz_superdistrict_county_df,
                             by=c("orig_taz"="ZONE"))
print(colnames(trips))
trips <- trips %>% left_join(taz_superdistrict_county_df,
                             by=c("dest_taz"="ZONE"))
print(colnames(trips))
trips <- trips %>% 
  rename(
    SD_orig              = SD.x,
    COUNTY_orig          = COUNTY.x,
    SD_NAME_orig         = SD_NAME.x,
    COUNTY_NAME_orig     = COUNTY_NAME.x,
    SD_NUM_NAME_orig     = SD_NUM_NAME.x,
    COUNTY_NUM_NAME_orig = COUNTY_NUM_NAME.x,
    SD_dest              = SD.y,
    COUNTY_dest          = COUNTY.y,
    SD_NAME_dest         = SD_NAME.y,
    COUNTY_NAME_dest     = COUNTY_NAME.y,
    SD_NUM_NAME_dest     = SD_NUM_NAME.y,
    COUNTY_NUM_NAME_dest = COUNTY_NUM_NAME.y
  )
print(colnames(trips))
for (selected_mode in selected_modes) {
  
  print(selected_mode)
  
  od_SDflow_1mode_commute_df <- trips  %>%
    group_by(SD_orig, SD_dest) %>%
    filter(trip_mode==selected_mode) %>%   
    filter(tour_purpose %in% tour_purposes) %>% 
    summarise(num_trips = sum(num_participants/sampleRate),
              avg_dist  = mean(distance))
  
  # make sure all SDs are listed
  od_SDflow_1mode_commute_df <- od_SDflow_1mode_commute_df %>% full_join(superdistrict_county_df,
                                                                         by=c("SD_orig"="SD"))
  
  od_SDflow_1mode_commute_df <- od_SDflow_1mode_commute_df %>% full_join(superdistrict_county_df,
                                                                         by=c("SD_dest"="SD"))
  
  od_SDflow_1mode_commute_df <- od_SDflow_1mode_commute_df %>% 
    rename(
      COUNTY_orig          = COUNTY.x,
      SD_NAME_orig         = SD_NAME.x,
      COUNTY_NAME_orig     = COUNTY_NAME.x,
      SD_NUM_NAME_orig     = SD_NUM_NAME.x,
      COUNTY_NUM_NAME_orig = COUNTY_NUM_NAME.x,
      COUNTY_dest          = COUNTY.y,
      SD_NAME_dest         = SD_NAME.y,
      COUNTY_NAME_dest     = COUNTY_NAME.y,
      SD_NUM_NAME_dest     = SD_NUM_NAME.y,
      COUNTY_NUM_NAME_dest = COUNTY_NUM_NAME.y
    )
  # add run id and mode
  od_SDflow_1mode_commute_df$runID <- run_id
  od_SDflow_1mode_commute_df$modeID <- selected_mode
  
  # convert to matrix format
  od_SDflowMX_1mode_commute_df <- od_SDflow_1mode_commute_df %>%
    group_by(SD_orig, SD_dest) %>%
    summarise(var=sum(num_trips))%>%
    spread(SD_dest, var)
  # %>%
  #  kable()
  
  od_DistanceMX_1mode_commute_df <- od_SDflow_1mode_commute_df %>%
    group_by(SD_orig, SD_dest) %>%
    summarise(var=sum(avg_dist))%>%
    spread(SD_dest, var)
  # %>%
  #  kable()
  
  # replace na with 0
  od_SDflowMX_1mode_commute_df[is.na(od_SDflowMX_1mode_commute_df)] = 0
  
  # if not include run_id in file name
  #OUTFILE1    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_SDflow_commute_mode", selected_mode, ".csv", sep = ""))
  # if include run_id in file name
  OUTFILE1    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_SDflow_commute_mode", selected_mode, "_", run_id, ".csv", sep = ""))
  write.csv(od_SDflow_1mode_commute_df, OUTFILE1, row.names = FALSE)
  
  #OUTFILE2    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_SDflowMX_commute_mode", selected_mode, ".csv", sep = ""))
  OUTFILE2    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_SDflowMX_commute_mode", selected_mode, "_", run_id, ".csv", sep = ""))
  write.csv(od_SDflowMX_1mode_commute_df, OUTFILE2, row.names = FALSE)
  
  #OUTFILE3    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_DistanceMX_commute_mode", selected_mode, ".csv", sep = ""))
  OUTFILE3    <- file.path(output_dir, run_id, "OUTPUT/updated_output", paste("od_DistanceMX_commute_mode", selected_mode, "_", run_id, ".csv", sep = ""))
  write.csv(od_DistanceMX_1mode_commute_df, OUTFILE3, row.names = FALSE)
  
}


