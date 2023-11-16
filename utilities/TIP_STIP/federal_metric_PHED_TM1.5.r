########################################################################################

# R code to calculate Peak Hour Excessive Delay(PHED)
# i.e. Annual Hours of Peak Hour Excessive Delay (PHED) Per Capita

# Background:
# -----------
# Webinar providing key definitions here: https://www.fhwa.dot.gov/tpm/rule.cfm (see June 1 webinar, around 30 minutes in, slide 35)
# Slides from the webinar here (no longer available online): M:\Application\Model One\TIP2019\Excessive_delay\170601pm3.pdf
# Additional info here: https://www.fhwa.dot.gov/tpm/rule/pm3/phed.pdf

# Key definitions:
# ----------------
# "Threshold": Travel Time at 20mph OR at 60% of the posted speed limit

# "Peak hours": They define "peak travel hours" as 6-10 a.m. on weekday mornings; and the weekday afternoon period is 3-7 p.m. or 4-8 p.m. (State DOTs and MPOs can choose one that suits them).
# In our travel model we have AM as 6-10 am) and PM as 3-7 pm). So these are the two time periods that we need to analysis (not all five time periods).

# Excessive delay is calculated for three modes - car (drive alone, shared by two, and shared by 3+), trucks (small and medium, and heavy vehicles), and buses.

########################################################################################


##################################
# set file paths
##################################

Scenario <- Sys.getenv("SCENARIO_DIR")
Scenario <- gsub("\\\\","/",Scenario) # switch slashes around
Scenario <- gsub('"', "", Scenario)   # no qoutes


# population inputs
taz_to_uza_file <-"X:/travel-model-one-master/utilities/TIP/taz_to_uza.csv"
tazData_file    <-file.path(Scenario, "INPUT", "landuse", "tazData.csv")

# output file location and name 
PHED_output_file <- file.path(Scenario, "OUTPUT", "metrics", "federal_metric_PHED.csv")

##################################
# Calculations for cars and trucks
##################################

# read the standard output avgload5period_vehclasses.csv from a scenario
file_cars_n_trucks <- file.path(Scenario, "/OUTPUT/avgload5period_vehclasses.csv")
RoadwayData <- read.csv(file=file_cars_n_trucks, header=TRUE, sep=",")

# check number of rows in the dataset
# nrow(RoadwayData)

# keep cases where facility type does not equal to 6
RoadwayData <- subset(RoadwayData, ft!=6)
# nrow(RoadwayData)

# add a column to show 60 percent of posted speed
RoadwayData$ffs60pc <- RoadwayData$ffs*0.6

# determine threshold speed
RoadwayData$threshold_speed <- pmax(RoadwayData$ffs60pc, 20)

# determine threshold time (in minutes)
RoadwayData$threshold_time <- RoadwayData$distance/RoadwayData$threshold_speed*60

#------
# analysis by time period
#------

# determine if the link is below threshold in a certain time period
RoadwayData$below_thresholdAM <- ifelse(RoadwayData$cspdAM<RoadwayData$threshold_speed, 1, 0)
RoadwayData$below_thresholdPM <- ifelse(RoadwayData$cspdPM<RoadwayData$threshold_speed, 1, 0)

# congested travel time (ctim) - threshold_time
RoadwayData$timediffAM <- RoadwayData$ctimAM - RoadwayData$threshold_time
RoadwayData$timediffPM <- RoadwayData$ctimPM - RoadwayData$threshold_time

# excessive delay by link in minutes
RoadwayData$delayAM = RoadwayData$below_thresholdAM * RoadwayData$timediffAM
RoadwayData$delayPM = RoadwayData$below_thresholdPM * RoadwayData$timediffPM

# excessive delay taking volume into account
RoadwayData$delayXvolAM = RoadwayData$delayAM * (RoadwayData$volAM_da * 1 + RoadwayData$volAM_s2 * 2 + RoadwayData$volAM_s3 * 3 + RoadwayData$volAM_sm * 1 + RoadwayData$volAM_hv * 1
			+ RoadwayData$volAM_dat * 1 + RoadwayData$volAM_s2t * 2 + RoadwayData$volAM_s3t * 3 + RoadwayData$volAM_smt * 1 + RoadwayData$volAM_hvt * 1
                        + RoadwayData$volAM_daav * 1 + RoadwayData$volAM_s2av * 2 + RoadwayData$volAM_s3av * 3)

