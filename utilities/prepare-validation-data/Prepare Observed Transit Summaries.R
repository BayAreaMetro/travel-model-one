#
# title: Prepare Observed Transit Summaries
# author: David Ory, Lisa Zorn
#
# Purpose
#
# Create year 2015 (approximately) validation summaries using the on-board survey results and ridership changes
# from MTC's Transit Statistical Summaries.
#
#### TODO
# 1. Add in the line by line stuff for Muni, VTA, and AC Transit

# Libraries
library(lubridate)
library(openxlsx)
library(dplyr)

#### Remote file names

F_INPUT_SURVEY_DIR     = "M:/Data/OnBoard/Data and Reports/_data Standardized"
F_INPUT_LEGACY_RDATA   = file.path(F_INPUT_SURVEY_DIR, "survey_legacy.RData")
F_INPUT_STANDARD_RDATA = file.path(F_INPUT_SURVEY_DIR, "survey_standard.RData")

F_VALIDATION_DIR       = "M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM151_IPA_00/OUTPUT/validation"
F_INPUT_RIDERSHIP      = "M:/Data/Transit/2015 Ridership/transit ridership growth database.xlsx"
F_INPUT_ESTIMATED      = "M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM151_IPA_00/OUTPUT/trn/trnline.csv"

F_INPUT_MUNI_APC       = "M:/Data/Transit/Muni APC Through Time/consolidated-database.csv"

F_OUTPUT_DIR          = F_VALIDATION_DIR
F_OUTPUT_OBS_EST      = "observed_and_estimated_ridership.csv"
F_OUTPUT_MUNI_OBS     = "muni_observed.csv"


#### Data reads
mode_codes_df <- read.xlsx(F_INPUT_RIDERSHIP, sheet="mode code database", colNames=TRUE)
ridership_df  <- read.xlsx(F_INPUT_RIDERSHIP, sheet="ridership database", colNames=TRUE)

# estimated_df has columns name, mode (number), total.boardings, ...
estimated_df <- read.table(file = F_INPUT_ESTIMATED, header = TRUE, sep = ",", stringsAsFactors = FALSE)

# manually recode 85 to 30 for now
# TODO fix in coding
estimated_df <- mutate(estimated_df, mode = ifelse(mode==85, 30, mode))

#### Prepare estimated database
estimated_mode_code <- estimated_df %>%
  rename(mode_code = mode) %>%
  group_by(mode_code) %>%
  summarise(estimated_boardings = sum(total.boardings)) %>%
  ungroup()

# add other fields
estimated_mode_code <- left_join(estimated_mode_code, mode_codes_df)

# TODO: create and append estimates by line when observed data is prepared

# muni model route names
muni_model_names <- estimated_df %>%
  filter(mode == 20 | mode == 21) %>%
  group_by(name) %>%
  summarise(count = n())

# TODO: START with the above summary and trim the names to match the observed names


#### Prepare mode codes database
travel_model_codes <- mode_codes_df %>%
  filter(technology != "support")

# Add column, op_tech_count that's the count of (operator, technology)
count_codes <- summarize(group_by(travel_model_codes, operator, technology),
                         op_tech_count = n()) %>% ungroup()

travel_model_codes <- left_join(travel_model_codes, count_codes, by = c("operator", "technology"))

remove(count_codes)


#### Prepare ridership database

# adjustment factor to adjust ridership from survey year to 2015
ridership_adjust <- ridership_df %>%
  filter(survey_year_ridership != "na") %>%
  mutate(adjustment = as.numeric(year_2015_ridership) / as.numeric(survey_year_ridership))

#### Prepare on-board survey information
load(F_INPUT_LEGACY_RDATA)
load(F_INPUT_STANDARD_RDATA)

# remove this column since it's not in legacy data so it causes the rbind to error
survey.standard <- survey.standard %>%
  select(-survey_time)

# put the survey data together and keep only the columns we care about
survey_df <- rbind(survey.standard, survey.legacy) %>%
  select(operator, weekpart, survey_tech, survey_year, day_part, route, weight)

# Get rid of partial surveys, get weekdays, other clean-up
survey_df <- survey_df %>%
  filter(operator != "BART PRE-TEST") %>%
  filter(operator != "SF Muni Early Tranche") %>%
  mutate(operator = ifelse(operator == "Golden Gate Transit (bus)", "Golden Gate Transit", operator)) %>%
  mutate(operator = ifelse(operator == "Golden Gate Transit (ferry)", "Golden Gate Transit", operator)) %>%
  filter(weekpart == "WEEKDAY") %>%
  rename(technology = survey_tech)

# sum by operator and tech
survey_operator_tech <- survey_df %>%
  group_by(operator, technology) %>%
  summarize(survey_boardings = sum(weight)) %>%
  ungroup()

# sum for all buses
survey_operator_allbus <- survey_operator_tech[ substr(survey_operator_tech$technology,
                                                       nchar(survey_operator_tech$technology)-3,
                                                       nchar(survey_operator_tech$technology)) == " bus", ] %>%
  group_by(operator) %>%
  summarize(count = n(), survey_boardings = sum(survey_boardings)) %>%
  ungroup() %>%
  filter(count > 1) %>%
  mutate(technology = "all bus") %>%
  select(-count)

