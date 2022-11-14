# ntd-wide-to-long.R
#
# Transforms NTD data from wide to long, and filters to Bay Area.
#
library(tidyr)
library(dplyr)
library(readxl)
library(lubridate)

BOX_DIR          <- "E:\\Box"
WORKING_DIR      <- file.path(BOX_DIR, "Modeling and Surveys", "Projects", "Transit Recovery Scenario Modeling")
INPUT_WORKBOOK   <- file.path(WORKING_DIR, "NTD Ridership and Service Data.xlsx")
INPUT_WORKSHEET  <- "VRM" # vehicle route miles
INPUT_AGENCY_CSV <- file.path(WORKING_DIR, "AgencyToCommonAgencyName.csv")

OUTPUT_FILE     <- file.path(WORKING_DIR, "NTD_long.rdata")

agency_df <- read.csv(file=INPUT_AGENCY_CSV)
NTD_df <- read_excel(path=INPUT_WORKBOOK, sheet=INPUT_WORKSHEET)

# join to our agency mapping and remove agencies not in that list
NTD_df <- left_join(NTD_df, agency_df) %>% 
  filter(!is.na(Common.Agency.Name))

NTD_long_df <- pivot_longer(
  data=NTD_df,
  cols=matches("([A-Z]{3})([0-9]{2})"),
  names_pattern="([A-Z]{3})([0-9]{2})",
  names_to=c("month","year"),
  values_to="Vehicle.Revenue.Miles"
)

# filter those with null Vehicle.Revenue.Miles
NTD_long_df <- filter(NTD_long_df, !is.na(Vehicle.Revenue.Miles))

# Make year 4-digits
NTD_long_df$year <- as.numeric(NTD_long_df$year)  
NTD_long_df <- mutate(NTD_long_df, year=ifelse(year<50, 2000+year, 1900+year))

# standardize month and include days per month
NTD_long_df <- mutate(
  NTD_long_df, 
  month_int = match(month, toupper(month.abb), nomatch=-1),
  day_one   = sprintf("%d-%02d-01", year, month_int),
  days_in_month = lubridate::days_in_month(as.Date(day_one))) %>%
  select(-day_one)

# Write it to rData
save(NTD_long_df, file=OUTPUT_FILE)