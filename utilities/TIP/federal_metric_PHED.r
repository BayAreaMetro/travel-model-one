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

Scenario <- "M:/Application/Model One/TIP2019/Scenarios/2030_06_701"
PHED_output_file <- "M:/Application/Model One/TIP2019/Scenarios/2030_06_701/OUTPUT/metrics/federal_metric_PHED_2030_06_701.csv"

SFOakUAlinks_txt <-"M:/Application/Model One/TIP2019/Excessive_delay/LinksInSFOakUA_2020n2022.txt"
SJUAlinks_txt <-"M:/Application/Model One/TIP2019/Excessive_delay/LinksInSJUA_2020n2022.txt"

SFOakUAtaz_txt <-"M:/Application/Model One/TIP2019/Excessive_delay/SFOakUA_706TAZ.txt"
SJUAtaz_txt <- "M:/Application/Model One/TIP2019/Excessive_delay/SJUA_336TAZ.txt"

##################################
# Calculations for cars and trucks
##################################

# read the standard output avgload5period_vehclasses.csv from a scenario
file_cars_n_trucks <- paste(Scenario, "/OUTPUT/avgload5period_vehclasses.csv", sep="")
RoadwayData <- read.csv(file=file_cars_n_trucks, header=TRUE, sep=",")

# check number of rows in the dataset
nrow(RoadwayData)

# keep cases where facility type does not equal to 6
RoadwayData <- subset(RoadwayData, ft!=6)
nrow(RoadwayData)

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
			+ RoadwayData$volAM_dat * 1 + RoadwayData$volAM_s2t * 2 + RoadwayData$volAM_s3t * 3 + RoadwayData$volAM_smt * 1 + RoadwayData$volAM_hvt * 1)

RoadwayData$delayXvolPM = RoadwayData$delayPM * (RoadwayData$volPM_da * 1 + RoadwayData$volPM_s2 * 2 + RoadwayData$volPM_s3 * 3 + RoadwayData$volPM_sm * 1 + RoadwayData$volPM_hv * 1
			+ RoadwayData$volPM_dat * 1 + RoadwayData$volPM_s2t * 2 + RoadwayData$volPM_s3t * 3 + RoadwayData$volPM_smt * 1 + RoadwayData$volPM_hvt * 1)

# total excessive delay in hours - cars and trucks
sum(RoadwayData$delayXvolAM)/60
sum(RoadwayData$delayXvolPM)/60

##################################
# Calculate for delay on buses
##################################

library(foreign)
library(dplyr)

# initiate a vector to store the 15 file paths
file_busesAM <- vector()
file_busesPM <- vector()

# specify the file paths here (15x2 because of AM and PM)
#AM
file_busesAM[1] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_com_wlk.dbf", sep="")
file_busesAM[2] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_exp_wlk.dbf", sep="")
file_busesAM[3] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_hvy_wlk.dbf", sep="")
file_busesAM[4] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_loc_wlk.dbf", sep="")
file_busesAM[5] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_lrf_wlk.dbf", sep="")
file_busesAM[6] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_com_drv.dbf", sep="")
file_busesAM[7] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_com_wlk.dbf", sep="")
file_busesAM[8] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_exp_drv.dbf", sep="")
file_busesAM[9] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_exp_wlk.dbf", sep="")
file_busesAM[10] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_hvy_drv.dbf", sep="")
file_busesAM[11] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_hvy_wlk.dbf", sep="")
file_busesAM[12] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_loc_drv.dbf", sep="")
file_busesAM[13] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_loc_wlk.dbf", sep="")
file_busesAM[14] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_lrf_drv.dbf", sep="")
file_busesAM[15] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_lrf_wlk.dbf", sep="")
#PM
file_busesPM[1] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_com_wlk.dbf", sep="")
file_busesPM[2] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_exp_wlk.dbf", sep="")
file_busesPM[3] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_hvy_wlk.dbf", sep="")
file_busesPM[4] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_loc_wlk.dbf", sep="")
file_busesPM[5] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_lrf_wlk.dbf", sep="")
file_busesPM[6] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_com_drv.dbf", sep="")
file_busesPM[7] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_com_wlk.dbf", sep="")
file_busesPM[8] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_exp_drv.dbf", sep="")
file_busesPM[9] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_exp_wlk.dbf", sep="")
file_busesPM[10] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_hvy_drv.dbf", sep="")
file_busesPM[11] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_hvy_wlk.dbf", sep="")
file_busesPM[12] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_loc_drv.dbf", sep="")
file_busesPM[13] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_loc_wlk.dbf", sep="")
file_busesPM[14] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_lrf_drv.dbf", sep="")
file_busesPM[15] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_lrf_wlk.dbf", sep="")


