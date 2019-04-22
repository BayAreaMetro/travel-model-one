#######################################################
### Script to summarize MTC OBS Database
### Create additional inputs for mode choice targets spreadsheet
### Author: Binny M Paul, binny.mathewpaul@rsginc.com
#######################################################
oldw <- getOption("warn")
options(warn = -1)
options(scipen=999)

library(plyr)
library(dplyr)
#install.packages("reshape2")
library(reshape)
library(reshape2)

library(data.table)

# User Inputs
OBS_Dir <- "E:/projects/clients/mtc/data/OBS_27Dec17"
geogXWalkDir  <- "E:/projects/clients/mtc/data/Trip End Geocodes"
Targets_Dir <- "E:/projects/clients/mtc/data/TransitRidershipTargets"
outFile <- "OBS_SummaryStatistics.csv"
SkimDir       <- "E:/projects/clients/mtc/data/Skim2015"
mazDataDir    <- "E:/projects/clients/mtc/2015_calibration/landuse"


load(paste(OBS_Dir, "survey.rdata", sep = "/"))
load(paste(OBS_Dir, "ancillary_variables.rdata", sep = "/"))
xwalk              <- read.csv(paste(geogXWalkDir, "geographicCWalk.csv", sep = "/"), as.is = T)
xwalk_SDist        <- read.csv(paste(geogXWalkDir, "geographicCWalk_SDist.csv", sep = "/"), as.is = T) # change by Khademul

DST_SKM   <- fread(paste(SkimDir, "SOV_DIST_MD_HWYSKM.csv", sep = "/"), stringsAsFactors = F, header = T)
DST_SKM   <- melt(DST_SKM, id = c("DISTDA"))
colnames(DST_SKM) <- c("o", "d", "dist")

mazData   <- read.csv(paste(mazDataDir, "maz_data_withDensity.csv", sep = "/"), as.is = T)
mazData$COUNTY <- xwalk$COUNTYNAME[match(mazData$MAZ, xwalk$MAZ)]

# consider only weekday records
OBS <- survey[!(survey$day_of_the_week %in% c("SATURDAY", "SUNDAY")),]
OBS_ancillary <- ancillary_df
remove(survey)
remove(ancillary_df)


# Process data for calibration targets preparation
OBS$work_before <- OBS_ancillary$at_work_prior_to_orig_purp[match(OBS$Unique_ID, OBS_ancillary$Unique_ID)]
OBS$work_after <- OBS_ancillary$at_work_after_dest_purp[match(OBS$Unique_ID, OBS_ancillary$Unique_ID)]

OBS$school_before <- OBS_ancillary$at_school_prior_to_orig_purp[match(OBS$Unique_ID, OBS_ancillary$Unique_ID)]
OBS$school_after <- OBS_ancillary$at_school_after_dest_purp[match(OBS$Unique_ID, OBS_ancillary$Unique_ID)]

OBS$work_before[OBS$work_before=="at work before surveyed trip"] <- 'Y'
OBS$work_before[OBS$work_before=="not at work before surveyed trip"] <- 'N'
OBS$work_before[OBS$work_before=="not relevant"] <- 'NA'

OBS$work_after[OBS$work_after=="at work after surveyed trip"] <- 'Y'
OBS$work_after[OBS$work_after=="not at work after surveyed trip"] <- 'N'
OBS$work_after[OBS$work_after=="not relevant"] <- 'NA'

OBS$school_before[OBS$school_before=="at school before surveyed trip"] <- 'Y'
OBS$school_before[OBS$school_before=="not at school before surveyed trip"] <- 'N'
OBS$school_before[OBS$school_before=="not relevant"] <- 'NA'

OBS$school_after[OBS$school_after=="at school after surveyed trip"] <- 'Y'
OBS$school_after[OBS$school_after=="not at school after surveyed trip"] <- 'N'
OBS$school_after[OBS$school_after=="not relevant"] <- 'NA'