RoadwayData$delayXvolPM = RoadwayData$delayPM * (RoadwayData$volPM_da * 1 + RoadwayData$volPM_s2 * 2 + RoadwayData$volPM_s3 * 3 + RoadwayData$volPM_sm * 1 + RoadwayData$volPM_hv * 1
			+ RoadwayData$volPM_dat * 1 + RoadwayData$volPM_s2t * 2 + RoadwayData$volPM_s3t * 3 + RoadwayData$volPM_smt * 1 + RoadwayData$volPM_hvt * 1
                        + RoadwayData$volPM_daav * 1 + RoadwayData$volPM_s2av * 2 + RoadwayData$volPM_s3av * 3)

# total excessive delay in hours - cars and trucks
print("total excessive delay in hours - cars and trucks")
print("------------------------------------------------")
sum(RoadwayData$delayXvolAM)/60
sum(RoadwayData$delayXvolPM)/60

##################################
# Calculate for delay on buses
##################################

library(dplyr)
library(foreign)

# read in the travel model model output file trnlink[EA,AM,MD,PM,EV]_ALLMSA.dbf
# we only want the AM and PM peak
file_trnlinkAM <- file.path(Scenario, "OUTPUT", "trn", "trnlinkAM_ALLMSA.dbf")
file_trnlinkPM <- file.path(Scenario, "OUTPUT", "trn", "trnlinkPM_ALLMSA.dbf")

trnlinkAM_df <- read.dbf(file_trnlinkAM, as.is = FALSE)
trnlinkPM_df <- read.dbf(file_trnlinkPM, as.is = FALSE)

# we only want bus lines
# i.e. MODE >= 10 and MODE<100
# according to this: https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/metrics/bus_opcost.py
busAM_df <-  filter(trnlinkAM_df,  MODE>=10 & MODE<100)
busPM_df <-  filter(trnlinkPM_df,  MODE>=10 & MODE<100)


# keep only 4 variables (A, B, MODE and AB_VOL)
busAM_df <-  select(busAM_df,  A, B, MODE, AB_VOL)
busPM_df <-  select(busPM_df,  A, B, MODE, AB_VOL)

busAM_AB_df <- busAM_df %>%
                        group_by(A,B) %>%
   					            summarise(bus_vol = sum(AB_VOL))

busPM_AB_df <- busPM_df %>%
                        group_by(A,B) %>%
	                      summarise(bus_vol = sum(AB_VOL))

# -------
# merge the bus volume to the RoadwayFile
# ------
RoadwayBusDataAM <- left_join(RoadwayData, busAM_AB_df, by = c("a" = "A", "b" = "B"))
RoadwayBusDataPM <- left_join(RoadwayData, busPM_AB_df, by = c("a" = "A", "b" = "B"))

# fill in the NAs after the left join
RoadwayBusDataAM$bus_vol[is.na(RoadwayBusDataAM$bus_vol)] <- 0
RoadwayBusDataPM$bus_vol[is.na(RoadwayBusDataPM$bus_vol)] <- 0

RoadwayBusDataAM$delayXbus_vol <- RoadwayBusDataAM$delayAM * RoadwayBusDataAM$bus_vol
RoadwayBusDataPM$delayXbus_vol <- RoadwayBusDataPM$delayPM * RoadwayBusDataPM$bus_vol

# total excessive delay in hours - bus only
print("total excessive delay in hours - bus only")
print("-----------------------------------------")
sum(RoadwayBusDataAM$delayXbus_vol)/60
sum(RoadwayBusDataPM$delayXbus_vol)/60

# total excessive delay in hours - car, bus, and trucks
print("total excessive delay in hours - car, bus, and trucks")
print("-----------------------------------------------------")
(sum(RoadwayBusDataAM$delayXvolAM) + sum(RoadwayBusDataAM$delayXbus_vol))/60
(sum(RoadwayBusDataPM$delayXvolPM) + sum(RoadwayBusDataPM$delayXbus_vol))/60


##################################
# Add geographic definitions
##################################