survey_sum <- rbind(survey_operator_allbus, survey_operator_tech)
# sort it
survey_sum <- survey_sum[order(survey_sum$operator),]

# join to ridership database
survey_adjustments <- left_join(survey_sum, ridership_adjust, by = c("operator", "technology"))

# these are the adjustments we'll make to the survey summary
survey_adjustments <- survey_adjustments %>%
  filter(!(is.na(adjustment))) %>%
  select(operator, technology, adjustment)

# join adjustments back to survey-operator-technology summary -- join on operator and technology
# this fails on technology which is only represented as allbus in survey_adjustments
first_oper_tech <- left_join(survey_operator_tech, survey_adjustments, by = c("operator", "technology"))

# these still need the adjustment -- join on tech="all bus"
then_just_oper <- first_oper_tech %>%
  filter(is.na(adjustment)) %>%
  select(-adjustment) %>%
  mutate(join_tech="all bus")

# these already have the adjustment factor
first_oper_tech <- first_oper_tech %>%
  filter(!(is.na(adjustment)))

# get the adjustment factor for these using the all_bus factors
then_just_oper <- left_join(then_just_oper, survey_adjustments, by = c("operator"="operator", "join_tech"="technology")) %>% select(-join_tech)

survey_adjusted <- rbind(first_oper_tech, then_just_oper)

survey_adjusted <- survey_adjusted %>%
  mutate(observed_boardings = survey_boardings * adjustment) %>%
  select(operator, technology, observed_boardings)

remove(first_oper_tech, survey_adjustments, survey_df, survey_operator_allbus,
       survey_operator_tech, survey_sum, survey.legacy, survey.standard, then_just_oper)


#### Use statistical summary ridership directly for non-surveyed routes
stats_riders <- ridership_df %>%
  filter(survey_year == "na") %>%
  select(operator, technology, observed_boardings = year_2015_ridership)

observed_ridership <- rbind(survey_adjusted, stats_riders)

remove(survey_adjusted, stats_riders)

# observed_ridership has operator, technology, observed_boardings
# where technology == "all bus" in some cases

#### Add travel model mode codes to observed ridership

# join will fail on tech="all bus"
observed_mode_code <- left_join(observed_ridership, travel_model_codes,
                                by = c("operator", "technology"))

# for those with more than one, divide observed ridership evenly amongst the travel submodes
# TODO: this is not a great assumption and could be better informed
observed_mode_code <- mutate(observed_mode_code,
                             observed_boardings = ifelse(is.na(op_tech_count),observed_boardings,observed_boardings/op_tech_count))

# fix join failed cases -- assuming all bus == express bus + local bus
all_bus_cases <- observed_mode_code %>%
  filter(is.na(mode_code)) %>%                     # join fail
  filter(technology=="all bus") %>%                # we can only fix this
  select(operator, observed_boardings)             # reset to the non-null columns, drop all bus technology since it's not helpful

bus_codes <- travel_model_codes %>% filter(technology == "local bus" | technology == "express bus")

# add count
bus_codes <- left_join(bus_codes, summarize(group_by(bus_codes, operator), bus_op_count=n()) %>% ungroup())

all_bus_cases <- left_join(all_bus_cases,
                           bus_codes,
                           by=c("operator"))
# for those with more than one, divide observed ridership amongst the travel submodes
# TODO: this is not a great assumption and could be better informed
all_bus_cases <- mutate(all_bus_cases,
                        observed_boardings = observed_boardings/bus_op_count)

# put them back together
observed_mode_code <- rbind(observed_mode_code,
                            select(all_bus_cases, -bus_op_count))
remove(bus_codes,all_bus_cases)

#### Find modes for which we have estimates, but nothing observed
output <- full_join(estimated_mode_code, observed_mode_code)

find_missing <- output %>%
  filter(!(is.na(estimated_boardings))) %>%
  filter(is.na(observed_boardings))

# Okay with these missing:
# 10 - West Berkeley
# 11 - Broadway Shuttle
# 14 - Caltrain Shuttle
# 16 - Palo Alto/Menlo Park Shuttles
# 19 - San Leandro Links
print("No observed boardings")
print(find_missing)
remove(find_missing)

# drop the ones where everything is NA but mode_code
output <- output %>% filter(!is.na(estimated_boardings) | !is.na(observed_boardings) | !is.na(operator) | !is.na(technology) )

# integerize observed boardings
output$observed_boardings <- as.integer(output$observed_boardings)
# reorder columns
output <- output[c("mode_code","operator","technology","mode_name","observed_boardings","estimated_boardings")]

#### Write to disk
write.csv(output, file = file.path(F_OUTPUT_DIR, F_OUTPUT_OBS_EST), row.names = FALSE, quote = TRUE)

#### Muni observed by route from APC
muni_apc_df <- read.table(file = F_INPUT_MUNI_APC, header = TRUE, sep = ",", stringsAsFactors = FALSE)

muni_observed <- muni_apc_df %>%
  mutate(start_year = year(as.Date(start_date, format = "%Y-%m-%d"))) %>%
  filter(start_year == 2015) %>%
  filter(week_part == "WEEKDAYS") %>%
  group_by(route) %>%
  summarise(boardings = sum(boardings)) %>%
  ungroup()

write.csv(muni_observed, file = file.path(F_OUTPUT_DIR, F_OUTPUT_MUNI_OBS), row.names = FALSE, quote = TRUE)