#Aggregate tour purposes
OBS <- OBS %>%
  mutate(agg_tour_purp = -9) %>% 
  # 1[Work]: work, work-related
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'work' | tour_purp == 'work-related'), 1, agg_tour_purp)) %>% 
  # 2[University]: university, college
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'university' | tour_purp == 'college'), 2, agg_tour_purp)) %>% 
  # 3[School]: school, grade school, high school
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'school' | tour_purp == 'high school' | tour_purp == 'grade school'), 3, agg_tour_purp)) %>% 
  # 4[Maintenance]: escorting, shopping, other maintenace
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'escorting' | tour_purp == 'shopping' | tour_purp == 'other maintenance'), 4, agg_tour_purp)) %>% 
  # 5[Discretionary]: social recreation, eat out, discretionary
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'social recreation' | tour_purp == 'eat out' | tour_purp == 'other discretionary'), 5, agg_tour_purp)) %>% 
  # 6[At-work]: At work
  mutate(agg_tour_purp = ifelse(agg_tour_purp == -9 & (tour_purp == 'at work'), 6, agg_tour_purp))


# Tour access/egress mode

# replace bike access mode with pnr
OBS$access_mode[OBS$access_mode=="bike"] <- 'pnr'
OBS$egress_mode[OBS$egress_mode=="bike"] <- 'pnr'
OBS$access_mode[OBS$access_mode=="bie"] <- 'pnr'
OBS$egress_mode[OBS$egress_mode=="bie"] <- 'pnr'

# Code missing access/egress mode

OBS$access_mode[OBS$access_mode=="."] <- "missing"
OBS$egress_mode[OBS$egress_mode=="."] <- "missing"

OBS <- OBS %>%
  mutate(access_mode = ifelse(is.na(access_mode), "missing", access_mode))
operator_access_mode <- xtabs(trip_weight~operator+access_mode, data = OBS[OBS$access_mode!="missing", ])
operator_access_mode <- data.frame(operator_access_mode)
molten <- melt(operator_access_mode, id = c("operator", "access_mode"))
operator_access_mode <- dcast(molten, operator~access_mode, sum)
operator_access_mode$tot <- operator_access_mode$walk+operator_access_mode$knr+operator_access_mode$pnr
operator_access_mode$w <- operator_access_mode$walk/operator_access_mode$tot
operator_access_mode$k <- operator_access_mode$knr/operator_access_mode$tot
operator_access_mode$p <- operator_access_mode$pnr/operator_access_mode$tot
operator_access_mode$c1 <- operator_access_mode$w
operator_access_mode$c2 <- operator_access_mode$w+operator_access_mode$k

returnAccessMode <- function(op)
{
  c1 <- operator_access_mode$c1[operator_access_mode$operator==op]
  c2 <- operator_access_mode$c2[operator_access_mode$operator==op]
  r <- runif(1)
  return(ifelse(r<c1, "walk", ifelse(r<c2, "knr", "pnr")))
}

OBS$access_mode[OBS$access_mode=="missing"] <- sapply(as.character(OBS$operator[OBS$access_mode=="missing"]),function(x) {returnAccessMode(x)} )

#-------------------------------------------------------------------------------------

OBS <- OBS %>%
  mutate(egress_mode = ifelse(is.na(egress_mode), "missing", egress_mode))
operator_egress_mode <- xtabs(trip_weight~operator+egress_mode, data = OBS[OBS$egress_mode!="missing", ])
operator_egress_mode <- data.frame(operator_egress_mode)
molten <- melt(operator_egress_mode, id = c("operator", "egress_mode"))
operator_egress_mode <- dcast(molten, operator~egress_mode, sum)
operator_egress_mode$tot <- operator_egress_mode$walk+operator_egress_mode$knr+operator_egress_mode$pnr
operator_egress_mode$w <- operator_egress_mode$walk/operator_egress_mode$tot
operator_egress_mode$k <- operator_egress_mode$knr/operator_egress_mode$tot
operator_egress_mode$p <- operator_egress_mode$pnr/operator_egress_mode$tot
operator_egress_mode$c1 <- operator_egress_mode$w
operator_egress_mode$c2 <- operator_egress_mode$w+operator_egress_mode$k

