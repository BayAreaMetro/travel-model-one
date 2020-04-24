# NETS Data Sole Proprietor Analysis.R
# National Establishment Time-Series 2015 data
# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set working directory

wd <- "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment"
setwd(wd)


# Import Data

nets_location = "M:/Data/NETS/2015/nets_2015_bayarea_v3.xlsx"

nets <- read_excel (nets_location,sheet="nets_raw") 

nets2 <- nets %>%              #Filter out sole proprietors and summarize to TAZ
  filter(emp>1) %>% 
  group_by(zone_id,naics_mtc) %>% 
  summarize(total=sum(emp)) %>% 
  spread(naics_mtc,total,fill=0) 



# Append zero values for San Quentin TAZ and append to full data, re-sort dataset, write it out

quentin <- data.frame(zone_id=1439, agrempn=0, fpsempn=0, herempn=0, mwtempn=0, othempn=0, retempn=0)

final <- rbind(as.data.frame(nets2),quentin) %>%
  mutate(totemp=agrempn+fpsempn+herempn+mwtempn+othempn+retempn) %>% 
  arrange(zone_id) 

write.csv(final, "2015 NETS without sole proprietors.csv", row.names = FALSE, quote = T)