# Read the geographic defintions
linksUA_file <- file.path(Scenario, "INPUT", "hwy", "forPHED", "freeflow_links_UA.csv")
linksUA_df <- read.csv(file=linksUA_file, header=TRUE, sep=",")

# Rename the variable linktaz_share to be linkUA_share

linksUA_df$linkUA_share <- linksUA_df$linktaz_share

# five UAs
AntiochUA_links    <- filter(linksUA_df, NAME10=="Antioch, CA")
ConcordUA_links    <- filter(linksUA_df, NAME10=="Concord, CA")
SFOakUA_links      <- filter(linksUA_df, NAME10=="San Francisco--Oakland, CA")
SJUA_links         <- filter(linksUA_df, NAME10=="San Jose, CA")
SantaRosaUA_links  <- filter(linksUA_df, NAME10=="Santa Rosa, CA")

# merge files to select links that are within the two urbanized areas respectively
# left join because the A-B pairs in freeflow_links_UA.csv are not necessarily unique          

AntiochUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, AntiochUA_links, by = c("a" = "A", "b" = "B"))
AntiochUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, AntiochUA_links, by = c("a" = "A", "b" = "B"))

ConcordUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, ConcordUA_links, by = c("a" = "A", "b" = "B"))
ConcordUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, ConcordUA_links, by = c("a" = "A", "b" = "B"))

SFOakUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, SFOakUA_links, by = c("a" = "A", "b" = "B"))
SFOakUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, SFOakUA_links, by = c("a" = "A", "b" = "B"))

SJUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, SJUA_links, by = c("a" = "A", "b" = "B"))
SJUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, SJUA_links, by = c("a" = "A", "b" = "B"))

SantaRosaUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, SantaRosaUA_links, by = c("a" = "A", "b" = "B"))
SantaRosaUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, SantaRosaUA_links, by = c("a" = "A", "b" = "B"))

# drop links that are not in the urbanized area
AntiochUA_RoadwayBusDataAM <- filter(AntiochUA_RoadwayBusDataAM, !is.na(NAME10))
AntiochUA_RoadwayBusDataPM <- filter(AntiochUA_RoadwayBusDataPM, !is.na(NAME10))

ConcordUA_RoadwayBusDataAM <- filter(ConcordUA_RoadwayBusDataAM, !is.na(NAME10))
ConcordUA_RoadwayBusDataPM <- filter(ConcordUA_RoadwayBusDataPM, !is.na(NAME10))

SFOakUA_RoadwayBusDataAM <- filter(SFOakUA_RoadwayBusDataAM, !is.na(NAME10))
SFOakUA_RoadwayBusDataPM <- filter(SFOakUA_RoadwayBusDataPM, !is.na(NAME10))

SJUA_RoadwayBusDataAM <- filter(SJUA_RoadwayBusDataAM, !is.na(NAME10))
SJUA_RoadwayBusDataPM <- filter(SJUA_RoadwayBusDataPM, !is.na(NAME10))

SantaRosaUA_RoadwayBusDataAM <- filter(SantaRosaUA_RoadwayBusDataAM, !is.na(NAME10))
SantaRosaUA_RoadwayBusDataPM <- filter(SantaRosaUA_RoadwayBusDataPM, !is.na(NAME10))

##################################
# Calculate population
##################################

taz_to_uza_df <- read.csv(file=taz_to_uza_file, header=TRUE, sep=",")
tazData_df    <- read.csv(file=tazData_file,    header=TRUE, sep=",")

# only need the totpop column from tazData
tazData_df    <- select(tazData_df, ZONE, TOTPOP)

# join the population data to the taz to uza correspondence file
population_df <- left_join(taz_to_uza_df, tazData_df, by = c("TAZ1454" = "ZONE"))

# get total population for the Bay Area
totpop_BayArea <- sum(population_df$TOTPOP)
print("Total population:")
print("-----------------")
print("Bay Area total population:")
totpop_BayArea

# calculate total population by UA

# AntiochUA
AntiochUA_pop_df1 <- filter(population_df, Majority_Name=="Antioch, CA")
AntiochUA_pop_df1$weighted_pop <- AntiochUA_pop_df1$Majority_percent/100*AntiochUA_pop_df1$TOTPOP

