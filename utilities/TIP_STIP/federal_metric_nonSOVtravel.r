########################################################################################

# R code to calculate the Non-Single Occupancy Vehicle Travel Measure
# i.e. Percent of Non-Single Occupancy Vehicle (SOV) Travel


# Background:
# -----------
# National Performance Management Measures for Congestion Mitigation and Air Quality Improvement (CMAQ) Program
# Slides providing key definition are available in Webinar here: https://www.fhwa.dot.gov/tpm/rule.cfm (see June 1 webinar)
# Slides are no longer available for downloading online so we save them here: M:\Application\Model One\TIP2019\Excessive_delay\170601pm3.pdf

# Key definitions:
# ----------------
# Mode shares for commute only, according to slide 38

########################################################################################


##################################
# set file paths
##################################

Scenario <- "M:/Application/Model One/TIP2019/Scenarios/2020_06_701"
ModeShare_output_file <- "M:/Application/Model One/TIP2019/Scenarios/2020_06_701/OUTPUT/metrics/federal_metric_ModeShare.csv"
NonSOVTravel_output_file <- "M:/Application/Model One/TIP2019/Scenarios/2020_06_701/OUTPUT/metrics/federal_metric_NonSOVTravel.csv"

SFOakUAtaz_txt <-"M:/Application/Model One/TIP2019/Excessive_delay/SFOakUA_706TAZ.txt"
SJUAtaz_txt <- "M:/Application/Model One/TIP2019/Excessive_delay/SJUA_336TAZ.txt"

##################################
# Calculate mode shares
##################################
library(dplyr)

# read the standard output CommuteByIncomeHousehold.csv from a scenario
# this file provides data on commute characteristics by household location. Sum(freq) = commute tours
file_commute <- paste(Scenario, "/OUTPUT/core_summaries/CommuteByIncomeHousehold.csv", sep="")
CommuteData <- read.csv(file=file_commute, header=TRUE, sep=",")

# check number of rows in the dataset
nrow(CommuteData)

# read files indicating tazs that lie within the two urbanized areas respectively
SFOakUA_TAZ <- read.csv(file=SFOakUAtaz_txt, header=TRUE, sep=",")
SJUA_TAZ <- read.csv(file=SJUAtaz_txt, header=TRUE, sep=",")

# merge the geographic definitions to the dataset
CommuteData_SFOakUA <- right_join(CommuteData, SFOakUA_TAZ, by = c("orig_taz" = "TAZ1454"))
CommuteData_SJUA <- right_join(CommuteData, SJUA_TAZ, by = c("orig_taz" = "TAZ1454"))

# tabulate tour mode shares
ModeShare_SFOakUA <- CommuteData_SFOakUA  %>%
												group_by(tour_mode) %>%
												summarize(ntours = sum(freq))
ModeShare_SJUA <- CommuteData_SJUA  %>%
												group_by(tour_mode) %>%
												summarize(ntours = sum(freq))

# join the two data frames
ModeShare_TwoUAs <- full_join(ModeShare_SFOakUA, ModeShare_SJUA, by = "tour_mode")

# rename columns
colnames(ModeShare_TwoUAs)[2] <- "ntours.SFOakUA"
colnames(ModeShare_TwoUAs)[3] <- "ntours.SJUA"


# add mode labels
ModeShare_TwoUAs <- ModeShare_TwoUAs %>%
												mutate(mode_labels = recode(tour_mode,
												"1" = "Drive alone free",
												"2" = "Drive alone pay",
												"3" = "Shared ride 2 free",
												"4" = "Shared ride 2 pay",
												"5" = "Shared ride 3+ free",
												"6" = "Shared ride 3+ pay",
												"7" = "Walk",
												"8" = "Bike",
												"9" = "Walk to local bus",
												"10" = "Walk to light rail or ferry",
												"11" = "Walk to express bus",
												"12" = "Walk to BART",
												"13" = "Walk to commuter rail",
												"14" = "Drive to local bus",
												"15" = "Drive to light rail or ferry",
												"16" = "Drive to express bus",
												"17" = "Drive to BART",
												"18" = "Drive to commuter rail"
												)
												)


# reorder columns
ModeShare_TwoUAs <- ModeShare_TwoUAs[,c("tour_mode", "mode_labels", "ntours.SFOakUA", "ntours.SJUA")]

# write out a mode share file
write.table(ModeShare_TwoUAs, file=(ModeShare_output_file), sep = ",", row.names=FALSE, col.names=TRUE)

# add a SOV vs non-SOV column
ModeShare_TwoUAs <- ModeShare_TwoUAs %>%
 												mutate(SOV_nonSOV = if_else(tour_mode <=2, 1,0))

# summarize data as SOV vs non SOV
NonSOVTravel_TwoUAs <- ModeShare_TwoUAs %>%
													group_by(SOV_nonSOV) %>%
													summarize(ntours.SFOakUA = sum(ntours.SFOakUA), ntours.SJUA = sum(ntours.SJUA))

# add SOV and non-SOV labels
NonSOVTravel_TwoUAs <- NonSOVTravel_TwoUAs %>%
												mutate(SOV_labels = recode(SOV_nonSOV,
												"0" = "Non-SOV",
												"1" = "SOV"))

# reorder the columns
NonSOVTravel_TwoUAs <- NonSOVTravel_TwoUAs[,c("SOV_nonSOV", "SOV_labels", "ntours.SFOakUA", "ntours.SJUA")]

# drop the line with NA
NonSOVTravel_TwoUAs <- NonSOVTravel_TwoUAs %>%
													na.omit()

# add two percentage columns
NonSOVTravel_TwoUAs <- NonSOVTravel_TwoUAs %>%
												mutate(percent.SFOakUA = ntours.SFOakUA / sum(ntours.SFOakUA), percent.SFJUA = ntours.SJUA / sum(ntours.SJUA) )

NonSOVTravel_TwoUAs

# write out a non-SOV travel share file
write.table(NonSOVTravel_TwoUAs, file=(NonSOVTravel_output_file), sep = ",", row.names=FALSE, col.names=TRUE)
