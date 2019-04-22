#######################################################
### Script to summarize MTC OBS Database
### Author: Binny M Paul, binny.mathewpaul@rsginc.com
#######################################################
oldw <- getOption("warn")
options(warn = -1)
options(scipen=999)

library(plyr)
library(dplyr)
library(reshape)
library(reshape2)

library(data.table)

# one of "maz_v1_0" or "maz_v2_2"
# Just use maz_v1_0 since the onboard survey geocoding was done to maz v1.0
geography = "maz_v1_0"

# User Inputs
if (Sys.getenv("USERNAME") == "binny.paul") {
  USERPROFILE   <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
  BOX_DEV       <- file.path(USERPROFILE, "Box Sync")
  BOX_TM2       <- file.path(BOX_DEV,     "Travel Model Two Development")
  BOX_TM1.5     <- file.path(BOX_DEV,     "Travel Model 1.5")
  OBS_Dir       <- file.path(BOX_DEV,     "Survey_Database_122717")
  OBS_Anc_Dir   <- file.path(BOX_TM2,     "Observed Data", "Transit", "Onboard Survey", "Data")
  Targets_Dir   <- file.path(BOX_TM2,     "Observed Data", "Transit", "Scaled Transit Ridership Targets")
  OutDir        <- file.path(BOX_TM2,     "Observed Data", "Transit", "Onboard Survey", paste0("CalibrationSummaries_", geography))
  OutDir_TM1.5  <- file.path(BOX_TM1.5,   "Calibration", "data", "ReweightedOBS")
  if (geography == "maz_v1_0") {
    geogXWalkDir  <- file.path(BOX_TM2, "Observed Data",   "CHTS Processing", "Trip End Geocodes maz_v1_0")
    oldTazSDXWalk <- file.path(BOX_TM2, "Model Geography", "taz1454_superdistrictv1.csv")
    districtDef   <- file.path(BOX_TM2, "Model Geography", "Zones v1.0", "maz_superdistrictv1.csv")
    SkimDir       <- file.path(BOX_TM2, "Observed Data",   "RSG_CHTS")
    mazDataDir    <- file.path(BOX_TM2, "Model Inputs",    "2015_maz_v1", "landuse")
    Geog_Dir1.5   <- file.path(BOX_TM1.5,   "Calibration", "data", "GeographicData")
  } else if (geography == "maz_v2_2") {
    geogXWalkDir  <- file.path(BOX_TM2, "Observed Data",   "CHTS Processing", "Trip End Geocodes maz_v2_2")
    districtDef   <- file.path(BOX_TM2, "Model Geography", "Zones v2.2", "sd22_from_tazV2_2.csv")
    SkimDir       <- file.path(BOX_TM2, "Model Geography", "Zones v2.2")
    mazDataDir    <- file.path(BOX_TM2, "Model Inputs",    "2015_revised_mazs", "landuse")
    Geog_Dir1.5   <- file.path(BOX_TM1.5,   "Calibration", "data", "GeographicData")
  }
} else {
  OBS_Dir       <- "E:/projects/clients/mtc/data/OBS_27Dec17"
  OBS_Anc_Dir   <- OBS_Dir
  OutDir        <- file.path(OBS_Dir, "Reports")
  geogXWalkDir  <- "E:/projects/clients/mtc/data/Trip End Geocodes"
  Targets_Dir   <- "E:/projects/clients/mtc/data/TransitRidershipTargets"
  outFile       <- "OBS_SummaryStatistics.csv"
  SkimDir       <- "E:/projects/clients/mtc/data/Skim2015"
  mazDataDir    <- "E:/projects/clients/mtc/2015_calibration/landuse"
}

load(file.path(OBS_Dir,     "survey.rdata"))
load(file.path(OBS_Anc_Dir, "ancillary_variables.rdata"))
xwalk              <- read.csv(file.path(geogXWalkDir, "geographicCWalk.csv"      ), as.is = T)
xwalk_SDist        <- read.csv(districtDef, as.is = T)
oldTazSDXWalk      <- read.csv(oldTazSDXWalk, as.is = T)

DST_SKM   <- fread(file.path(SkimDir, "SOV_DIST_MD_HWYSKM.csv"), stringsAsFactors = F, header = T)
DST_SKM   <- melt(DST_SKM, id = c("DISTDA"))
colnames(DST_SKM) <- c("o", "d", "dist")

mazData   <- read.csv(file.path(mazDataDir, "maz_data.csv"), as.is = T)
mazData$COUNTY <- xwalk$COUNTYNAME[match(mazData$MAZ_ORIGINAL, xwalk$MAZ_ORIGINAL)]

# Read in target boardings for 2015
boarding_targets <- read.csv(file.path(Targets_Dir, "transitRidershipTargets2015.csv"), header = TRUE, stringsAsFactors = FALSE)

# Read in guessed O-D distribution for un-surveyed operators
unsurveyed_targets <- read.csv(file.path(Targets_Dir, "Best_Guess_Unsurveyed_Operators2015.csv"), header = TRUE, stringsAsFactors = FALSE)

# Read taz15 to SD34 crosswalk
taz15_SD <- read.csv(file.path(Geog_Dir1.5, 'geographies','taz-superdistrict-county.csv'), as.is = T)
SD_SDNAME <- taz15_SD %>%
  select(-ZONE) %>%
  group_by(SD) %>%
  distinct()

# consider only weekday records
OBS <- survey[!(survey$day_of_the_week %in% c("SATURDAY", "SUNDAY")),]
OBS_ancillary <- ancillary_df
remove(survey)
remove(ancillary_df)

summary(OBS$orig_taz)
summary(OBS$dest_taz)

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

# trip mode check
OBS$trip_mode_check <- paste(OBS$tour_access_mode, OBS$survey_tech, OBS$operator, sep = "-")


#######################################
# remove trips with missing purpose
#####################################

OBS <- OBS[OBS$agg_tour_purp>0,]



OBS_collapsed <- data.frame()
for (i in 1:6){
  t <- xtabs(trip_weight~trip_mode+auto_suff, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t, stringsAsFactors = F)
  t[] <- lapply(t, function(x) if (is.factor(x)) as.character(x) else {x})
  t$purpose <- i
  OBS_collapsed <- rbind(OBS_collapsed,t)
}
colnames(OBS_collapsed) <- c("tripMode", "autoSuff", "trips", "tourPurpose")

temp <- data.frame()
for (i in 1:6){
  t <- xtabs(weight~trip_mode+auto_suff, data = OBS[OBS$agg_tour_purp==i,])
  t <- data.frame(t, stringsAsFactors = F)
  t[] <- lapply(t, function(x) if (is.factor(x)) as.character(x) else {x})
  t$purpose <- i
  temp <- rbind(temp,t)
}
colnames(temp) <- c("tripMode", "autoSuff", "boards", "tourPurpose")

