# Asana Task: https://app.asana.com/0/0/1204541827390079/f
# The script is to calculate the percent of local street within freeway buffers using TM2 network
# relevant shapfiles are saved here: 
# Box\NextGen Freeways Study\07 Tasks\07_AnalysisRound1\Corridor Level Visualization\Choosing Representative Links for Groupings\choosing parallel arterial links\Calculate_share_of_local_streets\TM2-networks

library(sf)
library(foreign)
library(tidyverse)
setwd("C:/Users/llin/Box/NextGen Freeways Study/07 Tasks/07_AnalysisRound1/Corridor Level Visualization/Choosing Representative Links for Groupings/choosing parallel arterial links/Calculate_share_of_local_streets/TM2-networks")

local   <- read.dbf("TM2_local_ft_2_4_5_6_7.dbf")


link <- read.dbf("Clipped_halfmi.dbf")
link <- read.dbf("Clipped_1mi.dbf")
link <- read.dbf("Clipped_2mi.dbf")
link <- read.dbf("Clipped_3mi.dbf")

clipped <- 
  link %>%
  select(A, B, Length_ft, Length_cp, lanes_EA, lanes_AM, lanes_MD, lanes_PM, lanes_EV) %>%
  mutate(Max_lanes         = pmax(lanes_EA, lanes_AM, lanes_MD, lanes_PM, lanes_EV),
         Length_lane_ft    = Max_lanes * Length_ft,
         Length_lane_cp_ft = Max_lanes * Length_cp) %>%
  select(-lanes_EA, -lanes_AM, -lanes_MD, -lanes_PM, -lanes_EV)
  

  

local_joined_clipped <-
  local %>%
  mutate(Max_lanes = pmax(lanes_EA, lanes_AM, lanes_MD, lanes_PM, lanes_EV)) %>%
  mutate(Length_lane_ft = Max_lanes * Length_ft) %>%
  left_join(clipped,
            by = c('A'='A', 'B'='B')) %>%
  mutate(PERCENTAGE      = ifelse(is.na(Length_cp/Length_ft.x),
                             0,
                             Length_cp/Length_ft.x)) %>%
  mutate(PERCENTAGE_lane = ifelse(is.na(Length_lane_cp_ft/Length_lane_ft.x),
                             0,
                             Length_lane_cp_ft/Length_lane_ft.x)) %>%
  select(A, B, ft, Length_ft.x, Length_cp, PERCENTAGE, Length_lane_ft.x, Length_lane_cp_ft, PERCENTAGE_lane) %>%
  rename(Length_ft      = Length_ft.x,
         Length_lane_ft = Length_lane_ft.x)



# all percentage for roadways
all_local           <- sum(local_joined_clipped$Length_ft)
within_3_mile_local <- sum(local_joined_clipped$Length_cp, na.rm = TRUE)                        
  
Percentage         <- within_3_mile_local/all_local

# all percentage for roadways lane length
all_local           <- sum(local_joined_clipped$Length_lane_ft)
within_3_mile_local <- sum(local_joined_clipped$Length_lane_cp_ft, na.rm = TRUE)                        

Percentage_lane     <- within_3_mile_local/all_local


write.csv(local_joined_clipped, "local_joined_clipped_halfmi.csv")