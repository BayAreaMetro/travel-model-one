# Quick script to try to figure out which ODs use the bay bridge (as oppose to other bridges)

# Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))
library(dplyr)

# base directory
BASE_DIR    <- "M:/Application/Model One/RTP2017/Scenarios/2015_06_002/OUTPUT"
BASE_DIR    <- gsub("\\\\","/",BASE_DIR) # switch slashes around

bridge_dir   <- data.frame(
  bridge   =c("Bay"      ,"Bay"      ,"SanMateoHayward","SanMateoHayward","RichmondSanRafael","RichmondSanRafael"),
  direction=c("Eastbound","Westbound","Eastbound"      ,"Westbound"      ,"Eastbound"        ,"Westbound"        ),
  link     =c("6973-2784","2783-6972","6383-3642"      ,"3650-6381"      ,"7853-2341"        ,"2342-7894"        )
)


# OUTPUT_DIR   <- gsub("\\\\","/",OUTPUT_DIR) # switch slashes around

bay_wb_filename <- file.path(BASE_DIR,"selectLink_BayBridge","loadAM_selectlink_2783-6972_ODs.txt")
bay_eb_filename <- file.path(BASE_DIR,"selectLink_BayBridge","loadAM_selectlink_6973-2784_ODs.txt")

smh_wb_filename <- file.path(BASE_DIR,"selectLink_SanMateoHaywardBridge","loadAM_selectlink_3650-6381_ODs.txt")
smh_eb_filename <- file.path(BASE_DIR,"selectLink_SanMateoHaywardBridge","loadAM_selectlink_6383-3642_ODs.txt")

rsr_wb_filename <- file.path(BASE_DIR,"selectLink_RichmondSanRafaelBridge","loadAM_selectlink_2342-7894_ODs.txt")
rsr_eb_filename <- file.path(BASE_DIR,"selectLink_RichmondSanRafaelBridge","loadAM_selectlink_7853-2341_ODs.txt")

# read them all
bay_wb_df <- read.table(bay_wb_filename, header=TRUE, strip.white=TRUE, sep=",")
bay_eb_df <- read.table(bay_eb_filename, header=TRUE, strip.white=TRUE, sep=",")

smh_wb_df <- read.table(smh_wb_filename, header=TRUE, strip.white=TRUE, sep=",")
smh_eb_df <- read.table(smh_eb_filename, header=TRUE, strip.white=TRUE, sep=",")

rsr_wb_df <- read.table(rsr_wb_filename, header=TRUE, strip.white=TRUE, sep=",")
rsr_eb_df <- read.table(rsr_eb_filename, header=TRUE, strip.white=TRUE, sep=",")

# only look at passenger vehicles
bay_wb_df <- mutate(bay_wb_df, bay_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,bay_vol_pax)
bay_eb_df <- mutate(bay_eb_df, bay_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,bay_vol_pax)

smh_wb_df <- mutate(smh_wb_df, smh_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,smh_vol_pax)
smh_eb_df <- mutate(smh_eb_df, smh_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,smh_vol_pax)

rsr_wb_df <- mutate(rsr_wb_df, rsr_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,rsr_vol_pax)
rsr_eb_df <- mutate(rsr_eb_df, rsr_vol_pax=vol_pax) %>% select(OTAZ,DTAZ,rsr_vol_pax)

# start with bay bridge non-zero ODs
bay_wb_df <- subset(bay_wb_df, bay_vol_pax>0.01)
bay_eb_df <- subset(bay_eb_df, bay_vol_pax>0.01)

# left_join other two bridges
bridge_wb_df <- left_join(bay_wb_df,    smh_wb_df)
bridge_wb_df <- left_join(bridge_wb_df, rsr_wb_df)

bridge_eb_df <- left_join(bay_eb_df,    smh_eb_df)
bridge_eb_df <- left_join(bridge_eb_df, rsr_eb_df)

remove(smh_wb_filename, smh_eb_filename, rsr_wb_filename, rsr_eb_filename)
remove(smh_wb_df, smh_eb_df, rsr_wb_df, rsr_eb_df)

# fill in NA
bridge_wb_df[is.na(bridge_wb_df)] <- 0
bridge_eb_df[is.na(bridge_eb_df)] <- 0

# tot_vol_pax
bridge_wb_df <- mutate(bridge_wb_df, tot_vol_pax= bay_vol_pax+smh_vol_pax+rsr_vol_pax)
bridge_eb_df <- mutate(bridge_eb_df, tot_vol_pax= bay_vol_pax+smh_vol_pax+rsr_vol_pax)

# bay bridge percentage
bridge_wb_df <- mutate(bridge_wb_df, bay_pct=bay_vol_pax/tot_vol_pax)
bridge_eb_df <- mutate(bridge_eb_df, bay_pct=bay_vol_pax/tot_vol_pax)

# join taz lat/longs for vis
taz_coords <- read.table(file.path(BASE_DIR,"selectLink_BayBridge","taz_nodes_WGS84.csv"),
                         header=TRUE, strip.white=TRUE, sep=",") %>% select(N,latitude,longitude)

bridge_wb_df <- left_join(bridge_wb_df, taz_coords, by=c("OTAZ"="N")) %>% rename(orig_latitude=latitude, orig_longitude=longitude)
bridge_wb_df <- left_join(bridge_wb_df, taz_coords, by=c("DTAZ"="N")) %>% rename(dest_latitude=latitude, dest_longitude=longitude)

bridge_eb_df <- left_join(bridge_eb_df, taz_coords, by=c("OTAZ"="N")) %>% rename(orig_latitude=latitude, orig_longitude=longitude)
bridge_eb_df <- left_join(bridge_eb_df, taz_coords, by=c("DTAZ"="N")) %>% rename(dest_latitude=latitude, dest_longitude=longitude)

# write out
OUTFILE_WB <- file.path(BASE_DIR,"selectLink_BayBridge","wb_bridges.csv")
OUTFILE_EB <- file.path(BASE_DIR,"selectLink_BayBridge","eb_bridges.csv")
write.table(bridge_wb_df, OUTFILE_WB, sep=",", row.names=FALSE, quote=FALSE)
write.table(bridge_eb_df, OUTFILE_EB, sep=",", row.names=FALSE, quote=FALSE)


