############################################################################################
### Script to create target summaries from MTC OBS towards TM 1.5 calibration
###
### Summaries:-
### - Boardings by depart hour and Operator/Technology
### - District X District transi summaries by purose and primary transit mode
### - Access & Egress mode summaries
###
### Author: Binny M Paul, binny.mathewpaul@rsginc.com, Dec 2018
############################################################################################
oldw <- getOption("warn")
options(warn = -1)
options(scipen=999)

### if 'plyr' package was used in the previous session then session needs to be restarted
### some of dplyr functions dont work work if dplyr is loaded after plyr
if (!"dplyr" %in% installed.packages()) install.packages("dplyr", repos='http://cran.us.r-project.org')
library(dplyr)


### USER INPUTS
#--------------

## Switches
# one of "maz_v1_0" or "maz_v2_2"
# Just use maz_v1_0 since the onboard survey geocoding was done to maz v1.0
geography <- "maz_v1_0"


## Input File Paths
if (Sys.getenv("USERNAME") == "binny.paul") {
  USERPROFILE   <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
  BOX_DEV       <- file.path(USERPROFILE, "Box Sync")
  BOX_TM2       <- file.path(BOX_DEV,     "Travel Model Two Development")
  BOX_TM1.5     <- file.path(BOX_DEV,     "Travel Model 1.5")
  OBS_Dir       <- file.path(BOX_TM1.5,   "Calibration", "data", "ReweightedOBS")
  Geog_Dir      <- file.path(BOX_TM1.5,   "Calibration", "data", "GeographicData")
  MC_Dir        <- file.path(BOX_TM1.5,   "Calibration", "mode choice targets")
  OutDir        <- file.path(BOX_TM1.5,   "Calibration", "OBS_Summaries")
} else {
  Project_Dir <- file.path('E:','projects','clients','mtc')
  OBS_Dir     <- file.path(Project_Dir, 'data','OBS_27Dec17')
  Geog_Dir    <- file.path(Project_Dir, 'data','TM1.5_Geographies')
  MC_Dir      <- file.path(Project_Dir, 'TM_1_5','ModeChoiceTargets')
}

# total tours in mode choice targets
MC_TotalTours <- 786781
MC_TotalTrips <- 1394561
MC_TotalBoardings <- 1628709
  


### READ INPUTS
#--------------
OBS <- read.csv(file.path(OBS_Dir,'OBS_processed_weighted.csv'), as.is = T)
taz15_SD <- read.csv(file.path(Geog_Dir, 'geographies','taz-superdistrict-county.csv'), as.is = T)
scaleFactors <- read.csv(file.path(MC_Dir,'OBS_Tour_Scale_Factors.csv'), as.is = T)


### DATA TRANSFORMATION
#-----------------------

tourPurpNames <- c('work','university','school','maintenance','discretionary','at-work')
tourPurpCodes <- c(1,2,3,4,5,6)
tourPurpDF    <- data.frame(tourPurposeName = tourPurpNames, code = tourPurpCodes)

# add super district names and IDs
OBS <- OBS %>%
  rename('Orig_SD' = 'Orig_SD34', 'Orig_SD_NAME' = 'Orig_SD34_NAME') %>%
  rename('Dest_SD' = 'Dest_SD34', 'Dest_SD_NAME' = 'Dest_SD34_NAME')

# recode access and egress modes
OBS <- OBS %>%
  mutate(accessModeTM1.5 = access_mode) %>%
  mutate(accessModeTM1.5 = ifelse((first_board_tech=="local bus" 
                                  | transfer_from_tech=="local bus") 
                                  & (survey_tech!="local bus") & (boardings > 1) 
                                  & (access_mode=='walk'),'LB',accessModeTM1.5)) %>%
  mutate(egressModeTM1.5 = egress_mode) %>%
  mutate(egressModeTM1.5 = ifelse((survey_tech!="local bus")
                                  & (transfer_to_tech=="local bus"
                                  | last_alight_tech=="local bus") & (boardings > 1) 
                                  & (egress_mode=='walk'),'LB',egressModeTM1.5))

OBS$accessModeTM1.5[is.na(OBS$accessModeTM1.5)] <- 'walk'
OBS$egressModeTM1.5[is.na(OBS$egressModeTM1.5)] <- 'walk'

OBS <- OBS %>%
  mutate(tour_access_modeTM1.5 = accessModeTM1.5) %>% 
  mutate(tour_access_modeTM1.5 = ifelse(outbound == 0, egressModeTM1.5, tour_access_modeTM1.5))

