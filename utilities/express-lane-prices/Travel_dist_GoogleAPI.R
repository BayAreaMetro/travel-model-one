# This script uses Google Dstance Matrix API to calculate travel distance for each tolled trips on EL.
# https://developers.google.com/maps/documentation/distance-matrix/overview
# The EL trip data are recived from YT Change in Oct, 2023
# We also received read points info All RPLong Lat.xlsx

# detail task is on Asana: https://app.asana.com/0/0/1205798175503103/f

# https://cran.r-project.org/web/packages/gmapsdistance/readme/README.html
# https://jul-carras.github.io/2019/01/19/ggmap_distances/
# The distance is returned in meters and the time in seconds.

setwd("C:/Users/llin/Box/Modeling and Surveys/Development/Travel_Model_1.6/Model_inputs/Express_Lanes/EL_Pricing_Data_March_2023")

library(sf)
library(stringr)
library(tidyverse)
library(readxl)
library(gmapsdistance)

###################
# data process

RP_LongLat <- 
  read_excel("All RPLong Lat.xlsx") %>%
  mutate(Lat  = as.numeric(Lat),
         Long = as.numeric(Long),
         Name = paste(gsub( " .*$", "", `Read Point Name`), 
                      "-", 
                      str_sub(`Read Point Name`, start = -1)))
INPUT <- "101 SB March 2023.xlsx"
fwy <- 
  read_excel(INPUT) 

fwy_LongLat <- 
  fwy %>%
  left_join(RP_LongLat %>% select(Name, Lat, Long),
            by = c('EntryReadPoint' = 'Name')) %>%
  rename('Lat_entry'  = 'Lat',
         'Long_entry' = 'Long') %>%
  left_join(RP_LongLat %>% select(Name, Lat, Long),
            by = c('ExitReadPoint' = 'Name')) %>%
  rename('Lat_exit'  = 'Lat',
         'Long_exit' = 'Long') %>%
  mutate(entry_input = paste0(Lat_entry, "+", Long_entry),
          exit_input  = paste0(Lat_exit,  "+", Long_exit)) 

fwy_unique_O <-
  unique(fwy_LongLat[c("EntryReadPoint","entry_input")])

fwy_unique_D <-
  unique(fwy_LongLat[c("ExitReadPoint","exit_input")])

# specify Google Distance Matrix API: https://developers.google.com/maps/documentation/distance-matrix/overview
# A free tier is provided - $200 monthly credit. This is enough for 40,000 Distance Matrix calls 
# or 20,000 Distance Matrix Advanced calls
google_api_key <- "YOUR KEY"
set.api.key(google_api_key)

 
origins <- c(unique(fwy_unique_O$entry_input))
destinations <- c(unique(fwy_unique_D$exit_input))


vector_inputs <- gmapsdistance(origin = origins,
                               destination = destinations,
                               mode = "driving")
Distance <-
  vector_inputs$Distance %>%
  as.data.frame() %>%
  tibble::rownames_to_column("Entry") %>%
  gather(Exit, Distance_meter, 2:ncol(.)) %>%
  mutate(Distance = Distance_meter/1609.34) %>% # 1 mile = 1609.34 meter
  left_join(fwy_unique_O, by = c('Entry' = 'entry_input')) %>%
  left_join(fwy_unique_D, by = c('Exit' = 'exit_input')) %>%
  select(EntryReadPoint, ExitReadPoint, Distance)
  
fwy_output <- 
  fwy %>%
  left_join(Distance, by = c('EntryReadPoint' = 'EntryReadPoint', 'ExitReadPoint' = 'ExitReadPoint'))
  
write.csv(fwy_output, "101SB_dist.csv")