OBS_collapsed$boards <- temp$boards[match(paste(OBS_collapsed$tripMode, OBS_collapsed$autoSuff, OBS_collapsed$tourPurpose), 
                                          paste(temp$tripMode, temp$autoSuff, temp$tourPurpose))]

xwalk_mode <- unique(OBS[,c("trip_mode", "operator", "survey_tech")])
OBS_collapsed$operator <- xwalk_mode$operator[match(OBS_collapsed$tripMode, xwalk_mode$trip_mode)]
OBS_collapsed$survey_tech <- xwalk_mode$survey_tech[match(OBS_collapsed$tripMode, xwalk_mode$trip_mode)]

#accessMode is tour access mode
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

write.csv(unified_collapsed, file.path(OutDir, "unified_collapsed.csv"), row.names = FALSE)

# Copy technology from target boardings
unified_collapsed <- merge(x=unified_collapsed, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by="operator", all.x = TRUE)

#Calculate distribution of trips/boardings by technology, tour purpose, access mode and auto sufficiency
unified_collapsed_technology <- aggregate(cbind(exp_factor, boards, trips, boardWeight_2015, tripWeight_2015)~technology+tourPurpose+accessMode+autoSuff, data = unified_collapsed, sum)
unified_collapsed_technology$exp_factor <- NA

obs_technology_trips <- aggregate(unified_collapsed_technology$tripWeight_2015, by = list(technology = unified_collapsed_technology$technology), sum)
colnames(obs_technology_trips) <- c("technology", "op_totTrips")
unified_collapsed_technology <- merge(x=unified_collapsed_technology, y=obs_technology_trips, by="technology", all.x = TRUE)

obs_technology_brdngs <- aggregate(unified_collapsed_technology$boardWeight_2015, by = list(technology = unified_collapsed_technology$technology), sum)
colnames(obs_technology_brdngs) <- c("technology", "op_totBrdngs")
unified_collapsed_technology <- merge(x=unified_collapsed_technology, y=obs_technology_brdngs, by="technology", all.x = TRUE)

unified_collapsed_technology$shares_trips <- unified_collapsed_technology$tripWeight_2015/unified_collapsed_technology$op_totTrips
unified_collapsed_technology$shares_brdngs <- unified_collapsed_technology$boardWeight_2015/unified_collapsed_technology$op_totBrdngs

write.csv(unified_collapsed_technology, file.path(OutDir, "unified_collapsed_technology.csv"), row.names = FALSE)

#Remaining total boardings by technology to be distributed
other_operators <- aggregate(boarding_targets$targets2015[boarding_targets$surveyed==0], by = list(tech = boarding_targets$technology[boarding_targets$surveyed==0]), sum)

# Calculate transfer rates by operator
transfer_data <- aggregate(cbind(boards, trips)~operator, data = unified_collapsed, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = boards/trips) 
transfer_data

