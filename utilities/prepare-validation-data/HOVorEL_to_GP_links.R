#
# HOV (or EL) to GP link
#
# note that essentially the same code is duplicated in:
# https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/toll_calibration/TollCalib_CheckSpeeds.R#L97-L133
# https://github.com/BayAreaMetro/NetworkWrangler/blob/049a7a8756ef37c09ed8b240875063e737f4be48/Wrangler/TransitNetwork.py#L1386-L1408

library(foreign) # read dbf from shapefile since we're already making one for this process
library(dplyr)

# --------------------
# User inputs
# --------------------

TM_VERSION      <- "TM1" # set to TM1 or TM2
#CROSSWALK_DIR   <- paste0("M:/Crosswalks/PeMSStations_",TM_VERSION,"network")
CROSSWALK_DIR   <- "L:/Application/Model_One/NextGenFwys/temp"
TM_NETWORK      <- "M:/Application/Model One/Networks/TM1_2015_Base_Network/shapefile/freeflow_links.dbf"
HOV_or_EL       <- "HOV" # HOV or EL
EL_firstvalue   <- 31
# firstvalue should be consistent with what is defined in the hwy param block
# https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/hwyParam.block#L13

# --------------------

OUTPUT_DBF      <- paste0(HOV_or_EL, "_to_gp_links.dbf")
OUTPUT_CSV      <- paste0(HOV_or_EL, "_to_gp_links.csv")

network_df      <- read.dbf(TM_NETWORK, as.is=TRUE) %>% select(A,B,LANES,USE,FT,ROUTENUM,ROUTEDIR,TOLLCLASS)

if (HOV_or_EL=="HOV") {
    hov_el_links_df        <- filter(network_df, USE==2 | USE==3)
    }
if (HOV_or_EL=="EL") {
    hov_el_links_df        <-  filter(network_df, TOLLCLASS>=EL_firstvalue)
    }
gp_links_df         <- filter(network_df, (USE==1) & ((FT<=3 | FT==5 | FT==8 | FT==10) | (FT==6)&(TOLLCLASS>0)) )  # last clause is for toll plaza GP links
notruck_links_df    <- filter(network_df , USE==4 & TOLLCLASS==0)
gp_notruck_links_df <- bind_rows(gp_links_df, notruck_links_df)

print(paste("Have", nrow(hov_el_links_df), " ",HOV_or_EL, " links"))

#############################################################
# first, try to find roadway links with dummy link connectors
dummy_links     <- filter(network_df, FT==6)

# dummy B => hov A, "A target" is the first point of dummy access link
hov_group1_df   <- inner_join(hov_el_links_df,
                              select(dummy_links, A,B),
                              by=c("A"="B"), suffix=c("","_GP")) # dummy B => hov A
# hov B => dummy A, "B target" is the second point of dummy egress link
hov_group1_df   <- inner_join(hov_group1_df,
                              select(dummy_links, A,B),
                              by=c("B"="A"), suffix=c("","_GP")) # hov B   => dummy A

hov_group1_df   <- inner_join(hov_group1_df, gp_notruck_links_df,
                              by=c("A_GP"="A", "B_GP"="B"),
                              suffix=c("","_GP"))

print(paste("Group1: found general purpose links for", nrow(hov_group1_df), "links"))

# join back to hov_links
hov_el_links_df <- left_join(hov_el_links_df, select(hov_group1_df, A,B,A_GP,B_GP))

#### output for looking at these
hov_el_links_df <- mutate(hov_el_links_df, A_B=paste0(A,"_",B), A_B_GP=paste0(A_GP,"_",B_GP))

write.dbf(hov_el_links_df, file.path(CROSSWALK_DIR,OUTPUT_DBF))
write.csv(hov_el_links_df, file.path(CROSSWALK_DIR,OUTPUT_CSV), row.names = FALSE)