#View(OBS[OBS$tour_access_modeTM1.5=='LB' & OBS$boardings==1, 
#         c('first_board_tech','transfer_from_tech','survey_tech','transfer_to_tech','last_alight_tech','boardings',
#           'accessModeTM1.5','egressModeTM1.5','tour_access_modeTM1.5','BEST_MODE')])


# Code dest_purp with NAs as 'missing' for unsurveyed operators
OBS$dest_purp[is.na(OBS$dest_purp)] <- "missing"

# recode orig and destination SD in tour format (a.k.a PA format)
OBS$Tour_Orig_SD_NAME <- OBS$Orig_SD_NAME
OBS$Tour_Orig_SD_NAME[OBS$dest_purp=='home'] <- OBS$Dest_SD_NAME[OBS$dest_purp=='home']
OBS$Tour_Dest_SD_NAME <- OBS$Dest_SD_NAME
OBS$Tour_Dest_SD_NAME[OBS$dest_purp=='home'] <- OBS$Orig_SD_NAME[OBS$dest_purp=='home']

# Code tour mode [BEST_MODE + access_mode]
# 06_Walk-Local,  07_Walk-Light Rail,  08_Walk-Ferry,  09_Walk-Express Bus,  10_Walk-Heavy Rail,  11_Walk-Commuter Rail
# 12_Drive-Local, 13_Drive-Light Rail, 14_Drive-Ferry, 15_Drive-Express Bus, 16_Drive-Heavy Rail, 17_Drive-Commuter Rail
# No info on the return trip, BEST trip mode assumed to be the tour mode
OBS <- OBS %>%
  mutate(tour_mode = '06_Walk-Local') %>%
  mutate(tour_mode = ifelse(tour_access_mode=='walk' & BEST_MODE=='LR', '07_Walk-Light Rail', tour_mode)) %>%
  mutate(tour_mode = ifelse(tour_access_mode=='walk' & BEST_MODE=='FR', '08_Walk-Ferry', tour_mode)) %>%
  mutate(tour_mode = ifelse(tour_access_mode=='walk' & BEST_MODE=='EB', '09_Walk-Express Bus', tour_mode)) %>%
  mutate(tour_mode = ifelse(tour_access_mode=='walk' & BEST_MODE=='HR', '10_Walk-Heavy Rail', tour_mode)) %>%
  mutate(tour_mode = ifelse(tour_access_mode=='walk' & BEST_MODE=='CR', '11_Walk-Commuter Rail', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='LB', '12_Drive-Local', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='LR', '13_Drive-Light Rail', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='FR', '14_Drive-Ferry', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='EB', '15_Drive-Express Bus', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='HR', '16_Drive-Heavy Rail', tour_mode)) %>%
  mutate(tour_mode = ifelse((tour_access_mode=='pnr' | tour_access_mode=='knr') & BEST_MODE=='CR', '17_Drive-Commuter Rail', tour_mode))

# code tour_mode ina different format
OBS$BEST_MODE_recode <- OBS$BEST_MODE
OBS$BEST_MODE_recode[OBS$BEST_MODE_recode == 'FR'] <- 'Ferry'

# Code tour mode for district summaries after combining Ferry and Light Rail
OBS$District_tour_mode <- OBS$BEST_MODE
OBS$District_tour_mode[OBS$BEST_MODE=='FR' | OBS$BEST_MODE=='LR'] <- 'LR/FR'


# Code tour purpose
OBS <- OBS %>%
  left_join(tourPurpDF, by = c('agg_tour_purp'='code')) 
# Code missing tour puroses as Total, total scale factors will be used
OBS$tourPurposeName <- as.character(OBS$tourPurposeName)
OBS$tourPurposeName[is.na(OBS$tourPurposeName)] <- 'total'

# Read scale factors
OBS <- OBS %>%
  left_join(scaleFactors, by = c('tour_mode'='tourMode', 'tourPurposeName'='tourPurpose'))

# Compute tour weights
OBS <- OBS %>%
  mutate(tour_weight2015 = trip_weight2015 * scaleFactor)

TotalTours <- sum(OBS$tour_weight2015)

OBS$tour_weight2015 <- OBS$tour_weight2015 * (MC_TotalTours/TotalTours)

# Compute adjusted weights for district summaries
# to account for missing origin/dest info
temp_tours <- sum(OBS$tour_weight2015[!is.na(OBS$Dest_SD_NAME) & !is.na(OBS$Orig_SD_NAME)])
temp_trips <- sum(OBS$trip_weight2015[!is.na(OBS$Dest_SD_NAME) & !is.na(OBS$Orig_SD_NAME)])

OBS$tour_weight2015_adj <- OBS$tour_weight2015 * (MC_TotalTours/temp_tours)
OBS$trip_weight2015_adj <- OBS$trip_weight2015 * (MC_TotalTrips/temp_trips)