# Calculate transfer rate by technology
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
unified_collapsed <- unified_collapsed[,c("operator", "tourPurpose", "accessMode", "autoSuff", "boards", 
                                          "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_LB_distribution <- other_LB_distribution[,c("operator", "tourPurpose", "accessMode", "autoSuff", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_EB_distribution <- other_EB_distribution[,c("operator", "tourPurpose", "accessMode", "autoSuff", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
other_CR_distribution <- other_CR_distribution[,c("operator", "tourPurpose", "accessMode", "autoSuff", "boards", 
                                                  "trips", "exp_factor", "boardWeight_2015", "tripWeight_2015", "shares_trips", "shares_brdngs")]
all_collapsed_operators <- rbind(unified_collapsed, other_LB_distribution, other_EB_distribution, other_CR_distribution)

# by technology
all_collapsed_technology <- all_collapsed_operators
all_collapsed_technology <- merge(x=all_collapsed_technology, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by = "operator", all.x = TRUE)
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_CR"] <- "CR"
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_EB"] <- "EB"
all_collapsed_technology$technology[all_collapsed_technology$operator=="Other_LB"] <- "LB"
#all_collapsed_tech_operator_boards <- aggregate(cbind(boardWeight_2015)~technology+operator+tourPurpose+accessMode+autoSuff, data = all_collapsed_technology, sum)
#all_collapsed_tech_operator_trips <- aggregate(cbind(tripWeight_2015)~technology+operator+tourPurpose+accessMode+autoSuff, data = all_collapsed_technology, sum)
all_collapsed_technology_boards <- aggregate(cbind(boardWeight_2015)~technology+tourPurpose+accessMode+autoSuff, data = all_collapsed_technology, sum)
all_collapsed_technology_trips <- aggregate(cbind(tripWeight_2015)~technology+tourPurpose+accessMode+autoSuff, data = all_collapsed_technology, sum)

write.csv(all_collapsed_operators, file.path(OutDir, "transit_trip_targets_operators.csv"), row.names = FALSE)
write.csv(all_collapsed_technology_trips, file.path(OutDir, "transit_trip_targets_technology.csv"), row.names = FALSE)

#write.csv(trips, file.path(OutDir,"transitTripSummary_OBS.csv"), row.names = FALSE)



###################################################
### Other transit summaries for validation ###
###################################################

OBS$accessMode <- OBS$tour_access_mode   ## tour access mode
OBS$accessMode[OBS$accessMode=="Walk"] <- "walk"
OBS$accessMode[OBS$accessMode=="PNR"] <- "pnr"
OBS$accessMode[OBS$accessMode=="KNR"] <- "knr"
OBS$operator[OBS$operator=="Tri"] <- "Tri-Delta"

# Edit operator names to show local and express bus
OBS$operator[OBS$operator=="AC Transit" & OBS$survey_tech=="local bus"] <- "AC Transit [LOCAL]"
OBS$operator[OBS$operator=="AC Transit" & OBS$survey_tech=="express bus"] <- "AC Transit [EXPRESS]"

OBS$operator[OBS$operator=="County Connection" & OBS$survey_tech=="local bus"] <- "County Connection [LOCAL]"
OBS$operator[OBS$operator=="County Connection" & OBS$survey_tech=="express bus"] <- "County Connection [EXPRESS]"

OBS$operator[OBS$operator=="Golden Gate Transit (bus)" & OBS$survey_tech=="local bus"] <- "Golden Gate Transit [LOCAL]"
OBS$operator[OBS$operator=="Golden Gate Transit (bus)" & OBS$survey_tech=="express bus"] <- "Golden Gate Transit [EXPRESS]"

OBS$operator[OBS$operator=="Napa Vine" & OBS$survey_tech=="local bus"] <- "Napa Vine [LOCAL]"
OBS$operator[OBS$operator=="Napa Vine" & OBS$survey_tech=="express bus"] <- "Napa Vine [EXPRESS]"

OBS$operator[OBS$operator=="SamTrans" & OBS$survey_tech=="local bus"] <- "SamTrans [LOCAL]"
OBS$operator[OBS$operator=="SamTrans" & OBS$survey_tech=="express bus"] <- "SamTrans [EXPRESS]"

OBS$operator[OBS$operator=="SF Muni" & OBS$survey_tech=="local bus"] <- "SF Muni [LOCAL]"
OBS$operator[OBS$operator=="SF Muni" & OBS$survey_tech=="light rail"] <- "SF Muni [LRT]"

OBS$operator[OBS$operator=="VTA" & OBS$survey_tech=="local bus"] <- "VTA [LOCAL]"
OBS$operator[OBS$operator=="VTA" & OBS$survey_tech=="express bus"] <- "VTA [EXPRESS]"
OBS$operator[OBS$operator=="VTA" & OBS$survey_tech=="light rail"] <- "VTA [LRT]"

## copy technology from the targets database
OBS <- merge(x=OBS, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by="operator", all.x = TRUE)

## remove records with missing purpose, those were not included in the mode choice targets calculations
OBS <- OBS[OBS$agg_tour_purp!=-9,]
OBS$tourPurpose <- OBS$agg_tour_purp

OBS$autoSuff <- OBS$auto_suff

## Scale up weight fields to match observed boardings of surveyed operators
## For unsurveyed operators, scale up in proportion to guessed O-D distribution
## -------------------------------------------------------------------------------

# compute original OBS trip and board totals by operator, purpose, access mode and auto suff
OBS_collapsed_original_boards <- aggregate(cbind(weight)~operator+tourPurpose+accessMode+autoSuff, data = OBS, sum)
OBS_collapsed_original_boards$key <- paste(OBS_collapsed_original_boards$operator,
                                           OBS_collapsed_original_boards$tourPurpose,
                                    OBS_collapsed_original_boards$accessMode,
                                    OBS_collapsed_original_boards$autoSuff, sep = "-")

OBS_collapsed_original_trips <- aggregate(cbind(trip_weight)~operator+tourPurpose+accessMode+autoSuff, data = OBS, sum)
OBS_collapsed_original_trips$key <- paste(OBS_collapsed_original_trips$operator, 
                                          OBS_collapsed_original_trips$tourPurpose,
                                           OBS_collapsed_original_trips$accessMode,
                                           OBS_collapsed_original_trips$autoSuff, sep = "-")

unified_collapsed <- merge(x=unified_collapsed, y=boarding_targets[boarding_targets$surveyed==1,c("operator","technology")], by="operator", all.x = TRUE)
surveyed_collapsed_operator_boards <- aggregate(cbind(boardWeight_2015)~operator+tourPurpose+accessMode+autoSuff, data = unified_collapsed, sum)
surveyed_collapsed_operator_trips <- aggregate(cbind(tripWeight_2015)~operator+tourPurpose+accessMode+autoSuff, data = unified_collapsed, sum)

surveyed_collapsed_operator_boards$key <- paste(surveyed_collapsed_operator_boards$operator, 
                                                  surveyed_collapsed_operator_boards$tourPurpose,
                                                  surveyed_collapsed_operator_boards$accessMode,
                                                  surveyed_collapsed_operator_boards$autoSuff, sep = "-")
surveyed_collapsed_operator_trips$key <- paste(surveyed_collapsed_operator_trips$operator,
                                                 surveyed_collapsed_operator_trips$tourPurpose,
                                                 surveyed_collapsed_operator_trips$accessMode,
                                                 surveyed_collapsed_operator_trips$autoSuff, sep = "-")

OBS$key <- paste(OBS$operator,
                 OBS$tourPurpose,
                 OBS$accessMode,
                 OBS$autoSuff, sep = "-")

OBS_expFac <- surveyed_collapsed_operator_boards
OBS_expFac$tripWeight_2015 <- surveyed_collapsed_operator_trips$tripWeight_2015[match(OBS_expFac$key, surveyed_collapsed_operator_trips$key)]

OBS_expFac$weight <- OBS_collapsed_original_boards$weight[match(OBS_expFac$key, OBS_collapsed_original_boards$key)]
OBS_expFac$trip_weight <- OBS_collapsed_original_trips$trip_weight[match(OBS_expFac$key, OBS_collapsed_original_trips$key)]

OBS_expFac[is.na(OBS_expFac)] <- 0

OBS_expFac$board_expFac <- OBS_expFac$boardWeight_2015/OBS_expFac$weight
OBS_expFac$trip_expFac <- OBS_expFac$tripWeight_2015/OBS_expFac$trip_weight


OBS$board_expFac <- OBS_expFac$board_expFac[match(OBS$key, OBS_expFac$key)]
OBS$trip_expFac <- OBS_expFac$trip_expFac[match(OBS$key, OBS_expFac$key)]

OBS$trip_weight2015 <- OBS$trip_weight * OBS$trip_expFac
OBS$board_weight2015 <- OBS$weight * OBS$board_expFac

## Add dummy records for un-surveyed operators

# copy agency name same as operator name [Update wherever necessary]
unsurveyed_targets$operator <- unsurveyed_targets$Agency_Name
unsurveyed_targets$operator[unsurveyed_targets$operator=='Amtrak San Joaquins'] <- 'Amtrak San Joaquin'
unsurveyed_targets$operator[unsurveyed_targets$operator=='FAST'] <- 'Fairfield and Suisun Transit [LOCAL]'
unsurveyed_targets$operator[unsurveyed_targets$operator=='WestCAT'] <- 'WestCAT [LOCAL]'

# Split FAST, WestCAT and Marin Transit by technology
FAST_total_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='FAST'])
FAST_EB_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='FAST' & boarding_targets$technology=='EB'])

WestCAT_total_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='WestCAT'])
WestCAT_EB_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='WestCAT' & boarding_targets$technology=='EB'])

Marin_total_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='Marin Transit'])
Marin_GG_brd <- sum(boarding_targets$targets2015[boarding_targets$Agency_Name=='Marin Transit' & boarding_targets$operator=='Golden Gate Transit [LOCAL]'])

FAST_EB <- unsurveyed_targets[unsurveyed_targets$Agency_Name=='FAST',]
FAST_EB$operator <- 'Fairfield and Suisun Transit'
FAST_EB$Target_Boardings <- FAST_EB$Target_Boardings * (FAST_EB_brd/FAST_total_brd)
unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='FAST'] <- 
  unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='FAST'] * ((FAST_total_brd-FAST_EB_brd)/FAST_total_brd)

WestCAT_EB <- unsurveyed_targets[unsurveyed_targets$Agency_Name=='WestCAT',]
WestCAT_EB$operator <- 'WestCAT'
WestCAT_EB$Target_Boardings <- WestCAT_EB$Target_Boardings * (WestCAT_EB_brd/WestCAT_total_brd)
unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='WestCAT'] <- 
  unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='WestCAT'] * ((WestCAT_total_brd-WestCAT_EB_brd)/WestCAT_total_brd)

