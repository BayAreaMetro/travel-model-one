# ntd-wide-to-long.R
#
# Transforms NTD data from wide to long, and filters to Bay Area.
# NTD Glossary: https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary
#
# It also creates versions similarly formated to Travel Model 1+ output files in order to view
# alongside travel model output.
#
# Input:
#  1) NTD monthly data spreadsheet downloaded from the NTD website 
#     (https://www.transit.dot.gov/ntd/data-product/monthly-module-raw-data-release)
#     and saved tonational-transit-database > Source 
#     (https://mtcdrive.box.com/s/786348kj1u364225mxfylklq0pt8yeay)
#
#  2) MonthlyToTypicalWeekdayRidership.xlsx
#     (https://mtcdrive.box.com/s/mbhdippfw1uds8ike3d3pdhhpu7r0agh)
#     that relates monthly boardings to average modeled weekday boardings based on Clipper data
#    
#  3) travel-model-one/TableauAliases.xlsx, sheet 'Transit Mode' which maps
#     Travel Model One transit modes
#     (https://github.com/BayAreaMetro/modeling-website/wiki/TransitModes) to 
#     NTD's Common.Agency.Name and NTD.mode (i.e. MB, CB, etc)
#
# Output:
#  1) NTD_long_[UPT,VRH,RVM].rdata (https://mtcdrive.box.com/v/national-transit-database)
#     which is consumed by SanFranciscoBayArea_NationalTransitDatabase.twb and published to
#     https://public.tableau.com/views/SanFranciscoBayArea_NationalTransitDatabase/Navigation
#
#  1.5) NTD_long_VRH_UPT.csv (https://mtcdrive.box.com/s/rtproamdd5zw4tjru2tv4d347d3291sc)
#     which is consumed by NTD-transit-recovery.twb
#
#  2) NTD_monthly_model.rdata (https://mtcdrive.box.com/v/national-transit-database)
#     which is NTD data filtered to model months ('MAR','APR','MAY','SEP','OCT','NOV')
#     Average daily columns of the variables are included in here.  For UPT, these are
#     calculated using MonthlyToTypicalWeekdayRidership.xlsx (see Input note above).
#     For the other variables, these are calculated by assuming dividing by the number
#     of days in the month.
#
#  3) NTD_yearly_model.rdata (https://mtcdrive.box.com/v/national-transit-database)
#     which is NTD data filtered to model months and aggregated (via mean) to years

library(tidyr)
library(dplyr)
library(stringr)
library(rlang)
library(readxl)
library(lubridate)

