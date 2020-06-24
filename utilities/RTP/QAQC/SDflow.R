library(tidyverse)

# user input
# run_id <- "2050_TM152_DBP_NoProject_08"
run_id <- "2050_TM152_DBP_PlusCrossing_08"

PBA50Location <- "M:/Application/Model One/RTP2021/Blueprint/"
trip_file    <- file.path(PBA50Location, run_id, "OUTPUT/updated_output", "trips.rdata")
load(trip_file)

geography_csv <- "C:/Users/ftsang/Documents/GitHub/travel-model-one/utilities/geographies/taz-superdistrict-county.csv"
geography_df  <- read.csv(file=geography_csv, header=TRUE, sep=",")

trips <- trips %>% left_join(geography_df,
                            by=c("orig_taz"="ZONE"))

trips <- trips %>% left_join(geography_df,
                            by=c("dest_taz"="ZONE"))

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


od_District_mode17_commute_df <- trips  %>%
                    group_by(SD_orig, SD_dest) %>%
                    filter(trip_mode==17) %>%   
                    filter(tour_purpose=="work_low" | tour_purpose=="work_med" | tour_purpose=="work_high" | tour_purpose=="work_very high" | tour_purpose=="university" | tour_purpose=="school_high" | tour_purpose=="school_grade") %>% 
                    summarise(num_trips = sum(num_participants/sampleRate),
                              avg_dist  = mean(distance))

od_Districtmx_mode17_commute_df <- od_District_mode17_commute_df %>%
  group_by(SD_orig, SD_dest) %>%
  summarise(var=sum(num_trips))%>%
  spread(SD_dest, var)
# %>%
#  kable()

od_Distancemx_mode17_commute_df <- od_District_mode17_commute_df %>%
  group_by(SD_orig, SD_dest) %>%
  summarise(var=sum(avg_dist))%>%
  spread(SD_dest, var)
# %>%
#  kable()

# replace na with 0
od_Districtmx_mode17_commute_df[is.na(od_Districtmx_mode17_commute_df)] = 0

OUTFILE1    <- file.path(PBA50Location, run_id, "OUTPUT/updated_output", "od_District_commute_mode17.csv")
write.csv(od_District_mode17_commute_df, OUTFILE1, row.names = FALSE)

OUTFILE2    <- file.path(PBA50Location, run_id, "OUTPUT/updated_output", "od_Districtmx_commute_mode17.csv")
write.csv(od_Districtmx_mode17_commute_df, OUTFILE2, row.names = FALSE)

OUTFILE3    <- file.path(PBA50Location, run_id, "OUTPUT/updated_output", "od_Distancemx_commute_mode17.csv")
write.csv(od_Distancemx_mode17_commute_df, OUTFILE3, row.names = FALSE)