Marin_GG <- unsurveyed_targets[unsurveyed_targets$Agency_Name=='Marin Transit',]
Marin_GG$operator <- 'Golden Gate Transit [LOCAL]'
Marin_GG$Target_Boardings <- Marin_GG$Target_Boardings * (Marin_GG_brd/Marin_total_brd)
unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='Marin Transit'] <- 
  unsurveyed_targets$Target_Boardings[unsurveyed_targets$Agency_Name=='Marin Transit'] * ((Marin_total_brd-Marin_GG_brd)/Marin_total_brd)


#unsurveyed_targets$operator <- boarding_targets$operator[match(unsurveyed_targets$Agency_Name, boarding_targets$Agency_Name)]
unsurveyed_targets <- rbind(unsurveyed_targets, FAST_EB, WestCAT_EB, Marin_GG)

unsurveyed_targets <- merge(x=unsurveyed_targets, y=boarding_targets[boarding_targets$surveyed==0,c("operator","technology")], by="operator", all.x = TRUE)

OD_Counts <- unsurveyed_targets %>%
  group_by(operator) %>%
  summarise(technology = unique(technology), numOD = n(), Target_Boardings = sum(Target_Boardings))

nrow_LB <- nrow(unified_collapsed_technology[unified_collapsed_technology$technology=='LB',])
nrow_EB <- nrow(unified_collapsed_technology[unified_collapsed_technology$technology=='EB',])
nrow_CR <- nrow(unified_collapsed_technology[unified_collapsed_technology$technology=='CR',])

unsurveyed_targets$numDemRows[unsurveyed_targets$technology=='LB'] <- nrow_LB
unsurveyed_targets$numDemRows[unsurveyed_targets$technology=='EB'] <- nrow_EB
unsurveyed_targets$numDemRows[unsurveyed_targets$technology=='CR'] <- nrow_CR

df_unsurveyed <- unsurveyed_targets[rep(row.names(unsurveyed_targets), unsurveyed_targets$numDemRows),]

df_dem <- data.frame()
for(i in 1:nrow(OD_Counts)){
  #agency <- as.character(OD_Counts[i,c('Agency_Name')]) 
  tech <- as.character(OD_Counts[i,c('technology')]) 
  numOD <-as.numeric(OD_Counts[i,c('numOD')])  
  
  for(j in 1:numOD){
    temp_df <- unified_collapsed_technology[unified_collapsed_technology$technology==tech,]
    df_dem <- rbind(df_dem, temp_df)
  }
}

# combine the expanded dataframes to create database for unsurveyed operators
dummy_unsurveyed <- cbind(df_unsurveyed,df_dem)

# selecte the required fields
dummy_unsurveyed <- dummy_unsurveyed[,c("operator","Agency_Name","Origin_Superdistrict","Destination_Superdistrict","Target_Boardings",
                                        "technology","tourPurpose","accessMode","autoSuff","shares_trips","shares_brdngs")]

transfer_rate_LB <- transfer_data_tech$transfer_rate[transfer_data_tech$technology=="LB"]
transfer_rate_EB <- transfer_data_tech$transfer_rate[transfer_data_tech$technology=="EB"]
transfer_rate_CR <- transfer_data_tech$transfer_rate[transfer_data_tech$technology=="CR"]

dummy_unsurveyed$Target_Trips[dummy_unsurveyed$technology=='LB'] <- dummy_unsurveyed$Target_Boardings[dummy_unsurveyed$technology=='LB']/transfer_rate_LB
dummy_unsurveyed$Target_Trips[dummy_unsurveyed$technology=='EB'] <- dummy_unsurveyed$Target_Boardings[dummy_unsurveyed$technology=='EB']/transfer_rate_EB
dummy_unsurveyed$Target_Trips[dummy_unsurveyed$technology=='CR'] <- dummy_unsurveyed$Target_Boardings[dummy_unsurveyed$technology=='CR']/transfer_rate_CR

dummy_unsurveyed$board_weight2015 <- dummy_unsurveyed$Target_Boardings * dummy_unsurveyed$shares_brdngs
dummy_unsurveyed$trip_weight2015 <- dummy_unsurveyed$Target_Trips * dummy_unsurveyed$shares_trips

OBS_unsurveyed <- data.frame(matrix(ncol = length(colnames(OBS)), nrow = nrow(dummy_unsurveyed)))
colnames(OBS_unsurveyed) <- colnames(OBS)

## Add known fields to dummy records representing boards/trips from unsurveyed operators
# existing fields
OBS_unsurveyed$operator         <- dummy_unsurveyed$operator
OBS_unsurveyed$technology       <- dummy_unsurveyed$technology
OBS_unsurveyed$tourPurpose      <- dummy_unsurveyed$tourPurpose
OBS_unsurveyed$accessMode       <- dummy_unsurveyed$accessMode
OBS_unsurveyed$autoSuff         <- dummy_unsurveyed$autoSuff
OBS_unsurveyed$board_weight2015 <- dummy_unsurveyed$board_weight2015
OBS_unsurveyed$trip_weight2015  <- dummy_unsurveyed$trip_weight2015

OBS_unsurveyed$agg_tour_purp    <- OBS_unsurveyed$tourPurpose
OBS_unsurveyed$tour_access_mode <- OBS_unsurveyed$accessMode
OBS_unsurveyed$auto_suff        <- OBS_unsurveyed$autoSuff
OBS_unsurveyed$boardings        <- 1

# recode existing fields for seamleass processing
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='LB'] <- 'local bus'
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='EB'] <- 'express bus'
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='LR'] <- 'light rail'
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='Ferry'] <- 'ferry'
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='HR'] <- 'heavy rail'
OBS_unsurveyed$survey_tech[OBS_unsurveyed$technology=='CR'] <- 'commuter rail'


# new fields
OBS_unsurveyed$surveyed <- 0
OBS_unsurveyed$Orig_SD34 <- dummy_unsurveyed$Origin_Superdistrict 
OBS_unsurveyed <- OBS_unsurveyed %>%
  dplyr::left_join(SD_SDNAME[,c("SD","SD_NAME")], by = c('Orig_SD34' = 'SD')) %>%
  dplyr::rename('Orig_SD34_NAME' = 'SD_NAME')

OBS_unsurveyed$Dest_SD34 <- dummy_unsurveyed$Destination_Superdistrict 
OBS_unsurveyed <- OBS_unsurveyed %>%
  left_join(SD_SDNAME[,c("SD","SD_NAME")], by = c('Dest_SD34' = 'SD')) %>%
  dplyr::rename('Dest_SD34_NAME' = 'SD_NAME')


## Combine original OBS and dummy records for unsurveyed operators
## ----------------------------------------------

# create new fields to be consistent with dummy unsurveyed operator records
OBS$surveyed <- 1

OBS <- OBS %>%
  left_join(taz15_SD[,c("ZONE","SD","SD_NAME")], by = c('orig_taz' = 'ZONE')) %>%
  dplyr::rename('Orig_SD34' = 'SD', 'Orig_SD34_NAME' = 'SD_NAME') %>%
  left_join(taz15_SD[,c("ZONE","SD","SD_NAME")], by = c('dest_taz' = 'ZONE')) %>%
  dplyr::rename('Dest_SD34' = 'SD', 'Dest_SD34_NAME' = 'SD_NAME')

