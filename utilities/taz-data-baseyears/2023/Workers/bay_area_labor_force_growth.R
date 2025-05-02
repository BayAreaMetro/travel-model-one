
# Script for calculating growth in labor force from Jan 2020 to Jan 2023 as a ratio


library(tidyverse)

# Set working directory as the location of the script
wd <- dirname(rstudioapi::getActiveDocumentContext()$path)
setwd(wd)

# Import Libraries
suppressMessages(library(tidyverse))

# Define paths
USERPROFILE <- gsub("\\\\", "/", Sys.getenv("USERPROFILE"))
BOX_TM <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
GITHUB_DIR <- file.path(USERPROFILE, "Documents", "GitHub")

if (Sys.getenv("USERNAME") %in% c("lzorn")) {
  GITHUB_DIR <- file.path("E:/GitHub")
  BOX_TM <- file.path("E:/Box/Modeling and Surveys")
}

TM1 <- file.path(GITHUB_DIR, 'travel-model-one', 'utilities', 'taz-data-baseyears', '2023')

# Load the EDD lmid data
edd_lf <- read.csv('Labor_Force_and_Unemployment_Rate_for_California_Counties_20231026.csv')
edd_lf$Date <- as.Date(edd_lf$Date, format = '%m/%d/%Y')

# Remove spaces from column names
colnames(edd_lf) <- gsub('\\.', '_', colnames(edd_lf))

# Filter for Area_Type=="County"
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

# Save the result to a CSV file
write.csv(target_ratio, file.path(TM1, "lf_growth_ratio_2020_2023.csv"), row.names = FALSE)