AntiochUA_pop_df2 <- filter(population_df, Minority_Name=="Antioch, CA" & Minority_Name!=Majority_Name)
AntiochUA_pop_df2$weighted_pop <- AntiochUA_pop_df2$Minority_percent/100*AntiochUA_pop_df2$TOTPOP

AntiochUA_pop_df  <- rbind(AntiochUA_pop_df1, AntiochUA_pop_df2)

AntiochUA_totpop <- sum(AntiochUA_pop_df$weighted_pop)


# ConcordUA
ConcordUA_pop_df1 <- filter(population_df, Majority_Name=="Concord, CA")
ConcordUA_pop_df1$weighted_pop <- ConcordUA_pop_df1$Majority_percent/100*ConcordUA_pop_df1$TOTPOP

ConcordUA_pop_df2 <- filter(population_df, Minority_Name=="Concord, CA" & Minority_Name!=Majority_Name)
ConcordUA_pop_df2$weighted_pop <- ConcordUA_pop_df2$Minority_percent/100*ConcordUA_pop_df2$TOTPOP

ConcordUA_pop_df  <- rbind(ConcordUA_pop_df1, ConcordUA_pop_df2)

ConcordUA_totpop <- sum(ConcordUA_pop_df$weighted_pop)


# SFOakUA
SFOakUA_pop_df1 <- filter(population_df, Majority_Name=="San Francisco--Oakland, CA")
SFOakUA_pop_df1$weighted_pop <- SFOakUA_pop_df1$Majority_percent/100*SFOakUA_pop_df1$TOTPOP

SFOakUA_pop_df2 <- filter(population_df, Minority_Name=="San Francisco--Oakland, CA" & Minority_Name!=Majority_Name)
SFOakUA_pop_df2$weighted_pop <- SFOakUA_pop_df2$Minority_percent/100*SFOakUA_pop_df2$TOTPOP

SFOakUA_pop_df  <- rbind(SFOakUA_pop_df1, SFOakUA_pop_df2)

SFOakUA_totpop <- sum(SFOakUA_pop_df$weighted_pop)

# SJUA
SJUA_pop_df1 <- filter(population_df, Majority_Name=="San Jose, CA")
SJUA_pop_df1$weighted_pop <- SJUA_pop_df1$Majority_percent/100*SJUA_pop_df1$TOTPOP

SJUA_pop_df2 <- filter(population_df, Minority_Name=="San Jose, CA" & Minority_Name!=Majority_Name)
SJUA_pop_df2$weighted_pop <- SJUA_pop_df2$Minority_percent/100*SJUA_pop_df2$TOTPOP

SJUA_pop_df  <- rbind(SJUA_pop_df1, SJUA_pop_df2)

SJUA_totpop <- sum(SJUA_pop_df$weighted_pop)

# SantaRosaUA
SantaRosaUA_pop_df1 <- filter(population_df, Majority_Name=="Santa Rosa, CA")
SantaRosaUA_pop_df1$weighted_pop <- SantaRosaUA_pop_df1$Majority_percent/100*SantaRosaUA_pop_df1$TOTPOP

SantaRosaUA_pop_df2 <- filter(population_df, Minority_Name=="Santa Rosa, CA" & Minority_Name!=Majority_Name)
SantaRosaUA_pop_df2$weighted_pop <- SantaRosaUA_pop_df2$Minority_percent/100*SantaRosaUA_pop_df2$TOTPOP

SantaRosaUA_pop_df  <- rbind(SantaRosaUA_pop_df1, SantaRosaUA_pop_df2)

SantaRosaUA_totpop <- sum(SantaRosaUA_pop_df$weighted_pop)


# display total population by UA
print("Antioch UA total population:")
AntiochUA_totpop
print("Concord UA total population:")
ConcordUA_totpop
print("San Francisco-Oakland UA total population:")
SFOakUA_totpop
print("San Jose UA total population:")
SJUA_totpop
print("Santa Rosa UA total population:")
SantaRosaUA_totpop