## View records with NAs as scale factors
#View(OBS[is.na(OBS$scaleFactor),
#         c('agg_tour_purp','tour_access_mode', 'BEST_MODE','tourPurposeName','tour_mode','scaleFactor')])


### GENERATE SUMMARIES
#---------------------

### boardings by depart  and return hour
OBS_original <- OBS
OBS <- OBS[OBS$surveyed==1,]

summary_boards_dep <- OBS[,c('survey_tech','operator','depart_hour','board_weight2015')] %>%
  filter(!is.na(survey_tech) & !is.na(operator) & !is.na(depart_hour) & !is.na(board_weight2015)) %>%
  group_by(survey_tech, operator, depart_hour) %>%
  summarise(boards = sum(board_weight2015)) %>%
  ungroup()

summary_boards_ret <- OBS[,c('survey_tech','operator','return_hour','board_weight2015')] %>%
  filter(!is.na(survey_tech) & !is.na(operator) & !is.na(return_hour) & !is.na(board_weight2015)) %>%
  group_by(survey_tech, operator, return_hour) %>%
  summarise(boards = sum(board_weight2015)) %>%
  ungroup()

hour_list <- seq(0,23)
df <- expand.grid(tech = unique(OBS$survey_tech), 
                  operator = unique(OBS$operator), 
                  hour = hour_list)
df$departure <- summary_boards_dep$boards[match(paste(df$tech, df$operator, df$hour, sep = "-"), 
                                                paste(summary_boards_dep$survey_tech, summary_boards_dep$operator, summary_boards_dep$depart_hour, sep = "-"))]
df$return <- summary_boards_ret$boards[match(paste(df$tech, df$operator, df$hour, sep = "-"), 
                                                paste(summary_boards_ret$survey_tech, summary_boards_ret$operator, summary_boards_ret$return_hour, sep = "-"))]
df[is.na(df)] <- 0
df$total <- df$departure + df$return
write.csv(df, file.path(OutDir,'OBS_Boardings_By_Hour.csv'), row.names = F)

OBS <- OBS_original
OBS$accessMode_original <- OBS$accessMode
OBS$accessMode[OBS$accessMode %in% c('knr','pnr')] <- 'drive'

# code access mode as walk and drive


### district X district trip summaries
orig_district_list <- unique(taz15_SD$SD_NAME)
dest_district_list <- orig_district_list
best_mode_list     <- unique(OBS$BEST_MODE)

district_summary <- data.frame()
for (i in 1:6){
  t <- xtabs(trip_weight2015_adj~accessMode+BEST_MODE+Orig_SD_NAME+Dest_SD_NAME, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t)
  t$purpose <- i
  district_summary <- rbind(district_summary,t)
}
colnames(district_summary) <- c("accessMode", "BEST_MODE", "Orig_SD_NAME", "Dest_SD_NAME", "trips", "tourPurpose")

# add marginals for tour purpose, best mode and access mode
# accessMode is tour access mode
access_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)
best_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)
tour_purp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, BEST_MODE) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

bm_am_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

bm_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

am_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

district_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

district_summary <- rbind(district_summary, best_mode_totals, tour_purp_totals, bm_am_totals, bm_tp_totals, am_tp_totals, district_totals)
write.csv(district_summary, file.path(OutDir,'OBS_District_TripFlows.csv'), row.names = F)


### district X district trip summaries [in Tour format (a.k.a PA format)]

district_summary <- data.frame()
for (i in 1:6){
  t <- xtabs(trip_weight2015_adj~accessMode+BEST_MODE+Tour_Orig_SD_NAME+Tour_Dest_SD_NAME, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t)
  t$purpose <- i
  district_summary <- rbind(district_summary,t)
}
colnames(district_summary) <- c("accessMode", "BEST_MODE", "Orig_SD_NAME", "Dest_SD_NAME", "trips", "tourPurpose")

# add marginals for tour purpose, best mode and access mode
# accessMode is tour access mode
access_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)
best_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)
tour_purp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, BEST_MODE) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

bm_am_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, tourPurpose) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

bm_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

am_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE) %>%
  summarise(trips = sum(trips)) %>%
  mutate(accessMode = "Total") %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

district_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME) %>%
  summarise(trips = sum(trips)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, trips, tourPurpose)

district_summary <- rbind(district_summary, best_mode_totals, tour_purp_totals, bm_am_totals, bm_tp_totals, am_tp_totals, district_totals)
write.csv(district_summary, file.path(OutDir,'OBS_District_TripFlows_PA.csv'), row.names = F)

### district X district tour summaries 