returnEgressMode <- function(op)
{
  c1 <- operator_egress_mode$c1[operator_egress_mode$operator==op]
  c2 <- operator_egress_mode$c2[operator_egress_mode$operator==op]
  r <- runif(1)
  return(ifelse(r<c1, "walk", ifelse(r<c2, "knr", "pnr")))
}

OBS$egress_mode[OBS$egress_mode=="missing"] <- sapply(as.character(OBS$operator[OBS$egress_mode=="missing"]),function(x) {returnEgressMode(x)} )

#-------------------------------------------------------------------------------------

OBS <- OBS %>%
  mutate(outbound = 1) %>% 
  # based on home destination
  mutate(outbound = ifelse(outbound == 1 & dest_purp == 'home', 0, outbound)) %>% 
  # if neither end is home and egress mode is PNR/KNR
  mutate(outbound = ifelse(outbound == 1 & orig_purp != 'home' & dest_purp != 'home' & (egress_mode == 'knr' | egress_mode == 'pnr'), 0, outbound)) %>% 
  # if neither end is home but have been to school/work before this trip
  mutate(outbound = ifelse(outbound == 1 & orig_purp != 'home' & dest_purp != 'home' & (school_before == 'Y' | work_before == 'Y'), 0, outbound))

#set NAs to 1 for outbound [Assume all missing to be outbound]
OBS$outbound[is.na(OBS$outbound)] <- 1

OBS <- OBS %>%
  mutate(tour_access_mode = access_mode) %>% 
  mutate(tour_access_mode = ifelse(outbound == 0, egress_mode, tour_access_mode))

# code missing access/egress mode as "walk"
OBS <- OBS %>%
  mutate(tour_access_mode = ifelse(tour_access_mode == "missing", "walk", tour_access_mode))

OBS <- OBS %>%
  # Access mode for at-work is always walk
  mutate(tour_access_mode = ifelse(agg_tour_purp == 6, 'walk', tour_access_mode))

# Trip mode with anchor access [at home end]
OBS <- OBS %>%
  mutate(trip_mode = paste(tour_access_mode, "-", survey_tech, "-", operator, sep = ""))

# Code missing auto sufficiency
OBS <- OBS %>%
  mutate(auto_suff = ifelse(is.na(auto_suff), "missing", auto_suff))
operator_autoSuff <- xtabs(trip_weight~operator+auto_suff, data = OBS[OBS$auto_suff!="missing", ])
operator_autoSuff <- data.frame(operator_autoSuff)
molten <- melt(operator_autoSuff, id = c("operator", "auto_suff"))
operator_autoSuff <- dcast(molten, operator~auto_suff, sum)
operator_autoSuff$tot <- operator_autoSuff$`zero autos`+operator_autoSuff$`auto sufficient`+operator_autoSuff$`auto negotiating`
operator_autoSuff$as1 <- operator_autoSuff$`zero autos`/operator_autoSuff$tot
operator_autoSuff$as2 <- operator_autoSuff$`auto negotiating`/operator_autoSuff$tot
operator_autoSuff$as3 <- operator_autoSuff$`auto sufficient`/operator_autoSuff$tot
operator_autoSuff$c1 <- operator_autoSuff$as1
operator_autoSuff$c2 <- operator_autoSuff$as1+operator_autoSuff$as2

returnAS <- function(op)
{
  c1 <- operator_autoSuff$c1[operator_autoSuff$operator==op]
  c2 <- operator_autoSuff$c2[operator_autoSuff$operator==op]
  r <- runif(1)
  return(ifelse(r<c1, "zero autos", ifelse(r<c2, "auto negotiating", "auto sufficient")))
}

