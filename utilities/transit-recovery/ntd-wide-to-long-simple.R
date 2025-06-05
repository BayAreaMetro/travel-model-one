# ntd-wide-to-long-simple.R
#
# Simplificatinon of ntd-wide-to-long.R, created for checking against
# CalSTA graph: https://app.asana.com/1/11860278793487/project/310827677834656/task/1210468712911666?focus=true
#
# Transforms NTD data from wide to long *without* filtering to Bay Area.
# NTD Glossary: https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary
#
# Input:
#  1) NTD monthly data spreadsheet downloaded from the NTD website 
#     (https://www.transit.dot.gov/ntd/data-product/monthly-module-raw-data-release)
#     and saved to national-transit-database > Source 
#     (https://mtcdrive.box.com/s/786348kj1u364225mxfylklq0pt8yeay)
#
# Output:
#  1) NTD_long_VRM.rdata
#
library(tidyr)
library(dplyr)
library(stringr)
library(rlang)
library(readxl)
library(lubridate)

# UZA = Urbanized Area https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary#U
BayArea_UZAs = c(
  "Antioch, CA",
  "Concord--Walnut Creek, CA",
  "Fairfield, CA",
  "Livermore--Pleasanton--Dublin, CA",
  "Napa, CA",
  "Petaluma, CA",
  "San Francisco-Oakland, CA",
  "San Jose, CA",
  "Santa Rosa, CA",
  "Vacaville, CA",
  "Vallejo, CA"
)

BOX_DIR          <- "E:\\Box"
WORKING_DIR      <- file.path(BOX_DIR, "Modeling and Surveys", "Share Data", "national-transit-database")
INPUT_WORKBOOK   <- file.path(WORKING_DIR, "Source", "February 2025 Complete Monthly Ridership (with adjustments and estimates)_250401.xlsx")
INPUT_WORKSHEETS <- c("VRM") # vehicle route mile

# in the WORKING_DIR
OUTPUT_FILE      <- file.path(".", "NTD_long.rdata")

# Excel stores days as days since 1970-01-01
# lubridate as days since 1900-01-01
DAYS_1900_TO_1970 <- 25569

for (worksheet in INPUT_WORKSHEETS) {
  print(paste("Processing worksheet", worksheet))
  NTD_df <- read_excel(path=INPUT_WORKBOOK, sheet=worksheet)

  # If column names are in Excel date formats, which are number of days since 1900 01 01
  # rename them. e.g. "44927" => JAN23
  NTD_df <- rename_with(NTD_df,
    ~ toupper(format(as_date(strtoi(.x) - DAYS_1900_TO_1970), "%b%y")),
    num_range(prefix="", 37000:50000)
  )
  # If column names are strings, e.g. 1/2010 rename them to JAN10
  NTD_df <- rename_with(NTD_df,
    ~ toupper(format(as_date(paste0("1/",.x), format="%d/%m/%Y"), "%b%y")),
    matches("^\\d+/\\d*$")
  )
  print("After renaming date columns")
  print(colnames(NTD_df))

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
  NTD_long_df <- rename(NTD_long_df, 
    Monthly.Vehicle.Revenue.Miles=VRM,
    average.daily.Vehicle.Revenue.Miles=average_daily
  )

  # Write it to rData
  out_file <- str_replace(OUTPUT_FILE, ".rdata", paste0("_",worksheet,".rdata"))
  print(paste("Saving", out_file))
  save(NTD_long_df, file=out_file)

}