district_summary <- data.frame()
for (i in 1:6){
  t <- xtabs(tour_weight2015_adj~accessMode+BEST_MODE+Tour_Orig_SD_NAME+Tour_Dest_SD_NAME, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t)
  t$purpose <- i
  district_summary <- rbind(district_summary,t)
}
colnames(district_summary) <- c("accessMode", "BEST_MODE", "Orig_SD_NAME", "Dest_SD_NAME", "tours", "tourPurpose")

# add marginals for tour purpose, best mode and access mode
# accessMode is tour access mode
access_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE, tourPurpose) %>%
  summarise(tours = sum(tours)) %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)
best_mode_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, tourPurpose) %>%
  summarise(tours = sum(tours)) %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)
tour_purp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode, BEST_MODE) %>%
  summarise(tours = sum(tours)) %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)

bm_am_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, tourPurpose) %>%
  summarise(tours = sum(tours)) %>%
  mutate(accessMode = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)

bm_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, accessMode) %>%
  summarise(tours = sum(tours)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)

am_tp_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME, BEST_MODE) %>%
  summarise(tours = sum(tours)) %>%
  mutate(accessMode = "Total") %>%
  mutate(tourPurpose = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)

district_totals <- district_summary %>%
  group_by(Orig_SD_NAME, Dest_SD_NAME) %>%
  summarise(tours = sum(tours)) %>%
  mutate(tourPurpose = "Total") %>%
  mutate(BEST_MODE = "Total") %>%
  mutate(accessMode = "Total") %>%
  ungroup() %>%
  select(accessMode, BEST_MODE, Orig_SD_NAME, Dest_SD_NAME, tours, tourPurpose)

district_summary <- rbind(district_summary, best_mode_totals, tour_purp_totals, bm_am_totals, bm_tp_totals, am_tp_totals, district_totals)
write.csv(district_summary, file.path(OutDir,'OBS_District_TourFlows.csv'), row.names = F)

OBS$accessMode <- OBS$accessMode_original

### Access and Egress summaries
OBS_original <- OBS
OBS <- OBS[OBS$surveyed==1,]

t1 <- xtabs(trip_weight2015~operator+accessModeTM1.5, data = OBS)
t1 <- data.frame(t1)

t2 <- xtabs(trip_weight2015~operator+egressModeTM1.5, data = OBS)
t2 <- data.frame(t2)

write.csv(t1, file.path(OutDir,'OBS_Access_Summary.csv'), row.names = F)
write.csv(t2, file.path(OutDir,'OBS_Egress_Summary.csv'), row.names = F)

OBS <- OBS_original

### Create summaries by tour mode for mode choice targets computation
all_collapsed_technology <- aggregate(cbind(trip_weight2015)~BEST_MODE_recode+tourPurpose+accessMode+autoSuff, data = OBS, sum)
write.csv(all_collapsed_technology, file.path(OutDir,'transit_trip_targets_tourmode.csv'), row.names = FALSE)

### total boardings by operator and technology
boardings <- xtabs(board_weight2015~technology+operator, data = OBS)
boardings <- data.frame(boardings)
boardings <- boardings[boardings$Freq>0, ]
colnames(boardings) <- c("technology", "operator", "Boardings")
write.csv(boardings, file.path(OutDir,'OBS_boardings.csv'), row.names = FALSE)


### Boardings freq distribution by Access Mode and Line Haul Mode (Best Mode)
boardings_dist <- xtabs(trip_weight2015~boardings+tour_access_modeTM1.5+BEST_MODE, data = OBS)
write.table("boardings_dist", file.path(OutDir, "OBS_BoardingsDistbn.csv"), sep = ",")
write.table(boardings_dist, file.path(OutDir, "OBS_BoardingsDistbn.csv"), sep = ",", append = T)


### Calculate transfer rates by operator
transfer_data <- aggregate(cbind(board_weight2015, trip_weight2015)~operator, data = OBS, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 

write.table("transfer_data", file.path(OutDir, "OBS_TransferRate.csv"), sep = ",")
write.table(transfer_data, file.path(OutDir, "OBS_TransferRate.csv"), sep = ",", append = T)

### Caculate transfer rate by technology
transfer_data_tech <- aggregate(cbind(board_weight2015, trip_weight2015)~technology, data = OBS, sum, na.rm = TRUE)
transfer_data_tech <- transfer_data_tech %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 

write.table("transfer_data_tech", file.path(OutDir, "OBS_TransferRate.csv"), sep = ",", append = T)
write.table(transfer_data_tech, file.path(OutDir, "OBS_TransferRate.csv"), sep = ",", append = T)



# Turn back warnings;
options(warn = oldw)



#finish