# UZA = Urbanized Area https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary#U
BayArea_UZAs = c(
  "Concord, CA",
  "Fairfield, CA",
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
INPUT_WORKBOOK   <- file.path(WORKING_DIR, "Source", "December 2023 Raw Monthly Ridership (no adjustments or estimates).xlsx")
INPUT_WORKSHEETS <- c("VRM","VRH","UPT") # vehicle route miles, vehicle route hours, unlinked passenger trips
INPUT_AGENCY_CSV <- file.path(WORKING_DIR, "AgencyToCommonAgencyName.csv")
INPUT_UPT_MONTHLY_TO_DAILY <- file.path(WORKING_DIR, "MonthlyToTypicalWeekdayRidership.xlsx")

# model/ntd files will get saved here (trnline_YYYY_NTD.csv)
# https://mtcdrive.box.com/s/vzsmmqa9oiz5jr6yqhmsnvm06hlwcoag
MODEL_OUTPUT_DIR <- file.path(BOX_DIR, "Modeling and Surveys", "Projects", "Transit Recovery Scenario Modeling")

# assuming cwd is travel-model-one
INPUT_MODEL_LOOKUP_XLSX <- file.path("..","TableauAliases.xlsx")
print(paste("Reading",normalizePath(INPUT_MODEL_LOOKUP_XLSX)))

# in the WORKING_DIR
OUTPUT_FILE      <- file.path(WORKING_DIR, "NTD_long.rdata")

# special VRH_UPT file
VRH_UPT_OUTPUT_FILE <- file.path(BOX_DIR, "Plan Bay Area 2050+", "Federal and State Approvals", "CARB Technical Methodology",
  "Exogenous Forces", "Mode_Preference_Change", "NTD_long_VRH_UPT.csv")

# Excel stores days as days since 1970-01-01
# lubridate as days since 1900-01-01
DAYS_1900_TO_1970 <- 25569

agency_df <- read.csv(file=INPUT_AGENCY_CSV)
upt_monthly_to_daily_df <- read_excel(INPUT_UPT_MONTHLY_TO_DAILY)

# model-specific summary
NTD_model_df <- data.frame()
# also output a text version with columns for VRH and UPT
VRH_UPT_join_df <- data.frame()

for (worksheet in INPUT_WORKSHEETS) {
  print(paste("Processing worksheet", worksheet))
  NTD_df <- read_excel(path=INPUT_WORKBOOK, sheet=worksheet)

  # join to our agency mapping and remove agencies not in that list
  NTD_df <- left_join(NTD_df, agency_df)

  # report on agencies with missing Common.Agency.Name
  missing_common_agency_name <- filter(NTD_df, is.na(Common.Agency.Name))
  # print(table(select(missing_common_agency_name, "UZA Name")))
  # filter to Bay Area UZAs
  missing_common_agency_name <- filter(missing_common_agency_name, 
    missing_common_agency_name["UZA Name"] %in% BayArea_UZAs)
  # summarize to Agency Name, UZA Name
  missing_common_agency_name <- table(select(missing_common_agency_name, "UZA Name", Agency))

  print(paste(nrow(missing_common_agency_name), "rows missing Common.Agency.Name:"))
  if (nrow(missing_common_agency_name) > 0) {
    print(missing_common_agency_name)
    write.csv(missing_common_agency_name, 
      file.path(WORKING_DIR, paste0("missing_common_agency_name_", worksheet, ".csv")),
      row.names=FALSE)
  }

  NTD_df <- filter(NTD_df, !is.na(Common.Agency.Name))

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

  # for UPT, use clipper-based data relating monthly ridership to
  # average modeled weekday
  if (worksheet=="UPT") {
    NTD_long_df <- left_join(NTD_long_df, upt_monthly_to_daily_df)
    stopifnot(nrow(filter(NTD_long_df, is.na("Monthly_To_Typical_Weekday")))==0)
    NTD_long_df <- mutate(NTD_long_df,
                          average_daily = !!as.symbol(worksheet) * Monthly_To_Typical_Weekday)
  } else {
    # add very simple average daily
    NTD_long_df <- mutate(NTD_long_df,
      average_daily = !!as.symbol(worksheet) / days_in_month
    )
  }
  
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
    # first just copy the VRH
    VRH_UPT_join_df <- data.frame(NTD_long_df)
  }
  if (worksheet=="UPT") {
    NTD_long_df <- rename(NTD_long_df, 
      Monthly.Unlinked.Passenger.Trips=UPT,
      average.daily.Unlinked.Passenger.Trips=average_daily)
    # join the VRH to UPT
    VRH_UPT_join_df <- full_join(VRH_UPT_join_df, NTD_long_df)
    print(paste("VRH_UPT_join_df columns:", colnames(VRH_UPT_join_df)))
  }

  # Write it to rData
  out_file <- str_replace(OUTPUT_FILE, ".rdata", paste0("_",worksheet,".rdata"))
  print(paste("Saving", out_file))
  save(NTD_long_df, file=out_file)

  # write the VRH_UPT_join_df to a csv
  print(paste("Saving", VRH_UPT_OUTPUT_FILE))
  write.csv(VRH_UPT_join_df, file=VRH_UPT_OUTPUT_FILE, row.names=FALSE)

  INDEX_COLS <- c(
    "NTD ID","Legacy NTD ID","Agency","Status","Reporter Type",
    # "UZA",  # not present in July 2023 dataset
    "UACE CD","UZA Name","Mode","3 Mode","TOS","Common.Agency.Name")

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
  
  print("NTD_model_df columns:")
  print(colnames(NTD_model_df))
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
  ) %>% ungroup()
model_output_file <- file.path(WORKING_DIR, "NTD_yearly_model.rdata")
print(paste("Saving", nrow(NTD_model_df), "rows to",model_output_file))
save(NTD_model_df, file=model_output_file)
NTD_model_rows = nrow(NTD_model_df)

# finally, create a version that is similar in style to model output
# start by aligning the mode numbers
NTD_agency_mode_tm_lookup <- read_excel(INPUT_MODEL_LOOKUP_XLSX, sheet="Transit Mode")

# let's look at the Common.Agency.Name versus NTD mode (CB, CC, etc)
options(max.print=2000)
print(table(NTD_model_df$Common.Agency.Name, NTD_model_df$Mode, useNA = "ifany"), n=100)

