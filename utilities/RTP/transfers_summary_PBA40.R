##################################
# Calculate number of transfers
# This script is for PBA40 only, because the trnlink outputs are pre-aggregated and no longer in .dbf in PBA50 (TM1.5)
##################################

library(foreign)
library(dplyr)

#Scenario <- "M:/Application/Model One/RTP2017/Scenarios/2040_06_694_Amd2"
Scenario <- "M:/Application/Model One/RTP2017/Scenarios/2030_06_694_Amd2"

# initiate a vector to store the 15 file paths
file_transitAM <- vector()
file_transitPM <- vector()

# specify the file paths here (15x2 because of AM and PM)
#AM
file_transitAM[1] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_com_wlk.dbf", sep="")
file_transitAM[2] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_exp_wlk.dbf", sep="")
file_transitAM[3] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_hvy_wlk.dbf", sep="")
file_transitAM[4] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_loc_wlk.dbf", sep="")
file_transitAM[5] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_drv_lrf_wlk.dbf", sep="")
file_transitAM[6] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_com_drv.dbf", sep="")
file_transitAM[7] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_com_wlk.dbf", sep="")
file_transitAM[8] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_exp_drv.dbf", sep="")
file_transitAM[9] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_exp_wlk.dbf", sep="")
file_transitAM[10] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_hvy_drv.dbf", sep="")
file_transitAM[11] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_hvy_wlk.dbf", sep="")
file_transitAM[12] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_loc_drv.dbf", sep="")
file_transitAM[13] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_loc_wlk.dbf", sep="")
file_transitAM[14] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_lrf_drv.dbf", sep="")
file_transitAM[15] <- paste(Scenario, "/OUTPUT/trn/trnlinkam_wlk_lrf_wlk.dbf", sep="")
#PM
file_transitPM[1] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_com_wlk.dbf", sep="")
file_transitPM[2] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_exp_wlk.dbf", sep="")
file_transitPM[3] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_hvy_wlk.dbf", sep="")
file_transitPM[4] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_loc_wlk.dbf", sep="")
file_transitPM[5] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_drv_lrf_wlk.dbf", sep="")
file_transitPM[6] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_com_drv.dbf", sep="")
file_transitPM[7] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_com_wlk.dbf", sep="")
file_transitPM[8] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_exp_drv.dbf", sep="")
file_transitPM[9] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_exp_wlk.dbf", sep="")
file_transitPM[10] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_hvy_drv.dbf", sep="")
file_transitPM[11] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_hvy_wlk.dbf", sep="")
file_transitPM[12] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_loc_drv.dbf", sep="")
file_transitPM[13] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_loc_wlk.dbf", sep="")
file_transitPM[14] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_lrf_drv.dbf", sep="")
file_transitPM[15] <- paste(Scenario, "/OUTPUT/trn/trnlinkPM_wlk_lrf_wlk.dbf", sep="")


# for loop to read the 15 files
# not sure if there is a more R way of coding this instead of the for loop, but for a loop works
for (i in 1:15) {

	# the following line is equivalent to:
	# 	TransitDataAM1 <- read.dbf(file_transitAM1, as.is = FALSE)
	# 	TransitDataAM2 <- read.dbf(file_transitAM2, as.is = FALSE)
	# 	TransitDataAM3 <- read.dbf(file_transitAM3, as.is = FALSE)
  # AM
	assign(paste("TransitDataAM",i, sep=""),read.dbf(file_transitAM[i], as.is = FALSE))
	# PM
	assign(paste("TransitDataPM",i, sep=""),read.dbf(file_transitPM[i], as.is = FALSE))

	# assign worked, but can I have a vector TransitDataAM[] instead?
	# this does not work
	# TransitDataAM[i] <- read.dbf(file_transitAM[i], as.is = FALSE)

	next
}



# Create a list
MylistAM <- list(TransitDataAM1, TransitDataAM2, TransitDataAM3, TransitDataAM4, TransitDataAM5, TransitDataAM6, TransitDataAM7, TransitDataAM8, TransitDataAM9, TransitDataAM10, TransitDataAM11, TransitDataAM12, TransitDataAM13, TransitDataAM14, TransitDataAM15)
MylistPM <- list(TransitDataPM1, TransitDataPM2, TransitDataPM3, TransitDataPM4, TransitDataPM5, TransitDataPM6, TransitDataPM7, TransitDataPM8, TransitDataPM9, TransitDataPM10, TransitDataPM11, TransitDataPM12, TransitDataPM13, TransitDataPM14, TransitDataPM15)


# we only want transfer links
# i.e. MODE = 3
NewList_TransferOnlyAM <- lapply(MylistAM, function(x) filter(x, (MODE==3)))
NewList_TransferOnlyPM <- lapply(MylistPM, function(x) filter(x, (MODE==3)))

# keep only 4 variables (A, B, MODE and AB_VOL)
NewList_4varsAM <- lapply(NewList_TransferOnlyAM, function(x) select(x, A, B, MODE, AB_VOL))
NewList_4varsPM <- lapply(NewList_TransferOnlyPM, function(x) select(x, A, B, MODE, AB_VOL))

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

TransitData15FilesAM <- NewList_ABpairsAM %>%
    Reduce(function(dtf1,dtf2) full_join(dtf1,dtf2,by=c("A","B")), .)

TransitData15FilesPM <- NewList_ABpairsPM %>%
		Reduce(function(dtf1,dtf2) full_join(dtf1,dtf2,by=c("A","B")), .)

# sum across the 15 columns (that came from 15 files)
# ie sum across all columns except for column A and B
TransitData15FilesAM$transfer_vol <- rowSums(TransitData15FilesAM[,-1:-2])
TransitData15FilesPM$transfer_vol <- rowSums(TransitData15FilesPM[,-1:-2])

# still to do: rename the columns
#TransitData15FilesAM <- TransitData15FilesAM %>% rename(drv_com_wlk = volume.x)
#volume.x	volume.y	volume.x.x	volume.y.y	volume.x.x.x	volume.y.y.y	volume.x.x.x.x	volume.y.y.y.y	volume.x.x.x.x.x	volume.y.y.y.y.y	volume.x.x.x.x.x.x	volume.y.y.y.y.y.y	volume.x.x.x.x.x.x.x	volume.y.y.y.y.y.y.y	volume


# write out a detailed output
write.csv(TransitData15FilesAM, file="C:/Users/ftsang/Box/Modeling and Surveys/Share Data/bespoke/Wayfinding_MTC-Steer/detailed_outfile_am.csv")
write.csv(TransitData15FilesPM, file="C:/Users/ftsang/Box/Modeling and Surveys/Share Data/bespoke/Wayfinding_MTC-Steer/detailed_outfile_pm.csv")

TransitData15FilesAM <- TransitData15FilesAM %>% select(A, B, transfer_vol)
TransitData15FilesPM <- TransitData15FilesPM %>% select(A, B, transfer_vol)

write.csv(TransitData15FilesAM, file="C:/Users/ftsang/Box/Modeling and Surveys/Share Data/bespoke/Wayfinding_MTC-Steer/transfer_outfile_am.csv")
write.csv(TransitData15FilesPM, file="C:/Users/ftsang/Box/Modeling and Surveys/Share Data/bespoke/Wayfinding_MTC-Steer/transfer_outfile_pm.csv")

