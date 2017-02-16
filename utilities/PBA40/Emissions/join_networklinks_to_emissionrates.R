
library(dplyr)

#
# This R script opens the following network csvs
# and left_joins them to the emissions rates in [county][year].csv
# where "Speed" is joined on int(CSPD[AM,MD,PM,EV,EA])
# 
# join is based on year, county, care/non-care area and speed
#
network_csv_files <- c("2015.csv",
                       "2040_694.csv",
                       "2040_690.csv",
                       "2040_691.csv",
                       "2040_693.csv",
                       "2040_696.csv")

# city county lookup file
CITY_COUNTY_FILE <- "City-County_Lookup.csv"

# and writes the file
OUTPUT_FILE <- "CARE-melt-wEmissions_2.10.17.csv"

# all files are expected to be here (note R's preference for slashes)
if (Sys.getenv("RSTUDIO_USER_IDENTITY") == "lzorn") {
  BASE_DIR <- "C:/Users/lzorn/Box Sync/CARE Communities/CARE-Data"
} else {
  BASE_DIR <- "~/Desktop/CARE-Data_R"
}

city_county_df <- read.table(file.path(BASE_DIR, CITY_COUNTY_FILE), header=TRUE, sep=",", stringsAsFactors=FALSE)

# loop through each network file
all_networks_df <- data.frame()
for (network_csv_file in network_csv_files) {
  
  # read the network file
  network_fullpath_file <- file.path(BASE_DIR, network_csv_file)
  cat(paste0("Reading [",network_fullpath_file,"]\n"))
  network_df <- read.table(network_fullpath_file, header=TRUE, sep=",", stringsAsFactors=FALSE)
  
  # note which file it came from
  network_df$scenario_str <- substr(network_csv_file,0,nchar(network_csv_file)-4)
  # and the year
  network_df$year <- strtoi(substr(network_csv_file,0,4))
  # add to all networks
  all_networks_df <- rbind(all_networks_df, network_df)
}
# remove clutter variables - everything is in the all_networks_df
remove(network_csv_file, network_fullpath_file, network_df)

# CARE field is currently 1 or NA -- make NAs into 0
all_networks_df <- mutate(all_networks_df, CARE = ifelse(is.na(CARE),0,CARE))

# add county based on city name
all_networks_df <- left_join(all_networks_df,
                             city_county_df,
                             by=c("CITYNAME"))

# read the emissions files
COUNTY_CODES <- 
  c("AL", # alameda
    "CC", # contra costa
    "MA", # marin
    "NA", # napa
    "SC", # santa clara
    "SF", # san francsico
    "SL", # solano
    "SM", # san mateo
    "SN") # sonoma
# these should be in the same order as COUNTY_CODES
COUNTIES <-
  c("Alameda",
    "Contra Costa",
    "Marin",
    "Napa",
    "Santa Clara",
    "San Francisco",
    "Solano",
    "San Mateo",
    "Sonoma")
county_codes_df <- data.frame(county_code=COUNTY_CODES, county=COUNTIES, stringsAsFactors=FALSE)

YEARS <- c(2015, 2040)
emission_rates_df <- data.frame()
for (year in YEARS) {
  for (county in COUNTY_CODES) {
    emission_fullpath_file <- file.path(BASE_DIR, paste0(county,year,".csv"))
    cat(paste0("Reading [",emission_fullpath_file,"]\n"))
    emission_df <- read.table(emission_fullpath_file, header=TRUE, sep=",")
    
    # tag with county
    emission_df <- mutate(emission_df, county_code=county, year=year)
    
    # add to all emission rates
    emission_rates_df <- rbind(emission_rates_df, emission_df)
  }
}
# remove clutter variables - everything is in the emission_rates_df
remove(year, county, emission_fullpath_file, emission_df)

# add county rather than county code to emissions file
emission_rates_df <- left_join(emission_rates_df,
                               county_codes_df,
                               by=c("county_code")) %>% select(-county_code)

# these are the columns in the emissions file
# they look like this: Speed, county, year [C,NC]_EO_PM2.5, [C,NC]_EO_Benzene, [C,NC]_EO_Butadiene, [C,NC]_EO_DieselPM

# let's split by care and no care so care rows are different from no-care rows
care_emission_rates_df   <- emission_rates_df %>% 
  select(-NC_EO_PM2.5,        -NC_EO_Benzene,          -NC_EO_Butadiene,            -NC_EO_DieselPM) %>%  # delete no care versions
  rename(    EO_PM2.5=C_EO_PM2.5, EO_Benzene=C_EO_Benzene, EO_Butadiene=C_EO_Butadiene, EO_DieselPM=C_EO_DieselPM) %>% # rename
  mutate(CARE=1) # tag as care

nocare_emission_rates_df <- emission_rates_df %>% 
  select(-C_EO_PM2.5,          -C_EO_Benzene,            -C_EO_Butadiene,              -C_EO_DieselPM) %>%  # delete care versions
  rename(   EO_PM2.5=NC_EO_PM2.5, EO_Benzene=NC_EO_Benzene, EO_Butadiene=NC_EO_Butadiene, EO_DieselPM=NC_EO_DieselPM) %>% # rename
  mutate(CARE=0)

emission_rates_df <- rbind(care_emission_rates_df, nocare_emission_rates_df)

emission_cols <- names(emission_rates_df)

# for each time period
TIMEPERIODS <- c("EA","AM","MD","PM","EV")
for (timeperiod in TIMEPERIODS) {

  # rename the emissions columns for this timeperiod
  # FROM: Speed,       year, county, CARE, EO_PM2.5,    EO_Benzene,    EO_Butadiene,    EO_DieselPM
  #   TO: CSPD_AM_int, year, COUNTY, CARE, EO_PM2.5 AM, EO_Benzene AM, EO_Butadiene AM, EO_DieselPM AM
  emission_cols_tp <- emission_cols
  for (colnum in 1:length(emission_cols)) {
    if (emission_cols[colnum] == "Speed") {
      emission_cols_tp[colnum] = paste0("CSPD",timeperiod,"_int")
    } else if ((emission_cols[colnum] == "year")|
               (emission_cols[colnum] == "CARE")) {
      emission_cols_tp[colnum] = emission_cols[colnum]
    } else if (emission_cols[colnum] == "county") {
      emission_cols_tp[colnum] = "COUNTY"
    } else {
      emission_cols_tp[colnum] = paste0(emission_cols[colnum]," ",timeperiod)
    }
  }
  emission_rates_tp_df <- emission_rates_df 
  names(emission_rates_tp_df) <- emission_cols_tp
  
  # create integerized cspd column
  cspd_float_col <- paste0("CSPD",timeperiod)
  cspd_int_col   <- paste0("CSPD",timeperiod,"_int")
  all_networks_df[[cspd_int_col]] <- trunc(all_networks_df[[cspd_float_col]])
  
  # join to emissions -- will join on year, COUNTY, CARE, CSPD[tp]_int
  all_networks_df <- left_join(all_networks_df, emission_rates_tp_df)
}
remove(timeperiod, emission_cols_tp, emission_rates_tp_df, cspd_float_col, cspd_int_col)

# write the result
output_fullpath <- file.path(BASE_DIR, OUTPUT_FILE)
write.table(all_networks_df, output_fullpath, sep=",", row.names=FALSE)