OBS <- rbind(OBS, OBS_unsurveyed)


## Check if the final weights match the target boardings
## ----------------------------------------------

#check final expanded boardings by operators
obs_operator_totals_check <- aggregate(OBS$board_weight2015, by = list(operator = OBS$operator), sum)
obs_operator_totals_check <- data.frame(obs_operator_totals_check)
colnames(obs_operator_totals_check) <- c("operator", "board_weight2015")
obs_operator_totals_check$targetBoardings <- boarding_targets$targets2015[match(obs_operator_totals_check$operator, boarding_targets$operator)]
obs_operator_totals_check

#check final expanded boardings by technology
obs_tech_totals_check <- aggregate(OBS$board_weight2015, by = list(technology = OBS$technology), sum)
obs_tech_totals_check <- data.frame(obs_tech_totals_check)
colnames(obs_tech_totals_check) <- c("technology", "board_weight2015")
boarding_targets_tech <- aggregate(boarding_targets$targets2015, by = list(technology = boarding_targets$technology), sum)
boarding_targets_tech <- data.frame(boarding_targets_tech)
colnames(boarding_targets_tech) <- c("technology", "targets2015")
obs_tech_totals_check$targetBoardings <- boarding_targets_tech$targets2015[match(obs_tech_totals_check$technology, boarding_targets_tech$technology)]
obs_tech_totals_check


## Make other data transformation to the OBS data
## ----------------------------------------------

OBS$tourtype[OBS$agg_tour_purp %in% c(1,2,3)] <- "Mandatory"
OBS$tourtype[OBS$agg_tour_purp %in% c(4,5,6)] <- "Non-Mandatory"


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

OBS$usedTotal <- OBS$usedLB+OBS$usedEB+OBS$usedLR+OBS$usedFR+OBS$usedHR+OBS$usedCR

OBS$usedLB[OBS$usedTotal==0 & OBS$path_line_haul=="LOC"] <- 1
OBS$usedEB[OBS$usedTotal==0 & OBS$path_line_haul=="EXP"] <- 1
OBS$usedLR[OBS$usedTotal==0 & OBS$path_line_haul=="LRF"] <- 1
OBS$usedHR[OBS$usedTotal==0 & OBS$path_line_haul=="HVY"] <- 1
OBS$usedCR[OBS$usedTotal==0 & OBS$path_line_haul=="COM"] <- 1

OBS$usedTotal <- OBS$usedLB+OBS$usedEB+OBS$usedLR+OBS$usedFR+OBS$usedHR+OBS$usedCR


OBS <- OBS %>%
  mutate(setType = ifelse(usedLB==1 & usedCR==0 & usedHR==0 & usedEB==0 & usedLR==0 & usedFR==0, "LOC", "None")) %>%
  mutate(setType = ifelse(usedLB==0 & (usedCR + usedHR + usedEB + usedLR + usedFR > 0), "PRE", setType)) %>%
  mutate(setType = ifelse(usedLB==1 & (usedCR + usedHR + usedEB + usedLR + usedFR > 0), "MIX", setType))

OBS$BEST_MODE <- "LB"
OBS$BEST_MODE[OBS$usedEB==1] <- "EB"
OBS$BEST_MODE[OBS$usedFR==1] <- "FR"
OBS$BEST_MODE[OBS$usedLR==1] <- "LR"
OBS$BEST_MODE[OBS$usedHR==1] <- "HR"
OBS$BEST_MODE[OBS$usedCR==1] <- "CR"


### Create all TM2 summaries using data from surveyed operators
### ------------------------------------------------------------
OBS_original <- OBS
OBS <- OBS[OBS$surveyed==1,]
### ------------------------------------------------------------

OBS$OCOUNTY <- xwalk$COUNTYNAME[match(OBS$orig_maz, xwalk$MAZ_ORIGINAL)]
OBS$DCOUNTY <- xwalk$COUNTYNAME[match(OBS$dest_maz, xwalk$MAZ_ORIGINAL)]

OBS$ODISTRICT <- xwalk_SDist$district_name[match(OBS$orig_maz, xwalk_SDist$MAZ_ORIGINAL)]
OBS$DDISTRICT <- xwalk_SDist$district_name[match(OBS$dest_maz, xwalk_SDist$MAZ_ORIGINAL)]

# read in districts using taz in old format
OBS$ODISTRICT_TAZ <- oldTazSDXWalk$district_name[match(OBS$orig_taz, oldTazSDXWalk$TAZ1454)]
OBS$DDISTRICT_TAZ <- oldTazSDXWalk$district_name[match(OBS$dest_taz, oldTazSDXWalk$TAZ1454)]

OBS$ODISTRICT[is.na(OBS$ODISTRICT)] <- OBS$ODISTRICT_TAZ[is.na(OBS$ODISTRICT)]
OBS$DDISTRICT[is.na(OBS$DDISTRICT)] <- OBS$DDISTRICT_TAZ[is.na(OBS$DDISTRICT)]

