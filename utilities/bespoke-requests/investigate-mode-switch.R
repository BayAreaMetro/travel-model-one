library(dplyr)
library(tidyr)

#
# load base trips
load("A:/Projects/2050_TM151_PPA_CG_02/updated_output/trips.rdata")
base_trips <- trips
remove(trips)

# summarize to AM trips by transit
base_am_transit_trips <- filter(base_trips, timeperiod_label=="AM Peak") %>%
  filter(trip_mode >= 9 ) %>%
  filter(trip_mode <= 18 ) %>% 
  mutate(simple_mode = case_when(trip_mode== 9 ~ "base_local",
                                 trip_mode==10 ~ "base_lrf",
                                 trip_mode==11 ~ "base_express",
                                 trip_mode==12 ~ "base_heavy",
                                 trip_mode==13 ~ "base_commuter",
                                 trip_mode==14 ~ "base_local",
                                 trip_mode==15 ~ "base_lrf",
                                 trip_mode==16 ~ "base_express",
                                 trip_mode==17 ~ "base_heavy",
                                 trip_mode==18 ~ "base_commuter"))

base_am_transit_trips_agg <- group_by(base_am_transit_trips, orig_taz, dest_taz, simple_mode) %>% 
  summarise(n = n()) %>% 
  spread(key=simple_mode, value=n, fill=0)


#
# load build trips
load("F:/Projects/2050_TM151_PPA_CG_02_21021_El_Camino_Real_BRT_test_00/updated_output/trips.rdata")
build_trips <- trips
remove(trips)

# summarize to AM trips by transit
build_am_transit_trips <- filter(build_trips, timeperiod_label=="AM Peak") %>%
  filter(trip_mode >= 9 ) %>%
  filter(trip_mode <= 18 ) %>% 
  mutate(simple_mode = case_when(trip_mode== 9 ~ "build_local",
                                 trip_mode==10 ~ "build_lrf",
                                 trip_mode==11 ~ "build_express",
                                 trip_mode==12 ~ "build_heavy",
                                 trip_mode==13 ~ "build_commuter",
                                 trip_mode==14 ~ "build_local",
                                 trip_mode==15 ~ "build_lrf",
                                 trip_mode==16 ~ "build_express",
                                 trip_mode==17 ~ "build_heavy",
                                 trip_mode==18 ~ "build_commuter"))

build_am_transit_trips_agg <- group_by(build_am_transit_trips, orig_taz, dest_taz, simple_mode) %>% 
  summarise(n = n()) %>% 
  spread(key=simple_mode, value=n, fill=0)

###################################

am_transit_trips_agg <- merge(base_am_transit_trips_agg, build_am_transit_trips_agg)

# of interest -- express bus increase, BART decrease
am_trips_focus <- filter(am_transit_trips_agg, build_express > base_express) %>% 
  filter( build_heavy < base_heavy) %>%
  mutate(switchers = (build_express-base_express)+(base_heavy-build_heavy))

