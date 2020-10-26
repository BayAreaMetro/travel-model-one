#
#
# tallyParking.R
#
# Tallies parking metrics for tours and trips using richer (CoreSummaries-produced) tour and trip data
# Run from model directory after CoreSummaries.R
library(dplyr)

# read tours and tazdata
TAZDATA_FILE      <- file.path("landuse","tazData.csv")
tazData           <- read.table(file=TAZDATA_FILE, header=TRUE, sep=",")
names(tazData)    <- toupper(names(tazData))
print(paste("Read",nrow(tazData),"rows from",TAZDATA_FILE))

load("updated_output/tours.rdata")

# filter to auto tours
tours <- filter(tours, (tour_mode >= 1)&(tour_mode <= 6))

# add orig_COUNTY
tours <- left_join(tours, rename(select(tazData, ZONE, COUNTY), orig_taz=ZONE, orig_COUNTY=COUNTY))

# parking_rate includes free parking for fp_choice work tours
# temporary: undo dividing parking cost amonst SR,SR3
tours <- mutate(tours, 
                tour_duration=end_hour-start_hour,
                indiv_joint = substr(tour_id,1,1),
                parking_cost_test = parking_rate*tour_duration*num_participants )

# convert to dollars
tours <- mutate(tours, parking_cost_test = parking_cost_test*0.01)

# parking_cost is already included so just summarize
tours <- mutate(tours, work_nonwork=ifelse(substr(tour_purpose,1,5)=='work_','Work','Non-Work'))

tour_parking_summary <- group_by(tours, work_nonwork, orig_COUNTY, dest_COUNTY) %>% 
  summarise(parking_cost = sum(parking_cost),
            parking_cost_test = sum(parking_cost_test),
            num_tours = n())

tour_parking_file <- file.path("metrics","parking_costs_tour.csv")
write.table(tour_parking_summary, tour_parking_file, sep=",", row.names=FALSE)