OBS$OTAZ <- xwalk$TAZ[match(OBS$orig_maz, xwalk$MAZ_ORIGINAL)]
OBS$DTAZ <- xwalk$TAZ[match(OBS$dest_maz, xwalk$MAZ_ORIGINAL)]
OBS$SKIMDIST <- DST_SKM$dist[match(paste(OBS$OTAZ, OBS$DTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]

# Define AccessEgress [mode used to access or egress transit] - same as tour access mode
#OBS$accessType <- "walk"
#OBS$accessType[OBS$access_mode=="knr" | OBS$egress_mode=="knr"] <- "knr"
#OBS$accessType[OBS$access_mode=="pnr" | OBS$egress_mode=="pnr"] <- "pnr"
OBS$accessType <- OBS$tour_access_mode

# Define number of transfers
OBS$nTransfers <- OBS$boardings - 1
OBS$nTransfers[OBS$nTransfers==0 & OBS$setType=="MIX"] <- 1

# Define period
OBS$period[OBS$depart_hour<6] <- "EA"
OBS$period[OBS$depart_hour>=6 & OBS$depart_hour<9] <- "AM"
OBS$period[OBS$depart_hour>=9 & OBS$depart_hour<15] <- "MD"
OBS$period[OBS$depart_hour>=15 & OBS$depart_hour<19] <- "PM"
OBS$period[OBS$depart_hour>=19] <- "EV"

#  Percentage of PNR trips to parking constrained zones 
mazData$parkConstraint <- 0
mazData$parkConstraint[mazData$park_area==1] <- 1
OBS$dest_park <- mazData$parkConstraint[match(OBS$dest_maz, mazData$MAZ_ORIGINAL)]
OBS$dest_park[is.na(OBS$dest_park)] <- 0


#  % of PNR trips to parking constraint zones
percentPNR <- sum(OBS$trip_weight2015[OBS$accessType=='pnr' & OBS$dest_park==1 & !is.na(OBS$dest_maz)])/
  sum(OBS$trip_weight2015[OBS$accessType=='pnr' & !is.na(OBS$dest_maz)]) * 100
cat("Percent of PNR trips to parking constraint zones", percentPNR)

write.table("percentPNR", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",")
write.table(percentPNR,   file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)

#  setType X accessType
set_access <- xtabs(trip_weight2015~setType+accessType, data = OBS)

write.table("set_access", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(set_access,   file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)

#  Transfers X setType
transfer_set <- xtabs(trip_weight2015~nTransfers+setType, data = OBS)
write.table("transfer_set", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_set,   file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)

## Calculate transfer rates by period, accessType and setType
transfer_data <- aggregate(cbind(board_weight2015, trip_weight2015)~period, data = OBS, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 
write.table("transfer_period", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_data,     file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)


transfer_data <- aggregate(cbind(board_weight2015, trip_weight2015)~accessType, data = OBS, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 
write.table("transfer_accessType", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_data,         file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)


transfer_data <- aggregate(cbind(board_weight2015, trip_weight2015)~setType, data = OBS, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 
write.table("transfer_setType", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_data,      file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)

#  Transfers X accessType
transfer_set <- xtabs(trip_weight2015~nTransfers+accessType, data = OBS)
write.table("transfer_set", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_set,   file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)

transfer_data <- aggregate(cbind(board_weight2015, trip_weight2015)~accessType + setType, data = OBS, sum, na.rm = TRUE)
transfer_data <- transfer_data %>%
  mutate(transfer_rate = board_weight2015/trip_weight2015) 
write.table("transfer_accessType_setType", file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)
write.table(transfer_data,                 file.path(OutDir, "OBS_TransitSummaries.csv"), sep = ",", append = T)


## TLFD by access mode
# code distance bins
OBS$distbin <- cut(OBS$SKIMDIST, breaks = c(seq(0,50, by=1), 9999), labels = F, right = F)
distBinCat <- data.frame(distbin = seq(1,51, by=1))

OBS$distbin10 <- cut(OBS$SKIMDIST, breaks = c(seq(0,2, by=0.1), 9999), labels = F, right = F)
distBinCat10 <- data.frame(distbin10 = seq(1,21, by=1))


# compute TLFDs by district and total
tlfd_transit <- ddply(OBS[!is.na(OBS$distbin),c("accessType", "distbin", "trip_weight2015")], c("accessType", "distbin"), summarise, transit = sum(trip_weight2015))
tlfd_transit <- cast(tlfd_transit, distbin~accessType, value = "transit", sum)
tlfd_transit$Total <- rowSums(tlfd_transit[,!colnames(tlfd_transit) %in% c("distbin")])
tlfd_transit_df <- merge(x = distBinCat, y = tlfd_transit, by = "distbin", all.x = TRUE)
tlfd_transit_df[is.na(tlfd_transit_df)] <- 0

write.csv(tlfd_transit_df, file.path(OutDir, "transitTLFD.csv"), row.names = F)

# compute TLFDs by district and total for BEST_MODE == CR
tlfd_transit <- ddply(OBS[!is.na(OBS$distbin) & OBS$BEST_MODE=="CR",c("accessType", "distbin", "trip_weight2015")], c("accessType", "distbin"), summarise, transit = sum(trip_weight2015))
tlfd_transit <- cast(tlfd_transit, distbin~accessType, value = "transit", sum)
tlfd_transit$Total <- rowSums(tlfd_transit[,!colnames(tlfd_transit) %in% c("distbin")])
tlfd_transit_df <- merge(x = distBinCat, y = tlfd_transit, by = "distbin", all.x = TRUE)
tlfd_transit_df[is.na(tlfd_transit_df)] <- 0

write.csv(tlfd_transit_df, file.path(OutDir, "transitTLFD_CR.csv"), row.names = F)

# compute TLFDs by 10ths of mile
tlfd_transit <- ddply(OBS[!is.na(OBS$distbin10),c("accessType", "distbin10", "trip_weight2015")], c("accessType", "distbin10"), summarise, transit = sum(trip_weight2015))
tlfd_transit <- cast(tlfd_transit, distbin10~accessType, value = "transit", sum)
tlfd_transit$Total <- rowSums(tlfd_transit[,!colnames(tlfd_transit) %in% c("distbin10")])
tlfd_transit_df <- merge(x = distBinCat10, y = tlfd_transit, by = "distbin10", all.x = TRUE)
tlfd_transit_df[is.na(tlfd_transit_df)] <- 0

write.csv(tlfd_transit_df, file.path(OutDir, "transitTLFD10.csv"), row.names = F)


## Create County-County transit trips summary
# filter records with missing origin/destinaiton information
trips_transit <- OBS[OBS$agg_tour_purp>0,]
trips_transit <- trips_transit[!is.na(trips_transit$OCOUNTY) & !is.na(trips_transit$DCOUNTY), ]

trips_transit <- data.table(trips_transit[,c("OCOUNTY", "DCOUNTY", "accessType", "tourtype", "trip_weight2015")])

trips_transit_summary <- trips_transit[, .(count = sum(trip_weight2015)), by = list(OCOUNTY, DCOUNTY, accessType, tourtype)]
trips_transit_summary_total <- data.table(trips_transit_summary[,c("OCOUNTY", "DCOUNTY", "accessType", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(OCOUNTY, DCOUNTY, accessType)]
trips_transit_summary_total$tourtype <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("OCOUNTY", "DCOUNTY", "accessType", "tourtype", "count")])

trips_transit_summary_total <- data.table(trips_transit_summary[,c("OCOUNTY", "DCOUNTY", "tourtype", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(OCOUNTY, DCOUNTY, tourtype)]
trips_transit_summary_total$accessType <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("OCOUNTY", "DCOUNTY", "accessType", "tourtype", "count")])


write.table(trips_transit_summary, file.path(OutDir, "trips_transit_summary.csv"), sep = ",", row.names = F)


## Create SuperDistrict - SuperDistrict transit trips summary
# filter records with missing origin/destination information
trips_transit <- OBS[OBS$agg_tour_purp>0,]
trips_transit <- trips_transit[!is.na(trips_transit$ODISTRICT) & !is.na(trips_transit$DDISTRICT), ]

trips_transit <- data.table(trips_transit[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "trip_weight2015")])

trips_transit_summary <- trips_transit[, .(count = sum(trip_weight2015)), by = list(ODISTRICT, DDISTRICT, accessType, tourtype)]
trips_transit_summary_total <- data.table(trips_transit_summary[,c("ODISTRICT", "DDISTRICT", "accessType", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(ODISTRICT, DDISTRICT, accessType)]
trips_transit_summary_total$tourtype <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "count")])

trips_transit_summary_total <- data.table(trips_transit_summary[,c("ODISTRICT", "DDISTRICT", "tourtype", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(ODISTRICT, DDISTRICT, tourtype)]
trips_transit_summary_total$accessType <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "count")])


write.table(trips_transit_summary, file.path(OutDir, "trips_transit_summary_SDist.csv"), sep = ",", row.names = F)


### District to District FLows by Line Haul Mode ###
tripsLOS <- OBS
names(tripsLOS)[names(tripsLOS)=="ODISTRICT"] <- "OSDIST"
names(tripsLOS)[names(tripsLOS)=="DDISTRICT"] <- "DSDIST"

tot_trips <- sum(tripsLOS$trip_weight2015)

tripsLOS <- tripsLOS[!is.na(tripsLOS$OSDIST) & !is.na(tripsLOS$DSDIST),]

dt_tripsLOS <- data.table(tripsLOS[,c("OSDIST","DSDIST","access_mode","BEST_MODE","usedLB","usedEB","usedFR","usedLR","usedHR","usedCR", "trip_weight2015")])

# line haul mode summary

trips_transit_summary_best <- dt_tripsLOS[, .(count = sum(trip_weight2015)), by = list(OSDIST, DSDIST, access_mode, BEST_MODE)]
trips_transit_summary_best_total <- data.table(trips_transit_summary_best[,c("OSDIST", "DSDIST", "access_mode", "count")])
trips_transit_summary_best_total <- trips_transit_summary_best_total[, (tot = sum(count)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_best_total$BEST_MODE <- "Total"
names(trips_transit_summary_best_total)[names(trips_transit_summary_best_total) == "V1"] <- "count"
trips_transit_summary_best <- rbind(trips_transit_summary_best, trips_transit_summary_best_total[,c("OSDIST", "DSDIST", "access_mode", "BEST_MODE", "count")])

trips_transit_summary_best_total <- data.table(trips_transit_summary_best[,c("OSDIST", "DSDIST", "BEST_MODE", "count")])
trips_transit_summary_best_total <- trips_transit_summary_best_total[, (tot = sum(count)), by = list(OSDIST, DSDIST, BEST_MODE)]
trips_transit_summary_best_total$access_mode <- "Total"
names(trips_transit_summary_best_total)[names(trips_transit_summary_best_total) == "V1"] <- "count"
trips_transit_summary_best <- rbind(trips_transit_summary_best, trips_transit_summary_best_total[,c("OSDIST", "DSDIST", "access_mode", "BEST_MODE", "count")])

write.table(trips_transit_summary_best, file.path(OutDir,"trips_transit_summary_best_S.csv"), sep = ",", row.names = F)

# used mode summary

trips_transit_summary_LB <- dt_tripsLOS[, .(freq = sum(usedLB*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_LB$used_mode <- "LB"
trips_transit_summary_EB <- dt_tripsLOS[, .(freq = sum(usedEB*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_EB$used_mode <- "EB"
trips_transit_summary_FR <- dt_tripsLOS[, .(freq = sum(usedFR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_FR$used_mode <- "FR"
trips_transit_summary_LR <- dt_tripsLOS[, .(freq = sum(usedLR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_LR$used_mode <- "LR"
trips_transit_summary_HR <- dt_tripsLOS[, .(freq = sum(usedHR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_HR$used_mode <- "HR"
trips_transit_summary_CR <- dt_tripsLOS[, .(freq = sum(usedCR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_CR$used_mode <- "CR"

trips_transit_summary_used <- rbind(trips_transit_summary_LB, 
                                    trips_transit_summary_EB,
                                    trips_transit_summary_FR,
                                    trips_transit_summary_LR,
                                    trips_transit_summary_HR,
                                    trips_transit_summary_CR)

trips_transit_summary_used_total <- data.table(trips_transit_summary_used[,c("OSDIST", "DSDIST", "access_mode", "freq")])
trips_transit_summary_used_total <- trips_transit_summary_used_total[, (tot = sum(freq)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_used_total$used_mode <- "Total"
names(trips_transit_summary_used_total)[names(trips_transit_summary_used_total) == "V1"] <- "freq"
trips_transit_summary_used <- rbind(trips_transit_summary_used, trips_transit_summary_used_total[,c("OSDIST", "DSDIST", "access_mode", "used_mode", "freq")])

trips_transit_summary_used_total <- data.table(trips_transit_summary_used[,c("OSDIST", "DSDIST", "used_mode", "freq")])
trips_transit_summary_used_total <- trips_transit_summary_used_total[, (tot = sum(freq)), by = list(OSDIST, DSDIST, used_mode)]
trips_transit_summary_used_total$access_mode <- "Total"
names(trips_transit_summary_used_total)[names(trips_transit_summary_used_total) == "V1"] <- "freq"
trips_transit_summary_used <- rbind(trips_transit_summary_used, trips_transit_summary_used_total[,c("OSDIST", "DSDIST", "access_mode", "used_mode", "freq")])

trips_transit_summary_used <- trips_transit_summary_used[,c("OSDIST","DSDIST","access_mode","used_mode","freq")]

write.table(trips_transit_summary_used, file.path(OutDir,"trips_transit_summary_used_S.csv"), sep = ",", row.names = F)

## Export weighted and processed OBS
#write.csv(OBS, paste(OBS_Dir,"OBS_processed_weighted_RSG.csv", sep = "//"), row.names = F)



## Generate District-District Summary in PA format
#####################################################

## Create District - District transit trips summary
# filter records with missing origin/destination information
trips_transit <- OBS[OBS$agg_tour_purp>0,]

# get origin and destination DISTRICT in PA format
trips_transit$ODISTRICT_PA <- trips_transit$ODISTRICT
trips_transit$ODISTRICT_PA[trips_transit$dest_purp=="home"] <- trips_transit$DDISTRICT[trips_transit$dest_purp=="home"]

trips_transit$DDISTRICT_PA <- trips_transit$DDISTRICT
trips_transit$DDISTRICT_PA[trips_transit$dest_purp=="home"] <- trips_transit$ODISTRICT[trips_transit$dest_purp=="home"]

trips_transit$ODISTRICT <- trips_transit$ODISTRICT_PA
trips_transit$DDISTRICT <- trips_transit$DDISTRICT_PA

trips_transit <- trips_transit[!is.na(trips_transit$ODISTRICT) & !is.na(trips_transit$DDISTRICT), ]
trips_transit <- data.table(trips_transit[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "trip_weight2015")])

trips_transit_summary <- trips_transit[, .(count = sum(trip_weight2015)), by = list(ODISTRICT, DDISTRICT, accessType, tourtype)]
trips_transit_summary_total <- data.table(trips_transit_summary[,c("ODISTRICT", "DDISTRICT", "accessType", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(ODISTRICT, DDISTRICT, accessType)]
trips_transit_summary_total$tourtype <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "count")])

trips_transit_summary_total <- data.table(trips_transit_summary[,c("ODISTRICT", "DDISTRICT", "tourtype", "count")])
trips_transit_summary_total <- trips_transit_summary_total[, (tot = sum(count)), by = list(ODISTRICT, DDISTRICT, tourtype)]
trips_transit_summary_total$accessType <- "Total"
names(trips_transit_summary_total)[names(trips_transit_summary_total) == "V1"] <- "count"
trips_transit_summary <- rbind(trips_transit_summary, trips_transit_summary_total[,c("ODISTRICT", "DDISTRICT", "accessType", "tourtype", "count")])


write.table(trips_transit_summary, file.path(OutDir, "trips_transit_summary_SDist_PA.csv"), sep = ",", row.names = F)


### District to District FLows by Line Haul Mode  in PA Format ###
tripsLOS <- OBS

# get origin and destination DISTRICT in PA format
tripsLOS$ODISTRICT_PA <- tripsLOS$ODISTRICT
tripsLOS$ODISTRICT_PA[tripsLOS$dest_purp=="home"] <- tripsLOS$DDISTRICT[tripsLOS$dest_purp=="home"]

tripsLOS$DDISTRICT_PA <- tripsLOS$DDISTRICT
tripsLOS$DDISTRICT_PA[tripsLOS$dest_purp=="home"] <- tripsLOS$ODISTRICT[tripsLOS$dest_purp=="home"]

tripsLOS$ODISTRICT <- tripsLOS$ODISTRICT_PA
tripsLOS$DDISTRICT <- tripsLOS$DDISTRICT_PA

names(tripsLOS)[names(tripsLOS)=="ODISTRICT"] <- "OSDIST"
names(tripsLOS)[names(tripsLOS)=="DDISTRICT"] <- "DSDIST"

tot_trips <- sum(tripsLOS$trip_weight2015)
tripsLOS <- tripsLOS[!is.na(tripsLOS$OSDIST) & !is.na(tripsLOS$DSDIST),]
dt_tripsLOS <- data.table(tripsLOS[,c("OSDIST","DSDIST","access_mode","BEST_MODE","usedLB","usedEB","usedFR","usedLR","usedHR","usedCR", "trip_weight2015")])

# line haul mode summary
trips_transit_summary_best <- dt_tripsLOS[, .(count = sum(trip_weight2015)), by = list(OSDIST, DSDIST, access_mode, BEST_MODE)]
trips_transit_summary_best_total <- data.table(trips_transit_summary_best[,c("OSDIST", "DSDIST", "access_mode", "count")])
trips_transit_summary_best_total <- trips_transit_summary_best_total[, (tot = sum(count)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_best_total$BEST_MODE <- "Total"
names(trips_transit_summary_best_total)[names(trips_transit_summary_best_total) == "V1"] <- "count"
trips_transit_summary_best <- rbind(trips_transit_summary_best, trips_transit_summary_best_total[,c("OSDIST", "DSDIST", "access_mode", "BEST_MODE", "count")])

trips_transit_summary_best_total <- data.table(trips_transit_summary_best[,c("OSDIST", "DSDIST", "BEST_MODE", "count")])
trips_transit_summary_best_total <- trips_transit_summary_best_total[, (tot = sum(count)), by = list(OSDIST, DSDIST, BEST_MODE)]
trips_transit_summary_best_total$access_mode <- "Total"
names(trips_transit_summary_best_total)[names(trips_transit_summary_best_total) == "V1"] <- "count"
trips_transit_summary_best <- rbind(trips_transit_summary_best, trips_transit_summary_best_total[,c("OSDIST", "DSDIST", "access_mode", "BEST_MODE", "count")])

write.table(trips_transit_summary_best, file.path(OutDir,"trips_transit_summary_best_S_PA.csv"), sep = ",", row.names = F)

# used mode summary

trips_transit_summary_LB <- dt_tripsLOS[, .(freq = sum(usedLB*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_LB$used_mode <- "LB"
trips_transit_summary_EB <- dt_tripsLOS[, .(freq = sum(usedEB*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_EB$used_mode <- "EB"
trips_transit_summary_FR <- dt_tripsLOS[, .(freq = sum(usedFR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_FR$used_mode <- "FR"
trips_transit_summary_LR <- dt_tripsLOS[, .(freq = sum(usedLR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_LR$used_mode <- "LR"
trips_transit_summary_HR <- dt_tripsLOS[, .(freq = sum(usedHR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_HR$used_mode <- "HR"
trips_transit_summary_CR <- dt_tripsLOS[, .(freq = sum(usedCR*trip_weight2015)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_CR$used_mode <- "CR"

trips_transit_summary_used <- rbind(trips_transit_summary_LB, 
                                    trips_transit_summary_EB,
                                    trips_transit_summary_FR,
                                    trips_transit_summary_LR,
                                    trips_transit_summary_HR,
                                    trips_transit_summary_CR)

trips_transit_summary_used_total <- data.table(trips_transit_summary_used[,c("OSDIST", "DSDIST", "access_mode", "freq")])
trips_transit_summary_used_total <- trips_transit_summary_used_total[, (tot = sum(freq)), by = list(OSDIST, DSDIST, access_mode)]
trips_transit_summary_used_total$used_mode <- "Total"
names(trips_transit_summary_used_total)[names(trips_transit_summary_used_total) == "V1"] <- "freq"
trips_transit_summary_used <- rbind(trips_transit_summary_used, trips_transit_summary_used_total[,c("OSDIST", "DSDIST", "access_mode", "used_mode", "freq")])

trips_transit_summary_used_total <- data.table(trips_transit_summary_used[,c("OSDIST", "DSDIST", "used_mode", "freq")])
trips_transit_summary_used_total <- trips_transit_summary_used_total[, (tot = sum(freq)), by = list(OSDIST, DSDIST, used_mode)]
trips_transit_summary_used_total$access_mode <- "Total"
names(trips_transit_summary_used_total)[names(trips_transit_summary_used_total) == "V1"] <- "freq"
trips_transit_summary_used <- rbind(trips_transit_summary_used, trips_transit_summary_used_total[,c("OSDIST", "DSDIST", "access_mode", "used_mode", "freq")])

trips_transit_summary_used <- trips_transit_summary_used[,c("OSDIST","DSDIST","access_mode","used_mode","freq")]

write.table(trips_transit_summary_used, file.path(OutDir,"trips_transit_summary_used_S_PA.csv"), sep = ",", row.names = F)



# Export weighted and processed OBS
#####################################

# remove trips with missing purose
OBS <- OBS_original
OBS <- OBS[OBS$agg_tour_purp>0,]

# Fields "trip_weight2015" and "board_weight2015" represents weights matching 2015 boardings
# data for surveyed and unsurveyed operators
write.csv(OBS, paste(OutDir_TM1.5,"OBS_processed_weighted.csv", sep = "//"), row.names = F)




# Turn back warnings;
options(warn = oldw)




