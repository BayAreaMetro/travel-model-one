library(dplyr)
library(stringr)

load('M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_16/OUTPUT/updated_output/trips.rdata')

trips['trip_cnt'] <- trips['num_participants']/trips['sampleRate']

trips['trip_mode_category'] <- trips['trip_mode']
trips <- trips %>%
  mutate(trip_mode_category = trip_mode) %>%
  mutate(trip_mode_category = ifelse(trip_mode %in% c(1, 2),
                                     'Drive Alone',
                                     ifelse(trip_mode %in% c(3, 4, 5, 6),
                                            'Carpool',
                                            ifelse(trip_mode==7,
                                                   'Walk',
                                                   ifelse(trip_mode==8,
                                                          'Bike',
                                                          ifelse(trip_mode %in% c(9, 10, 11, 12, 13),
                                                                 'Walk to Transit',
                                                                 ifelse(trip_mode %in% c(14, 15, 16, 17, 18),
                                                                        'Drive to Transit',
                                                                        ifelse(trip_mode %in% c(19, 20, 21),
                                                                               'Taxi or TNC',
                                                                               trip_mode_category))))))))


trips_summary <- trips %>%
  dplyr::group_by(orig_taz, dest_taz, trip_mode_category, timeperiod_label) %>%
  dplyr::summarize(Number_trips = sum(trip_cnt))

write.csv(trips_summary, 'M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_16/OUTPUT/updated_output/trips_OD_summary.csv', row.names = FALSE)