OBS$auto_suff[OBS$auto_suff=="missing" | OBS$auto_suff=="Missing"] <- sapply(as.character(OBS$operator[OBS$auto_suff=="missing" | OBS$auto_suff=="Missing"]),function(x) {returnAS(x)} )

# get BEST mode or the tour mode [best among all used modes]
################################################################

operator = c("ACE",               "AC TRANSIT",        "AIR BART",         "AMTRAK",              "BART",             
             "CALTRAIN",          "COUNTY CONNECTION", "FAIRFIELD-SUISUN", "GOLDEN GATE TRANSIT", "GOLDEN GATE FERRY", 
             "MARIN TRANSIT",     "MUNI",              "NAPA VINE",        "RIO-VISTA",           "SAMTRANS",
             "SANTA ROSA CITYBUS","SF BAY FERRY",      "SOLTRANS",          "TRI-DELTA",          "UNION CITY",          
             "WESTCAT",           "VTA",               "OTHER",             "PRIVATE SHUTTLE",  "OTHER AGENCY",        
             "BLUE GOLD FERRY", "None")

technology = c("commuter rail", "local bus", "local bus", "commuter rail", "heavy rail", 
               "commuter rail", "local bus", "local bus", "express bus",   "ferry",      
               "local bus",     "local bus", "local bus", "local bus",     "local bus",
               "local bus",     "ferry",     "local bus", "local bus",     "local bus",     
               "local bus",     "local bus", "local bus", "local bus",     "local bus",     
               "ferry", "None")

opTechXWalk <- data.frame(operator, technology)

OBS$transfer_from_tech <- opTechXWalk$technology[match(OBS$transfer_from, opTechXWalk$operator)]
OBS$transfer_to_tech <- opTechXWalk$technology[match(OBS$transfer_to, opTechXWalk$operator)]

# Code Mode Set Type
OBS <- OBS %>%
  mutate(usedLB = ifelse(first_board_tech=="local bus" 
                         | transfer_from_tech=="local bus"
                         | survey_tech=="local bus"
                         | transfer_to_tech=="local bus"
                         | last_alight_tech=="local bus",1,0)) %>%
  mutate(usedCR = ifelse(first_board_tech=="commuter rail" 
                         | transfer_from_tech=="commuter rail"
                         | survey_tech=="commuter rail"
                         | transfer_to_tech=="commuter rail"
                         | last_alight_tech=="commuter rail",1,0)) %>%
  mutate(usedHR = ifelse(first_board_tech=="heavy rail" 
                         | transfer_from_tech=="heavy rail"
                         | survey_tech=="heavy rail"
                         | transfer_to_tech=="heavy rail"
                         | last_alight_tech=="heavy rail",1,0)) %>%
  mutate(usedEB = ifelse(first_board_tech=="express bus" 
                         | transfer_from_tech=="express bus"
                         | survey_tech=="express bus"
                         | transfer_to_tech=="express bus"
                         | last_alight_tech=="express bus",1,0)) %>%
  mutate(usedLR = ifelse(first_board_tech=="light rail" 
                         | transfer_from_tech=="light rail"
                         | survey_tech=="light rail"
                         | transfer_to_tech=="light rail"
                         | last_alight_tech=="light rail",1,0)) %>%
  mutate(usedFR = ifelse(first_board_tech=="ferry" 
                         | transfer_from_tech=="ferry"
                         | survey_tech=="ferry"
                         | transfer_to_tech=="ferry"
                         | last_alight_tech=="ferry",1,0))

# recode used fields based on path line haul code
OBS$usedLB[is.na(OBS$usedLB)] <- 0
OBS$usedEB[is.na(OBS$usedEB)] <- 0
OBS$usedLR[is.na(OBS$usedLR)] <- 0
OBS$usedFR[is.na(OBS$usedFR)] <- 0
OBS$usedHR[is.na(OBS$usedHR)] <- 0
OBS$usedCR[is.na(OBS$usedCR)] <- 0

