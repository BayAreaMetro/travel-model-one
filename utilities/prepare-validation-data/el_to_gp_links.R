#
# adapted from HOV to GP links
#

library(foreign) # read dbf from shapefile since we're already making one for this process
library(dplyr)


TM_VERSION      <- "" # set to TM1 or TM2 or nothing in other uses
INPUT_DIR       <- "L:/RTP2021_PPA/Projects/3000_ExpLanes/2050_TM151_PPA_CG_16_3000_ExpLanes_01"
TM_NETWORK      <- file.path(INPUT_DIR, "shapefiles", "network_links.dbf")
OUTPUT_DBF      <- "el_to_gp_links.dbf"
OUTPUT_CSV      <- "el_to_gp_links.csv"

network_df      <- read.dbf(TM_NETWORK, as.is=TRUE) %>% select(A,B,LANES,USE,FT,TOLLCLASS,ROUTENUM,ROUTEDIR,DISTANCE,PROJ)

hov_links_df        <-  filter(network_df, TOLLCLASS>9 )
gp_links_df         <- filter(network_df, USE==1 & (FT<=3 | FT==5 | FT==8 | FT==10))
notruck_links_df    <- filter(network_df , USE==4 & TOLLCLASS==0)
gp_notruck_links_df <- bind_rows(gp_links_df, notruck_links_df)

print(paste("Have", nrow(hov_links_df), "HOV links"))

#############################################################
# first, try to find roadway links with dummy link connectors
dummy_links     <- filter(network_df, FT==6)

# dummy B => hov A, "A target" is the first point of dummy access link
hov_group1_df   <- inner_join(hov_links_df, 
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
hov_links_df <- left_join(hov_links_df, select(hov_group1_df, A,B,A_GP,B_GP, DISTANCE_GP))

#### output for looking at these
hov_links_df <- mutate(hov_links_df, A_B=paste0(A,"_",B), A_B_GP=paste0(A_GP,"_",B_GP))

write.dbf(hov_links_df, file.path(INPUT_DIR,OUTPUT_DBF))
write.csv(hov_links_df, file.path(INPUT_DIR,OUTPUT_CSV), row.names = FALSE)