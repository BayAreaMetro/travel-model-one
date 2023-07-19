library(tidyverse)
library(sf)
library(readxl)

Network_P4a <- read.csv("L:/Application/Model_One/NextGenFwys/Scenarios/2035_TM152_NGF_NP10_Path2a_02/OUTPUT/avgload5period.csv")
Toll <- read_excel("C:/Users/llin/Documents/GitHub/travel-model-one/utilities/NextGenFwys/TOLLCLASS_Designations.xlsx")
A_B_tolled_artrials_tolled_freeways <-
  Network_P4a %>%
  filter(tollclass >= 770000) %>%
  select(a, b, tollclass)%>%
  left_join(Toll, by=c('tollclass'='tollclass')) 


