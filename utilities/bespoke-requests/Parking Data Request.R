# Parking Data Request.R
# Output TAZ parking assumptions for 2015, 2035, and 2050
# SI

# Import libraries

suppressMessages(library(tidyverse))

# Set up directories

wd <- "M:/Data/Requests/Dave Vautin/Model Data"
setwd(wd)

MODEL_DATA_BASE_DIR <-"M:/Application/Model One/RTP2021"
Y_2015 <- file.path(MODEL_DATA_BASE_DIR,"IncrementalProgress","2015_TM152_IPA_16","INPUT","landuse","tazData.csv")
Y_2035 <- file.path(MODEL_DATA_BASE_DIR,"IncrementalProgress","2035_TM152_IPA_00","INPUT","landuse","tazData.csv")
Y_2050 <- file.path(MODEL_DATA_BASE_DIR,"Blueprint","2050_TM152_DBP_Basic_00","INPUT","landuse","tazData.csv")

# Bring in files and select TAZ and parking data only

data_2015 <- read.csv(Y_2015, header=TRUE) %>% 
  select(ZONE,PRKCST_2015=PRKCST,OPRKCST_2015=OPRKCST)
data_2035 <- read.csv(Y_2035, header=TRUE) %>% 
  select(ZONE,PRKCST_2035=PRKCST,OPRKCST_2035=OPRKCST)
data_2050 <- read.csv(Y_2050, header=TRUE) %>% 
  select(ZONE,PRKCST_2050=PRKCST,OPRKCST_2050=OPRKCST)

# Join into a single file and output

temp  <- left_join(data_2015,data_2035,by="ZONE")
final <- left_join(temp,data_2050,by="ZONE")

write.csv(final, "TAZ Parking Data 2015_2035_2050.csv", row.names=FALSE, quote = T)





