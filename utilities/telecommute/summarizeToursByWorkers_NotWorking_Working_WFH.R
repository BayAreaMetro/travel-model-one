# Quick script to look at tours and trips per person including person type, income quartile, wfh choice and work location
# See Summarize tours per worker by work/WFH/not working (https://app.asana.com/0/1204085012544660/1206490710866789/f
library(tidyr)
library(dplyr)

options(width=500)

# load persons.rdata
load("updated_output/persons.rdata")
print("persons:")
print(str(persons))
persons <- select(persons, hh_id, person_id, ptype_label, incQ_label, wfh_choice, SD, WorkLocation)
persons <- mutate(persons, has_workLocation=WorkLocation > 0)
print(table(persons$ptype_label, useNA="always"))

# I initially tried to do this with the tours data but it doesn't work, because the join tours are not
# disaggregated to persons, so they don't get included.
# The joint trips are disaggregated, so using that source instead.

# load trips.rdata
load("updated_output/trips.rdata")
print("trips:")
print(str(trips))

trips <- select(trips, hh_id, person_id, tour_id, tour_purpose, trip_mode)
trips <- mutate(trips, num_trips=1) # since some persons won't make trips
person_trips <- full_join(
    persons, trips,
    relationship = "one-to-many"
)
# fill in num_trips = 0 for those people
person_trips <- mutate(person_trips, num_trips = ifelse(is.na(num_trips), 0, num_trips))
# also tally work trips and non work trips
person_trips <- mutate(person_trips, 
    num_work_trips    = ifelse(tour_purpose %in% c("work_low","work_med","work_high","work_very high"), num_trips, 0),
    num_nonwork_trips = num_trips - num_work_trips,
)
print("head(person_trips):")
print(head(person_trips, n=100))

# some trips don't have a person?
print("trips without persons:")
trips_without_person <- filter(person_trips, is.na(person_trips$ptype_label))
print(trips_without_person)
# there shouldn't be
stopifnot( nrow(trips_without_person) == 0)

# some trips don't have a tour_purpose?
print("trips without tour_purpose:")
trips_without_purpose <- filter(person_trips, is.na(person_trips$tour_purpose))
print(trips_without_purpose)
# looks like these aren't trips -- they're person records for persons who didn't make a trip.  That's ok since their num_trips = 0
stopifnot( sum(trips_without_purpose$num_trips) == 0)

# create person attribute: has_workTour == num_work_trips > 0
person_has_work_tour <- person_trips %>%
    group_by(hh_id, person_id) %>%
    summarise(
        num_work_trips = sum(num_work_trips),
    ) %>% mutate(has_workTour = num_work_trips > 0)
print("head(person_has_work_tour):")
print(head(person_has_work_tour))

# add that attribute to person_trips
nrow_person_trips <- nrow(person_trips)
person_trips <- left_join(
    person_trips,
    select(person_has_work_tour, hh_id, person_id, has_workTour)
)
stopifnot( nrow_person_trips == nrow(person_trips))

# I was going to include tour_purpose and trip_mode in the groupby, but it doesn't work because the person segments don't make sense
person_trips_summary <- person_trips %>%
    group_by(ptype_label, incQ_label, SD, wfh_choice, has_workLocation, has_workTour) %>%
    summarise(
        num_persons = n_distinct(person_id),
        num_tours = n_distinct(person_id, tour_id, na.rm=TRUE), # if either person_id or tour_id is null, exclude
        num_trips = sum(num_trips),
        num_work_trips = sum(num_work_trips),
        num_nonwork_trips = sum(num_nonwork_trips),
    )
print("person_trips_summary")
print(person_trips_summary)
# save it
output_file <- "tripsByWorkerSegments.csv"
write.csv(person_trips_summary, output_file, row.names = FALSE)
print(paste("Wrote",output_file))
