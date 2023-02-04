# ntd-wide-to-long.R
#
# Transforms NTD data from wide to long, and filters to Bay Area.
# NTD Glossary: https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary
library(tidyr)
library(dplyr)
library(stringr)
library(rlang)
library(readxl)
library(lubridate)

BOX_DIR          <- "E:\\Box"
WORKING_DIR      <- file.path(BOX_DIR, "Modeling and Surveys", "Projects", "Transit Recovery Scenario Modeling")
INPUT_WORKBOOK   <- file.path(WORKING_DIR, "NTD Ridership and Service Data.xlsx")
INPUT_WORKSHEETS <- c("VRM","VRH","UPT") # vehicle route miles, vehicle route hours, unlinked passenger trips
INPUT_AGENCY_CSV <- file.path(WORKING_DIR, "AgencyToCommonAgencyName.csv")

OUTPUT_FILE      <- file.path(WORKING_DIR, "NTD_long.rdata")

agency_df <- read.csv(file=INPUT_AGENCY_CSV)

# model-specific summary
NTD_model_df <- data.frame()

for (worksheet in INPUT_WORKSHEETS) {
  NTD_df <- read_excel(path=INPUT_WORKBOOK, sheet=worksheet)

  # join to our agency mapping and remove agencies not in that list
  NTD_df <- left_join(NTD_df, agency_df)

  # report on agencies with missing Common.Agency.Name
  missing_common_agency_name <- filter(NTD_df, is.na(Common.Agency.Name))
  print("Missing Common.Agency.Name:")
  missing_common_agency_name <- table(missing_common_agency_name$Agency)
  write.csv(missing_common_agency_name, "missing_common_agency_name.csv", row.names=FALSE)

  NTD_df <- filter(NTD_df, !is.na(Common.Agency.Name))

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

  # add very simple average daily
  NTD_long_df <- mutate(NTD_long_df,
    average_daily = !!as.symbol(worksheet) / days_in_month
  )
  
  # rename column
  if (worksheet=="VRM") {
    NTD_long_df <- rename(NTD_long_df, 
      Monthly.Vehicle.Revenue.Miles=VRM,
      average.daily.Vehicle.Revenue.Miles=average_daily
    )
  }
  if (worksheet=="VRH") {
    NTD_long_df <- rename(NTD_long_df, 
      Monthly.Vehicle.Revenue.Hours=VRH,
      average.daily.Vehicle.Revenue.Hours=average_daily
    )
  }
  if (worksheet=="UPT") {
    NTD_long_df <- rename(NTD_long_df, 
      Monthly.Unlinked.Passenger.Trips=UPT,
      average.daily.Unlinked.Passenger.Trips=average_daily)
  }

  # Write it to rData
  out_file <- str_replace(OUTPUT_FILE, ".rdata", paste0("_",worksheet,".rdata"))
  print(paste("Saving", out_file))
  save(NTD_long_df, file=out_file)

  INDEX_COLS <- c(
    "5 digit NTD ID","4 digit NTD ID","Agency","Active","Reporter Type",
    "UZA","UZA Name","Modes","TOS","Common.Agency.Name")

  # model-specific summary -- filter to just model months
  NTD_long_df <- filter(NTD_long_df, month %in% c('MAR','APR','MAY','SEP','OCT','NOV'))
  print(paste("Filtering to model months:",nrow(NTD_long_df),"rows"))
  if (nrow(NTD_model_df) == 0)
    NTD_model_df <- NTD_long_df
  else {
     NTD_model_df <- full_join(NTD_model_df, NTD_long_df,
      by=append(INDEX_COLS, c("month","year","month_int","days_in_month")))
    print(paste("Joining with other variables; nrow: ",nrow(NTD_model_df),"rows"))
    # print(head(NTD_model_df))
  }
}

# model data has been filtered to model months -- save this version
model_output_file <- file.path(WORKING_DIR, "NTD_monthly_model.rdata")
print(paste("Saving", nrow(NTD_model_df), "rows to",model_output_file))
save(NTD_model_df, file=model_output_file)

# plus a yearly version
NTD_model_df <- group_by(NTD_model_df, across(all_of(append(INDEX_COLS, "year")))) %>%
  summarize(
    average.Monthly.Vehicle.Revenue.Miles   =mean(Monthly.Vehicle.Revenue.Miles),
    average.daily.Vehicle.Revenue.Miles     =mean(average.daily.Vehicle.Revenue.Miles),
    average.Monthly.Vehicle.Revenue.Hours   =mean(Monthly.Vehicle.Revenue.Hours),
    average.daily.Vehicle.Revenue.Hours     =mean(average.daily.Vehicle.Revenue.Hours),
    average.Monthly.Unlinked.Passenger.Trips=mean(Monthly.Unlinked.Passenger.Trips),
    average.daily.Unlinked.Passenger.Trips  =mean(average.daily.Unlinked.Passenger.Trips)
  )
model_output_file <- file.path(WORKING_DIR, "NTD_yearly_model.rdata")
print(paste("Saving", nrow(NTD_model_df), "rows to",model_output_file))
save(NTD_model_df, file=model_output_file)