OBS$usedTotal <- OBS$usedLB+OBS$usedEB+OBS$usedFR+OBS$usedLR+OBS$usedHR+OBS$usedCR

OBS$usedLB[OBS$usedTotal==0 & OBS$path_line_haul=="LOC"] <- 1
OBS$usedEB[OBS$usedTotal==0 & OBS$path_line_haul=="EXP"] <- 1
OBS$usedLR[OBS$usedTotal==0 & OBS$path_line_haul=="LRF"] <- 1
OBS$usedHR[OBS$usedTotal==0 & OBS$path_line_haul=="HVY"] <- 1
OBS$usedCR[OBS$usedTotal==0 & OBS$path_line_haul=="COM"] <- 1

OBS$BEST_MODE <- "LB"
OBS$BEST_MODE[OBS$usedEB==1] <- "EB"
OBS$BEST_MODE[OBS$usedFR==1] <- "FR"
OBS$BEST_MODE[OBS$usedLR==1] <- "LR"
OBS$BEST_MODE[OBS$usedHR==1] <- "HR"
OBS$BEST_MODE[OBS$usedCR==1] <- "CR"

########################################

OBS_collapsed <- data.frame()
for (i in 1:6){
  t <- xtabs(trip_weight~trip_mode+BEST_MODE, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t, stringsAsFactors = F)
  t$purpose <- i
  OBS_collapsed <- rbind(OBS_collapsed,t)
}
colnames(OBS_collapsed) <- c("tripMode", "BEST_MODE", "trips", "tourPurpose")

temp <- data.frame()
for (i in 1:6){
  t <- xtabs(weight~trip_mode+BEST_MODE, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t, stringsAsFactors = F)
  t$purpose <- i
  temp <- rbind(temp,t)
}
colnames(temp) <- c("tripMode", "BEST_MODE", "boards", "tourPurpose")

OBS_collapsed$boards <- temp$boards[match(paste(OBS_collapsed$tripMode, OBS_collapsed$BEST_MODE, OBS_collapsed$tourPurpose), 
                                          paste(temp$tripMode, temp$BEST_MODE, temp$tourPurpose))]

xwalk_mode <- unique(OBS[,c("trip_mode", "operator", "survey_tech")])
OBS_collapsed$operator <- xwalk_mode$operator[match(OBS_collapsed$tripMode, xwalk_mode$trip_mode)]
OBS_collapsed$survey_tech <- xwalk_mode$survey_tech[match(OBS_collapsed$tripMode, xwalk_mode$trip_mode)]


unified_collapsed <- OBS_collapsed
unified_collapsed$accessMode <- sapply(as.character(unified_collapsed$tripMode),function(x) unlist(strsplit(x, "-"))[[1]] )
unified_collapsed$accessMode[unified_collapsed$accessMode=="Walk"] <- "walk"
unified_collapsed$accessMode[unified_collapsed$accessMode=="PNR"] <- "pnr"
unified_collapsed$accessMode[unified_collapsed$accessMode=="KNR"] <- "knr"
unified_collapsed$survey_tech <- sapply(as.character(unified_collapsed$tripMode),function(x) unlist(strsplit(x, "-"))[[2]] )
unified_collapsed$operator <- sapply(as.character(unified_collapsed$tripMode),function(x) unlist(strsplit(x, "-"))[[3]] )
unified_collapsed$operator[unified_collapsed$operator=="Tri"] <- "Tri-Delta"

# Edit operator names to show local and express bus
unified_collapsed$operator[unified_collapsed$operator=="AC Transit" & unified_collapsed$survey_tech=="local bus"] <- "AC Transit [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="AC Transit" & unified_collapsed$survey_tech=="express bus"] <- "AC Transit [EXPRESS]"

