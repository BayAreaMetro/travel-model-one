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

# relevant script for transit:
# https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/PBA40/metrics/bus_opcost.py

########################################################################################


##################################
# set file paths
##################################

Scenario <- "M:/Application/Model One/RTP2017/Scenarios/2030_06_694_Amd1"
PHED_output_file <- "M:/Application/Model One/TIP2019/Excessive_delay/PHED.csv"

##################################
# Calculations for cars and trucks
##################################

# read the standard output avgload5period_vehclasses.csv from a scenario
file_cars_n_trucks <- paste(Scenario, "/OUTPUT/avgload5period_vehclasses.csv", sep="")
HwyData <- read.csv(file=file_cars_n_trucks, header=TRUE, sep=",")

# check number of rows in the dataset
nrow(HwyData)

# keep cases where facility type does not equal to 6
HwyData <- subset(HwyData, ft!=6)
nrow(HwyData)

# add a column to show 60 percent of posted speed
HwyData$ffs60pc <- HwyData$ffs*0.6

# determine threshold speed
HwyData$threshold_speed <- pmax(HwyData$ffs60pc, 20)

# determine threshold time (in minutes)
HwyData$threshold_time <- HwyData$distance/HwyData$threshold_speed*60

#------
# analysis by time period
#------

# determine if the link is below threshold in a certain time period
HwyData$below_thresholdAM <- ifelse(HwyData$cspdAM<HwyData$threshold_speed, 1, 0)
HwyData$below_thresholdPM <- ifelse(HwyData$cspdPM<HwyData$threshold_speed, 1, 0)

# congested travel time (ctim) - threshold_time
HwyData$timediffAM <- HwyData$ctimAM - HwyData$threshold_time
HwyData$timediffPM <- HwyData$ctimPM - HwyData$threshold_time

# excessive delay by link in minutes
HwyData$delayAM = HwyData$below_thresholdAM * HwyData$timediffAM
HwyData$delayPM = HwyData$below_thresholdPM * HwyData$timediffPM

# excessive delay taking volume into account
HwyData$delayXvolAM = HwyData$delayAM * (HwyData$volAM_da * 1 + HwyData$volAM_s2 * 2 + HwyData$volAM_s3 * 3 + HwyData$volAM_sm * 1 + HwyData$volAM_hv * 1
			+ HwyData$volAM_dat * 1 + HwyData$volAM_s2t * 2 + HwyData$volAM_s3t * 3 + HwyData$volAM_smt * 1 + HwyData$volAM_hvt * 1)

HwyData$delayXvolPM = HwyData$delayPM * (HwyData$volPM_da * 1 + HwyData$volPM_s2 * 2 + HwyData$volPM_s3 * 3 + HwyData$volPM_sm * 1 + HwyData$volPM_hv * 1
			+ HwyData$volPM_dat * 1 + HwyData$volPM_s2t * 2 + HwyData$volPM_s3t * 3 + HwyData$volPM_smt * 1 + HwyData$volPM_hvt * 1)

# total excessive delay in hours - cars and trucks
sum(HwyData$delayXvolAM)/60
sum(HwyData$delayXvolPM)/60

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
# according to this: https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/PBA40/metrics/bus_opcost.py
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
write.csv(BusData15FilesAM, file="M:/Application/Model One/TIP2019/Excessive_delay/temp_outfile_am.csv")
write.csv(BusData15FilesAM, file="M:/Application/Model One/TIP2019/Excessive_delay/temp_outfile_pm.csv")

# -------
# merge the bus volume to the HwyFile
# ------
HwyBusDataAM <- left_join(HwyData, BusData15FilesAM, by = c("a" = "A", "b" = "B"))
HwyBusDataPM <- left_join(HwyData, BusData15FilesPM, by = c("a" = "A", "b" = "B"))

# fill in the NAs after the left join
HwyBusDataAM$bus_vol[is.na(HwyBusDataAM$bus_vol)] <- 0
HwyBusDataPM$bus_vol[is.na(HwyBusDataPM$bus_vol)] <- 0

HwyBusDataAM$delayXbus_vol <- HwyBusDataAM$delayAM * HwyBusDataAM$bus_vol
HwyBusDataPM$delayXbus_vol <- HwyBusDataPM$delayPM *HwyBusDataPM$ bus_vol

# total excessive delay in hours - bus only
sum(HwyBusDataAM$delayXbus_vol)/60
sum(HwyBusDataPM$delayXbus_vol)/60

# total excessive delay in hours - car, bus, and trucks
(sum(HwyBusDataAM$delayXvolAM) + sum(HwyBusDataAM$delayXbus_vol))/60
(sum(HwyBusDataPM$delayXvolPM) + sum(HwyBusDataPM$delayXbus_vol))/60

##################################
# Calculate population
##################################

# read the activity pattern file to get total population
file_population <- paste(Scenario, "/OUTPUT/core_summaries/ActivityPattern.csv", sep="")
ActivityData <- read.csv(file=file_population, header=TRUE, sep=",")
totpop <- sum(ActivityData$freq)
totpop

# total excessive delay *per person* in hours - car, bus, and trucks
sum(HwyBusDataAM$delayXvolAM + HwyBusDataAM$delayXbus_vol)/60/totpop
sum(HwyBusDataPM$delayXvolPM + HwyBusDataPM$delayXbus_vol)/60/totpop


##################################
# Annualize the results
##################################
# assume 260 days 
# 52 weeks * 5 weekdays per week = 260 days
# although 52*7 = 364 and the maximum number of days in a year is 366, so the max number of weekday in a year can be 262

# total excessive delay *per person* in hours - car, bus, and trucks - annualized
PHED <- (sum(HwyBusDataAM$delayXvolAM + HwyBusDataAM$delayXbus_vol)/60/totpop + sum(HwyBusDataPM$delayXvolPM + HwyBusDataPM$delayXbus_vol)/60/totpop)* 260
PHED

# write out the results
# Annual Hours of Peak Hour Excessive Delay (PHED) Per Capita
write.csv(PHED, file=(PHED_output_file))