# for loop to read the 15 files
# not sure if there is a more R way of coding this instead of the for loop, but for a loop works
for (i in 1:15) {

	# the following line is equivalent to:
	# 	BusDataAM1 <- read.dbf(file_busesAM1, as.is = FALSE)
	# 	BusDataAM2 <- read.dbf(file_busesAM2, as.is = FALSE)
	# 	BusDataAM3 <- read.dbf(file_busesAM3, as.is = FALSE)
  # AM
	assign(paste("BusDataAM",i, sep=""),read.dbf(file_busesAM[i], as.is = FALSE))
	# PM
	assign(paste("BusDataPM",i, sep=""),read.dbf(file_busesPM[i], as.is = FALSE))

	# assign worked, but can I have a vector BusDataAM[] instead?
	# this does not work
	# BusDataAM[i] <- read.dbf(file_busesAM[i], as.is = FALSE)

	next
}



# Create a list
MylistAM <- list(BusDataAM1, BusDataAM2, BusDataAM3, BusDataAM4, BusDataAM5, BusDataAM6, BusDataAM7, BusDataAM8, BusDataAM9, BusDataAM10, BusDataAM11, BusDataAM12, BusDataAM13, BusDataAM14, BusDataAM15)
MylistPM <- list(BusDataPM1, BusDataPM2, BusDataPM3, BusDataPM4, BusDataPM5, BusDataPM6, BusDataPM7, BusDataPM8, BusDataPM9, BusDataPM10, BusDataPM11, BusDataPM12, BusDataPM13, BusDataPM14, BusDataPM15)

# we only want bus lines
# i.e. MODE >= 10 and MODE<100
# according to this: https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/RTP/metrics/bus_opcost.py
# NewList1 <- filter(BusDataAM1, (MODE>=10 & MODE<100))
# NewList2 <- filter(BusDataAM2, (MODE>=10 & MODE<100))
NewList_busonlyAM <- lapply(MylistAM, function(x) filter(x, (MODE>=10 & MODE<100)))
NewList_busonlyPM <- lapply(MylistPM, function(x) filter(x, (MODE>=10 & MODE<100)))

# keep only 4 variables (A, B, MODE and AB_VOL)
NewList_4varsAM <- lapply(NewList_busonlyAM, function(x) select(x, A, B, MODE, AB_VOL))
NewList_4varsPM <- lapply(NewList_busonlyPM, function(x) select(x, A, B, MODE, AB_VOL))

NewList_ABpairsAM <- lapply(NewList_4varsAM, function(x) x %>%
   							group_by(A,B) %>%
   							summarise(volume = sum(AB_VOL)))
NewList_ABpairsPM <- lapply(NewList_4varsPM, function(x) x %>%
								group_by(A,B) %>%
								summarise(volume = sum(AB_VOL)))

# Simultaneously merge multiple data.frames in a list
# https://stackoverflow.com/questions/8091303/simultaneously-merge-multiple-data-frames-in-a-list
# list(x,y,z) %>%
#    Reduce(function(dtf1,dtf2) full_join(dtf1,dtf2,by="i"), .)

BusData15FilesAM <- NewList_ABpairsAM %>%
    Reduce(function(dtf1,dtf2) full_join(dtf1,dtf2,by=c("A","B")), .)

BusData15FilesPM <- NewList_ABpairsPM %>%
		Reduce(function(dtf1,dtf2) full_join(dtf1,dtf2,by=c("A","B")), .)

# sum across the 15 columns (that came from 15 files)
# ie sum across all columns except for column A and B
BusData15FilesAM$bus_vol <- rowSums(BusData15FilesAM[,-1:-2])
BusData15FilesPM$bus_vol <- rowSums(BusData15FilesPM[,-1:-2])

# write out a file to check
# write.csv(BusData15FilesAM, file="M:/Application/Model One/TIP2019/Excessive_delay/temp_outfile_am.csv")
# write.csv(BusData15FilesAM, file="M:/Application/Model One/TIP2019/Excessive_delay/temp_outfile_pm.csv")

# -------
# merge the bus volume to the RoadwayFile
# ------
RoadwayBusDataAM <- left_join(RoadwayData, BusData15FilesAM, by = c("a" = "A", "b" = "B"))
RoadwayBusDataPM <- left_join(RoadwayData, BusData15FilesPM, by = c("a" = "A", "b" = "B"))

# fill in the NAs after the left join
RoadwayBusDataAM$bus_vol[is.na(RoadwayBusDataAM$bus_vol)] <- 0
RoadwayBusDataPM$bus_vol[is.na(RoadwayBusDataPM$bus_vol)] <- 0

RoadwayBusDataAM$delayXbus_vol <- RoadwayBusDataAM$delayAM * RoadwayBusDataAM$bus_vol
RoadwayBusDataPM$delayXbus_vol <- RoadwayBusDataPM$delayPM * RoadwayBusDataPM$bus_vol

# total excessive delay in hours - bus only
sum(RoadwayBusDataAM$delayXbus_vol)/60
sum(RoadwayBusDataPM$delayXbus_vol)/60

