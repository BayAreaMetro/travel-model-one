library(tidyverse)
library(dplyr)

# ACS 2017-2021 create TAZ data for 2020.R
# Create "2020" TAZ data from ACS 2017-2021 
# SI

# Notes

# The working directory is set as the location of the script. All other paths in TM1 will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)


# Import Libraries

suppressMessages(library(tidyverse))

# path preliminaries
USERPROFILE          <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
GITHUB_DIR           <- file.path(USERPROFILE,"Documents","GitHub")
if (Sys.getenv("USERNAME") %in% c("lzorn")) {
  GITHUB_DIR         <- file.path("E://GitHub")
  BOX_TM             <- file.path("E://Box/Modeling and Surveys")
}
TM1                   <- file.path(GITHUB_DIR,'travel-model-one','utilities','taz-data-baseyears')

# Load the EDD lmid data - downloaded from 
# https://data.edd.ca.gov/Labor-Force-and-Unemployment-Rates/Labor-Force-and-Unemployment-Rate-for-California-C/r8rw-9pxx

edd_lf <- read.csv('Labor_Force_and_Unemployment_Rate_for_California_Counties_20231026.csv')
edd_lf$Date <- as.Date(edd_lf$Date,format = '%m/%d/%Y')

# Remove spaces from column names
colnames(edd_lf) <- gsub('\\.', '_', colnames(edd_lf))

# Filter for AreaType=="County"
edd_lf <- edd_lf %>%
  filter(Area_Type == "County")

# Create a new column 'county_name'
edd_lf$county_name <- gsub(' County', '', edd_lf$Area_Name)

# Define bayareafips_full as a list of county names you want to filter by
bayareafips_full <- list('06001' = 'Alameda',
                         '06013' = 'Contra Costa',
                         '06041' = 'Marin',
                         '06055' = 'Napa',
                         '06075' = 'San Francisco',
                         '06081' = 'San Mateo',
                         '06085' = 'Santa Clara',
                         '06097' = 'Sonoma',
                         '06095' = 'Solano')

# Filter for counties in bayareafips_full
edd_lf_bayarea <- edd_lf %>%
  filter(county_name %in% bayareafips_full)

# Set Date and county_name as the index and select Employment column
edd_lf_bayarea <- edd_lf_bayarea %>%
  select(Date, county_name, Employment)

# Define REFERENCE_DATE and TARGET_DATE
REFERENCE_DATE <- as.Date('2020-01-01')
TARGET_DATE <- as.Date('2023-01-01')

# Calculate the ratio as the ratio of the sum of county EMPRES, at different dates
target_ratio <- sum(edd_lf_bayarea$Employment[edd_lf_bayarea$Date == TARGET_DATE]) /
  sum(edd_lf_bayarea$Employment[edd_lf_bayarea$Date == REFERENCE_DATE])

print(target_ratio)


write.csv(target_ratio,file.path(TM1,"2023","lf_growth_ratio_2020_2023.csv"),row.names = F)


# # Plot the data
# edd_lf_bayarea %>%
#   group_by(Date,county_name) %>%
#   summarize(Employment = sum(Employment)) %>%
#   ggplot(aes(x = Date, y = Employment, color = county_name)) +
#   geom_line() +
#   labs(title = 'Employed Residents, Bay Area, 1992-2023')

