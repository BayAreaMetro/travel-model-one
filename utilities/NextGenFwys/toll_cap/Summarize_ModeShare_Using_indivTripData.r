# ----------------------------------
#
# R script to summarize the test run results after running just core
# it reads indivTripData_1 (and householdData_1 for income info)
# it summarizes the mode split by income groups (above or below the cut-off)
#
# ----------------------------------

library(dplyr)
library(knitr)


# ------------------
# input location
# ------------------
# baseline
#trip_file_path <- "//model3-c/Model3C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TollCapTest15pc/main/indivTripData_1.csv"
#hhld_file_path <- "//model3-c/Model3C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TollCapTest15pc/main/householdData_1.csv"

# test - cap set at 38.5 cents
#trip_file_path <- "//model3-c/Model3C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TripTollCapAt38pt5/main/indivTripData_1.csv"
#hhld_file_path <- "//model3-c/Model3C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TripTollCapAt38pt5/main/householdData_1.csv"

# the replication test i.e. post new implementation, with toll cap set to a very high number
trip_file_path <- "//model2-c/Model2C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TollCapTest/main/indivTripData_1.csv"
hhld_file_path <- "//model2-c/Model2C-Share/Projects/2035_TM160_IPA_12_NGFr1_AllLanePlusTransit_TollCapTest/main/householdData_1.csv"

hhldinc_cutoff <- 50000

# ------------------

# Read the CSV file into a data frame
df_indivTripData <- read.csv(trip_file_path)
df_householdData <- read.csv(hhld_file_path)

# list all the variables
variable_names <- names(df_indivTripData)
print(variable_names)

variable_names <- names(df_householdData)
print(variable_names)

# ------------------

# look at the results by income
# need to join the household data file to get household income

df_indivTripData <- df_indivTripData %>%
  left_join(df_householdData %>% select(hh_id, income), by = 'hh_id')

# create a new variable
df_indivTripData <- df_indivTripData %>%
  mutate(income_cat = case_when(
    income < hhldinc_cutoff ~ "1. Hhld income less than hhldinc_cutoff",
    TRUE ~ "2. Hhld income higher than hhldinc_cutoff"
  ))

# ------------------


df_indivTripData <- df_indivTripData %>%
  mutate(trip_mode_description = case_when(
    trip_mode == 1 ~ 'Drive alone, no toll',
    trip_mode == 2 ~ 'Drive alone, pay toll',
    trip_mode == 3 ~ 'Shared ride 2, no toll',
    trip_mode == 4 ~ 'Shared ride 2, pay toll',
    trip_mode == 5 ~ 'Shared ride 3+, no toll',
    trip_mode == 6 ~ 'Shared ride 3+, pay toll',
    trip_mode == 7 ~ 'Walk all the way',
    trip_mode == 8 ~ 'Bicycle all the way',
    trip_mode == 9 ~ 'Walk to local bus',
    trip_mode == 10 ~ 'Walk to light rail or ferry',
    trip_mode == 11 ~ 'Walk to express bus',
    trip_mode == 12 ~ 'Walk to heavy rail',
    trip_mode == 13 ~ 'Walk to commuter rail',
    trip_mode == 14 ~ 'Drive to local bus',
    trip_mode == 15 ~ 'Drive to light rail or ferry',
    trip_mode == 16 ~ 'Drive to express bus',
    trip_mode == 17 ~ 'Drive to heavy rail',
    trip_mode == 18 ~ 'Drive to commuter rail',
    trip_mode == 19 ~ 'Taxi',
    trip_mode == 20 ~ 'TNC single party',
    trip_mode == 21 ~ 'TNC shared'
  ))


# table for "1. Hhld income less than hhldinc_cutoff"
df_indivTripData_LowInc <- df_indivTripData %>%
 filter(income_cat == "1. Hhld income less than hhldinc_cutoff")

df_indivTripData_LowInc %>%
  group_by(trip_mode) %>%
  summarise(trip_mode_description = first(trip_mode_description),
            count = n()) %>%
  mutate(percentage = count / sum(count) * 100) %>%
  kable("markdown", caption = "Frequency and Percentage Table for trip_mode - low income")


# table for "2. Hhld income higher than hhldinc_cutoff"
df_indivTripData_NonLowInc <- df_indivTripData %>%
 filter(income_cat == "2. Hhld income higher than hhldinc_cutoff")

df_indivTripData_NonLowInc %>%
  group_by(trip_mode) %>%
  summarise(trip_mode_description = first(trip_mode_description),
            count = n()) %>%
  mutate(percentage = count / sum(count) * 100) %>%
  kable("markdown", caption = "Frequency and Percentage Table for trip_mode - non low income")