# total excessive delay *per person* in hours - car, bus, and trucks (per day)
AntiochUA_AM <-sum((AntiochUA_RoadwayBusDataAM$delayXvolAM + AntiochUA_RoadwayBusDataAM$delayXbus_vol)*AntiochUA_RoadwayBusDataAM$linkUA_share)/60/AntiochUA_totpop
AntiochUA_PM <-sum((AntiochUA_RoadwayBusDataPM$delayXvolPM + AntiochUA_RoadwayBusDataPM$delayXbus_vol)*AntiochUA_RoadwayBusDataPM$linkUA_share)/60/AntiochUA_totpop

ConcordUA_AM <-sum((ConcordUA_RoadwayBusDataAM$delayXvolAM + ConcordUA_RoadwayBusDataAM$delayXbus_vol)*ConcordUA_RoadwayBusDataAM$linkUA_share)/60/ConcordUA_totpop
ConcordUA_PM <-sum((ConcordUA_RoadwayBusDataPM$delayXvolPM + ConcordUA_RoadwayBusDataPM$delayXbus_vol)*ConcordUA_RoadwayBusDataPM$linkUA_share)/60/ConcordUA_totpop

SFOakUA_AM <-sum((SFOakUA_RoadwayBusDataAM$delayXvolAM + SFOakUA_RoadwayBusDataAM$delayXbus_vol)*SFOakUA_RoadwayBusDataAM$linkUA_share)/60/SFOakUA_totpop
SFOakUA_PM <-sum((SFOakUA_RoadwayBusDataPM$delayXvolPM + SFOakUA_RoadwayBusDataPM$delayXbus_vol)*SFOakUA_RoadwayBusDataPM$linkUA_share)/60/SFOakUA_totpop

SJUA_AM <- sum((SJUA_RoadwayBusDataAM$delayXvolAM + SJUA_RoadwayBusDataAM$delayXbus_vol)*SJUA_RoadwayBusDataAM$linkUA_share)/60/SJUA_totpop
SJUA_PM <- sum((SJUA_RoadwayBusDataPM$delayXvolPM + SJUA_RoadwayBusDataPM$delayXbus_vol)*SJUA_RoadwayBusDataPM$linkUA_share)/60/SJUA_totpop

SantaRosaUA_AM <-sum((SantaRosaUA_RoadwayBusDataAM$delayXvolAM + SantaRosaUA_RoadwayBusDataAM$delayXbus_vol)*SantaRosaUA_RoadwayBusDataAM$linkUA_share)/60/SantaRosaUA_totpop
SantaRosaUA_PM <-sum((SantaRosaUA_RoadwayBusDataPM$delayXvolPM + SantaRosaUA_RoadwayBusDataPM$delayXbus_vol)*SantaRosaUA_RoadwayBusDataPM$linkUA_share)/60/SantaRosaUA_totpop

##################################
# Annualize the results
##################################
# assume 260 days
# 52 weeks * 5 weekdays per week = 260 days
# although 52*7 = 364 and the maximum number of days in a year is 366, so the max number of weekday in a year can be 262

# total excessive delay *per person* in hours - car, bus, and trucks - annualized
PHED_AntiochUA <- (AntiochUA_AM + AntiochUA_PM)* 260
PHED_ConcordUA <- (ConcordUA_AM + ConcordUA_PM)* 260
PHED_SFOakUA <- (SFOakUA_AM + SFOakUA_PM)* 260
PHED_SJUA <- (SJUA_AM + SJUA_PM)* 260
PHED_SantaRosaUA <- (SantaRosaUA_AM + SantaRosaUA_PM)* 260

print("Hours of total annual excessive delay -- in car, bus, and trucks -- per person")
print("-------------------------------------------------------------------------------")

print("PHED - Antioch UA")
PHED_AntiochUA
print("PHED - Concord UA")
PHED_ConcordUA
print("PHED - San Francisco/Oakland UA")
PHED_SFOakUA
print("PHED - San Jose UA")
PHED_SJUA
print("PHED - Santa Rosa UA")
PHED_SantaRosaUA

PHED <- data.frame(PHED_AntiochUA,PHED_ConcordUA,PHED_SFOakUA, PHED_SJUA,PHED_SantaRosaUA)

# write out the results
# Annual Hours of Peak Hour Excessive Delay (PHED) Per Capita
write.table(PHED, file=(PHED_output_file), sep = ",", row.names=FALSE, col.names=TRUE)