unified_collapsed$operator[unified_collapsed$operator=="County Connection" & unified_collapsed$survey_tech=="local bus"] <- "County Connection [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="County Connection" & unified_collapsed$survey_tech=="express bus"] <- "County Connection [EXPRESS]"

unified_collapsed$operator[unified_collapsed$operator=="Golden Gate Transit (bus)" & unified_collapsed$survey_tech=="local bus"] <- "Golden Gate Transit [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="Golden Gate Transit (bus)" & unified_collapsed$survey_tech=="express bus"] <- "Golden Gate Transit [EXPRESS]"

unified_collapsed$operator[unified_collapsed$operator=="Napa Vine" & unified_collapsed$survey_tech=="local bus"] <- "Napa Vine [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="Napa Vine" & unified_collapsed$survey_tech=="express bus"] <- "Napa Vine [EXPRESS]"

unified_collapsed$operator[unified_collapsed$operator=="SamTrans" & unified_collapsed$survey_tech=="local bus"] <- "SamTrans [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="SamTrans" & unified_collapsed$survey_tech=="express bus"] <- "SamTrans [EXPRESS]"

unified_collapsed$operator[unified_collapsed$operator=="SF Muni" & unified_collapsed$survey_tech=="local bus"] <- "SF Muni [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="SF Muni" & unified_collapsed$survey_tech=="light rail"] <- "SF Muni [LRT]"

unified_collapsed$operator[unified_collapsed$operator=="VTA" & unified_collapsed$survey_tech=="local bus"] <- "VTA [LOCAL]"
unified_collapsed$operator[unified_collapsed$operator=="VTA" & unified_collapsed$survey_tech=="express bus"] <- "VTA [EXPRESS]"
unified_collapsed$operator[unified_collapsed$operator=="VTA" & unified_collapsed$survey_tech=="light rail"] <- "VTA [LRT]"


# code technology
survey_tech <- c("commuter rail", "express bus", "ferry", "heavy rail", "local bus",  "metro", "cable car", "SCVTA Express", "SCVTA Local", "SCVTA LRT")
technology <- c("CR", "EB", "Ferry", "HR", "LB", "")

# Calculate group total boarding by operator
obs_operator_totals <- aggregate(unified_collapsed$boards, by = list(operator = unified_collapsed$operator), sum)
obs_operator_totals <- data.frame(obs_operator_totals)
colnames(obs_operator_totals) <- c("operator", "boardWeight")

# Read in target boardings for 2015
boarding_targets <- read.csv(paste(Targets_Dir, "transitRidershipTargets2015.csv", sep = "/"), header = TRUE, stringsAsFactors = FALSE)
target_operator_totals <- aggregate(boarding_targets$targets2015, by = list(operator = boarding_targets$operator), sum)
target_operator_totals <- data.frame(target_operator_totals)
colnames(target_operator_totals) <- c("operator", "targetBoardings")

# Compute expansion factors
expansion_factors <- obs_operator_totals
expansion_factors$targetBoardings <- target_operator_totals$targetBoardings[match(expansion_factors$operator, target_operator_totals$operator)]

expansion_factors <- expansion_factors %>%
  mutate(exp_factor = targetBoardings/boardWeight) 

unified_collapsed$exp_factor <- expansion_factors$exp_factor[match(unified_collapsed$operator, expansion_factors$operator)]
unified_collapsed$boardWeight_2015 <- unified_collapsed$boards * unified_collapsed$exp_factor
unified_collapsed$tripWeight_2015 <- unified_collapsed$trips * unified_collapsed$exp_factor

#check final expanded boardings
obs_operator_totals_check <- aggregate(unified_collapsed$boardWeight_2015, by = list(operator = unified_collapsed$operator), sum)
obs_operator_totals_check <- data.frame(obs_operator_totals_check)
colnames(obs_operator_totals_check) <- c("operator", "boardWeight2015")
obs_operator_totals_check$targetBoardings <- target_operator_totals$targetBoardings[match(obs_operator_totals_check$operator, target_operator_totals$operator)]
obs_operator_totals_check

