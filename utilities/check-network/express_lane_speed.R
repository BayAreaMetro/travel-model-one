#
# summarize express lane speed
# for toll rates calibration
#

library(foreign) # read dbf from shapefile
library(dplyr)

# remove all variables from the r environment
rm(list=ls())

# the loaded network 
MODELOUTPUT_DIR       <- "L:/RTP2021_PPA/Projects/2050_TM151_PPA_BF_05/OUTPUT"
LOADED_NETWORK_CSV    <- file.path(MODELOUTPUT_DIR, "avgload5period.csv")
UNLOADED_NETWORK_DBF  <- file.path("M:/Application/Model One/Mock Futures/Express_Lane_length_correction/Full Express Lane Buildout/OUTPUT/shapefiles", "network_links.dbf") # from cube_to_shapefile.py
# Note that "Full Express Lane Buildout" seems to be missing 5 toll classes

OUTPUT_CSV            <- "express_lane_speed_ALL.csv"
OUTPUT_NAN_CSV            <- "express_lane_speed_NAN.csv"


unloaded_network_df        <-  read.dbf(UNLOADED_NETWORK_DBF, as.is=TRUE) %>% select(A,B,LANES,USE,FT,TOLLCLASS)
el_links_df                <-  filter(unloaded_network_df, TOLLCLASS>9)

loaded_network_df          <-  read.csv(file=LOADED_NETWORK_CSV, header=TRUE, sep=",")



# join the As and Bs of EL links to the loaded network
el_loaded_df <- loaded_network_df %>% right_join(el_links_df,
                                      by=c("a"="A", "b"="B"))

# summarise
el_summary_df <- el_loaded_df %>%
                    group_by(TOLLCLASS) %>%
                    summarise(avgspeed_EA = mean(cspdEA), 
                              maxspeed_EA = max(cspdEA),
                              avgspeed_AM = mean(cspdAM),
                              maxspeed_AM = max(cspdAM),
                              avgspeed_MD = mean(cspdMD),
                              maxspeed_MD = max(cspdMD),
                              avgspeed_PM = mean(cspdPM),
                              maxspeed_PM = max(cspdPM),
                              avgspeed_EV = mean(cspdEV), 
                              maxspeed_EV = max(cspdEV),
                              link_count = n())

# n.a. in the summary means some of the links in the "fully built out network" is not in the project network
# is this how we'd expect the projects to be layered?
# for example, the three existing toll classes 25, 31 and 32 are all n.a.

# check number of links with na and without na

el_loaded_nan_df <- na.omit(el_loaded_df)

el_summary_nan_df <- el_loaded_nan_df %>%
                    group_by(TOLLCLASS) %>%
                    summarise(avgspeed_EAnan = mean(cspdEA), 
                              maxspeed_EAnan = max(cspdEA),
                              avgspeed_AMnan = mean(cspdAM),
                              maxspeed_AMnan = max(cspdAM),
                              avgspeed_MDnan = mean(cspdMD),
                              maxspeed_MDnan = max(cspdMD),
                              avgspeed_PMnan = mean(cspdPM),
                              maxspeed_PMnan = max(cspdPM),
                              avgspeed_EVnan = mean(cspdEV), 
                              maxspeed_EVnan = max(cspdEV),
                              link_countnan = n())

el_summary_df <- el_summary_df %>% left_join(el_summary_nan_df,
                                      by=c("TOLLCLASS"))

write.csv(el_summary_df, file.path(MODELOUTPUT_DIR,OUTPUT_CSV), row.names = FALSE)
write.csv(el_summary_nan_df, file.path(MODELOUTPUT_DIR,OUTPUT_NAN_CSV), row.names = FALSE)
# maybe merge toll class name to improve clarity
# just looking at the existing express lanes 31 and 32 have fairly high speed in baseline05, there is no need to increase toll rate for them?