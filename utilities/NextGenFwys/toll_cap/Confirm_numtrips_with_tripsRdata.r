# -------------------------------------------------------------------------
# Analysis to inform the implementation of a "pseudo monthly toll cap" aka "trip toll cap" strategy
# Specifically, it confirms the 
#
# input:   
# %TARGET_DIR%\updated_output\trips.rdata
#
# -------------------------------------------------------------------------

library(dplyr)
library(knitr) # for the kable function that creates well-formatted tables 

# ------------------------------------------
# read inputs
# ------------------------------------------
# look at the scenario in Round 1: All Lane Tolling + Transit 
# it has Means_Based_Tolling_Q1Factor  = 1, so it's probably closest to what we'll have for Round 2
TARGET_DIR="//model3-a/Model3A-Share/Projects/2035_TM152_NGF_NP10_Path1a_02"

# another Round 1 scenario is: All Lane Tolling + Affordability Focus
# it has Means_Based_Tolling_Q1Factor  = 0.5 
# (note that in Round 2, in pathways where we have monthly toll cap, we won't have toll discount, so Path1a in Round 1 is a better choice for this analysis)
# TARGET_DIR="//MODEL3-B/Model3B-Share/Projects/2035_TM152_NGF_NP10_Path1b_02"

trips_file <- file.path(TARGET_DIR, "updated_output", "trips.rdata")
load(trips_file)
# this data frame has 15,455,351 observations

# ------------------------------------------
# Preprocessing 
# ------------------------------------------

# The dataframe already has a name - it's trips
# Rename dataframe with a df_ prefix to make it easier to remember it is a data frame
df_trips <- trips
rm(trips)

# look at the variable names
variable_names <- names(df_trips)
variable_names_df <- data.frame(variable_name = variable_names)
print(variable_names_df)
# Ionecan identify the toll trips based on the trip modes
# trip_mode=2, 4, or 6

# Note that the input file trips.rdata is a 50% sample
SAMPLESHARE  <- 0.5


#-----------------------------------------------
# Create a universe of tolled trips
#-----------------------------------------------

df_tolltrips <- df_trips %>%
  filter(trip_mode == 2 | trip_mode == 4 | trip_mode == 6)
# this data frame has 1,188,456 observations


#-----------------------------------------------
# Convert the trip level data frame to person level
#-----------------------------------------------

df_tollRoadUsers <- df_tolltrips %>%
  group_by(person_id) %>%
  summarise(
    hhld_incQ               = first(incQ),
    hhld_incQ_label         = first(incQ_label),
    hhld_income             = first(income),
    hhld_autos              = first(autos),
    home_taz                = first(home_taz),
    person_numtrips         = n(),
  )

# this database has 823,410 individuals

# not using the variable "cost" from trips.rdata because it is not just toll cost. It includes auto operating cost.
# the cost databases do not split auto costs by bridge tolls, value tolls, and distance-based auto operating costs.
# reference: https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/core_summaries/CoreSummaries.R#L324-L325


#-----------------------------------------------
# Convert the trip level data frame to person level
#-----------------------------------------------

df_tollRoadUsersNumTripsTable <- df_tollRoadUsers %>%
  group_by(person_numtrips) %>%
  summarise(count = n()) %>%
  mutate(percentage = count / sum(count) * 100)

# Print the table using kable
kable(df_tollRoadUsersNumTripsTable, caption = "Toll Trip Frequency Table of Toll Road Users", format = "markdown")

# results: 93% of the toll road users user make 1 or 2 toll trips in the simulated day 
