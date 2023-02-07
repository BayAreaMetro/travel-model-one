# ntd-wide-to-long.R
#
# Transforms NTD data from wide to long, and filters to Bay Area.
# NTD Glossary: https://www.transit.dot.gov/ntd/national-transit-database-ntd-glossary
#
# It also creates versions simililarly formated to Travel Model 1+ output files in order to view
# alongside travel model output.
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
INPUT_WORKSHEETS <- c("VRM","VRH","UPT") # vehicle route miles, vehicle route hours, unlinked passenger trips
INPUT_AGENCY_CSV <- file.path(WORKING_DIR, "AgencyToCommonAgencyName.csv")

# assuming workingdir is travel-model-one
INPUT_MODEL_LOOKUP_XLSX <- file.path("utilities","TableauAliases.xlsx")

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
  ) %>% ungroup()
model_output_file <- file.path(WORKING_DIR, "NTD_yearly_model.rdata")
print(paste("Saving", nrow(NTD_model_df), "rows to",model_output_file))
save(NTD_model_df, file=model_output_file)
NTD_model_rows = nrow(NTD_model_df)

# finally, create a version that is similar in style to model output
# start by aligning the mode numbers
NTD_agency_mode_tm_lookup <- read_excel(INPUT_MODEL_LOOKUP_XLSX, sheet="Transit Mode")

# try to associate NTD_model_df with a travel model transit mode number
# note: multiple="first" works for dplyr 1.1.0
NTD_model_df <- left_join(NTD_model_df, NTD_agency_mode_tm_lookup, 
  by=c("Common.Agency.Name"="Common.Agency.Name", "Modes"="NTD.mode"), 
  multiple="first")
print(paste("Now have",nrow(NTD_model_df),"rows"))
stopifnot(nrow(NTD_model_df)==NTD_model_rows)

# join failure: missing Transit Mode
NTD_model_df["Modes backup"] = "MB" # default to motor bus
NTD_model_df[NTD_model_df$Common.Agency.Name == "BART",     "Modes backup"] <- "HR" # BART is heavy rail
NTD_model_df[NTD_model_df$Common.Agency.Name == "Caltrain", "Modes backup"] <- "CR" # Caltrain is commuter rail
NTD_model_df[(NTD_model_df$Common.Agency.Name == "SFMTA") &
             (NTD_model_df$Modes == "SR"), "Modes backup"] <- "LR" # Muni Streetcar Rail is Lightrail

# print the agency/mode and try a backup mode
missing_df <- filter(select(NTD_model_df, Common.Agency.Name, Modes, "Modes backup", "Transit Mode"), 
  is.na(NTD_model_df["Transit Mode"])) %>% distinct()
print(paste("Missing Transit Mode: "))
print(missing_df)

NTD_model_df <- left_join(NTD_model_df, NTD_agency_mode_tm_lookup,
  by=c("Common.Agency.Name"="Common.Agency.Name", "Modes backup"="NTD.mode"),
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
  -`Modes backup`, -`Transit Mode backup`, -`Transit Mode Name backup`, -`Mode Category backup`)

# transform columns to: 
# name	mode	owner	frequency	line time	line dist	total boardings	passenger miles	passenger hours	path id
#
# hours per timeperiod = 24
# vehicle runs per period = [Hours per Timeperiod]*60.0/[Frequency] = 24*60/frequency
# vehicle revenue hours per time period = [Vehicle runs per period]*[Line Time]/60.0
#   = (24*60/frequency)*60/60 = (24*60/frequency)
# so frequency = 24*60/vrh
NTD_model_df <- mutate(NTD_model_df, 
  name        = paste0(as.character(`Transit Mode`), "_NTD_", Modes, "_", as.character(year)),
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
  output_file <- file.path(WORKING_DIR, paste0('trnline_', save_year, '_NTD.csv'))
  NTD_model_year_df <- filter(NTD_model_df, year==save_year) %>%
    select(name, mode, owner, frequency, `line time`, `line dist`, `total boardings`,
    `passenger miles`, `passenger hours`, `path id`)

    write.csv(NTD_model_year_df, output_file, row.names=FALSE)
    print(paste("Wrote", nrow(NTD_model_year_df), "rows to", output_file))
}