# total excessive delay in hours - car, bus, and trucks
(sum(RoadwayBusDataAM$delayXvolAM) + sum(RoadwayBusDataAM$delayXbus_vol))/60
(sum(RoadwayBusDataPM$delayXvolPM) + sum(RoadwayBusDataPM$delayXbus_vol))/60


##################################
# Add geographic definitions
##################################

# Read the geographic defintions
SFOakUA_links <- read.csv(file=SFOakUAlinks_txt, header=TRUE, sep=",")
SJUA_links <- read.csv(file=SJUAlinks_txt, header=TRUE, sep=",")

SFOakUA_links <- select(SFOakUA_links, A, B, DISTANCE)
SJUA_links <- select(SJUA_links, A, B, DISTANCE)

# merge files indicating links that lie within the two urbanized areas respectively
SFOakUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, SFOakUA_links, by = c("a" = "A", "b" = "B"))
SFOakUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, SFOakUA_links, by = c("a" = "A", "b" = "B"))

SJUA_RoadwayBusDataAM <- left_join(RoadwayBusDataAM, SJUA_links, by = c("a" = "A", "b" = "B"))
SJUA_RoadwayBusDataPM <- left_join(RoadwayBusDataPM, SJUA_links, by = c("a" = "A", "b" = "B"))

# filter out the irrelevant links
SFOakUA_RoadwayBusDataAM <- filter(SFOakUA_RoadwayBusDataAM, !is.na(DISTANCE))
SFOakUA_RoadwayBusDataPM <- filter(SFOakUA_RoadwayBusDataPM, !is.na(DISTANCE))

SJUA_RoadwayBusDataAM <- filter(SJUA_RoadwayBusDataAM, !is.na(DISTANCE))
SJUA_RoadwayBusDataPM <- filter(SJUA_RoadwayBusDataPM, !is.na(DISTANCE))

##################################
# Calculate population
##################################

# read the VMT file to get total population
file_population <- paste(Scenario, "/OUTPUT/core_summaries/AutoTripsVMT_personsHomeWork.csv", sep="")
VMTData <- read.csv(file=file_population, header=TRUE, sep=",")
totpop_BayArea <- sum(VMTData$freq)
totpop_BayArea

# read files indicating tazs that lie within the two urbanized areas respectively
SFOakUA_TAZ <- read.csv(file=SFOakUAtaz_txt, header=TRUE, sep=",")
SJUA_TAZ <- read.csv(file=SJUAtaz_txt, header=TRUE, sep=",")

# merge the files
VMTData_SFOakUA <- left_join(VMTData,SFOakUA_TAZ, by = c("taz" = "TAZ1454"))
VMTData_SJUA <- left_join(VMTData,SJUA_TAZ, by = c("taz" = "TAZ1454"))

# filter out the irrelevant zones
VMTData_SFOakUA <- filter(VMTData_SFOakUA, !is.na(FID))
VMTData_SJUA <- filter(VMTData_SJUA, !is.na(FID))

# calculate total population by UA
SFOakUA_totpop <- sum(VMTData_SFOakUA$freq)
SJUA_totpop <- sum(VMTData_SJUA$freq)

# display total population by UA
SFOakUA_totpop
SJUA_totpop

# total excessive delay *per person* in hours - car, bus, and trucks (per day)
SFOakUA_AM <-sum(SFOakUA_RoadwayBusDataAM$delayXvolAM + SFOakUA_RoadwayBusDataAM$delayXbus_vol)/60/SFOakUA_totpop
SFOakUA_PM <-sum(SFOakUA_RoadwayBusDataPM$delayXvolPM + SFOakUA_RoadwayBusDataPM$delayXbus_vol)/60/SFOakUA_totpop

SJUA_AM <- sum(SJUA_RoadwayBusDataAM$delayXvolAM + SJUA_RoadwayBusDataAM$delayXbus_vol)/60/SJUA_totpop
SJUA_PM <- sum(SJUA_RoadwayBusDataPM$delayXvolPM + SJUA_RoadwayBusDataPM$delayXbus_vol)/60/SJUA_totpop


##################################
# Annualize the results
##################################
# assume 260 days
# 52 weeks * 5 weekdays per week = 260 days
# although 52*7 = 364 and the maximum number of days in a year is 366, so the max number of weekday in a year can be 262

# total excessive delay *per person* in hours - car, bus, and trucks - annualized
PHED_SFOakUA <- (SFOakUA_AM + SFOakUA_PM)* 260
PHED_SJUA <- (SJUA_AM + SJUA_PM)* 260

PHED_SFOakUA
PHED_SJUA

PHED <- data.frame(PHED_SFOakUA, PHED_SJUA)

# write out the results
# Annual Hours of Peak Hour Excessive Delay (PHED) Per Capita
write.table(PHED, file=(PHED_output_file), sep = ",", row.names=FALSE, col.names=TRUE)