#Calculate distribution of trips/boardings by operator, tour purpose, access mode and auto sufficiency
obs_operator_trips <- aggregate(unified_collapsed$tripWeight_2015, by = list(operator = unified_collapsed$operator), sum)
colnames(obs_operator_trips) <- c("operator", "op_totTrips")
unified_collapsed <- merge(x=unified_collapsed, y=obs_operator_trips, by="operator", all.x = TRUE)

obs_operator_brdngs <- aggregate(unified_collapsed$boardWeight_2015, by = list(operator = unified_collapsed$operator), sum)
colnames(obs_operator_brdngs) <- c("operator", "op_totBrdngs")
unified_collapsed <- merge(x=unified_collapsed, y=obs_operator_brdngs, by="operator", all.x = TRUE)

unified_collapsed$shares_trips <- unified_collapsed$tripWeight_2015/unified_collapsed$op_totTrips
unified_collapsed$shares_brdngs <- unified_collapsed$boardWeight_2015/unified_collapsed$op_totBrdngs

write.csv(unified_collapsed, paste(OBS_Dir, "Reports_TM15//unified_collapsed.csv", sep = "//"), row.names = FALSE)

# Copy technology from target boardings
unified_collapsed <- merge(x=unified_collapsed, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by="operator", all.x = TRUE)

#Calculate distribution of trips/boardings by technology, tour purpose, access mode and BEST_MODE
unified_collapsed_technology <- aggregate(cbind(exp_factor, boards, trips, boardWeight_2015, tripWeight_2015)~technology+tourPurpose+accessMode+BEST_MODE, data = unified_collapsed, sum)
unified_collapsed_technology$exp_factor <- NA

obs_technology_trips <- aggregate(unified_collapsed_technology$tripWeight_2015, by = list(technology = unified_collapsed_technology$technology), sum)
colnames(obs_technology_trips) <- c("technology", "op_totTrips")
unified_collapsed_technology <- merge(x=unified_collapsed_technology, y=obs_technology_trips, by="technology", all.x = TRUE)

obs_technology_brdngs <- aggregate(unified_collapsed_technology$boardWeight_2015, by = list(technology = unified_collapsed_technology$technology), sum)
colnames(obs_technology_brdngs) <- c("technology", "op_totBrdngs")
unified_collapsed_technology <- merge(x=unified_collapsed_technology, y=obs_technology_brdngs, by="technology", all.x = TRUE)

unified_collapsed_technology$shares_trips <- unified_collapsed_technology$tripWeight_2015/unified_collapsed_technology$op_totTrips
unified_collapsed_technology$shares_brdngs <- unified_collapsed_technology$boardWeight_2015/unified_collapsed_technology$op_totBrdngs

write.csv(unified_collapsed_technology, paste(OBS_Dir, "Reports_TM15//unified_collapsed_technology.csv", sep = "//"), row.names = FALSE)

#Remaining total boardings by technology to be distributed
other_operators <- aggregate(boarding_targets$targets2015[boarding_targets$surveyed==0], by = list(tech = boarding_targets$technology[boarding_targets$surveyed==0]), sum)

# Calculate transfer rates by operator
transfer_data <- aggregate(cbind(boards, trips)~operator, data = unified_collapsed, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = boards/trips) 
transfer_data

# Caculate transfer rate by technology
transfer_data_tech <- aggregate(cbind(boards, trips)~technology, data = unified_collapsed, sum, na.rm = TRUE)
transfer_data_tech <- transfer_data_tech %>%
  mutate(transfer_rate = boards/trips) 
transfer_data_tech