# try to associate NTD_model_df with a travel model transit mode number
# so each Common.Agency.Name/NTD.mode
# note: multiple="first" works for dplyr 1.1.0
NTD_model_df <- left_join(NTD_model_df, NTD_agency_mode_tm_lookup, 
  by=c("Common.Agency.Name"="Common.Agency.Name", "Mode"="NTD.mode"), 
  multiple="first")
print(paste("Now have",nrow(NTD_model_df),"rows"))
stopifnot(nrow(NTD_model_df)==NTD_model_rows)

# join failure: missing Transit Mode
NTD_model_df["Mode backup"] = "MB" # default to motor bus
NTD_model_df[NTD_model_df$Common.Agency.Name == "BART",     "Mode backup"] <- "HR" # BART is heavy rail
NTD_model_df[NTD_model_df$Common.Agency.Name == "Caltrain", "Mode backup"] <- "CR" # Caltrain is commuter rail
NTD_model_df[(NTD_model_df$Common.Agency.Name == "SFMTA") &
             (NTD_model_df$Mode == "SR"), "Mode backup"] <- "LR" # Muni Streetcar Rail is Lightrail

# print the agency/mode and try a backup mode
missing_df <- filter(select(NTD_model_df, Common.Agency.Name, Mode, "Mode backup", "Transit Mode"), 
  is.na(`Transit Mode`)) %>% distinct()
print(paste("Missing Transit Mode: "))
print(missing_df, n=100)

NTD_model_df <- left_join(NTD_model_df, NTD_agency_mode_tm_lookup,
  by=c("Common.Agency.Name"="Common.Agency.Name", "Mode backup"="NTD.mode"),
  multiple="first",
  suffix=c(""," backup")
)
# use the backup join if needed
NTD_model_df <- mutate(NTD_model_df,
  `Transit Mode`      = ifelse(is.na(`Transit Mode`),      `Transit Mode backup`,      `Transit Mode`),
  `Transit Mode Name` = ifelse(is.na(`Transit Mode Name`), `Transit Mode Name backup`, `Transit Mode Name`),
  `Mode Category`     = ifelse(is.na(`Mode Category`),     `Mode Category backup`,     `Mode Category`)
)
# verify we've solved it -- no more undefined transit modes
stopifnot(nrow(filter(NTD_model_df, is.na(`Transit Mode`)))==0)
# remove backup cols
NTD_model_df <- select(NTD_model_df, 
  -`Mode backup`, -`Transit Mode backup`, -`Transit Mode Name backup`, -`Mode Category backup`)

print(table(NTD_model_df$Common.Agency.Name, NTD_model_df$`Transit Mode`, useNA = "ifany"))

# transform columns to: 
# name	mode	owner	frequency	line time	line dist	total boardings	passenger miles	passenger hours	path id
#
# hours per timeperiod = 24
# vehicle runs per period = [Hours per Timeperiod]*60.0/[Frequency] = 24*60/frequency
# vehicle revenue hours per time period = [Vehicle runs per period]*[Line Time]/60.0
#   = (24*60/frequency)*60/60 = (24*60/frequency)
# so frequency = 24*60/vrh
NTD_model_df <- mutate(NTD_model_df, 
  name        = paste0(as.character(`Transit Mode`), "_NTD_", Mode, "_", as.character(year)),
  mode        = `Transit Mode`,
  `path id`   = "24_NTD_NTD_NTD", # am_wlk_loc_wlk
  owner       = 0,    # do we use this?
  `line time` = 60.0, # minutes; placeholder
  `line dist` = 10.0, # miles;   placeholder
  frequency   = 24.0*60.0/average.daily.Vehicle.Revenue.Hours,
  `total boardings` = average.daily.Unlinked.Passenger.Trips,
  `passenger miles` = 99, # we dont' know this; placeholder
  `passenger hours` = 99, # we dont' know this; placeholder
)

# save by year
for (save_year in unique(NTD_model_df$year)) {
  output_file <- file.path(MODEL_OUTPUT_DIR, paste0('trnline_', save_year, '_NTD.csv'))
  NTD_model_year_df <- filter(NTD_model_df, year==save_year) %>%
    select(name, mode, owner, frequency, `line time`, `line dist`, `total boardings`,
    `passenger miles`, `passenger hours`, `path id`)

    write.csv(NTD_model_year_df, output_file, row.names=FALSE)
    print(paste("Wrote", nrow(NTD_model_year_df), "rows to", output_file))
}
