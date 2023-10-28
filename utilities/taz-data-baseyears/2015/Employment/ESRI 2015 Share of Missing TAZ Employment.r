# ESRI 2015 Share of Missing TAZ Employment.r
# Identify TAZes with high share of missing employment
# April 21, 2020
# SI

# Import Libraries

suppressMessages(library(tidyverse))

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

# Data locations

USERPROFILE             <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
esri_location           <- file.path(USERPROFILE,"Box", "esri", "ESRI_2015_Disaggregate.Rdata")

# Bring in data and sum missing employment against total employment

load(esri_location)

missing_emp <- ESRI_2015_Disaggregate %>% mutate(
  missing=if_else(naics2==0,EMPNUM,0),
  total=EMPNUM) %>% 
  group_by(TAZ1454) %>% 
  summarize(missing_emp=sum(missing),total_emp=sum(total)) %>% mutate(
  share_missing_emp=missing_emp/total_emp) %>% 
    arrange(desc(share_missing_emp))

# Export CSV

write.csv(missing_emp, "ESRI 2015 Share of Missing TAZ Employment.csv", row.names = FALSE, quote = T)