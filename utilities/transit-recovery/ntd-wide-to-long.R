# ntd-wide-to-long.R
#
# Transforms NTD data from wide to long, and filters to Bay Area.
#
library(tidyr)
library(dplyr)
library(stringr)
library(rlang)
library(readxl)
library(lubridate)

BOX_DIR          <- "E:\\Box"
WORKING_DIR      <- file.path(BOX_DIR, "Modeling and Surveys", "Projects", "Transit Recovery Scenario Modeling")
INPUT_WORKBOOK   <- file.path(WORKING_DIR, "NTD Ridership and Service Data.xlsx")
INPUT_WORKSHEETS <- c("VRM","VRH") # vehicle route miles, vehicle route hours
INPUT_AGENCY_CSV <- file.path(WORKING_DIR, "AgencyToCommonAgencyName.csv")

OUTPUT_FILE     <- file.path(WORKING_DIR, "NTD_long.rdata")

agency_df <- read.csv(file=INPUT_AGENCY_CSV)

for (worksheet in INPUT_WORKSHEETS) {
  NTD_df <- read_excel(path=INPUT_WORKBOOK, sheet=worksheet)

  # join to our agency mapping and remove agencies not in that list
  NTD_df <- left_join(NTD_df, agency_df) %>% 
    filter(!is.na(Common.Agency.Name))

  NTD_long_df <- pivot_longer(
    data=NTD_df,
    cols=matches("([A-Z]{3})([0-9]{2})"),
    names_pattern="([A-Z]{3})([0-9]{2})",
    names_to=c("month","year"),
    values_to=worksheet, # VRM or VRH
  )

  # filter those with null VRM or VRH
  NTD_long_df <- filter(NTD_long_df, !is.na(!!sym(worksheet)))

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
  
  # rename column
  if (worksheet=="VRM") {
    NTD_long_df <- rename(NTD_long_df, Vehicle.Revenue.Miles=VRM)
  }
  if (worksheet=="VRH") {
    NTD_long_df <- rename(NTD_long_df, Vehicle.Revenue.Hours=VRH)
  }

  # Write it to rData
  out_file <- str_replace(OUTPUT_FILE, ".rdata", paste0("_",worksheet,".rdata"))
  print(paste("Saving", out_file))
  save(NTD_long_df, file=out_file)
}