#Other operator commuter rail targets [Caltrain transfer rates and distribution used]
CR_boardings <- other_operators$x[other_operators$tech=="CR"]
CR_trips <- CR_boardings/transfer_data_tech$transfer_rate[transfer_data_tech$technology=="CR"]
other_CR_distribution <- unified_collapsed_technology[unified_collapsed_technology$technology=="CR",]
other_CR_distribution$operator <- "Other_CR"
other_CR_distribution$boardWeight_2015 <- CR_boardings*other_CR_distribution$shares_brdngs
other_CR_distribution$tripWeight_2015 <- CR_trips*other_CR_distribution$shares_trips
other_CR_distribution$boards <- NA
other_CR_distribution$trips <- NA
other_CR_distribution$exp_factor <- NA

#Other operator bus targets [LAVTA transfer rates and distribution used]
LB_boardings <- other_operators$x[other_operators$tech=="LB"]
LB_trips <- LB_boardings/transfer_data_tech$transfer_rate[transfer_data_tech$technology=="LB"]
other_LB_distribution <- unified_collapsed_technology[unified_collapsed_technology$technology=="LB",]
other_LB_distribution$operator <- "Other_LB"
other_LB_distribution$boardWeight_2015 <- LB_boardings*other_LB_distribution$shares_brdngs
other_LB_distribution$tripWeight_2015 <- LB_trips*other_LB_distribution$shares_trips
other_LB_distribution$boards <- NA
other_LB_distribution$trips <- NA
other_LB_distribution$exp_factor <- NA

#Other operator express bus targets
EB_boardings <- other_operators$x[other_operators$tech=="EB"]
EB_trips <- EB_boardings/transfer_data_tech$transfer_rate[transfer_data_tech$technology=="EB"]
other_EB_distribution <- unified_collapsed_technology[unified_collapsed_technology$technology=="EB",]
other_EB_distribution$operator <- "Other_EB"
other_EB_distribution$boardWeight_2015 <- EB_boardings*other_EB_distribution$shares_brdngs
other_EB_distribution$tripWeight_2015 <- EB_trips*other_EB_distribution$shares_trips
other_EB_distribution$boards <- NA
other_EB_distribution$trips <- NA
other_EB_distribution$exp_factor <- NA

# by operator
unified_collapsed <- unified_collapsed[,c("operator", "tourPurpose", "accessMode", "BEST_MODE", "boards", 
                                          "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_LB_distribution <- other_LB_distribution[,c("operator", "tourPurpose", "accessMode", "BEST_MODE", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_EB_distribution <- other_EB_distribution[,c("operator", "tourPurpose", "accessMode", "BEST_MODE", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_CR_distribution <- other_CR_distribution[,c("operator", "tourPurpose", "accessMode", "BEST_MODE", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
all_collapsed_operators <- rbind(unified_collapsed, other_LB_distribution, other_EB_distribution,other_CR_distribution)

# by technology
all_collapsed_technology <- all_collapsed_operators
all_collapsed_technology <- merge(x=all_collapsed_technology, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by = "operator", all.x = TRUE)
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_CR"] <- "CR"
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_EB"] <- "EB"
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_LB"] <- "LB"
all_collapsed_technology$BEST_MODE[all_collapsed_technology$operator=="Other_CR"] <- "CR"
all_collapsed_technology$BEST_MODE[all_collapsed_technology$operator=="Other_EB"] <- "EB"
all_collapsed_technology$BEST_MODE[all_collapsed_technology$operator=="Other_LB"] <- "LB"
all_collapsed_technology <- aggregate(cbind(tripWeight_2015)~technology+tourPurpose+accessMode+BEST_MODE, data = all_collapsed_technology, sum)


write.csv(all_collapsed_operators, paste(OBS_Dir, "Reports_TM15\\transit_trip_targets_operators.csv", sep = "/"), row.names = FALSE)
write.csv(all_collapsed_technology, paste(OBS_Dir, "Reports_TM15\\transit_trip_targets_technology_BESTMODE.csv", sep = "/"), row.names = FALSE)


# Turn back warnings;
options(warn = oldw)





