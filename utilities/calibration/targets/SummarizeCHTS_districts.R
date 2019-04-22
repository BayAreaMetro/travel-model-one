#######################################################
### Script for summarizing CHTS
### Author: Binny M Paul, binny.paul@rsginc.com
### Oct 2017
### Copy of OHAS processing script
#######################################################

#-------------------------------------------------------------------------------
# person trips to be used for tour/trip mode choice
# unique joint tours to be used for all joint tour level summaries
# unique joint tours to be used for all summaries created for joint purposes (e.g., jMain & jDisc)
# person trips/tours to be used for all totals
#-------------------------------------------------------------------------------

# Following standard purpose/market segmentation coding to be used for tours/trips
#-------------------------------------------------------------------------------

# Recode tour purpose into unique market segmentations
# Work   - [No Subtours ], [All            ], [TOURPURP - (1,10)    ] 
# Univ   - [No Subtours ], [All            ], [TOURPURP - (2)       ] 
# Schl   - [No Subtours ], [All            ], [TOURPURP - (3)       ]
# iEsc   - [No Subtours ], [All            ], [TOURPURP - (4)       ]
# iShop  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (5)       ]
# iMain  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (6)       ]
# iEati  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (7)       ]
# iVisi  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (8)       ]
# iDisc  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (9)       ]   
# jShop  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (5)       ]
# jMain  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (6)       ]
# jEati  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (7)       ]
# jVisi  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (8)       ]
# jDisc  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (9)       ]   
# AtWork - [All Subtours], [All            ], [TOURPURP - (All)     ]    
# Other  - [No Subtours ], [All            ], [TOURPURP - (11,12,13)] 


## Libraries
############

library(plyr)
library(weights)
library(reshape)
library(data.table)

## User Inputs
###############

# Directories
WD                   <- "E:/projects/clients/mtc/data/CHTS_Summaries"
CHTS_raw_Dir         <- "E:/projects/clients/mtc/data/fromNREL/standardized_data_redacted_PII"
Survey_Dir           <- "E:/projects/clients/mtc/data/CHTS"
Survey_Processed_Dir <- "E:/projects/clients/mtc/data/CHTS_processed"
SkimDir              <- "E:/projects/clients/mtc/data/Skim2010"
geogXWalkDir         <- "E:/projects/clients/mtc/data/Trip End Geocodes"
CensusACS_Dir        <- "E:/projects/clients/mtc/data/Census/ACS_5YearEstimates"
mazDataDir           <- "E:/projects/clients/mtc/2015_test_2018_12_09/landuse"
geographyTM1.5       <- "E:/projects/clients/mtc/data/TM1.5_Geographies"

## Read Data
xwalk                <- read.csv(paste(geogXWalkDir, "geographicCWalk.csv", sep = "/"), as.is = T)
hh                   <- read.table(paste(Survey_Dir, "chts_hrecx_abmxfer.dat", sep = "/"), header = T)
#hh_raw              <- read.csv(paste(CHTS_raw_Dir, "survey_households.csv", sep = "/"), as.is = T)
per                  <- read.table(paste(Survey_Dir, "chts_precx_abmxfer.dat", sep = "/"), header = T)
per_raw              <- read.csv(paste(CHTS_raw_Dir, "survey_person.csv", sep = "/"), as.is = T)
place_raw            <- read.csv(paste(CHTS_raw_Dir, "survey_place.csv", sep = "/"), as.is = T)
mazData              <- read.csv(paste(mazDataDir, "maz_data_withDensity.csv", sep = "/"), as.is = T)

xwalk_SDist          <- read.csv(paste(geogXWalkDir, "geographicCWalk_SDist.csv", sep = "/"), as.is = T) # change by Khademul
mazData_SDist        <- read.csv(paste(mazDataDir, "maz_data_withDensity_SDist.csv", sep = "/"), as.is = T) # change by Khademul
maz_taz15            <- read.csv(paste(geographyTM1.5, "maz22_taz1454.csv", sep = "/"), as.is = T) 
taz15_sd             <- read.csv(paste(geographyTM1.5, "geographies/taz-superdistrict-county.csv", sep = "/"), as.is = T) 

processedPerson      <- read.csv(paste(Survey_Processed_Dir, "persons.csv", sep = "/"), as.is = T)
proc_hh              <- read.csv(paste(Survey_Processed_Dir, "households.csv", sep = "/"), as.is = T)
tours                <- read.csv(paste(Survey_Processed_Dir, "tours.csv", sep = "/"), as.is = T)
trips                <- read.csv(paste(Survey_Processed_Dir, "trips.csv", sep = "/"), as.is = T)
jutrips              <- read.csv(paste(Survey_Processed_Dir, "unique_joint_ultrips.csv", sep = "/"), as.is = T)
jtours               <- read.csv(paste(Survey_Processed_Dir, "unique_joint_tours.csv", sep = "/"), as.is = T)

hhloc                <- read.csv(paste(geogXWalkDir, "CHTS1213hhLoc.csv", sep = "/"), as.is = T)
plloc                <- read.csv(paste(geogXWalkDir, "CHTS1213placeLoc.csv", sep = "/"), as.is = T)
scloc                <- read.csv(paste(geogXWalkDir, "CHTS1213schlLoc.csv", sep = "/"), as.is = T)
wkloc                <- read.csv(paste(geogXWalkDir, "CHTS1213workLoc.csv", sep = "/"), as.is = T)

# subset weights [re-weighted, excludes records collected during summer months]
hhweights_sub        <- read.csv(paste(Survey_Processed_Dir, "households_SUBSET.csv", sep = "/"), as.is = T)
perweights_sub       <- read.csv(paste(Survey_Processed_Dir, "persons_SUBSET.csv", sep = "/"), as.is = T)

# skims
DST_SKM   <- fread(paste(SkimDir, "SOV_DIST_MD_HWYSKM.csv", sep = "/"), stringsAsFactors = F, header = T)
DST_SKM   <- melt(DST_SKM, id = c("DISTDA"))
colnames(DST_SKM) <- c("o", "d", "dist")

districtList         <- sort(unique(xwalk$COUNTYNAME))
SuperdistrictList    <- sort(unique(xwalk_SDist$SDISTNAME)) # change by Khademul

# Define other variables
pertypeCodes <- data.frame(code = c(1,2,3,4,5,6,7,8,"All"), 
                           name = c("FT Worker", "PT Worker", "Univ Stud", "Non Worker", "Retiree", "Driv Stud", "NonDriv Stud", "Pre-School", "All"))


## Prepare Data File
####################
setwd(WD)

### keep only weekday records
proc_hh$DOW <- hh$hhdow[match(proc_hh$HH_ID, hh$hhno)]
processedPerson$DOW <- proc_hh$DOW[match(processedPerson$HH_ID, proc_hh$HH_ID)]
tours$DOW <- proc_hh$DOW[match(tours$HH_ID, proc_hh$HH_ID)]
trips$DOW <- proc_hh$DOW[match(trips$HH_ID, proc_hh$HH_ID)]
jutrips$DOW <- proc_hh$DOW[match(jutrips$HH_ID, proc_hh$HH_ID)]
jtours$DOW <- proc_hh$DOW[match(jtours$HH_ID, proc_hh$HH_ID)]

proc_hh <- proc_hh[proc_hh$DOW<=5,]
processedPerson <- processedPerson[processedPerson$DOW<=5,]
tours <- tours[tours$DOW<=5,]
trips <- trips[trips$DOW<=5,]
jutrips <- jutrips[jutrips$DOW<=5,]
jtours <- jtours[jtours$DOW<=5,]
hhweights_sub <- hhweights_sub[hhweights_sub$WEEKEND==0,]
perweights_sub <- perweights_sub[perweights_sub$WEEKEND==0,]

### rename fields in raw CHTS files
names(hh)[names(hh)=="hhno"]   <- 'SAMPN'
names(per)[names(per)=="hhno"] <- 'SAMPN'
names(per)[names(per)=="pno"]  <- 'PERNO'

### manually fix perid in processed person file
processedPerson$PER_ID[processedPerson$HH_ID==1395452 & processedPerson$PER_ID==4] <- 3
processedPerson$PER_ID[processedPerson$HH_ID==1490071 & processedPerson$PER_ID==2] <- 1
processedPerson$PER_ID[processedPerson$HH_ID==1687680 & processedPerson$PER_ID==4] <- 3
processedPerson$PER_ID[processedPerson$HH_ID==1870731 & processedPerson$PER_ID==4] <- 3
processedPerson$PER_ID[processedPerson$HH_ID==1932621 & processedPerson$PER_ID==2] <- 1
processedPerson$PER_ID[processedPerson$HH_ID==1969505 & processedPerson$PER_ID==3] <- 2
processedPerson$PER_ID[processedPerson$HH_ID==2022431 & processedPerson$PER_ID==3] <- 2
processedPerson$PER_ID[processedPerson$HH_ID==2510564 & processedPerson$PER_ID==5] <- 4
processedPerson$PER_ID[processedPerson$HH_ID==2510564 & processedPerson$PER_ID==6] <- 5
processedPerson$PER_ID[processedPerson$HH_ID==2521589 & processedPerson$PER_ID==2] <- 1
processedPerson$PER_ID[processedPerson$HH_ID==2521589 & processedPerson$PER_ID==3] <- 2
processedPerson$PER_ID[processedPerson$HH_ID==2639241 & processedPerson$PER_ID==4] <- 3
processedPerson$PER_ID[processedPerson$HH_ID==2645403 & processedPerson$PER_ID==4] <- 3


hh <- hh[hh$SAMPN %in% hhweights_sub$HH_ID,]
hh <- hh[hh$SAMPN %in% proc_hh$HH_ID,]

per$uid <- paste(per$SAMPN, per$PERNO, sep = "-")
processedPerson$uid <- paste(processedPerson$HH_ID, processedPerson$PER_ID, sep = "-")
perweights_sub$uid <- paste(perweights_sub$HH_ID, perweights_sub$PER_ID, sep = "-")


per <- per[per$uid %in% perweights_sub$uid,]
per <- per[per$uid %in% processedPerson$uid,]

tours$uid <- paste(tours$HH_ID, tours$PER_ID, sep = "-")
trips$uid <- paste(trips$HH_ID, trips$PER_ID, sep = "-")
#tours <- tours[tours$uid %in% processedPerson$uid,]
#trips <- trips[trips$uid %in% processedPerson$uid,]
#jtours <- jtours[jtours$HH_ID %in% proc_hh$HH_ID,]
tours <- tours[tours$uid %in% perweights_sub$uid,]
trips <- trips[trips$uid %in% perweights_sub$uid,]
jtours <- jtours[jtours$HH_ID %in% hhweights_sub$HH_ID,]


### copy weights from subset_weights file
hh$finalweight <- hhweights_sub$HHWEIGHT_SUB[match(hh$SAMPN, hhweights_sub$HH_ID)]
per$finalweight <- perweights_sub$PERWEIGHT_SUB[match(per$SAMPN*100+per$PERNO, perweights_sub$HH_ID*100+perweights_sub$PER_ID)]
hh$finalweight[is.na(hh$finalweight)] <- 0
per$finalweight[is.na(per$finalweight)] <- 0

### copy weight field
#hh$finalweight     <- hh$hhexpfac
#per$finalweight    <- per$psexpfac
per$hhweight       <- hh$finalweight[match(per$SAMPN, hh$SAMPN)]
tours$finalweight  <- hh$finalweight[match(tours$HH_ID, hh$SAMPN)]
trips$finalweight  <- hh$finalweight[match(trips$HH_ID, hh$SAMPN)]
jtours$finalweight <- hh$finalweight[match(jtours$HH_ID, hh$SAMPN)]

### copy location info [first remove existing location fields]
# copy the sequential version of MAZs/TAZs [MAZ instead of MAZ_ORIGINAL]
hh$HHMAZ <- hhloc$MAZ_V10[match(hh$SAMPN, hhloc$SAMPN)]
hh$HHMAZ_ORIGINAL <- hh$HHMAZ
hh$HHMAZ <- xwalk$MAZ[match(hh$HHMAZ, xwalk$MAZ_ORIGINAL)]
#manual fixing of home TAZ
hh$HHMAZ[hh$SAMPN==1692707] <- 24082
hh$HHMAZ[hh$SAMPN==1913749] <- 24257
hh$HHTAZ <- xwalk$TAZ[match(hh$HHMAZ, xwalk$MAZ)]
hh$HHMAZ[is.na(hh$HHMAZ)] <- 0
hh$HHTAZ[is.na(hh$HHTAZ)] <- 0
hh$HTAZ15 <- maz_taz15$TAZ1454[match(hh$HHMAZ_ORIGINAL, maz_taz15$maz)]
hh$H_SD <- taz15_sd$SD_NAME[match(hh$HTAZ15, taz15_sd$ZONE)]

per$WMAZ <- wkloc$MAZ_V10[match(paste(per$SAMPN, per$PERNO, sep = "-"), paste(wkloc$SAMPN, wkloc$PERNO, sep = "-"))]
per$WMAZ_ORIGINAL <- per$WMAZ
per$WMAZ <- xwalk$MAZ[match(per$WMAZ, xwalk$MAZ_ORIGINAL)]
per$WTAZ <- xwalk$TAZ[match(per$WMAZ, xwalk$MAZ)]
per$WMAZ[is.na(per$WMAZ)] <- 0
per$WTAZ[is.na(per$WTAZ)] <- 0

per$SMAZ <- scloc$MAZ_V10[match(paste(per$SAMPN, per$PERNO, sep = "-"), paste(scloc$SAMPN, scloc$PERNO, sep = "-"))]
per$SMAZ_ORIGINAL <- per$SMAZ
per$SMAZ <- xwalk$MAZ[match(per$SMAZ, xwalk$MAZ_ORIGINAL)]
per$STAZ <- xwalk$TAZ[match(per$SMAZ, xwalk$MAZ)]
per$SMAZ[is.na(per$SMAZ)] <- 0
per$STAZ[is.na(per$STAZ)] <- 0

per$STAZ15 <- maz_taz15$TAZ1454[match(per$SMAZ_ORIGINAL, maz_taz15$maz)]
per$S_SD <- taz15_sd$SD_NAME[match(per$STAZ15, taz15_sd$ZONE)]
per$WTAZ15 <- maz_taz15$TAZ1454[match(per$WMAZ_ORIGINAL, maz_taz15$maz)]
per$W_SD <- taz15_sd$SD_NAME[match(per$WTAZ15, taz15_sd$ZONE)]

trips$ORIG_MAZ <- plloc$MAZ_V10[match(paste(trips$HH_ID, trips$PER_ID, trips$ORIG_PLACENO, sep = "-"), 
                                      paste(plloc$SAMPN, plloc$PERNO, plloc$PLANO, sep = "-"))]
trips$ORIG_MAZ <- xwalk$MAZ[match(trips$ORIG_MAZ, xwalk$MAZ_ORIGINAL)]
trips$ORIG_TAZ <- xwalk$TAZ[match(trips$ORIG_MAZ, xwalk$MAZ)]
trips$ORIG_MAZ[is.na(trips$ORIG_MAZ)] <- 0
trips$ORIG_TAZ[is.na(trips$ORIG_TAZ)] <- 0

trips$DEST_MAZ <- plloc$MAZ_V10[match(paste(trips$HH_ID, trips$PER_ID, trips$DEST_PLACENO, sep = "-"), 
                                      paste(plloc$SAMPN, plloc$PERNO, plloc$PLANO, sep = "-"))]
trips$DEST_MAZ <- xwalk$MAZ[match(trips$DEST_MAZ, xwalk$MAZ_ORIGINAL)]
trips$DEST_TAZ <- xwalk$TAZ[match(trips$DEST_MAZ, xwalk$MAZ)]
trips$DEST_MAZ[is.na(trips$DEST_MAZ)] <- 0
trips$DEST_TAZ[is.na(trips$DEST_TAZ)] <- 0

trips$OCOUNTY <- xwalk$COUNTYNAME[match(trips$ORIG_MAZ, xwalk$MAZ)]
trips$DCOUNTY <- xwalk$COUNTYNAME[match(trips$DEST_MAZ, xwalk$MAZ)]
trips$OCOUNTY[is.na(trips$OCOUNTY)] <- "Missing"
trips$DCOUNTY[is.na(trips$DCOUNTY)] <- "Missing"


tours$ORIG_MAZ <- plloc$MAZ_V10[match(paste(tours$HH_ID, tours$PER_ID, tours$ORIG_PLACENO, sep = "-"), 
                                      paste(plloc$SAMPN, plloc$PERNO, plloc$PLANO, sep = "-"))]
tours$ORIG_MAZ <- xwalk$MAZ[match(tours$ORIG_MAZ, xwalk$MAZ_ORIGINAL)]
tours$ORIG_TAZ <- xwalk$TAZ[match(tours$ORIG_MAZ, xwalk$MAZ)]
tours$ORIG_MAZ[is.na(tours$ORIG_MAZ)] <- 0
tours$ORIG_TAZ[is.na(tours$ORIG_TAZ)] <- 0

tours$DEST_MAZ <- plloc$MAZ_V10[match(paste(tours$HH_ID, tours$PER_ID, tours$DEST_PLACENO, sep = "-"), 
                                      paste(plloc$SAMPN, plloc$PERNO, plloc$PLANO, sep = "-"))]
tours$DEST_MAZ <- xwalk$MAZ[match(tours$DEST_MAZ, xwalk$MAZ_ORIGINAL)]
tours$DEST_TAZ <- xwalk$TAZ[match(tours$DEST_MAZ, xwalk$MAZ)]
tours$DEST_MAZ[is.na(tours$DEST_MAZ)] <- 0
tours$DEST_TAZ[is.na(tours$DEST_TAZ)] <- 0

names(processedPerson)[names(processedPerson)=="HH_ID"] <- "HHID"
names(processedPerson)[names(processedPerson)=="PER_ID"] <- "PERID"

hh$HHVEH[hh$hhvehs == 0] <- 0
hh$HHVEH[hh$hhvehs == 1] <- 1
hh$HHVEH[hh$hhvehs == 2] <- 2
hh$HHVEH[hh$hhvehs == 3] <- 3
hh$HHVEH[hh$hhvehs >= 4] <- 4

hh$HHSIZE[hh$hhsize == 1] <- 1
hh$HHSIZE[hh$hhsize == 2] <- 2
hh$HHSIZE[hh$hhsize == 3] <- 3
hh$HHSIZE[hh$hhsize == 4] <- 4
hh$HHSIZE[hh$hhsize >= 5] <- 5

#Adults in the HH
adults <- count(per[!is.na(per$pagey),], c("SAMPN"), "pagey>=18 & pagey<99")
hh$ADULTS <- adults$freq[match(hh$SAMPN, adults$SAMPN)]
hh$ADULTS[is.na(hh$ADULTS)] <- 0

# define Districts - County for MTC
hh$HDISTRICT <- xwalk$COUNTYNAME[match(hh$HHMAZ, xwalk$MAZ)]
hh$HDISTRICT_S <- xwalk_SDist$SDISTNAME[match(hh$HHMAZ, xwalk$MAZ)] # change by Khademul

per$PERTYPE <- processedPerson$PERSONTYPE[match(per$SAMPN*100+per$PERNO, processedPerson$HHID*100+processedPerson$PERID)]
per$HHTAZ <- hh$HHTAZ[match(per$SAMPN, hh$SAMPN)]
per$HDISTRICT <- hh$HDISTRICT[match(per$SAMPN, hh$SAMPN)]
per$H_SD <- hh$H_SD[match(per$SAMPN, hh$SAMPN)]

per$WDISTRICT <- xwalk$COUNTYNAME[match(per$WMAZ, xwalk$MAZ)]

per$HDISTRICT_S <- hh$HDISTRICT_S[match(per$SAMPN, hh$SAMPN)] # change by Khademul
per$WDISTRICT_S <- xwalk_SDist$SDISTNAME[match(per$WMAZ, xwalk$MAZ)] # change by Khademul


##-------Compute Summary Statistics-------
##########################################

# Auto ownership
autoOwnership <- count(hh[!is.na(hh$HHVEH),], c("HHVEH"), "finalweight")
write.csv(autoOwnership, "autoOwnership.csv", row.names = TRUE)

# Persons by person type
pertypeDistbn <- count(per[!is.na(per$PERTYPE),], c("PERTYPE"), "finalweight")
write.csv(pertypeDistbn, "pertypeDistbn.csv", row.names = TRUE)

# Mandatory DC
# emp_loc_type - 1:fixed, 2:WFH, 3: varies
per$empl_loc_type <- per_raw$empl_loc_type[match(paste(per$SAMPN, per$PERNO, sep = "-"), paste(per_raw$sampno, per_raw$perno, sep = "-"))]
per$empl_loc_type[is.na(per$empl_loc_type)] <- 0
# workers <- per[per$WTAZ>0 & per$PERTYPE<=3 & per$empl_loc_type!=2, c("SAMPN", "PERNO", "HHTAZ", "WTAZ", "empl_loc_type","PERTYPE", "HDISTRICT", "WDISTRICT", "finalweight")] # change by Khademul
workers <- per[per$WTAZ>0 & per$PERTYPE<=3 & per$empl_loc_type!=2, c("SAMPN", "PERNO", "HHTAZ", "WTAZ", "empl_loc_type","PERTYPE", "HDISTRICT", "WDISTRICT", "HDISTRICT_S", "WDISTRICT_S", "finalweight")] # change by Khademul
workers$WDIST <- DST_SKM$dist[match(paste(workers$HHTAZ, workers$WTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]

# students <- per[per$STAZ>0, c("SAMPN", "PERNO", "HHTAZ", "STAZ", "PERTYPE", "HDISTRICT", "finalweight")] # change by Khademul
students <- per[per$STAZ>0, c("SAMPN", "PERNO", "HHTAZ", "STAZ", "PERTYPE", "HDISTRICT", "HDISTRICT_S", "H_SD", "S_SD", "finalweight")] # change by Khademul
students$SDIST <- DST_SKM$dist[match(paste(students$HHTAZ, students$STAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]

# code distance bins
workers$distbin <- cut(workers$WDIST, breaks = c(seq(0,50, by=1), 9999), labels = F, right = F)
students$distbin <- cut(students$SDIST, breaks = c(seq(0,50, by=1), 9999), labels = F, right = F)

# alternate distbin profile for workers
#workers$distbin <- cut(workers$WDIST, breaks = c(0, 3, 5, 10, 15, 20, 30, 40, 50, 60, 9999), labels = F, right = F)


distBinCat <- data.frame(distbin = seq(1,51, by=1))
#distBinCat <- data.frame(distbin = seq(1,10, by=1))

# compute TLFDs by district and total
tlfd_work <- ddply(workers[,c("HDISTRICT", "distbin", "finalweight")], c("HDISTRICT", "distbin"), summarise, work = sum((HDISTRICT>0)*finalweight))
tlfd_work <- cast(tlfd_work, distbin~HDISTRICT, value = "work", sum)
tlfd_work$Total <- rowSums(tlfd_work[,!colnames(tlfd_work) %in% c("distbin")])
tlfd_work_df <- merge(x = distBinCat, y = tlfd_work, by = "distbin", all.x = TRUE)
tlfd_work_df[is.na(tlfd_work_df)] <- 0

tlfd_univ <- ddply(students[students$PERTYPE==3,c("HDISTRICT", "distbin", "finalweight")], c("HDISTRICT", "distbin"), summarise, univ = sum((HDISTRICT>0)*finalweight))
tlfd_univ <- cast(tlfd_univ, distbin~HDISTRICT, value = "univ", sum)
tlfd_univ$Total <- rowSums(tlfd_univ[,!colnames(tlfd_univ) %in% c("distbin")])
tlfd_univ_df <- merge(x = distBinCat, y = tlfd_univ, by = "distbin", all.x = TRUE)
tlfd_univ_df[is.na(tlfd_univ_df)] <- 0

tlfd_schl <- ddply(students[students$PERTYPE>=6,c("HDISTRICT", "distbin", "finalweight")], c("HDISTRICT", "distbin"), summarise, schl = sum((HDISTRICT>0)*finalweight))
tlfd_schl <- cast(tlfd_schl, distbin~HDISTRICT, value = "schl", sum)
tlfd_schl$Total <- rowSums(tlfd_schl[,!colnames(tlfd_schl) %in% c("distbin")])
tlfd_schl_df <- merge(x = distBinCat, y = tlfd_schl, by = "distbin", all.x = TRUE)
tlfd_schl_df[is.na(tlfd_schl_df)] <- 0

write.csv(tlfd_work_df, "workTLFD.csv", row.names = F)
write.csv(tlfd_univ_df, "univTLFD.csv", row.names = F)
write.csv(tlfd_schl_df, "schlTLFD.csv", row.names = F)

# compute TLFDs by district and total (change by khademul)
tlfd_work_S <- ddply(workers[,c("HDISTRICT_S", "distbin", "finalweight")], c("HDISTRICT_S", "distbin"), summarise, work = sum((HDISTRICT_S>0)*finalweight))
tlfd_work_S <- cast(tlfd_work_S, distbin~HDISTRICT_S, value = "work", sum)
tlfd_work_S$Total <- rowSums(tlfd_work_S[,!colnames(tlfd_work_S) %in% c("distbin")])
tlfd_work_S_df <- merge(x = distBinCat, y = tlfd_work_S, by = "distbin", all.x = TRUE)
tlfd_work_S_df[is.na(tlfd_work_S_df)] <- 0

tlfd_univ_S <- ddply(students[students$PERTYPE==3,c("HDISTRICT_S", "distbin", "finalweight")], c("HDISTRICT_S", "distbin"), summarise, univ = sum((HDISTRICT_S>0)*finalweight))
tlfd_univ_S <- cast(tlfd_univ_S, distbin~HDISTRICT_S, value = "univ", sum)
tlfd_univ_S$Total <- rowSums(tlfd_univ_S[,!colnames(tlfd_univ_S) %in% c("distbin")])
tlfd_univ_S_df <- merge(x = distBinCat, y = tlfd_univ_S, by = "distbin", all.x = TRUE)
tlfd_univ_S_df[is.na(tlfd_univ_S_df)] <- 0

tlfd_schl_S <- ddply(students[students$PERTYPE>=6,c("HDISTRICT_S", "distbin", "finalweight")], c("HDISTRICT_S", "distbin"), summarise, schl = sum((HDISTRICT_S>0)*finalweight))
tlfd_schl_S <- cast(tlfd_schl_S, distbin~HDISTRICT_S, value = "schl", sum)
tlfd_schl_S$Total <- rowSums(tlfd_schl_S[,!colnames(tlfd_schl_S) %in% c("distbin")])
tlfd_schl_S_df <- merge(x = distBinCat, y = tlfd_schl_S, by = "distbin", all.x = TRUE)
tlfd_schl_S_df[is.na(tlfd_schl_S_df)] <- 0

write.csv(tlfd_work_S_df, "workTLFD_S.csv", row.names = F)
write.csv(tlfd_univ_S_df, "univTLFD_S.csv", row.names = F)
write.csv(tlfd_schl_S_df, "schlTLFD_S.csv", row.names = F)

cat("\n Average distance to workplace (Total): ", weighted.mean(workers$WDIST, workers$finalweight, na.rm = TRUE))
cat("\n Average distance to university (Total): ", weighted.mean(students$SDIST[students$PERTYPE == 3], students$finalweight[students$PERTYPE == 3], na.rm = TRUE))
cat("\n Average distance to school (Total): ", weighted.mean(students$SDIST[students$PERTYPE >= 6 & students$PERTYPE <= 7], students$finalweight[students$PERTYPE >= 6 & students$PERTYPE <= 7], na.rm = TRUE))

## Output avg trip lengths for visualizer
district_df <- data.frame(HDISTRICT = c(districtList, "Total"))
district_df_S <- data.frame(HDISTRICT_S = c(SuperdistrictList, "Total")) # change by khademul

workTripLengths <- ddply(workers[,c("HDISTRICT", "WDIST", "finalweight")], c("HDISTRICT"), summarise, work = weighted.mean(WDIST,finalweight))
totalLength     <- data.frame("Total", weighted.mean(workers$WDIST,workers$finalweight))
colnames(totalLength) <- colnames(workTripLengths)
workTripLengths <- rbind(workTripLengths, totalLength)
workTripLengths_df <- merge(x = district_df, y = workTripLengths, by = "HDISTRICT", all.x = TRUE)
workTripLengths_df[is.na(workTripLengths_df)] <- 0

# change by khademul
workTripLengths_S <- ddply(workers[,c("HDISTRICT_S", "WDIST", "finalweight")], c("HDISTRICT_S"), summarise, work = weighted.mean(WDIST,finalweight))
totalLength_S     <- data.frame("Total", weighted.mean(workers$WDIST,workers$finalweight))
colnames(totalLength_S) <- colnames(workTripLengths_S)
workTripLengths_S <- rbind(workTripLengths_S, totalLength_S)
workTripLengths_S_df <- merge(x = district_df_S, y = workTripLengths_S, by = "HDISTRICT_S", all.x = TRUE)
workTripLengths_S_df[is.na(workTripLengths_S_df)] <- 0

univTripLengths <- ddply(students[students$PERTYPE==3,c("HDISTRICT", "SDIST", "finalweight")], c("HDISTRICT"), summarise, univ = weighted.mean(SDIST,finalweight))
totalLength     <- data.frame("Total", weighted.mean(students$SDIST[students$PERTYPE==3], students$finalweight[students$PERTYPE==3]))
colnames(totalLength) <- colnames(univTripLengths)
univTripLengths <- rbind(univTripLengths, totalLength)
univTripLengths_df <- merge(x = district_df, y = univTripLengths, by = "HDISTRICT", all.x = TRUE)
univTripLengths_df[is.na(univTripLengths_df)] <- 0

# change by khademul
univTripLengths_S <- ddply(students[students$PERTYPE==3,c("HDISTRICT_S", "SDIST", "finalweight")], c("HDISTRICT_S"), summarise, univ = weighted.mean(SDIST,finalweight))
totalLength_S     <- data.frame("Total", weighted.mean(students$SDIST[students$PERTYPE==3], students$finalweight[students$PERTYPE==3]))
colnames(totalLength_S) <- colnames(univTripLengths_S)
univTripLengths_S <- rbind(univTripLengths_S, totalLength_S)
univTripLengths_S_df <- merge(x = district_df_S, y = univTripLengths_S, by = "HDISTRICT_S", all.x = TRUE)
univTripLengths_S_df[is.na(univTripLengths_S_df)] <- 0

schlTripLengths <- ddply(students[students$PERTYPE>=6,c("HDISTRICT", "SDIST", "finalweight")], c("HDISTRICT"), summarise, schl = weighted.mean(SDIST,finalweight))
totalLength     <- data.frame("Total", weighted.mean(students$SDIST[students$PERTYPE>=6], students$finalweight[students$PERTYPE>=6]))
colnames(totalLength) <- colnames(schlTripLengths)
schlTripLengths <- rbind(schlTripLengths, totalLength)
schlTripLengths_df <- merge(x = district_df, y = schlTripLengths, by = "HDISTRICT", all.x = TRUE)
schlTripLengths_df[is.na(schlTripLengths_df)] <- 0

# change by khademul
schlTripLengths_S <- ddply(students[students$PERTYPE>=6,c("HDISTRICT_S", "SDIST", "finalweight")], c("HDISTRICT_S"), summarise, schl = weighted.mean(SDIST,finalweight))
totalLength_S     <- data.frame("Total", weighted.mean(students$SDIST[students$PERTYPE>=6], students$finalweight[students$PERTYPE>=6]))
colnames(totalLength_S) <- colnames(schlTripLengths_S)
schlTripLengths_S <- rbind(schlTripLengths_S, totalLength_S)
schlTripLengths_S_df <- merge(x = district_df_S, y = schlTripLengths_S, by = "HDISTRICT_S", all.x = TRUE)
schlTripLengths_S_df[is.na(schlTripLengths_S_df)] <- 0

mandTripLengths <- cbind(workTripLengths_df, univTripLengths_df$univ, schlTripLengths_df$schl)
colnames(mandTripLengths) <- c("District", "Work", "Univ", "Schl")
write.csv(mandTripLengths, "mandTripLengths.csv", row.names = F)

# change by khademul
mandTripLengths_S <- cbind(workTripLengths_S_df, univTripLengths_S_df$univ, schlTripLengths_S_df$schl)
colnames(mandTripLengths_S) <- c("SuperDistrict", "Work", "Univ", "Schl")
write.csv(mandTripLengths_S, "mandTripLengths_S.csv", row.names = F)

# Work from home [for each district and total]
per$worker[per$PERTYPE<=2 | (per$PERTYPE==3 & !is.na(per$WTAZ))] <- 1
per$worker[is.na(per$worker)] <- 0
per$wfh[per$empl_loc_type==2] <- 1
per$wfh[is.na(per$wfh)] <- 0

districtWorkers <- ddply(per[per$worker==1,c("HDISTRICT", "finalweight")], c("HDISTRICT"), summarise, workers = sum(finalweight))
districtWorkers_df <- merge(x = data.frame(HDISTRICT = districtList), y = districtWorkers, by = "HDISTRICT", all.x = TRUE)
districtWorkers_df[is.na(districtWorkers_df)] <- 0

# change by khademul
districtWorkers_S <- ddply(per[per$worker==1,c("HDISTRICT_S", "finalweight")], c("HDISTRICT_S"), summarise, workers = sum(finalweight))
districtWorkers_S_df <- merge(x = data.frame(HDISTRICT_S = SuperdistrictList), y = districtWorkers_S, by = "HDISTRICT_S", all.x = TRUE)
districtWorkers_S_df[is.na(districtWorkers_S_df)] <- 0

districtWfh     <- ddply(per[per$worker==1 & per$wfh==1,c("HDISTRICT", "finalweight")], c("HDISTRICT"), summarise, wfh = sum(finalweight))
districtWfh_df <- merge(x = data.frame(HDISTRICT = districtList), y = districtWfh, by = "HDISTRICT", all.x = TRUE)
districtWfh_df[is.na(districtWfh_df)] <- 0

# change by khademul
districtWfh_S     <- ddply(per[per$worker==1 & per$wfh==1,c("HDISTRICT_S", "finalweight")], c("HDISTRICT_S"), summarise, wfh = sum(finalweight))
districtWfh_S_df <- merge(x = data.frame(HDISTRICT_S = SuperdistrictList), y = districtWfh_S, by = "HDISTRICT_S", all.x = TRUE)
districtWfh_S_df[is.na(districtWfh_S_df)] <- 0

wfh_summary     <- cbind(districtWorkers_df, districtWfh_df$wfh)
colnames(wfh_summary) <- c("District", "Workers", "WFH")
totalwfh        <- data.frame("Total", sum((per$worker==1)*per$finalweight), sum((per$worker==1 & per$wfh==1)*per$finalweight))
colnames(totalwfh) <- colnames(wfh_summary)
wfh_summary <- rbind(wfh_summary, totalwfh)
write.csv(wfh_summary, "wfh_summary.csv", row.names = F)

# change by khademul
wfh_summary_S     <- cbind(districtWorkers_S_df, districtWfh_S_df$wfh)
colnames(wfh_summary_S) <- c("SuperDistrict", "Workers", "WFH")
totalwfh_S        <- data.frame("Total", sum((per$worker==1)*per$finalweight), sum((per$worker==1 & per$wfh==1)*per$finalweight))
colnames(totalwfh_S) <- colnames(wfh_summary_S)
wfh_summary_S <- rbind(wfh_summary_S, totalwfh_S)
write.csv(wfh_summary_S, "wfh_summary_S.csv", row.names = F)

# County-County Flows
countyFlows <- xtabs(finalweight~HDISTRICT+WDISTRICT, data = workers)
countyFlows[is.na(countyFlows)] <- 0
countyFlows <- addmargins(as.table(countyFlows))
countyFlows <- as.data.frame.matrix(countyFlows)
colnames(countyFlows)[colnames(countyFlows)=="Sum"] <- "Total"
rownames(countyFlows)[rownames(countyFlows)=="Sum"] <- "Total"
write.csv(countyFlows, "countyFlows.csv", row.names = T)

# change by khademul
countyFlows_S <- xtabs(finalweight~HDISTRICT_S+WDISTRICT_S, data = workers)
countyFlows_S[is.na(countyFlows_S)] <- 0
countyFlows_S <- addmargins(as.table(countyFlows_S))
countyFlows_S <- as.data.frame.matrix(countyFlows_S)
colnames(countyFlows_S)[colnames(countyFlows_S)=="Sum"] <- "Total"
rownames(countyFlows_S)[rownames(countyFlows_S)=="Sum"] <- "Total"
write.csv(countyFlows_S, "countyFlows_S.csv", row.names = T)

# SD to SD university student flow
univFlows_SD <- xtabs(finalweight~H_SD+S_SD, data = students[students$PERTYPE==3,])
univFlows_SD[is.na(univFlows_SD)] <- 0
univFlows_SD <- addmargins(as.table(univFlows_SD))
univFlows_SD <- as.data.frame.matrix(univFlows_SD)
colnames(univFlows_SD)[colnames(univFlows_SD)=="Sum"] <- "Total"
rownames(univFlows_SD)[rownames(univFlows_SD)=="Sum"] <- "Total"
write.csv(univFlows_SD, "univFlows_SD.csv", row.names = T)

#Workers in the HH
workersHH <- count(per[!is.na(per$WTAZ) & !is.na(per$PERTYPE) & !is.na(per$empl_loc_type),], c("SAMPN"), "(per$PERTYPE<=2) | (per$PERTYPE==3 & per$WTAZ>0)")
hh$WORKERS <- workersHH$freq[match(hh$SAMPN, workersHH$SAMPN)]
hh$WORKERS[is.na(hh$WORKERS)] <- 0


# Process Tour file
#------------------
#tours$finalweight <- hh$finalweight[match(tours$HH_ID, hh$SAMPN)]
tours <- tours[!is.na(tours$finalweight),]
tours$PERTYPE <- per$PERTYPE[match(tours$HH_ID*100+tours$PER_ID, per$SAMPN*100+per$PERNO)]
tours$DISTMILE <- tours$DIST/5280
tours$HHVEH <- hh$HHVEH[match(tours$HH_ID, hh$SAMPN)]
tours$ADULTS <- hh$ADULTS[match(tours$HH_ID, hh$SAMPN)]
#tours$AUTOSUFF[tours$HHVEH == 0] <- 0
#tours$AUTOSUFF[tours$HHVEH < tours$ADULTS & tours$HHVEH > 0] <- 1
#tours$AUTOSUFF[tours$HHVEH >= tours$ADULTS & tours$HHVEH > 0] <- 2
tours$WORKERS <- hh$WORKERS[match(tours$HH_ID, hh$SAMPN)]
tours$AUTOSUFF[tours$HHVEH == 0] <- 0
tours$AUTOSUFF[tours$HHVEH < tours$WORKERS & tours$HHVEH > 0] <- 1
tours$AUTOSUFF[tours$HHVEH >= tours$WORKERS & tours$HHVEH > 0] <- 2

tours$TOTAL_STOPS <- tours$OUTBOUND_STOPS + tours$INBOUND_STOPS

tours$SKIMDIST <- DST_SKM$dist[match(paste(tours$ORIG_TAZ, tours$DEST_TAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]

## Recode tour mode
tours$TOURMODE_RECODE[tours$TOURMODE==1]  <- "01_Auto SOV"  #SOV
tours$TOURMODE_RECODE[tours$TOURMODE==2]  <- "02_Auto 2 Person (Free)"  #HOV2
tours$TOURMODE_RECODE[tours$TOURMODE==3]  <- "03_Auto 3+ Person (Free)"  #HOV3
tours$TOURMODE_RECODE[tours$TOURMODE==4]  <- "04_Walk"  #Walk
tours$TOURMODE_RECODE[tours$TOURMODE==5]  <- "05_Bike/Moped"  #Bike
tours$TOURMODE_RECODE[tours$TOURMODE==6]  <- "06_Walk-Transit"  #WT
tours$TOURMODE_RECODE[tours$TOURMODE==7]  <- "07_PNR-Transit"  #PNR
tours$TOURMODE_RECODE[tours$TOURMODE==8]  <- "08_KNR-Transit"  #KNR
tours$TOURMODE_RECODE[tours$TOURMODE==9]  <- "09_School Bus"  #SchoolBus
tours$TOURMODE_RECODE[tours$TOURMODE==10] <- "10_Taxi/Shuttle" #Taxi
tours$TOURMODE_RECODE[tours$TOURMODE==11] <- "11_Other" #Other



# Recode time bin windows
tours$ANCHOR_DEPART_BIN[tours$ANCHOR_DEPART_BIN<=4] <- 1
tours$ANCHOR_DEPART_BIN[!is.na(tours$ANCHOR_DEPART_BIN) & tours$ANCHOR_DEPART_BIN>=5 & tours$ANCHOR_DEPART_BIN<=42] <- tours$ANCHOR_DEPART_BIN[!is.na(tours$ANCHOR_DEPART_BIN) & tours$ANCHOR_DEPART_BIN>=5 & tours$ANCHOR_DEPART_BIN<=42]-3
tours$ANCHOR_DEPART_BIN[tours$ANCHOR_DEPART_BIN>=43] <- 40

tours$ANCHOR_ARRIVE_BIN[tours$ANCHOR_ARRIVE_BIN<=4] <- 1
tours$ANCHOR_ARRIVE_BIN[!is.na(tours$ANCHOR_ARRIVE_BIN) & tours$ANCHOR_ARRIVE_BIN>=5 & tours$ANCHOR_ARRIVE_BIN<=42] <- tours$ANCHOR_ARRIVE_BIN[!is.na(tours$ANCHOR_ARRIVE_BIN) & tours$ANCHOR_ARRIVE_BIN>=5 & tours$ANCHOR_ARRIVE_BIN<=42]-3
tours$ANCHOR_ARRIVE_BIN[tours$ANCHOR_ARRIVE_BIN>=43] <- 40

# cap tour duration at 20 hours
tours$TOUR_DUR_BIN[tours$TOUR_DUR_BIN>=40] <- 40


# Recode tour purpose into unique market segmentations
# Work   - [No Subtours ], [All            ], [TOURPURP - (1,10)    ] 
# Univ   - [No Subtours ], [All            ], [TOURPURP - (2)       ] 
# Schl   - [No Subtours ], [All            ], [TOURPURP - (3)       ]  
# iMain  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (4,5,6)   ]   
# iDisc  - [No Subtours ], [Non-Fully_Joint], [TOURPURP - (7,8,9)   ]   
# jMain  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (4,5,6)   ]       
# jDisc  - [No Subtours ], [Fully_Joint    ], [TOURPURP - (7,8,9)   ]   
# AtWork - [All Subtours], [All            ], [TOURPURP - (All)     ]    
# Other  - [No Subtours ], [All            ], [TOURPURP - (11,12,13)] 

tours$TOURPURP_RECODE <- "Other"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$TOURPURP %in% c(1,10)] <- "Work"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$TOURPURP %in% c(2)] <- "University"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$TOURPURP %in% c(3)] <- "School"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$FULLY_JOINT==0 & tours$TOURPURP %in% c(4,5,6)] <- "Indi-Main"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$FULLY_JOINT==0 & tours$TOURPURP %in% c(7,8,9)] <- "Indi-Disc"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$FULLY_JOINT==1 & tours$TOURPURP %in% c(4,5,6)] <- "Joint-Main"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==0 & tours$FULLY_JOINT==1 & tours$TOURPURP %in% c(7,8,9)] <- "Joint-Disc"
tours$TOURPURP_RECODE[tours$IS_SUBTOUR==1] <- "At-Work"


# Export data for mode choice targets spreadsheet
write.csv(tours[,c("HH_ID", "PER_ID", "TOUR_ID","TOURMODE_RECODE", "TOURPURP_RECODE", "AUTOSUFF", "finalweight", "DOW")], 
          "tourModeChoice.csv", row.names = F)

# Recode workrelated tours which are not at work subtour as work tour
tours$TOURPURP[tours$TOURPURP == 10] <- 1

# Copy TOURPURP to trip file
trips$TOURPURP <- tours$TOURPURP[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]
trips$TOURPURP_RECODE <- tours$TOURPURP_RECODE[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]
trips$TOURMODE_RECODE <- tours$TOURMODE_RECODE[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]
trips$AUTOSUFF <- tours$AUTOSUFF[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]
trips$IS_SUBTOUR <- tours$IS_SUBTOUR[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]

tours$TOTAL_STOPS <- tours$OUTBOUND_STOPS + tours$INBOUND_STOPS

#----------------
jtours <- jtours[!is.na(jtours$finalweight),]

#copy tour mode & other attributes
jtours$TOURMODE <- tours$TOURMODE[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                    tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$AUTOSUFF <- tours$AUTOSUFF[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                    tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$ANCHOR_DEPART_BIN <- tours$ANCHOR_DEPART_BIN[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                                      tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$ANCHOR_ARRIVE_BIN <- tours$ANCHOR_ARRIVE_BIN[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                                      tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$TOUR_DUR_BIN <- tours$TOUR_DUR_BIN[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                            tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$DIST <- tours$DIST[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                            tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$DISTMILE <- jtours$DIST/5280

jtours$OUTBOUND_STOPS <- tours$OUTBOUND_STOPS[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                                tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$INBOUND_STOPS <- tours$INBOUND_STOPS[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                              tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$TOTAL_STOPS <- tours$TOTAL_STOPS[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                          tours$HH_ID*1000+tours$JTOUR_ID*10)]
jtours$SKIMDIST <- tours$SKIMDIST[match(jtours$HH_ID*1000+jtours$JTOUR_ID*10,
                                                    tours$HH_ID*1000+tours$JTOUR_ID*10)]


# stop freq model calibration summary
temp_tour <- tours
temp_tour$TOURPURP[temp_tour$IS_SUBTOUR==1] <- 20
temp_tour1 <- temp_tour[(temp_tour$TOURPURP==20 | temp_tour$TOURPURP<=9) & temp_tour$FULLY_JOINT==0,c("TOURPURP","OUTBOUND_STOPS","INBOUND_STOPS", "finalweight")]
temp_tour2 <- jtours[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=9,c("JOINT_PURP","OUTBOUND_STOPS","INBOUND_STOPS", "finalweight")]
colnames(temp_tour2) <- colnames(temp_tour1)
temp_tour <- rbind(temp_tour1,temp_tour2)

# code stop frequency model alternatives
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==0 & temp_tour$INBOUND_STOPS==0] <- 1
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==0 & temp_tour$INBOUND_STOPS==1] <- 2
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==0 & temp_tour$INBOUND_STOPS==2] <- 3
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==0 & temp_tour$INBOUND_STOPS>=3] <- 4
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==1 & temp_tour$INBOUND_STOPS==0] <- 5
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==1 & temp_tour$INBOUND_STOPS==1] <- 6
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==1 & temp_tour$INBOUND_STOPS==2] <- 7
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==1 & temp_tour$INBOUND_STOPS>=3] <- 8
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==2 & temp_tour$INBOUND_STOPS==0] <- 9
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==2 & temp_tour$INBOUND_STOPS==1] <- 10
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==2 & temp_tour$INBOUND_STOPS==2] <- 11
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS==2 & temp_tour$INBOUND_STOPS>=3] <- 12
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS>=3 & temp_tour$INBOUND_STOPS==0] <- 13
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS>=3 & temp_tour$INBOUND_STOPS==1] <- 14
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS>=3 & temp_tour$INBOUND_STOPS==2] <- 15
temp_tour$STOP_FREQ_ALT[temp_tour$OUTBOUND_STOPS>=3 & temp_tour$INBOUND_STOPS>=3] <- 16
temp_tour$STOP_FREQ_ALT[is.na(temp_tour$STOP_FREQ_ALT)] <- 0

stopFreqModel_summary <- xtabs(finalweight~STOP_FREQ_ALT+TOURPURP, data = temp_tour[temp_tour$TOURPURP<=9 | temp_tour$TOURPURP==20,])
write.csv(stopFreqModel_summary, "stopFreqModel_summary.csv", row.names = T)




# Process Trip file
#------------------
#trips$finalweight <- hh$finalweight[match(trips$HH_ID, hh$SAMPN)]
trips <- trips[!is.na(trips$finalweight),]

#trips$JTRIP_ID <- lapply(trips$JTRIP_ID, as.character)
#trips$JTRIP_ID <- lapply(trips$JTRIP_ID, as.integer)

trips$JTRIP_ID <- as.character(trips$JTRIP_ID)
trips$JTRIP_ID <- as.integer(trips$JTRIP_ID)
trips$JTRIP_ID[is.na(trips$JTRIP_ID)] <- 0

# recode tour mode for mode choice targets
trips$TRIPMODE_RECODE[trips$TRIPMODE==1]    <- "01_Auto SOV (Free)"            
trips$TRIPMODE_RECODE[trips$TRIPMODE==2]    <- "02_Auto SOV (Pay)"           
trips$TRIPMODE_RECODE[trips$TRIPMODE==3]    <- "03_Auto 2 Person (Free)"       
trips$TRIPMODE_RECODE[trips$TRIPMODE==4]    <- "04_Auto 2 Person (Pay)"       
trips$TRIPMODE_RECODE[trips$TRIPMODE==5]    <- "05_Auto 3+ Person (Free)"      
trips$TRIPMODE_RECODE[trips$TRIPMODE==6]    <- "06_Auto 3+ Person (Pay)"       
trips$TRIPMODE_RECODE[trips$TRIPMODE==7]    <- "07_Walk"
trips$TRIPMODE_RECODE[trips$TRIPMODE==8]    <- "08_Bike/Moped"
trips$TRIPMODE_RECODE[trips$TRIPMODE==9]    <- "09_Walk-Transit"
trips$TRIPMODE_RECODE[trips$TRIPMODE==23]   <- "10_Walk-Ferry"
trips$TRIPMODE_RECODE[trips$TRIPMODE==10]   <- "11_Walk-BRT/Streetcar"
trips$TRIPMODE_RECODE[trips$TRIPMODE==11]   <- "12_Walk-LRT"
trips$TRIPMODE_RECODE[trips$TRIPMODE==12]   <- "13_PNR-Transit"
trips$TRIPMODE_RECODE[trips$TRIPMODE==33]   <- "14_PNR-Ferry"
trips$TRIPMODE_RECODE[trips$TRIPMODE==13]   <- "15_PNR-BRT/Streetcar"
trips$TRIPMODE_RECODE[trips$TRIPMODE==14]   <- "16_PNR-LRT"
trips$TRIPMODE_RECODE[trips$TRIPMODE==15]   <- "17_KNR-Transit"
trips$TRIPMODE_RECODE[trips$TRIPMODE==43]   <- "18_KNR-Ferry"
trips$TRIPMODE_RECODE[trips$TRIPMODE==16]   <- "19_KNR-BRT/Streetcar"
trips$TRIPMODE_RECODE[trips$TRIPMODE==17]   <- "20_KNR-LRT"
trips$TRIPMODE_RECODE[trips$TRIPMODE==18]   <- "21_School Bus"
trips$TRIPMODE_RECODE[trips$TRIPMODE==19]   <- "22_Taxi/Shuttle"
trips$TRIPMODE_RECODE[trips$TRIPMODE==20]   <- "23_Other"
trips$TRIPMODE_RECODE[trips$TRIPMODE==22]   <- "24_Walk-UR"
trips$TRIPMODE_RECODE[trips$TRIPMODE==21]   <- "25_Walk-CR"
trips$TRIPMODE_RECODE[trips$TRIPMODE==32]   <- "26_PNR-UR"
trips$TRIPMODE_RECODE[trips$TRIPMODE==31]   <- "27_PNR-CR"
trips$TRIPMODE_RECODE[trips$TRIPMODE==42]   <- "28_KNR-UR"
trips$TRIPMODE_RECODE[trips$TRIPMODE==41]   <- "29_KNR-CR"

#trips$TRIPMODE_RECODE[is.na(trips$TRIPMODE_RECODE)] <- "Missing"


# Recode trip mode
trips$TRIPMODE_DISAGG <- trips$TRIPMODE
trips$TRIPMODE[trips$TRIPMODE>=1 & trips$TRIPMODE<=2]                                               <- 1  #SOV
trips$TRIPMODE[trips$TRIPMODE>=3 & trips$TRIPMODE<=4]                                               <- 2  #HOV2
trips$TRIPMODE[trips$TRIPMODE>=5 & trips$TRIPMODE<=6]                                               <- 3  #HOV3
trips$TRIPMODE[trips$TRIPMODE==7]                                                                   <- 4  #Walk
trips$TRIPMODE[trips$TRIPMODE==8]                                                                   <- 5  #Bike
trips$TRIPMODE[(trips$TRIPMODE>=9 & trips$TRIPMODE<=11)|(trips$TRIPMODE>=21 & trips$TRIPMODE<=23)]  <- 6  #WT
trips$TRIPMODE[(trips$TRIPMODE>=12 & trips$TRIPMODE<=14)|(trips$TRIPMODE>=31 & trips$TRIPMODE<=33)] <- 7  #PNR
trips$TRIPMODE[(trips$TRIPMODE>=15 & trips$TRIPMODE<=17)|(trips$TRIPMODE>=41 & trips$TRIPMODE<=43)] <- 8  #KNR
trips$TRIPMODE[trips$TRIPMODE==18]                                                                  <- 9  #SchoolBus
trips$TRIPMODE[trips$TRIPMODE==19]                                                                  <- 10 #Taxi
trips$TRIPMODE[trips$TRIPMODE==20]                                                                  <- 11 #Other

# Recode time bin windows
trips$ORIG_DEP_BIN[trips$ORIG_DEP_BIN<=4] <- 1
trips$ORIG_DEP_BIN[!is.na(trips$ORIG_DEP_BIN) & trips$ORIG_DEP_BIN>=5 & trips$ORIG_DEP_BIN<=42] <- trips$ORIG_DEP_BIN[!is.na(trips$ORIG_DEP_BIN) & trips$ORIG_DEP_BIN>=5 & trips$ORIG_DEP_BIN<=42]-3
trips$ORIG_DEP_BIN[trips$ORIG_DEP_BIN>=43] <- 40

trips$ORIG_ARR_BIN[trips$ORIG_ARR_BIN<=4] <- 1
trips$ORIG_ARR_BIN[!is.na(trips$ORIG_ARR_BIN) & trips$ORIG_ARR_BIN>=5 & trips$ORIG_ARR_BIN<=42] <- trips$ORIG_ARR_BIN[!is.na(trips$ORIG_ARR_BIN) & trips$ORIG_ARR_BIN>=5 & trips$ORIG_ARR_BIN<=42]-3
trips$ORIG_ARR_BIN[trips$ORIG_ARR_BIN>=43] <- 40

trips$DEST_DEP_BIN[trips$DEST_DEP_BIN<=4] <- 1
trips$DEST_DEP_BIN[!is.na(trips$DEST_DEP_BIN) & trips$DEST_DEP_BIN>=5 & trips$DEST_DEP_BIN<=42] <- trips$DEST_DEP_BIN[!is.na(trips$DEST_DEP_BIN) & trips$DEST_DEP_BIN>=5 & trips$DEST_DEP_BIN<=42]-3
trips$DEST_DEP_BIN[trips$DEST_DEP_BIN>=43] <- 40

trips$DEST_ARR_BIN[trips$DEST_ARR_BIN<=4] <- 1
trips$DEST_ARR_BIN[!is.na(trips$DEST_ARR_BIN) & trips$DEST_ARR_BIN>=5 & trips$DEST_ARR_BIN<=42] <- trips$DEST_ARR_BIN[!is.na(trips$DEST_ARR_BIN) & trips$DEST_ARR_BIN>=5 & trips$DEST_ARR_BIN<=42]-3
trips$DEST_ARR_BIN[trips$DEST_ARR_BIN>=43] <- 40

#Mark trips which are stops on the tour [not to primary destination and not going back to tour anchor/origin]
trips$stops[trips$DEST_PURP>0 & trips$DEST_PURP<=10 & trips$DEST_IS_TOUR_DEST==0 & trips$DEST_IS_TOUR_ORIG==0] <- 1
trips$stops[is.na(trips$stops)] <- 0

trips$TOUROTAZ <- tours$ORIG_TAZ[match(trips$HH_ID*1000+trips$PER_ID*100+trips$TOUR_ID, 
                                   tours$HH_ID*1000+tours$PER_ID*100+tours$TOUR_ID)]
trips$TOURDTAZ <- tours$DEST_TAZ[match(trips$HH_ID*1000+trips$PER_ID*100+trips$TOUR_ID, 
                                   tours$HH_ID*1000+tours$PER_ID*100+tours$TOUR_ID)]	

# copy tour dep hour and minute
trips$ANCHOR_DEPART_HOUR <- tours$ANCHOR_DEPART_HOUR[match(trips$HH_ID*1000+trips$PER_ID*100+trips$TOUR_ID, 
                                                           tours$HH_ID*1000+tours$PER_ID*100+tours$TOUR_ID)]
trips$ANCHOR_DEPART_MIN <- tours$ANCHOR_DEPART_MIN[match(trips$HH_ID*1000+trips$PER_ID*100+trips$TOUR_ID, 
                                                         tours$HH_ID*1000+tours$PER_ID*100+tours$TOUR_ID)]

trips$od_dist <- DST_SKM$dist[match(paste(trips$ORIG_TAZ, trips$DEST_TAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
trips$od_dist[is.na(trips$od_dist)] <- 0

# export trip file for tour mode choice targets spreadsheet
write.csv(trips[, c("HH_ID", "PER_ID", "TOUR_ID", "TRIP_ID", "TRIPMODE_RECODE","TOURMODE_RECODE", "TOURPURP_RECODE", "AUTOSUFF", "finalweight", "DOW")], 
          "tripModeChoice.csv", row.names = F)


### Create tour and trip file for TM1.5 mode choice targets spreadsheet
########################################################################

# recode trip mode in TM 1.5 format
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==7]                   <- "01_Walk"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==8]                   <- "02_Bike/Moped"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(1,2)]          <- "03_Drive Alone"            
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(3,4)]          <- "04_Shared Ride 2"            
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(5,6)]          <- "05_Shared Ride 3+"            
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==9]                   <- "06_Walk-Local"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(11)]           <- "07_Walk-Light Rail" 
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(23)]           <- "08_Walk-Ferry" 
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==10]                  <- "09_Walk-Express Bus"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==22]                  <- "10_Walk-Heavy Rail"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==21]                  <- "11_Walk-Commuter Rail"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(12,15)]        <- "12_Drive-Local"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(14,17)]        <- "13_Drive-Light Rail"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(33,43)]        <- "14_Drive-Ferry"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(13,16)]        <- "15_Drive-Express Bus"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(32,42)]        <- "16_Drive-Heavy Rail"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG %in% c(31,41)]        <- "17_Drive-Commuter Rail"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==18]                  <- "18_School Bus"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==19]                  <- "19_Taxi/Shuttle"
trips$TRIPMODE_TM15[trips$TRIPMODE_DISAGG==20]                  <- "20_Other"



# recode tour modes in TM 1.5 format

calc_tour_mode <-function(modes_str){
  
  tour_mode <- "None"
  trip_modes <- unlist(strsplit(modes_str, ","))
  
  modes_used <- c()
  for (modes in trip_modes){
    modes_used <- c(modes_used, modes)
  }
  
  dt_modes <- c("12_Drive-Local","13_Drive-Light Rail","14_Drive-Ferry","15_Drive-Express Bus","16_Drive-Heavy Rail","17_Drive-Commuter Rail")
  wt_modes <- c("06_Walk-Local","07_Walk-Light Rail","08_Walk-Ferry","09_Walk-Express Bus","10_Walk-Heavy Rail","11_Walk-Commuter Rail")
  
  lb_modes <- c("12_Drive-Local","06_Walk-Local")
  eb_modes <- c("15_Drive-Express Bus","09_Walk-Express Bus")
  fr_modes <- c("14_Drive-Ferry","08_Walk-Ferry")
  lr_modes <- c("13_Drive-Light Rail","07_Walk-Light Rail")
  hr_modes <- c("16_Drive-Heavy Rail","10_Walk-Heavy Rail")
  cr_modes <- c("17_Drive-Commuter Rail","11_Walk-Commuter Rail")
  
  # Tour mode coding to follow this heirarchy
  # CR > HR > LR > Ferry > EB > LB
  # dt > wt
  # transit > sch bus > bike > taxi > SR3 > SR3 > DA > walk
  
  if(length(intersect(modes_used, dt_modes))>0){
    if(length(intersect(modes_used, cr_modes))>0){
      tour_mode <- "17_Drive-Commuter Rail"
    }else if(length(intersect(modes_used, hr_modes))>0){
      tour_mode <- "16_Drive-Heavy Rail"
    }else if(length(intersect(modes_used, lr_modes))>0){
      tour_mode <- "13_Drive-Light Rail"
    }else if(length(intersect(modes_used, fr_modes))>0){
      tour_mode <- "14_Drive-Ferry"
    }else if(length(intersect(modes_used, eb_modes))>0){
      tour_mode <- "15_Drive-Express Bus"
    }else if(length(intersect(modes_used, lb_modes))>0){
      tour_mode <- "12_Drive-Local"
    }
  }else if(length(intersect(modes_used, wt_modes))>0){
    if(length(intersect(modes_used, cr_modes))>0){
      tour_mode <- "11_Walk-Commuter Rail"
    }else if(length(intersect(modes_used, hr_modes))>0){
      tour_mode <- "10_Walk-Heavy Rail"
    }else if(length(intersect(modes_used, lr_modes))>0){
      tour_mode <- "07_Walk-Light Rail"
    }else if(length(intersect(modes_used, fr_modes))>0){
      tour_mode <- "08_Walk-Ferry"
    }else if(length(intersect(modes_used, eb_modes))>0){
      tour_mode <- "09_Walk-Express Bus"
    }else if(length(intersect(modes_used, lb_modes))>0){
      tour_mode <- "06_Walk-Local"
    }
  }else if("18_School Bus" %in% modes_used){
    tour_mode <- "18_School Bus"
  }else if("02_Bike/Moped" %in% modes_used){
    tour_mode <- "02_Bike/Moped"
  }else if("19_Taxi/Shuttle" %in% modes_used){
    tour_mode <- "19_Taxi/Shuttle"
  }else if("05_Shared Ride 3+" %in% modes_used){
    tour_mode <- "05_Shared Ride 3+"
  }else if("04_Shared Ride 2" %in% modes_used){
    tour_mode <- "04_Shared Ride 2"
  }else if("03_Drive Alone" %in% modes_used){
    tour_mode <- "03_Drive Alone"
  }else if("01_Walk" %in% modes_used){
    tour_mode <- "01_Walk"
  }else{
    tour_mode <- "20_Other"
  }
  
  return(tour_mode)
}


tour_trip_modes <- aggregate(TRIPMODE_TM15 ~ HH_ID + PER_ID + TOUR_ID, data = trips, paste, collapse = ",")
tour_trip_modes$tour_mode <- apply(tour_trip_modes, 1, function(x) calc_tour_mode(x["TRIPMODE_TM15"]))

# copy the computed tour mode to tour and trip table
tours$TOURMODE_TM15 <- tour_trip_modes$tour_mode[match(paste(tours$HH_ID, tours$PER_ID, tours$TOUR_ID, sep = "-"), 
                                                       paste(tour_trip_modes$HH_ID, tour_trip_modes$PER_ID, tour_trip_modes$TOUR_ID, sep = "-"))]
trips$TOURMODE_TM15 <- tours$TOURMODE_TM15[match(paste(trips$HH_ID, trips$PER_ID, trips$TOUR_ID, sep = "-"), 
                                                 paste(tours$HH_ID, tours$PER_ID, tours$TOUR_ID, sep = "-"))]



# Export data for mode choice targets spreadsheet
write.csv(tours[,c("HH_ID", "PER_ID", "TOUR_ID","TOURMODE_TM15", "TOURPURP_RECODE", "AUTOSUFF", "finalweight", "DOW")], 
          "tourModeChoice_TM15.csv", row.names = F)
# export trip file for tour mode choice targets spreadsheet
write.csv(trips[, c("HH_ID", "PER_ID", "TOUR_ID", "TRIP_ID", "TRIPMODE_TM15","TOURMODE_TM15", "TOURPURP_RECODE", "AUTOSUFF", "finalweight", "DOW")], 
          "tripModeChoice_TM15.csv", row.names = F)



#create stops table
stops <- trips[trips$stops==1,]

stops$finaldestTAZ[stops$IS_INBOUND==0] <- stops$TOURDTAZ[stops$IS_INBOUND==0]
stops$finaldestTAZ[stops$IS_INBOUND==1] <- stops$TOUROTAZ[stops$IS_INBOUND==1]

stops$od_dist <- DST_SKM$dist[match(paste(stops$ORIG_TAZ, stops$finaldestTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
stops$os_dist <- DST_SKM$dist[match(paste(stops$ORIG_TAZ, stops$DEST_TAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
stops$sd_dist <- DST_SKM$dist[match(paste(stops$DEST_TAZ, stops$finaldestTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
stops$out_dir_dist <- stops$os_dist + stops$sd_dist - stops$od_dist				

#Joint trips		
#---------------------------------------------------------------------------------------------
# create joint trips file from trip file [trips belonging to fully joint tours]
trips$JTOUR_ID <- tours$JTOUR_ID[match(trips$HH_ID*10000+trips$PER_ID*1000+trips$TOUR_ID*10, 
                                       tours$HH_ID*10000+tours$PER_ID*1000+tours$TOUR_ID*10)]
trips$JTOUR_ID[is.na(trips$JTOUR_ID)] <- 0

jtrips <- trips[trips$JTOUR_ID>0 & trips$JTRIP_ID>0,]   #this contains a joint trip for each person

# joint trips should be a household level file, therefore, remove person dimension
jtrips$PER_ID <- NULL
jtrips <- unique(jtrips[,c("HH_ID", "JTRIP_ID")])
jtrips$uid <- paste(jtrips$HH_ID, jtrips$JTRIP_ID, sep = "-")

jutrips$uid <- paste(jutrips$HH_ID, jutrips$JTRIP_ID, sep = "-")

jtrips$NUMBER_HH <- jutrips$NUMBER_HH[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_1 <- jutrips$PERSON_1[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_2 <- jutrips$PERSON_2[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_3 <- jutrips$PERSON_3[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_4 <- jutrips$PERSON_4[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_5 <- jutrips$PERSON_5[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_6 <- jutrips$PERSON_6[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_7 <- jutrips$PERSON_7[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_8 <- jutrips$PERSON_8[match(jtrips$uid, jutrips$uid)]
jtrips$PERSON_9 <- jutrips$PERSON_9[match(jtrips$uid, jutrips$uid)]
jtrips$COMPOSITION <- jutrips$COMPOSITION[match(jtrips$uid, jutrips$uid)]

jtrips$TOUR_ID <- trips$TOUR_ID[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$JTOUR_ID <- trips$JTOUR_ID[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$finalweight <- trips$finalweight[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	

#remove joint tours from joint_tours with no joint trips in jtrips 
jtours_jtrips <- unique(jtrips[,c("HH_ID", "JTOUR_ID")])
jtours_jtrips$uid <- paste(jtours_jtrips$HH_ID, jtours_jtrips$JTOUR_ID, sep = "-")

jtours$uid <- paste(jtours$HH_ID, jtours$JTOUR_ID, sep = "-")
jtours <- jtours[jtours$uid %in% jtours_jtrips$uid,]
#---------------------------------------------------------------------------------------------

jtrips <- jtrips[!is.na(jtrips$finalweight),]

jtrips$stops <- trips$stops[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$TOURPURP <- trips$TOURPURP[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$DEST_PURP <- trips$DEST_PURP[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$TRIPMODE <- trips$TRIPMODE[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]
jtrips$TOURMODE <- trips$TOURMODE[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$ORIG_TAZ <- trips$ORIG_TAZ[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$DEST_TAZ <- trips$DEST_TAZ[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$TOUROTAZ <- trips$TOUROTAZ[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$TOURDTAZ <- trips$TOURDTAZ[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]
jtrips$DEST_DEP_BIN <- trips$DEST_DEP_BIN[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]
jtrips$ORIG_DEP_BIN <- trips$ORIG_DEP_BIN[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]
jtrips$IS_INBOUND <- trips$IS_INBOUND[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]	
jtrips$ANCHOR_DEPART_HOUR <- trips$ANCHOR_DEPART_HOUR[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]															  
jtrips$ANCHOR_DEPART_MIN <- trips$ANCHOR_DEPART_MIN[match(jtrips$HH_ID*10000+jtrips$JTRIP_ID*100,trips$HH_ID*10000+trips$JTRIP_ID*100)]															  

#some joint trips missing in trip file, so couldnt copy their attributes
jtrips <- jtrips[!is.na(jtrips$IS_INBOUND),]

# get person type and age of all memebrs on joint tours
jtrips$PERTYPE_1 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_1, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_2 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_2, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_3 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_3, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_4 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_4, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_5 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_5, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_6 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_6, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_7 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_7, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_8 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_8, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]
jtrips$PERTYPE_9 <- processedPerson$PERSONTYPE[match(jtrips$HH_ID*100+jtrips$PERSON_9, 
                                                     processedPerson$HHID*100+processedPerson$PERID)]

jtrips$PERTYPE_1 <- ifelse(is.na(jtrips$PERTYPE_1), 0, jtrips$PERTYPE_1)
jtrips$PERTYPE_2 <- ifelse(is.na(jtrips$PERTYPE_2), 0, jtrips$PERTYPE_2)
jtrips$PERTYPE_3 <- ifelse(is.na(jtrips$PERTYPE_3), 0, jtrips$PERTYPE_3)
jtrips$PERTYPE_4 <- ifelse(is.na(jtrips$PERTYPE_4), 0, jtrips$PERTYPE_4)
jtrips$PERTYPE_5 <- ifelse(is.na(jtrips$PERTYPE_5), 0, jtrips$PERTYPE_5)
jtrips$PERTYPE_6 <- ifelse(is.na(jtrips$PERTYPE_6), 0, jtrips$PERTYPE_6)
jtrips$PERTYPE_7 <- ifelse(is.na(jtrips$PERTYPE_7), 0, jtrips$PERTYPE_7)
jtrips$PERTYPE_8 <- ifelse(is.na(jtrips$PERTYPE_8), 0, jtrips$PERTYPE_8)
jtrips$PERTYPE_9 <- ifelse(is.na(jtrips$PERTYPE_9), 0, jtrips$PERTYPE_9)


jtrips$AGE_1 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_1, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_2 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_2, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_3 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_3, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_4 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_4, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_5 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_5, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_6 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_6, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_7 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_7, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_8 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_8, 
                                          processedPerson$HHID*100+processedPerson$PERID)]
jtrips$AGE_9 <- processedPerson$AGE[match(jtrips$HH_ID*100+jtrips$PERSON_9, 
                                          processedPerson$HHID*100+processedPerson$PERID)]

jtrips$AGE_1 <- ifelse(is.na(jtrips$AGE_1), 0, jtrips$AGE_1)
jtrips$AGE_2 <- ifelse(is.na(jtrips$AGE_2), 0, jtrips$AGE_2)
jtrips$AGE_3 <- ifelse(is.na(jtrips$AGE_3), 0, jtrips$AGE_3)
jtrips$AGE_4 <- ifelse(is.na(jtrips$AGE_4), 0, jtrips$AGE_4)
jtrips$AGE_5 <- ifelse(is.na(jtrips$AGE_5), 0, jtrips$AGE_5)
jtrips$AGE_6 <- ifelse(is.na(jtrips$AGE_6), 0, jtrips$AGE_6)
jtrips$AGE_7 <- ifelse(is.na(jtrips$AGE_7), 0, jtrips$AGE_7)
jtrips$AGE_8 <- ifelse(is.na(jtrips$AGE_8), 0, jtrips$AGE_8)
jtrips$AGE_9 <- ifelse(is.na(jtrips$AGE_9), 0, jtrips$AGE_9)

jtrips$MAX_AGE <- pmax(jtrips$AGE_1, jtrips$AGE_2, jtrips$AGE_3, 
                       jtrips$AGE_4, jtrips$AGE_5, jtrips$AGE_6, 
                       jtrips$AGE_7, jtrips$AGE_8, jtrips$AGE_9)

#create stops table
jstops <- jtrips[jtrips$stops==1,]

jstops$finaldestTAZ[jstops$IS_INBOUND==0] <- jstops$TOURDTAZ[jstops$IS_INBOUND==0]
jstops$finaldestTAZ[jstops$IS_INBOUND==1] <- jstops$TOUROTAZ[jstops$IS_INBOUND==1]

jstops$od_dist <- DST_SKM$dist[match(paste(jstops$ORIG_TAZ, jstops$finaldestTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
jstops$os_dist <- DST_SKM$dist[match(paste(jstops$ORIG_TAZ, jstops$DEST_TAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]
jstops$sd_dist <- DST_SKM$dist[match(paste(jstops$DEST_TAZ, jstops$finaldestTAZ, sep = "-"), paste(DST_SKM$o, DST_SKM$d, sep = "-"))]

jstops$out_dir_dist <- jstops$os_dist + jstops$sd_dist - jstops$od_dist	


#---------------------------------------------------------------------------------														  
# create summary for Indi NonMand Tour Frequency Calibration
#---------------------------------------------------------------------------------														  

workCounts <- count(tours[tours$TOURPURP<=10,], c( "HH_ID", "PER_ID"), "(TOURPURP %in% c(1,10)) & IS_SUBTOUR == 0") #[excluding at work subtours]. joint work tours should be considered individual mandatory tours
atWorkCounts <- count(tours[tours$TOURPURP<=10,], c("HH_ID", "PER_ID"), "(IS_SUBTOUR == 1)") #include joint work-subtours as individual subtours
schlCounts <- count(tours[tours$TOURPURP<=10,], c("HH_ID", "PER_ID"), "(TOURPURP %in% c(2,3)) & IS_SUBTOUR == 0") #joint school/university tours should be considered individual mandatory tours
inmCounts <- count(tours[tours$TOURPURP<=10,], c("HH_ID", "PER_ID"), "(TOURPURP>=4 & TOURPURP<=9 & FULLY_JOINT==0 & IS_SUBTOUR == 0) | (TOURPURP==4 & FULLY_JOINT==1 & IS_SUBTOUR == 0)") #joint escort tours should be considered individual non-mandatory tours
itourCounts <- count(tours[tours$TOURPURP<=10,], c("HH_ID", "PER_ID"), "(TOURPURP <= 10 & IS_SUBTOUR == 0 & FULLY_JOINT==0) | (TOURPURP <= 4 & FULLY_JOINT==1 & IS_SUBTOUR == 0)")  #number of individual tours per person [excluding at work subtours]
jtourCounts <- count(tours[tours$TOURPURP<=10,], c("HH_ID", "PER_ID"), "TOURPURP >= 5 & TOURPURP <= 9 & IS_SUBTOUR == 0 & FULLY_JOINT==1")  #number of joint tours per person [excluding at work subtours, also excluding joint escort tours]

workCounts_temp <- workCounts
schlCounts_temp <- schlCounts
inmCounts_temp <- inmCounts
jtourCounts_temp <- jtourCounts
atWorkCounts_temp <- atWorkCounts

colnames(workCounts_temp)[3] <- "freq_work"
colnames(schlCounts_temp)[3] <- "freq_schl"
colnames(inmCounts_temp)[3] <- "freq_inm"
colnames(jtourCounts_temp)[3] <- "freq_joint"
colnames(atWorkCounts_temp)[3] <- "freq_atwork"

temp <- merge(workCounts_temp, schlCounts_temp, by = c( "HH_ID", "PER_ID"))
temp1 <- merge(temp, inmCounts_temp, by = c( "HH_ID", "PER_ID"))
temp1$freq_m <- temp1$freq_work + temp1$freq_schl
temp1 <- temp1[temp1$freq_m>0 | temp1$freq_inm>0,]

#joint tours
jtourCounts_temp[is.na(jtourCounts_temp)] <- 0
temp_joint <- jtourCounts_temp[jtourCounts_temp$freq_joint>0,]

temp2 <- merge(temp1, temp_joint, by = c("HH_ID", "PER_ID"), all = T)
temp2 <- merge(temp2, atWorkCounts_temp, by = c("HH_ID", "PER_ID"), all = T)
temp2[is.na(temp2)] <- 0

#add number of joint tours to non-mandatory
temp2$freq_nm <- temp2$freq_inm + temp2$freq_joint

#total tours
temp2$total_tours <- temp2$freq_nm+temp2$freq_m+temp2$freq_atwork

temp2$PERTYPE <- per$PERTYPE[match(temp2$HH_ID*1000+temp2$PER_ID*10,per$SAMPN*1000+per$PERNO*10)]
temp2$finalweight <- per$finalweight[match(temp2$HH_ID*1000+temp2$PER_ID*10,per$SAMPN*1000+per$PERNO*10)]
temp2 <- temp2[!is.na(temp2$PERTYPE),]

persons_mand <- temp2[temp2$freq_m>0,]  #persons with atleast 1 mandatory tours
persons_nomand <- temp2[temp2$freq_m==0,] #active persons with 0 mandatory tours

# joint tours counted as iNM for calibraiton purpose [model does not allow 0 iNM and >0 JT]

freq_nmtours_mand <- count(persons_mand, c("PERTYPE","freq_nm"), "finalweight")
freq_nmtours_nomand <- count(persons_nomand, c("PERTYPE","freq_nm"), "finalweight")

write.table("Non-Mandatory Tours for Persons with at-least 1 Mandatory Tour", "indivNMTourFreq.csv", sep = ",", row.names = F, append = F)
write.table(freq_nmtours_mand, "indivNMTourFreq.csv", sep = ",", row.names = F, append = T)
write.table("Non-Mandatory Tours for Active Persons with 0 Mandatory Tour", "indivNMTourFreq.csv", sep = ",", row.names = F, append = T)
write.table(freq_nmtours_nomand, "indivNMTourFreq.csv", sep = ",", row.names = F, append = TRUE)

#---------------------------------------------------------------------------------														  
# End of Indi Non Mand Tour Frequency Calibration Summary
#---------------------------------------------------------------------------------														  



#---------------------------------------------------------------------------------														  

#workCounts <- count(tours, c( "HH_ID", "PER_ID"), "TOURPURP == 1 & IS_SUBTOUR == 0") #[excluding at work subtours]
#atWorkCounts <- count(tours, c("HH_ID", "PER_ID"), "TOURPURP == 10 & FULLY_JOINT==0 & IS_SUBTOUR == 1")
#schlCounts <- count(tours, c("HH_ID", "PER_ID"), "TOURPURP == 2 | TOURPURP == 3")
#inmCounts <- count(tours, c("HH_ID", "PER_ID"), "TOURPURP>=4 & TOURPURP<=9 & FULLY_JOINT==0 & IS_SUBTOUR == 0")
#itourCounts <- count(tours, c("HH_ID", "PER_ID"), "TOURPURP <= 10 & IS_SUBTOUR == 0 & FULLY_JOINT==0")  #number of individual tours per person [excluding at work subtours]
#jtourCounts <- count(tours, c("HH_ID", "PER_ID"), "TOURPURP >= 5 & TOURPURP <= 9 & IS_SUBTOUR == 0 & FULLY_JOINT==1")  #number of joint tours per person [excluding at work subtours]
joint5 <- count(jtours, c("HH_ID"), "JOINT_PURP==5")
joint6 <- count(jtours, c("HH_ID"), "JOINT_PURP==6")
joint7 <- count(jtours, c("HH_ID"), "JOINT_PURP==7")
joint8 <- count(jtours, c("HH_ID"), "JOINT_PURP==8")
joint9 <- count(jtours, c("HH_ID"), "JOINT_PURP==9")

hh$joint5 <- joint5$freq[match(hh$SAMPN, joint5$HH_ID)]
hh$joint6 <- joint6$freq[match(hh$SAMPN, joint6$HH_ID)]
hh$joint7 <- joint7$freq[match(hh$SAMPN, joint7$HH_ID)]
hh$joint8 <- joint8$freq[match(hh$SAMPN, joint8$HH_ID)]
hh$joint9 <- joint9$freq[match(hh$SAMPN, joint9$HH_ID)]
hh$jtours <- hh$joint5+hh$joint6+hh$joint7+hh$joint8+hh$joint9

hh$joint5[is.na(hh$joint5)] <- 0
hh$joint6[is.na(hh$joint6)] <- 0
hh$joint7[is.na(hh$joint7)] <- 0
hh$joint8[is.na(hh$joint8)] <- 0
hh$joint9[is.na(hh$joint9)] <- 0
hh$jtours[is.na(hh$jtours)] <- 0
hh$JOINT <- 0
hh$JOINT[hh$jtours>0] <- 1

# code JTF category
hh$jtf[hh$jtours==0] <- 1 
hh$jtf[hh$joint5==1] <- 2
hh$jtf[hh$joint6==1] <- 3
hh$jtf[hh$joint7==1] <- 4
hh$jtf[hh$joint8==1] <- 5
hh$jtf[hh$joint9==1] <- 6

hh$jtf[hh$joint5>=2] <- 7
hh$jtf[hh$joint6>=2] <- 8
hh$jtf[hh$joint7>=2] <- 9
hh$jtf[hh$joint8>=2] <- 10
hh$jtf[hh$joint9>=2] <- 11

hh$jtf[hh$joint5>=1 & hh$joint6>=1] <- 12
hh$jtf[hh$joint5>=1 & hh$joint7>=1] <- 13
hh$jtf[hh$joint5>=1 & hh$joint8>=1] <- 14
hh$jtf[hh$joint5>=1 & hh$joint9>=1] <- 15

hh$jtf[hh$joint6>=1 & hh$joint7>=1] <- 16
hh$jtf[hh$joint6>=1 & hh$joint8>=1] <- 17
hh$jtf[hh$joint6>=1 & hh$joint9>=1] <- 18

hh$jtf[hh$joint7>=1 & hh$joint8>=1] <- 19
hh$jtf[hh$joint7>=1 & hh$joint9>=1] <- 20

hh$jtf[hh$joint8>=1 & hh$joint9>=1] <- 21

per$workTours   <- workCounts$freq[match(per$SAMPN*1000+per$PERNO*10, workCounts$HH_ID*1000+workCounts$PER_ID*10)]
per$atWorkTours <- atWorkCounts$freq[match(per$SAMPN*1000+per$PERNO*10, atWorkCounts$HH_ID*1000+atWorkCounts$PER_ID*10)]
per$schlTours   <- schlCounts$freq[match(per$SAMPN*1000+per$PERNO*10, schlCounts$HH_ID*1000+schlCounts$PER_ID*10)]
per$inmTours    <- inmCounts$freq[match(per$SAMPN*1000+per$PERNO*10, inmCounts$HH_ID*1000+inmCounts$PER_ID*10)]
per$inmTours[is.na(per$inmTours)] <- 0
per$inumTours <- itourCounts$freq[match(per$SAMPN*1000+per$PERNO*10, itourCounts$HH_ID*1000+itourCounts$PER_ID*10)]
per$inumTours[is.na(per$inumTours)] <- 0
per$jnumTours <- jtourCounts$freq[match(per$SAMPN*1000+per$PERNO*10, jtourCounts$HH_ID*1000+jtourCounts$PER_ID*10)]
per$jnumTours[is.na(per$jnumTours)] <- 0
per$numTours <- per$inumTours + per$jnumTours

per$workTours[is.na(per$workTours)] <- 0
per$schlTours[is.na(per$schlTours)] <- 0
per$atWorkTours[is.na(per$atWorkTours)] <- 0

# Individual tours by person type
per$numTours[is.na(per$numTours)] <- 0
toursPertypeDistbn <- count(tours[!is.na(tours$TOURPURP) & tours$TOURPURP<=10 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR==0,], c("PERTYPE"), "finalweight")
write.csv(toursPertypeDistbn, "toursPertypeDistbn.csv", row.names = TRUE)

# Total tours by person type for visualizer
totaltoursPertypeDistbn <- count(tours[!is.na(tours$PERTYPE) & !is.na(tours$TOURPURP) & tours$TOURPURP<=10 & tours$IS_SUBTOUR==0,], c("PERTYPE"), "finalweight")
write.csv(totaltoursPertypeDistbn, "total_tours_by_pertype_vis.csv", row.names = F)


# Total indi NM tours by person type and purpose
tours_pertype_purpose <- count(tours[(tours$TOURPURP>=4 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR==0) | (tours$TOURPURP==4 & tours$FULLY_JOINT==0),], c("PERTYPE", "TOURPURP"), "finalweight")
write.csv(tours_pertype_purpose, "tours_pertype_purpose.csv", row.names = TRUE)

tours_pertype_purpose <- xtabs(freq~PERTYPE+TOURPURP, tours_pertype_purpose)
tours_pertype_purpose[is.na(tours_pertype_purpose)] <- 0
tours_pertype_purpose <- addmargins(as.table(tours_pertype_purpose))
tours_pertype_purpose <- as.data.frame.matrix(tours_pertype_purpose)

totalPersons <- sum(pertypeDistbn$freq)
totalPersons_DF <- data.frame("Total", totalPersons)
colnames(totalPersons_DF) <- colnames(pertypeDistbn)
pertypeDF <- rbind(pertypeDistbn, totalPersons_DF)
nm_tour_rates <- tours_pertype_purpose/pertypeDF$freq
nm_tour_rates$pertype <- row.names(nm_tour_rates)
nm_tour_rates <- melt(nm_tour_rates, id = c("pertype"))
colnames(nm_tour_rates) <- c("pertype", "tour_purp", "tour_rate")
nm_tour_rates$pertype <- as.character(nm_tour_rates$pertype)
nm_tour_rates$tour_purp <- as.character(nm_tour_rates$tour_purp)
nm_tour_rates$pertype[nm_tour_rates$pertype=="Sum"] <- "All"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp=="Sum"] <- "All"
nm_tour_rates$pertype <- pertypeCodes$name[match(nm_tour_rates$pertype, pertypeCodes$code)]

nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==4] <- "Escorting"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==5] <- "Shopping"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==6] <- "Maintenance"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==7] <- "EatingOut"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==8] <- "Visiting"
nm_tour_rates$tour_purp[nm_tour_rates$tour_purp==9] <- "Discretionary"

write.csv(nm_tour_rates, "nm_tour_rates.csv", row.names = F)

# Total tours by purpose X tourtype
t1 <- wtd.hist(tours$TOURPURP[!is.na(tours$TOURPURP) & tours$TOURPURP<=10 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR==0], breaks = seq(1,10, by=1), freq = NULL, right=FALSE, weight=tours$finalweight[!is.na(tours$TOURPURP) & tours$TOURPURP<=10 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR==0])
t3 <- wtd.hist(jtours$JOINT_PURP[jtours$JOINT_PURP<10], breaks = seq(1,10, by=1), freq = NULL, right=FALSE, weight=jtours$finalweight[jtours$JOINT_PURP<10])
tours_purpose_type <- data.frame(t1$counts, t3$counts)
colnames(tours_purpose_type) <- c("indi", "joint")
write.csv(tours_purpose_type, "tours_purpose_type.csv", row.names = TRUE)


# DAP by pertype
per$DAP <- "H"
per$DAP[per$workTours > 0 | per$schlTours > 0] <- "M"
per$DAP[per$numTours > 0 & per$DAP == "H"] <- "N"
dapSummary <- count(per, c("PERTYPE", "DAP"), "finalweight")
write.csv(dapSummary, "dapSummary.csv", row.names = TRUE)

# Prepare DAP summary for visualizer
dapSummary_vis <- xtabs(freq~PERTYPE+DAP, dapSummary)
dapSummary_vis <- addmargins(as.table(dapSummary_vis))
dapSummary_vis <- as.data.frame.matrix(dapSummary_vis)

dapSummary_vis$id <- row.names(dapSummary_vis)
dapSummary_vis <- melt(dapSummary_vis, id = c("id"))
colnames(dapSummary_vis) <- c("PERTYPE", "DAP", "freq")
dapSummary_vis$DAP <- as.character(dapSummary_vis$DAP)
dapSummary_vis$PERTYPE <- as.character(dapSummary_vis$PERTYPE)
dapSummary_vis <- dapSummary_vis[dapSummary_vis$DAP!="Sum",]
dapSummary_vis$PERTYPE[dapSummary_vis$PERTYPE=="Sum"] <- "Total"
write.csv(dapSummary_vis, "dapSummary_vis.csv", row.names = TRUE)

# HHSize X Joint
hhsizeJoint <- count(hh[hh$HHSIZE>=2,], c("HHSIZE", "JOINT"), "finalweight")
write.csv(hhsizeJoint, "hhsizeJoint.csv", row.names = TRUE)

#mandatory tour frequency
per$mtf <- 0
per$mtf[per$workTours == 1] <- 1
per$mtf[per$workTours >= 2] <- 2
per$mtf[per$schlTours == 1] <- 3
per$mtf[per$schlTours >= 2] <- 4
per$mtf[per$workTours >= 1 & per$schlTours >= 1] <- 5

mtfSummary <- count(per[per$mtf > 0,], c("PERTYPE", "mtf"), "finalweight")
write.csv(mtfSummary, "mtfSummary.csv")
write.csv(tours, "tours_test.csv")

# Prepare MTF summary for visualizer
mtfSummary_vis <- xtabs(freq~PERTYPE+mtf, mtfSummary)
mtfSummary_vis <- addmargins(as.table(mtfSummary_vis))
mtfSummary_vis <- as.data.frame.matrix(mtfSummary_vis)

mtfSummary_vis$id <- row.names(mtfSummary_vis)
mtfSummary_vis <- melt(mtfSummary_vis, id = c("id"))
colnames(mtfSummary_vis) <- c("PERTYPE", "MTF", "freq")
mtfSummary_vis$PERTYPE <- as.character(mtfSummary_vis$PERTYPE)
mtfSummary_vis$MTF <- as.character(mtfSummary_vis$MTF)
mtfSummary_vis <- mtfSummary_vis[mtfSummary_vis$MTF!="Sum",]
mtfSummary_vis$PERTYPE[mtfSummary_vis$PERTYPE=="Sum"] <- "Total"
write.csv(mtfSummary_vis, "mtfSummary_vis.csv")

# indi NM summary
# joint tours included to be consistent with model 
# [Model doesnt allow 0 iNM and >0 JT]
inm0Summary <- count(per[per$numTours==0,], c("PERTYPE"), "finalweight")
inm1Summary <- count(per[per$numTours==1,], c("PERTYPE"), "finalweight")
inm2Summary <- count(per[per$numTours==2,], c("PERTYPE"), "finalweight")
inm3Summary <- count(per[per$numTours>=3,], c("PERTYPE"), "finalweight")

inmSummary <- data.frame(PERTYPE = c(1,2,3,4,5,6,7,8))
inmSummary$tour0 <- inm0Summary$freq[match(inmSummary$PERTYPE, inm0Summary$PERTYPE)]
inmSummary$tour1 <- inm1Summary$freq[match(inmSummary$PERTYPE, inm1Summary$PERTYPE)]
inmSummary$tour2 <- inm2Summary$freq[match(inmSummary$PERTYPE, inm2Summary$PERTYPE)]
inmSummary$tour3pl <- inm3Summary$freq[match(inmSummary$PERTYPE, inm3Summary$PERTYPE)]

write.table(inmSummary, "innmSummary.csv", col.names=TRUE, sep=",")

# prepare INM summary for visualizer
inmSummary_vis <- melt(inmSummary, id=c("PERTYPE"))
inmSummary_vis$variable <- as.character(inmSummary_vis$variable)
inmSummary_vis$variable[inmSummary_vis$variable=="tour0"] <- "0"
inmSummary_vis$variable[inmSummary_vis$variable=="tour1"] <- "1"
inmSummary_vis$variable[inmSummary_vis$variable=="tour2"] <- "2"
inmSummary_vis$variable[inmSummary_vis$variable=="tour3pl"] <- "3pl"
inmSummary_vis <- xtabs(value~PERTYPE+variable, inmSummary_vis)
inmSummary_vis <- addmargins(as.table(inmSummary_vis))
inmSummary_vis <- as.data.frame.matrix(inmSummary_vis)

inmSummary_vis$id <- row.names(inmSummary_vis)
inmSummary_vis <- melt(inmSummary_vis, id = c("id"))
colnames(inmSummary_vis) <- c("PERTYPE", "nmtours", "freq")
inmSummary_vis$PERTYPE <- as.character(inmSummary_vis$PERTYPE)
inmSummary_vis$nmtours <- as.character(inmSummary_vis$nmtours)
inmSummary_vis <- inmSummary_vis[inmSummary_vis$nmtours!="Sum",]
inmSummary_vis$PERTYPE[inmSummary_vis$PERTYPE=="Sum"] <- "Total"
write.csv(inmSummary_vis, "inmSummary_vis.csv")

# Joint Tour Frequency and composition
jtfSummary <- count(hh[!is.na(hh$jtf),], c("jtf"), "finalweight")
jointComp <- count(jtours[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=9,], c("COMPOSITION"), "finalweight")
jointPartySize <- count(jtours[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=9,], c("NUMBER_HH"), "finalweight")
jointCompPartySize <- count(jtours[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=9,], c("COMPOSITION","NUMBER_HH"), "finalweight")

hh$jointCat[hh$jtours==0] <- 0
hh$jointCat[hh$jtours==1] <- 1
hh$jointCat[hh$jtours>=2] <- 2

jointToursHHSize <- count(hh[!is.na(hh$HHSIZE) & !is.na(hh$jointCat),], c("HHSIZE", "jointCat"), "finalweight")

write.table(jtfSummary, "jtfSummary.csv", col.names=TRUE, sep=",")
write.table(jointComp, "jtfSummary.csv", col.names=TRUE, sep=",", append=TRUE)
write.table(jointPartySize, "jtfSummary.csv", col.names=TRUE, sep=",", append=TRUE)
write.table(jointCompPartySize, "jtfSummary.csv", col.names=TRUE, sep=",", append=TRUE)
write.table(jointToursHHSize, "jtfSummary.csv", col.names=TRUE, sep=",", append=TRUE)

#cap joint party size to 5+
jointPartySize$freq[jointPartySize$NUMBER_HH==5] <- sum(jointPartySize$freq[jointPartySize$NUMBER_HH>=5])
jointPartySize <- jointPartySize[jointPartySize$NUMBER_HH<=5, ]

jtf <- data.frame(jtf_code = seq(from = 1, to = 21), 
                  alt_name = c("No Joint Tours", "1 Shopping", "1 Maintenance", "1 Eating Out", "1 Visiting", "1 Other Discretionary", 
                               "2 Shopping", "1 Shopping / 1 Maintenance", "1 Shopping / 1 Eating Out", "1 Shopping / 1 Visiting", 
                               "1 Shopping / 1 Other Discretionary", "2 Maintenance", "1 Maintenance / 1 Eating Out", 
                               "1 Maintenance / 1 Visiting", "1 Maintenance / 1 Other Discretionary", "2 Eating Out", "1 Eating Out / 1 Visiting", 
                               "1 Eating Out / 1 Other Discretionary", "2 Visiting", "1 Visiting / 1 Other Discretionary", "2 Other Discretionary"))
jtf$freq <- jtfSummary$freq[match(jtf$jtf_code, jtfSummary$jtf)]
jtf[is.na(jtf)] <- 0

jointComp$COMPOSITION[jointComp$COMPOSITION==1] <- "All Adult"
jointComp$COMPOSITION[jointComp$COMPOSITION==2] <- "All Children"
jointComp$COMPOSITION[jointComp$COMPOSITION==3] <- "Mixed"

jointToursHHSizeProp <- xtabs(freq~jointCat+HHSIZE, jointToursHHSize[jointToursHHSize$HHSIZE>1,])
jointToursHHSizeProp <- addmargins(as.table(jointToursHHSizeProp))
jointToursHHSizeProp <- jointToursHHSizeProp[-4,]  #remove last row 
jointToursHHSizeProp <- prop.table(jointToursHHSizeProp, margin = 2)
jointToursHHSizeProp <- as.data.frame.matrix(jointToursHHSizeProp)
jointToursHHSizeProp <- jointToursHHSizeProp*100
jointToursHHSizeProp$jointTours <- row.names(jointToursHHSizeProp)
jointToursHHSizeProp <- melt(jointToursHHSizeProp, id = c("jointTours"))
colnames(jointToursHHSizeProp) <- c("jointTours", "hhsize", "freq")
jointToursHHSizeProp$hhsize <- as.character(jointToursHHSizeProp$hhsize)
jointToursHHSizeProp$hhsize[jointToursHHSizeProp$hhsize=="Sum"] <- "Total"

jointCompPartySize$COMPOSITION[jointCompPartySize$COMPOSITION==1] <- "All Adult"
jointCompPartySize$COMPOSITION[jointCompPartySize$COMPOSITION==2] <- "All Children"
jointCompPartySize$COMPOSITION[jointCompPartySize$COMPOSITION==3] <- "Mixed"

jointCompPartySizeProp <- xtabs(freq~COMPOSITION+NUMBER_HH, jointCompPartySize)
jointCompPartySizeProp <- addmargins(as.table(jointCompPartySizeProp))
jointCompPartySizeProp <- jointCompPartySizeProp[,-6]  #remove last row 
jointCompPartySizeProp <- prop.table(jointCompPartySizeProp, margin = 1)
jointCompPartySizeProp <- as.data.frame.matrix(jointCompPartySizeProp)
jointCompPartySizeProp <- jointCompPartySizeProp*100
jointCompPartySizeProp$comp <- row.names(jointCompPartySizeProp)
jointCompPartySizeProp <- melt(jointCompPartySizeProp, id = c("comp"))
colnames(jointCompPartySizeProp) <- c("comp", "partysize", "freq")
jointCompPartySizeProp$comp <- as.character(jointCompPartySizeProp$comp)
jointCompPartySizeProp$comp[jointCompPartySizeProp$comp=="Sum"] <- "Total"

# Cap joint comp party size at 5
jointCompPartySizeProp <- jointCompPartySizeProp[jointCompPartySizeProp$partysize!="Sum",]
jointCompPartySizeProp$partysize <- as.numeric(as.character(jointCompPartySizeProp$partysize))
jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="All Adult" & jointCompPartySizeProp$partysize==5] <- 
  sum(jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="All Adult" & jointCompPartySizeProp$partysize>=5])
jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="All Children" & jointCompPartySizeProp$partysize==5] <- 
  sum(jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="All Children" & jointCompPartySizeProp$partysize>=5])
jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="Mixed" & jointCompPartySizeProp$partysize==5] <- 
  sum(jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="Mixed" & jointCompPartySizeProp$partysize>=5])
jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="Total" & jointCompPartySizeProp$partysize==5] <- 
  sum(jointCompPartySizeProp$freq[jointCompPartySizeProp$comp=="Total" & jointCompPartySizeProp$partysize>=5])

jointCompPartySizeProp <- jointCompPartySizeProp[jointCompPartySizeProp$partysize<=5,]



write.csv(jtf, "jtf.csv", row.names = F)
write.csv(jointComp, "jointComp.csv", row.names = F)
write.csv(jointPartySize, "jointPartySize.csv", row.names = F)
write.csv(jointCompPartySizeProp, "jointCompPartySize.csv", row.names = F)
write.csv(jointToursHHSizeProp, "jointToursHHSize.csv", row.names = F)

# TOD Profile
tod1 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
tod2 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
tod3 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
tod4 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
todi56 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
todi789 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
todj56 <- wtd.hist(jtours$ANCHOR_DEPART_BIN[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
todj789 <- wtd.hist(jtours$ANCHOR_DEPART_BIN[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
tod15 <- wtd.hist(tours$ANCHOR_DEPART_BIN[tours$IS_SUBTOUR == 1], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

todDepProfile <- data.frame(tod1$counts, tod2$counts, tod3$counts, tod4$counts, todi56$counts, todi789$counts
                            , todj56$counts, todj789$counts, tod15$counts)
colnames(todDepProfile) <- c("work", "univ", "sch", "esc", "imain", "idisc", 
                             "jmain", "jdisc", "atwork")
write.csv(todDepProfile, "todDepProfile.csv")

# prepare input for visualizer
todDepProfile_vis <- todDepProfile
todDepProfile_vis$id <- row.names(todDepProfile_vis)
todDepProfile_vis <- melt(todDepProfile_vis, id = c("id"))
colnames(todDepProfile_vis) <- c("id", "purpose", "freq")

todDepProfile_vis$purpose <- as.character(todDepProfile_vis$purpose)
todDepProfile_vis <- xtabs(freq~id+purpose, todDepProfile_vis)
todDepProfile_vis <- addmargins(as.table(todDepProfile_vis))
todDepProfile_vis <- as.data.frame.matrix(todDepProfile_vis)
todDepProfile_vis$id <- row.names(todDepProfile_vis)
todDepProfile_vis <- melt(todDepProfile_vis, id = c("id"))
colnames(todDepProfile_vis) <- c("timebin", "PURPOSE", "freq")
todDepProfile_vis$PURPOSE <- as.character(todDepProfile_vis$PURPOSE)
todDepProfile_vis$timebin <- as.character(todDepProfile_vis$timebin)
todDepProfile_vis <- todDepProfile_vis[todDepProfile_vis$timebin!="Sum",]
todDepProfile_vis$PURPOSE[todDepProfile_vis$PURPOSE=="Sum"] <- "Total"
todDepProfile_vis$timebin <- as.numeric(todDepProfile_vis$timebin)

arr1 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
arr2 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
arr3 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
arr4 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
arri56 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
arri789 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
arrj56 <- wtd.hist(jtours$ANCHOR_ARRIVE_BIN[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
arrj789 <- wtd.hist(jtours$ANCHOR_ARRIVE_BIN[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
arr15 <- wtd.hist(tours$ANCHOR_ARRIVE_BIN[tours$IS_SUBTOUR == 1], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])


todArrProfile <- data.frame(arr1$counts, arr2$counts, arr3$counts, arr4$counts, arri56$counts, arri789$counts
                            , arrj56$counts, arrj789$counts, arr15$counts)
colnames(todArrProfile) <- c("work", "univ", "sch", "esc", "imain", "idisc", 
                             "jmain", "jdisc", "atwork")
write.csv(todArrProfile, "todArrProfile.csv")

# prepare input for visualizer
todArrProfile_vis <- todArrProfile
todArrProfile_vis$id <- row.names(todArrProfile_vis)
todArrProfile_vis <- melt(todArrProfile_vis, id = c("id"))
colnames(todArrProfile_vis) <- c("id", "purpose", "freq_arr")

todArrProfile_vis$purpose <- as.character(todArrProfile_vis$purpose)
todArrProfile_vis <- xtabs(freq_arr~id+purpose, todArrProfile_vis)
todArrProfile_vis <- addmargins(as.table(todArrProfile_vis))
todArrProfile_vis <- as.data.frame.matrix(todArrProfile_vis)
todArrProfile_vis$id <- row.names(todArrProfile_vis)
todArrProfile_vis <- melt(todArrProfile_vis, id = c("id"))
colnames(todArrProfile_vis) <- c("timebin", "PURPOSE", "freq")
todArrProfile_vis$PURPOSE <- as.character(todArrProfile_vis$PURPOSE)
todArrProfile_vis$timebin <- as.character(todArrProfile_vis$timebin)
todArrProfile_vis <- todArrProfile_vis[todArrProfile_vis$timebin!="Sum",]
todArrProfile_vis$PURPOSE[todArrProfile_vis$PURPOSE=="Sum"] <- "Total"
todArrProfile_vis$timebin <- as.numeric(todArrProfile_vis$timebin)

dur1 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
dur2 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
dur3 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
dur4 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
duri56 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
duri789 <- wtd.hist(tours$TOUR_DUR_BIN[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
durj56 <- wtd.hist(jtours$TOUR_DUR_BIN[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
durj789 <- wtd.hist(jtours$TOUR_DUR_BIN[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
dur15 <- wtd.hist(tours$TOUR_DUR_BIN[tours$IS_SUBTOUR == 1], breaks = seq(1,41, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

todDurProfile <- data.frame(dur1$counts, dur2$counts, dur3$counts, dur4$counts, duri56$counts, duri789$counts
                            , durj56$counts, durj789$counts, dur15$counts)
colnames(todDurProfile) <- c("work", "univ", "sch", "esc", "imain", "idisc", 
                             "jmain", "jdisc", "atwork")
write.csv(todDurProfile, "todDurProfile.csv")

# prepare input for visualizer
todDurProfile_vis <- todDurProfile
todDurProfile_vis$id <- row.names(todDurProfile_vis)
todDurProfile_vis <- melt(todDurProfile_vis, id = c("id"))
colnames(todDurProfile_vis) <- c("id", "purpose", "freq_dur")

todDurProfile_vis$purpose <- as.character(todDurProfile_vis$purpose)
todDurProfile_vis <- xtabs(freq_dur~id+purpose, todDurProfile_vis)
todDurProfile_vis <- addmargins(as.table(todDurProfile_vis))
todDurProfile_vis <- as.data.frame.matrix(todDurProfile_vis)
todDurProfile_vis$id <- row.names(todDurProfile_vis)
todDurProfile_vis <- melt(todDurProfile_vis, id = c("id"))
colnames(todDurProfile_vis) <- c("timebin", "PURPOSE", "freq")
todDurProfile_vis$PURPOSE <- as.character(todDurProfile_vis$PURPOSE)
todDurProfile_vis$timebin <- as.character(todDurProfile_vis$timebin)
todDurProfile_vis <- todDurProfile_vis[todDurProfile_vis$timebin!="Sum",]
todDurProfile_vis$PURPOSE[todDurProfile_vis$PURPOSE=="Sum"] <- "Total"
todDurProfile_vis$timebin <- as.numeric(todDurProfile_vis$timebin)

todDepProfile_vis <- todDepProfile_vis[order(todDepProfile_vis$timebin, todDepProfile_vis$PURPOSE), ]
todArrProfile_vis <- todArrProfile_vis[order(todArrProfile_vis$timebin, todArrProfile_vis$PURPOSE), ]
todDurProfile_vis <- todDurProfile_vis[order(todDurProfile_vis$timebin, todDurProfile_vis$PURPOSE), ]
todProfile_vis <- data.frame(todDepProfile_vis, todArrProfile_vis$freq, todDurProfile_vis$freq)
colnames(todProfile_vis) <- c("id", "purpose", "freq_dep", "freq_arr", "freq_dur")
write.csv(todProfile_vis, "todProfile_vis.csv", row.names = F)

# Tour Mode X Auto Suff
tmode1_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0])
tmode2_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0])
tmode3_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==0])
tmode4_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==0])
tmode5_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==0])
tmode6_as0 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==0])
tmode7_as0 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==0])
tmode8_as0 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==0])

tmodeAS0Profile <- data.frame(tmode1_as0$counts, tmode2_as0$counts, tmode3_as0$counts, tmode4_as0$counts,
                              tmode5_as0$counts, tmode6_as0$counts, tmode7_as0$counts, tmode8_as0$counts)
colnames(tmodeAS0Profile) <- c("work", "univ", "sch", "imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(tmodeAS0Profile, "tmodeAS0Profile_CHTS.csv")

# Prepeare data for visualizer
tmodeAS0Profile_vis <- tmodeAS0Profile[1:9,]
tmodeAS0Profile_vis$id <- row.names(tmodeAS0Profile_vis)
tmodeAS0Profile_vis <- melt(tmodeAS0Profile_vis, id = c("id"))
colnames(tmodeAS0Profile_vis) <- c("id", "purpose", "freq_as0")

tmodeAS0Profile_vis <- xtabs(freq_as0~id+purpose, tmodeAS0Profile_vis)
tmodeAS0Profile_vis[is.na(tmodeAS0Profile_vis)] <- 0
tmodeAS0Profile_vis <- addmargins(as.table(tmodeAS0Profile_vis))
tmodeAS0Profile_vis <- as.data.frame.matrix(tmodeAS0Profile_vis)

tmodeAS0Profile_vis$id <- row.names(tmodeAS0Profile_vis)
tmodeAS0Profile_vis <- melt(tmodeAS0Profile_vis, id = c("id"))
colnames(tmodeAS0Profile_vis) <- c("id", "purpose", "freq_as0")
tmodeAS0Profile_vis$id <- as.character(tmodeAS0Profile_vis$id)
tmodeAS0Profile_vis$purpose <- as.character(tmodeAS0Profile_vis$purpose)
tmodeAS0Profile_vis <- tmodeAS0Profile_vis[tmodeAS0Profile_vis$id!="Sum",]
tmodeAS0Profile_vis$purpose[tmodeAS0Profile_vis$purpose=="Sum"] <- "Total"


tmode1_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1])
tmode2_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1])
tmode3_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==1])
tmode4_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==1])
tmode5_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==1])
tmode6_as1 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==1])
tmode7_as1 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==1])
tmode8_as1 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==1])

tmodeAS1Profile <- data.frame(tmode1_as1$counts, tmode2_as1$counts, tmode3_as1$counts, tmode4_as1$counts,
                              tmode5_as1$counts, tmode6_as1$counts, tmode7_as1$counts, tmode8_as1$counts)
colnames(tmodeAS1Profile) <- c("work", "univ", "sch", "imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(tmodeAS1Profile, "tmodeAS1Profile_CHTS.csv")

# Prepeare data for visualizer
tmodeAS1Profile_vis <- tmodeAS1Profile[1:9,]
tmodeAS1Profile_vis$id <- row.names(tmodeAS1Profile_vis)
tmodeAS1Profile_vis <- melt(tmodeAS1Profile_vis, id = c("id"))
colnames(tmodeAS1Profile_vis) <- c("id", "purpose", "freq_as1")

tmodeAS1Profile_vis <- xtabs(freq_as1~id+purpose, tmodeAS1Profile_vis)
tmodeAS1Profile_vis[is.na(tmodeAS1Profile_vis)] <- 0
tmodeAS1Profile_vis <- addmargins(as.table(tmodeAS1Profile_vis))
tmodeAS1Profile_vis <- as.data.frame.matrix(tmodeAS1Profile_vis)

tmodeAS1Profile_vis$id <- row.names(tmodeAS1Profile_vis)
tmodeAS1Profile_vis <- melt(tmodeAS1Profile_vis, id = c("id"))
colnames(tmodeAS1Profile_vis) <- c("id", "purpose", "freq_as1")
tmodeAS1Profile_vis$id <- as.character(tmodeAS1Profile_vis$id)
tmodeAS1Profile_vis$purpose <- as.character(tmodeAS1Profile_vis$purpose)
tmodeAS1Profile_vis <- tmodeAS1Profile_vis[tmodeAS1Profile_vis$id!="Sum",]
tmodeAS1Profile_vis$purpose[tmodeAS1Profile_vis$purpose=="Sum"] <- "Total"

tmode1_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==1 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2])
tmode2_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==2 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2])
tmode3_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP==3 & tours$IS_SUBTOUR == 0 & tours$AUTOSUFF==2])
tmode4_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=4 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==2])
tmode5_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0 & tours$AUTOSUFF==2])
tmode6_as2 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=4 & jtours$JOINT_PURP<=6 & jtours$AUTOSUFF==2])
tmode7_as2 <- wtd.hist(jtours$TOURMODE[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9 & jtours$AUTOSUFF==2])
tmode8_as2 <- wtd.hist(tours$TOURMODE[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = tours$finalweight[!is.na(tours$TOURMODE) & tours$IS_SUBTOUR==1 & tours$AUTOSUFF==2])

tmodeAS2Profile <- data.frame(tmode1_as2$counts, tmode2_as2$counts, tmode3_as2$counts, tmode4_as2$counts,
                              tmode5_as2$counts, tmode6_as2$counts, tmode7_as2$counts, tmode8_as2$counts)
colnames(tmodeAS2Profile) <- c("work", "univ", "sch", "imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(tmodeAS2Profile, "tmodeAS2Profile_CHTS.csv")

# Prepeare data for visualizer
tmodeAS2Profile_vis <- tmodeAS2Profile[1:9,]
tmodeAS2Profile_vis$id <- row.names(tmodeAS2Profile_vis)
tmodeAS2Profile_vis <- melt(tmodeAS2Profile_vis, id = c("id"))
colnames(tmodeAS2Profile_vis) <- c("id", "purpose", "freq_as2")

tmodeAS2Profile_vis <- xtabs(freq_as2~id+purpose, tmodeAS2Profile_vis)
tmodeAS2Profile_vis[is.na(tmodeAS2Profile_vis)] <- 0
tmodeAS2Profile_vis <- addmargins(as.table(tmodeAS2Profile_vis))
tmodeAS2Profile_vis <- as.data.frame.matrix(tmodeAS2Profile_vis)

tmodeAS2Profile_vis$id <- row.names(tmodeAS2Profile_vis)
tmodeAS2Profile_vis <- melt(tmodeAS2Profile_vis, id = c("id"))
colnames(tmodeAS2Profile_vis) <- c("id", "purpose", "freq_as2")
tmodeAS2Profile_vis$id <- as.character(tmodeAS2Profile_vis$id)
tmodeAS2Profile_vis$purpose <- as.character(tmodeAS2Profile_vis$purpose)
tmodeAS2Profile_vis <- tmodeAS2Profile_vis[tmodeAS2Profile_vis$id!="Sum",]
tmodeAS2Profile_vis$purpose[tmodeAS2Profile_vis$purpose=="Sum"] <- "Total"


# Combine three AS groups
tmodeProfile_vis <- data.frame(tmodeAS0Profile_vis, tmodeAS1Profile_vis$freq_as1, tmodeAS2Profile_vis$freq_as2)
colnames(tmodeProfile_vis) <- c("id", "purpose", "freq_as0", "freq_as1", "freq_as2")
tmodeProfile_vis$freq_all <- tmodeProfile_vis$freq_as0 + tmodeProfile_vis$freq_as1 + tmodeProfile_vis$freq_as2
write.csv(tmodeProfile_vis, "tmodeProfile_vis_CHTS.csv", row.names = F)

# Non-mandatory tour distance profile
tourdist4 <- wtd.hist(tours$SKIMDIST[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
tourdisti56 <- wtd.hist(tours$SKIMDIST[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0])
tourdisti789 <- wtd.hist(tours$SKIMDIST[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0])
tourdistj56 <- wtd.hist(jtours$SKIMDIST[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
tourdistj789 <- wtd.hist(jtours$SKIMDIST[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
tourdist10 <- wtd.hist(tours$SKIMDIST[tours$IS_SUBTOUR == 1], breaks = c(seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

tourDistProfile <- data.frame(tourdist4$counts, tourdisti56$counts, tourdisti789$counts, tourdistj56$counts, tourdistj789$counts, tourdist10$counts)
colnames(tourDistProfile) <- c("esco", "imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(tourDistProfile, "nonMandTourDistProfile.csv")

#prepare input for visualizer
tourDistProfile_vis <- tourDistProfile
tourDistProfile_vis$id <- row.names(tourDistProfile_vis)
tourDistProfile_vis <- melt(tourDistProfile_vis, id = c("id"))
colnames(tourDistProfile_vis) <- c("id", "purpose", "freq")

tourDistProfile_vis <- xtabs(freq~id+purpose, tourDistProfile_vis)
tourDistProfile_vis <- addmargins(as.table(tourDistProfile_vis))
tourDistProfile_vis <- as.data.frame.matrix(tourDistProfile_vis)
tourDistProfile_vis$id <- row.names(tourDistProfile_vis)
tourDistProfile_vis <- melt(tourDistProfile_vis, id = c("id"))
colnames(tourDistProfile_vis) <- c("distbin", "PURPOSE", "freq")
tourDistProfile_vis$PURPOSE <- as.character(tourDistProfile_vis$PURPOSE)
tourDistProfile_vis$distbin <- as.character(tourDistProfile_vis$distbin)
tourDistProfile_vis <- tourDistProfile_vis[tourDistProfile_vis$distbin!="Sum",]
tourDistProfile_vis$PURPOSE[tourDistProfile_vis$PURPOSE=="Sum"] <- "Total"
tourDistProfile_vis$distbin <- as.numeric(tourDistProfile_vis$distbin)

write.csv(tourDistProfile_vis, "tourDistProfile_vis.csv", row.names = F)

cat("\n Average Tour Distance [esco]: ", weighted.mean(tours$SKIMDIST[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], na.rm = TRUE))
cat("\n Average Tour Distance [imain]: ", weighted.mean(tours$SKIMDIST[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], na.rm = TRUE))
cat("\n Average Tour Distance [idisc]: ", weighted.mean(tours$SKIMDIST[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], na.rm = TRUE))
cat("\n Average Tour Distance [jmain]: ", weighted.mean(jtours$SKIMDIST[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], na.rm = TRUE))
cat("\n Average Tour Distance [jdisc]: ", weighted.mean(jtours$SKIMDIST[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], na.rm = TRUE))
cat("\n Average Tour Distance [atwork]: ", weighted.mean(tours$SKIMDIST[tours$IS_SUBTOUR == 1], tours$finalweight[tours$IS_SUBTOUR == 1], na.rm = TRUE))

## Output average trips lengths for visualizer

avgTripLengths <- c(weighted.mean(tours$SKIMDIST[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], na.rm = TRUE),
                    weighted.mean(tours$SKIMDIST[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], na.rm = TRUE),
                    weighted.mean(tours$SKIMDIST[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$IS_SUBTOUR == 0 & tours$FULLY_JOINT==0], na.rm = TRUE),
                    weighted.mean(jtours$SKIMDIST[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], na.rm = TRUE),
                    weighted.mean(jtours$SKIMDIST[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], na.rm = TRUE),
                    weighted.mean(tours$SKIMDIST[tours$IS_SUBTOUR == 1], tours$finalweight[tours$IS_SUBTOUR == 1], na.rm = TRUE))


nmSkimDist <- c(tours$SKIMDIST[tours$TOURPURP %in% c(4) & tours$IS_SUBTOUR == 0],
                tours$SKIMDIST[tours$TOURPURP %in% c(5,6,7,8,9) & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0],
                tours$SKIMDIST[tours$IS_SUBTOUR==1],
                jtours$SKIMDIST[jtours$JOINT_PURP %in% c(5,6,7,8,9)])
nmWeights  <- c(tours$finalweight[tours$TOURPURP %in% c(4) & tours$IS_SUBTOUR == 0],
                tours$finalweight[tours$TOURPURP %in% c(5,6,7,8,9) & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0],
                tours$finalweight[tours$IS_SUBTOUR==1],
                jtours$finalweight[jtours$JOINT_PURP %in% c(5,6,7,8,9)])

totAvgNonMand <- weighted.mean(nmSkimDist, nmWeights, na.rm = TRUE)

avgTripLengths <- c(avgTripLengths, totAvgNonMand)

nonMandTourPurpose <- c("esco", "imain", "idisc", "jmain", "jdisc", "atwork", "Total")

nonMandTripLengths <- data.frame(purpose = nonMandTourPurpose, avgTripLength = avgTripLengths)

write.csv(nonMandTripLengths, "nonMandTripLengths.csv", row.names = F)



# STop Frequency
#Outbound
stopfreq1 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(tours$OUTBOUND_STOPS[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jtours$OUTBOUND_STOPS[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
stopfreqj789 <- wtd.hist(jtours$OUTBOUND_STOPS[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
stopfreq10 <- wtd.hist(tours$OUTBOUND_STOPS[tours$IS_SUBTOUR == 1], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopFreqOutProfile.csv")

# prepare stop frequency input for visualizer
stopFreqout_vis <- stopFreq
stopFreqout_vis$id <- row.names(stopFreqout_vis)
stopFreqout_vis <- melt(stopFreqout_vis, id = c("id"))
colnames(stopFreqout_vis) <- c("id", "purpose", "freq")

stopFreqout_vis <- xtabs(freq~purpose+id, stopFreqout_vis)
stopFreqout_vis <- addmargins(as.table(stopFreqout_vis))
stopFreqout_vis <- as.data.frame.matrix(stopFreqout_vis)
stopFreqout_vis$id <- row.names(stopFreqout_vis)
stopFreqout_vis <- melt(stopFreqout_vis, id = c("id"))
colnames(stopFreqout_vis) <- c("purpose", "nstops", "freq")
stopFreqout_vis$purpose <- as.character(stopFreqout_vis$purpose)
stopFreqout_vis$nstops <- as.character(stopFreqout_vis$nstops)
stopFreqout_vis <- stopFreqout_vis[stopFreqout_vis$nstops!="Sum",]
stopFreqout_vis$purpose[stopFreqout_vis$purpose=="Sum"] <- "Total"


#Inbound
stopfreq1 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(tours$INBOUND_STOPS[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jtours$INBOUND_STOPS[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
stopfreqj789 <- wtd.hist(jtours$INBOUND_STOPS[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
stopfreq10 <- wtd.hist(tours$INBOUND_STOPS[tours$IS_SUBTOUR == 1], breaks = c(seq(0,3, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopFreqInbProfile.csv")

# prepare stop frequency input for visualizer
stopFreqinb_vis <- stopFreq
stopFreqinb_vis$id <- row.names(stopFreqinb_vis)
stopFreqinb_vis <- melt(stopFreqinb_vis, id = c("id"))
colnames(stopFreqinb_vis) <- c("id", "purpose", "freq")

stopFreqinb_vis <- xtabs(freq~purpose+id, stopFreqinb_vis)
stopFreqinb_vis <- addmargins(as.table(stopFreqinb_vis))
stopFreqinb_vis <- as.data.frame.matrix(stopFreqinb_vis)
stopFreqinb_vis$id <- row.names(stopFreqinb_vis)
stopFreqinb_vis <- melt(stopFreqinb_vis, id = c("id"))
colnames(stopFreqinb_vis) <- c("purpose", "nstops", "freq")
stopFreqinb_vis$purpose <- as.character(stopFreqinb_vis$purpose)
stopFreqinb_vis$nstops <- as.character(stopFreqinb_vis$nstops)
stopFreqinb_vis <- stopFreqinb_vis[stopFreqinb_vis$nstops!="Sum",]
stopFreqinb_vis$purpose[stopFreqinb_vis$purpose=="Sum"] <- "Total"


stopfreqDir_vis <- data.frame(stopFreqout_vis, stopFreqinb_vis$freq)
colnames(stopfreqDir_vis) <- c("purpose", "nstops", "freq_out", "freq_inb")
write.csv(stopfreqDir_vis, "stopfreqDir_vis.csv", row.names = F)


#Total

# computing adjusted total stops by capping outbound and inbound stops at 3
# to be consistent with model
tours$TOTAL_STOPS_ABM <- ifelse(tours$OUTBOUND_STOPS>=3, 3, tours$OUTBOUND_STOPS) + ifelse(tours$INBOUND_STOPS>=3, 3, tours$INBOUND_STOPS)
jtours$TOTAL_STOPS_ABM <- ifelse(jtours$OUTBOUND_STOPS>=3, 3, jtours$OUTBOUND_STOPS) + ifelse(jtours$INBOUND_STOPS>=3, 3, jtours$INBOUND_STOPS)

stopfreq1 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==1 & tours$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==2 & tours$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==3 & tours$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP==4 & tours$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=5 & tours$TOURPURP<=6 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$TOURPURP>=7 & tours$TOURPURP<=9 & tours$FULLY_JOINT==0 & tours$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jtours$TOTAL_STOPS_ABM[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=5 & jtours$JOINT_PURP<=6])
stopfreqj789 <- wtd.hist(jtours$TOTAL_STOPS_ABM[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = jtours$finalweight[jtours$JOINT_PURP>=7 & jtours$JOINT_PURP<=9])
stopfreq10 <- wtd.hist(tours$TOTAL_STOPS_ABM[tours$IS_SUBTOUR == 1], breaks = c(seq(0,6, by=1), 9999), freq = NULL, right=FALSE, weight = tours$finalweight[tours$IS_SUBTOUR == 1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopFreqTotProfile.csv")

# prepare stop frequency input for visualizer
stopFreq_vis <- stopFreq
stopFreq_vis$id <- row.names(stopFreq_vis)
stopFreq_vis <- melt(stopFreq_vis, id = c("id"))
colnames(stopFreq_vis) <- c("id", "purpose", "freq")

stopFreq_vis <- xtabs(freq~purpose+id, stopFreq_vis)
stopFreq_vis <- addmargins(as.table(stopFreq_vis))
stopFreq_vis <- as.data.frame.matrix(stopFreq_vis)
stopFreq_vis$id <- row.names(stopFreq_vis)
stopFreq_vis <- melt(stopFreq_vis, id = c("id"))
colnames(stopFreq_vis) <- c("purpose", "nstops", "freq")
stopFreq_vis$purpose <- as.character(stopFreq_vis$purpose)
stopFreq_vis$nstops <- as.character(stopFreq_vis$nstops)
stopFreq_vis <- stopFreq_vis[stopFreq_vis$nstops!="Sum",]
stopFreq_vis$purpose[stopFreq_vis$purpose=="Sum"] <- "Total"

write.csv(stopFreq_vis, "stopfreq_total_vis.csv", row.names = F)

#Stop purpose X TourPurpose
stopfreq1 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(stops$DEST_PURP[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jstops$DEST_PURP[jstops$TOURPURP>=5 & jstops$TOURPURP<=6], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=5 & jstops$TOURPURP<=6])
stopfreqj789 <- wtd.hist(jstops$DEST_PURP[jstops$TOURPURP>=7 & jstops$TOURPURP<=9], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=7 & jstops$TOURPURP<=9])
stopfreq10 <- wtd.hist(stops$DEST_PURP[stops$SUBTOUR==1], breaks = c(seq(1,10, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$SUBTOUR==1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopPurposeByTourPurpose.csv")

# prepare stop frequency input for visualizer
stopFreq_vis <- stopFreq
stopFreq_vis$id <- row.names(stopFreq_vis)
stopFreq_vis <- melt(stopFreq_vis, id = c("id"))
colnames(stopFreq_vis) <- c("stop_purp", "purpose", "freq")

stopFreq_vis <- xtabs(freq~purpose+stop_purp, stopFreq_vis)
stopFreq_vis <- addmargins(as.table(stopFreq_vis))
stopFreq_vis <- as.data.frame.matrix(stopFreq_vis)
stopFreq_vis$purpose <- row.names(stopFreq_vis)
stopFreq_vis <- melt(stopFreq_vis, id = c("purpose"))
colnames(stopFreq_vis) <- c("purpose", "stop_purp", "freq")
stopFreq_vis$purpose <- as.character(stopFreq_vis$purpose)
stopFreq_vis$stop_purp <- as.character(stopFreq_vis$stop_purp)
stopFreq_vis <- stopFreq_vis[stopFreq_vis$stop_purp!="Sum",]
stopFreq_vis$purpose[stopFreq_vis$purpose=="Sum"] <- "Total"

write.csv(stopFreq_vis, "stoppurpose_tourpurpose_vis.csv", row.names = F)

#Out of direction - Stop Location
stopfreq1 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(stops$out_dir_dist[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jstops$out_dir_dist[jstops$TOURPURP>=5 & jstops$TOURPURP<=6], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=5 & jstops$TOURPURP<=6])
stopfreqj789 <- wtd.hist(jstops$out_dir_dist[jstops$TOURPURP>=7 & jstops$TOURPURP<=9], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=7 & jstops$TOURPURP<=9])
stopfreq10 <- wtd.hist(stops$out_dir_dist[stops$SUBTOUR==1], breaks = c(-9999,seq(0,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$SUBTOUR==1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopOutOfDirectionDC.csv")

# prepare stop location input for visualizer
stopDC_vis <- stopFreq
stopDC_vis$id <- row.names(stopDC_vis)
stopDC_vis <- melt(stopDC_vis, id = c("id"))
colnames(stopDC_vis) <- c("id", "purpose", "freq")

stopDC_vis <- xtabs(freq~id+purpose, stopDC_vis)
stopDC_vis <- addmargins(as.table(stopDC_vis))
stopDC_vis <- as.data.frame.matrix(stopDC_vis)
stopDC_vis$id <- row.names(stopDC_vis)
stopDC_vis <- melt(stopDC_vis, id = c("id"))
colnames(stopDC_vis) <- c("distbin", "PURPOSE", "freq")
stopDC_vis$PURPOSE <- as.character(stopDC_vis$PURPOSE)
stopDC_vis$distbin <- as.character(stopDC_vis$distbin)
stopDC_vis <- stopDC_vis[stopDC_vis$distbin!="Sum",]
stopDC_vis$PURPOSE[stopDC_vis$PURPOSE=="Sum"] <- "Total"
stopDC_vis$distbin <- as.numeric(stopDC_vis$distbin)

write.csv(stopDC_vis, "stopDC_vis.csv", row.names = F)

# compute average out of dir distance for visualizer
avgDistances <- c(weighted.mean(stops$out_dir_dist[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], weight = stops$finalweight[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], na.rm = TRUE),
                  weighted.mean(jstops$out_dir_dist[jstops$TOURPURP>=5 & jstops$TOURPURP<=6], weight = jstops$finalweight[jstops$TOURPURP>=5 & jstops$TOURPURP<=6], na.rm = TRUE),
                  weighted.mean(jstops$out_dir_dist[jstops$TOURPURP>=7 & jstops$TOURPURP<=9], weight = jstops$finalweight[jstops$TOURPURP>=7 & jstops$TOURPURP<=9], na.rm = TRUE),
                  weighted.mean(stops$out_dir_dist[stops$SUBTOUR==1], weight = stops$finalweight[stops$SUBTOUR==1], na.rm = TRUE))

purp <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork", "total")

###
stopsDist <- c(stops$out_dir_dist[stops$TOURPURP %in% c(4) & stops$IS_SUBTOUR==0], 
               stops$out_dir_dist[stops$TOURPURP %in% c(5,6,7,8,9) & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR==0], 
                stops$out_dir_dist[stops$IS_SUBTOUR==1],
                jstops$out_dir_dist[jstops$JOINT_PURP %in% c(5,6,7,8,9)])
stopsWeights  <- c(stops$finalweight[stops$TOURPURP %in% c(4) & stops$IS_SUBTOUR==0], 
                   stops$finalweight[stops$TOURPURP %in% c(5,6,7,8,9) & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR==0], 
                stops$finalweight[stops$IS_SUBTOUR==1],
                jstops$finalweight[jstops$JOINT_PURP %in% c(5,6,7,8,9)])

totAvgStopDist <- weighted.mean(stopsDist, stopsWeights, na.rm = TRUE)

avgDistances <- c(avgDistances, totAvgStopDist)

###

avgStopOutofDirectionDist <- data.frame(purpose = purp, avgDist = avgDistances)

write.csv(avgStopOutofDirectionDist, "avgStopOutofDirectionDist_vis.csv", row.names = F)


#Stop Departure Time
stopfreq1 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==1 & stops$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==2 & stops$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==3 & stops$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP==4 & stops$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=5 & stops$TOURPURP<=6 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(stops$DEST_DEP_BIN[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$TOURPURP>=7 & stops$TOURPURP<=9 & stops$FULLY_JOINT==0 & stops$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jstops$DEST_DEP_BIN[jstops$TOURPURP>=5 & jstops$TOURPURP<=6], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=5 & jstops$TOURPURP<=6])
stopfreqj789 <- wtd.hist(jstops$DEST_DEP_BIN[jstops$TOURPURP>=7 & jstops$TOURPURP<=9], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = jstops$finalweight[jstops$TOURPURP>=7 & jstops$TOURPURP<=9])
stopfreq10 <- wtd.hist(stops$DEST_DEP_BIN[stops$SUBTOUR==1], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = stops$finalweight[stops$SUBTOUR==1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "stopDeparture.csv")

# prepare stop departure input for visualizer
stopDep_vis <- stopFreq
stopDep_vis$id <- row.names(stopDep_vis)
stopDep_vis <- melt(stopDep_vis, id = c("id"))
colnames(stopDep_vis) <- c("id", "purpose", "freq_stop")

stopDep_vis$purpose <- as.character(stopDep_vis$purpose)
stopDep_vis <- xtabs(freq_stop~id+purpose, stopDep_vis)
stopDep_vis <- addmargins(as.table(stopDep_vis))
stopDep_vis <- as.data.frame.matrix(stopDep_vis)
stopDep_vis$id <- row.names(stopDep_vis)
stopDep_vis <- melt(stopDep_vis, id = c("id"))
colnames(stopDep_vis) <- c("timebin", "PURPOSE", "freq")
stopDep_vis$PURPOSE <- as.character(stopDep_vis$PURPOSE)
stopDep_vis$timebin <- as.character(stopDep_vis$timebin)
stopDep_vis <- stopDep_vis[stopDep_vis$timebin!="Sum",]
stopDep_vis$PURPOSE[stopDep_vis$PURPOSE=="Sum"] <- "Total"
stopDep_vis$timebin <- as.numeric(stopDep_vis$timebin)

#Trip Departure Time
stopfreq1 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP==1 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP==1 & trips$IS_SUBTOUR == 0])
stopfreq2 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP==2 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP==2 & trips$IS_SUBTOUR == 0])
stopfreq3 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP==3 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP==3 & trips$IS_SUBTOUR == 0])
stopfreq4 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP==4 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP==4 & trips$IS_SUBTOUR == 0])
stopfreqi56 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP>=5 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP>=5 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$IS_SUBTOUR == 0])
stopfreqi789 <- wtd.hist(trips$ORIG_DEP_BIN[trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$IS_SUBTOUR == 0], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$IS_SUBTOUR == 0])
stopfreqj56 <- wtd.hist(jtrips$ORIG_DEP_BIN[jtrips$TOURPURP>=5 & jtrips$TOURPURP<=6], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = jtrips$finalweight[jtrips$TOURPURP>=5 & jtrips$TOURPURP<=6])
stopfreqj789 <- wtd.hist(jtrips$ORIG_DEP_BIN[jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = jtrips$finalweight[jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9])
stopfreq10 <- wtd.hist(trips$ORIG_DEP_BIN[trips$SUBTOUR==1], breaks = c(seq(1,40, by=1), 9999), freq = NULL, right=FALSE, weight = trips$finalweight[trips$SUBTOUR==1])

stopFreq <- data.frame(stopfreq1$counts, stopfreq2$counts, stopfreq3$counts, stopfreq4$counts, stopfreqi56$counts
                       , stopfreqi789$counts, stopfreqj56$counts, stopfreqj789$counts, stopfreq10$counts)
colnames(stopFreq) <- c("work", "univ", "sch", "esco","imain", "idisc", "jmain", "jdisc", "atwork")
write.csv(stopFreq, "tripDeparture.csv")

# prepare stop departure input for visualizer
tripDep_vis <- stopFreq
tripDep_vis$id <- row.names(tripDep_vis)
tripDep_vis <- melt(tripDep_vis, id = c("id"))
colnames(tripDep_vis) <- c("id", "purpose", "freq_trip")

tripDep_vis$purpose <- as.character(tripDep_vis$purpose)
tripDep_vis <- xtabs(freq_trip~id+purpose, tripDep_vis)
tripDep_vis <- addmargins(as.table(tripDep_vis))
tripDep_vis <- as.data.frame.matrix(tripDep_vis)
tripDep_vis$id <- row.names(tripDep_vis)
tripDep_vis <- melt(tripDep_vis, id = c("id"))
colnames(tripDep_vis) <- c("timebin", "PURPOSE", "freq")
tripDep_vis$PURPOSE <- as.character(tripDep_vis$PURPOSE)
tripDep_vis$timebin <- as.character(tripDep_vis$timebin)
tripDep_vis <- tripDep_vis[tripDep_vis$timebin!="Sum",]
tripDep_vis$PURPOSE[tripDep_vis$PURPOSE=="Sum"] <- "Total"
tripDep_vis$timebin <- as.numeric(tripDep_vis$timebin)

stopTripDep_vis <- data.frame(stopDep_vis, tripDep_vis$freq)
colnames(stopTripDep_vis) <- c("timebin", "purpose", "freq_stop", "freq_trip")
write.csv(stopTripDep_vis, "stopTripDep_vis.csv", row.names = F)

#Trip Mode Summary
#Work
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0 & trips$TOURPURP==1 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==1 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_Work_CHTS.csv")

# Prepeare data for visualizer
tripModeProfile1_vis <- tripModeProfile[1:9,]
tripModeProfile1_vis$id <- row.names(tripModeProfile1_vis)
tripModeProfile1_vis <- melt(tripModeProfile1_vis, id = c("id"))
colnames(tripModeProfile1_vis) <- c("id", "purpose", "freq1")

tripModeProfile1_vis <- xtabs(freq1~id+purpose, tripModeProfile1_vis)
tripModeProfile1_vis[is.na(tripModeProfile1_vis)] <- 0
tripModeProfile1_vis <- addmargins(as.table(tripModeProfile1_vis))
tripModeProfile1_vis <- as.data.frame.matrix(tripModeProfile1_vis)

tripModeProfile1_vis$id <- row.names(tripModeProfile1_vis)
tripModeProfile1_vis <- melt(tripModeProfile1_vis, id = c("id"))
colnames(tripModeProfile1_vis) <- c("id", "purpose", "freq1")
tripModeProfile1_vis$id <- as.character(tripModeProfile1_vis$id)
tripModeProfile1_vis$purpose <- as.character(tripModeProfile1_vis$purpose)
tripModeProfile1_vis <- tripModeProfile1_vis[tripModeProfile1_vis$id!="Sum",]
tripModeProfile1_vis$purpose[tripModeProfile1_vis$purpose=="Sum"] <- "Total"

#Univ                                                         
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==2 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_Univ_CHTS.csv")

tripModeProfile2_vis <- tripModeProfile[1:9,]
tripModeProfile2_vis$id <- row.names(tripModeProfile2_vis)
tripModeProfile2_vis <- melt(tripModeProfile2_vis, id = c("id"))
colnames(tripModeProfile2_vis) <- c("id", "purpose", "freq2")

tripModeProfile2_vis <- xtabs(freq2~id+purpose, tripModeProfile2_vis)
tripModeProfile2_vis[is.na(tripModeProfile2_vis)] <- 0
tripModeProfile2_vis <- addmargins(as.table(tripModeProfile2_vis))
tripModeProfile2_vis <- as.data.frame.matrix(tripModeProfile2_vis)

tripModeProfile2_vis$id <- row.names(tripModeProfile2_vis)
tripModeProfile2_vis <- melt(tripModeProfile2_vis, id = c("id"))
colnames(tripModeProfile2_vis) <- c("id", "purpose", "freq2")
tripModeProfile2_vis$id <- as.character(tripModeProfile2_vis$id)
tripModeProfile2_vis$purpose <- as.character(tripModeProfile2_vis$purpose)
tripModeProfile2_vis <- tripModeProfile2_vis[tripModeProfile2_vis$id!="Sum",]
tripModeProfile2_vis$purpose[tripModeProfile2_vis$purpose=="Sum"] <- "Total"

#School                                                       
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP==3 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_Schl_CHTS.csv")

tripModeProfile3_vis <- tripModeProfile[1:9,]
tripModeProfile3_vis$id <- row.names(tripModeProfile3_vis)
tripModeProfile3_vis <- melt(tripModeProfile3_vis, id = c("id"))
colnames(tripModeProfile3_vis) <- c("id", "purpose", "freq3")

tripModeProfile3_vis <- xtabs(freq3~id+purpose, tripModeProfile3_vis)
tripModeProfile3_vis[is.na(tripModeProfile3_vis)] <- 0
tripModeProfile3_vis <- addmargins(as.table(tripModeProfile3_vis))
tripModeProfile3_vis <- as.data.frame.matrix(tripModeProfile3_vis)

tripModeProfile3_vis$id <- row.names(tripModeProfile3_vis)
tripModeProfile3_vis <- melt(tripModeProfile3_vis, id = c("id"))
colnames(tripModeProfile3_vis) <- c("id", "purpose", "freq3")
tripModeProfile3_vis$id <- as.character(tripModeProfile3_vis$id)
tripModeProfile3_vis$purpose <- as.character(tripModeProfile3_vis$purpose)
tripModeProfile3_vis <- tripModeProfile3_vis[tripModeProfile3_vis$id!="Sum",]
tripModeProfile3_vis$purpose[tripModeProfile3_vis$purpose=="Sum"] <- "Total"

#iMain                                                        
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=4 & trips$TOURPURP<=6 & trips$FULLY_JOINT==0 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_iMain_CHTS.csv")

tripModeProfile4_vis <- tripModeProfile[1:9,]
tripModeProfile4_vis$id <- row.names(tripModeProfile4_vis)
tripModeProfile4_vis <- melt(tripModeProfile4_vis, id = c("id"))
colnames(tripModeProfile4_vis) <- c("id", "purpose", "freq4")

tripModeProfile4_vis <- xtabs(freq4~id+purpose, tripModeProfile4_vis)
tripModeProfile4_vis[is.na(tripModeProfile4_vis)] <- 0
tripModeProfile4_vis <- addmargins(as.table(tripModeProfile4_vis))
tripModeProfile4_vis <- as.data.frame.matrix(tripModeProfile4_vis)

tripModeProfile4_vis$id <- row.names(tripModeProfile4_vis)
tripModeProfile4_vis <- melt(tripModeProfile4_vis, id = c("id"))
colnames(tripModeProfile4_vis) <- c("id", "purpose", "freq4")
tripModeProfile4_vis$id <- as.character(tripModeProfile4_vis$id)
tripModeProfile4_vis$purpose <- as.character(tripModeProfile4_vis$purpose)
tripModeProfile4_vis <- tripModeProfile4_vis[tripModeProfile4_vis$id!="Sum",]
tripModeProfile4_vis$purpose[tripModeProfile4_vis$purpose=="Sum"] <- "Total"

#iDisc                                                        
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==1 & trips$IS_SUBTOUR==0])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==2 & trips$IS_SUBTOUR==0])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==3 & trips$IS_SUBTOUR==0])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==4 & trips$IS_SUBTOUR==0])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==5 & trips$IS_SUBTOUR==0])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==6 & trips$IS_SUBTOUR==0])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==7 & trips$IS_SUBTOUR==0])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==8 & trips$IS_SUBTOUR==0])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURPURP>=7 & trips$TOURPURP<=9 & trips$FULLY_JOINT==0 & trips$TOURMODE==9 & trips$IS_SUBTOUR==0])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_iDisc_CHTS.csv")

tripModeProfile5_vis <- tripModeProfile[1:9,]
tripModeProfile5_vis$id <- row.names(tripModeProfile5_vis)
tripModeProfile5_vis <- melt(tripModeProfile5_vis, id = c("id"))
colnames(tripModeProfile5_vis) <- c("id", "purpose", "freq5")

tripModeProfile5_vis <- xtabs(freq5~id+purpose, tripModeProfile5_vis)
tripModeProfile5_vis[is.na(tripModeProfile5_vis)] <- 0
tripModeProfile5_vis <- addmargins(as.table(tripModeProfile5_vis))
tripModeProfile5_vis <- as.data.frame.matrix(tripModeProfile5_vis)

tripModeProfile5_vis$id <- row.names(tripModeProfile5_vis)
tripModeProfile5_vis <- melt(tripModeProfile5_vis, id = c("id"))
colnames(tripModeProfile5_vis) <- c("id", "purpose", "freq5")
tripModeProfile5_vis$id <- as.character(tripModeProfile5_vis$id)
tripModeProfile5_vis$purpose <- as.character(tripModeProfile5_vis$purpose)
tripModeProfile5_vis <- tripModeProfile5_vis[tripModeProfile5_vis$id!="Sum",]
tripModeProfile5_vis$purpose[tripModeProfile5_vis$purpose=="Sum"] <- "Total"

#jMain                                                        
tripmode1 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==1])
tripmode2 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==2])
tripmode3 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==3], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==3])
tripmode4 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==4], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==4])
tripmode5 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==5], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==5])
tripmode6 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==6], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==6])
tripmode7 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==7], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==7])
tripmode8 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==8], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==8])
tripmode9 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==9], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=4 & jtrips$TOURPURP<=6 & jtrips$TOURMODE==9])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_jMain_CHTS.csv")

tripModeProfile6_vis <- tripModeProfile[1:9,]
tripModeProfile6_vis$id <- row.names(tripModeProfile6_vis)
tripModeProfile6_vis <- melt(tripModeProfile6_vis, id = c("id"))
colnames(tripModeProfile6_vis) <- c("id", "purpose", "freq6")

tripModeProfile6_vis <- xtabs(freq6~id+purpose, tripModeProfile6_vis)
tripModeProfile6_vis[is.na(tripModeProfile6_vis)] <- 0
tripModeProfile6_vis <- addmargins(as.table(tripModeProfile6_vis))
tripModeProfile6_vis <- as.data.frame.matrix(tripModeProfile6_vis)

tripModeProfile6_vis$id <- row.names(tripModeProfile6_vis)
tripModeProfile6_vis <- melt(tripModeProfile6_vis, id = c("id"))
colnames(tripModeProfile6_vis) <- c("id", "purpose", "freq6")
tripModeProfile6_vis$id <- as.character(tripModeProfile6_vis$id)
tripModeProfile6_vis$purpose <- as.character(tripModeProfile6_vis$purpose)
tripModeProfile6_vis <- tripModeProfile6_vis[tripModeProfile6_vis$id!="Sum",]
tripModeProfile6_vis$purpose[tripModeProfile6_vis$purpose=="Sum"] <- "Total"

#jDisc                                                        
tripmode1 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==1])
tripmode2 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==2])
tripmode3 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==3], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==3])
tripmode4 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==4], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==4])
tripmode5 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==5], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==5])
tripmode6 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==6], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==6])
tripmode7 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==7], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==7])
tripmode8 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==8], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==8])
tripmode9 <- wtd.hist(jtrips$TRIPMODE[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==9], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = jtrips$finalweight[!is.na(jtrips$TRIPMODE) & jtrips$TRIPMODE>0  & jtrips$TOURPURP>=7 & jtrips$TOURPURP<=9 & jtrips$TOURMODE==9])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_jDisc_CHTS.csv")

tripModeProfile7_vis <- tripModeProfile[1:9,]
tripModeProfile7_vis$id <- row.names(tripModeProfile7_vis)
tripModeProfile7_vis <- melt(tripModeProfile7_vis, id = c("id"))
colnames(tripModeProfile7_vis) <- c("id", "purpose", "freq7")

tripModeProfile7_vis <- xtabs(freq7~id+purpose, tripModeProfile7_vis)
tripModeProfile7_vis[is.na(tripModeProfile7_vis)] <- 0
tripModeProfile7_vis <- addmargins(as.table(tripModeProfile7_vis))
tripModeProfile7_vis <- as.data.frame.matrix(tripModeProfile7_vis)

tripModeProfile7_vis$id <- row.names(tripModeProfile7_vis)
tripModeProfile7_vis <- melt(tripModeProfile7_vis, id = c("id"))
colnames(tripModeProfile7_vis) <- c("id", "purpose", "freq7")
tripModeProfile7_vis$id <- as.character(tripModeProfile7_vis$id)
tripModeProfile7_vis$purpose <- as.character(tripModeProfile7_vis$purpose)
tripModeProfile7_vis <- tripModeProfile7_vis[tripModeProfile7_vis$id!="Sum",]
tripModeProfile7_vis$purpose[tripModeProfile7_vis$purpose=="Sum"] <- "Total"

#At-work                                                       
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==1])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==2])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==3], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==3])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==4], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==4])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==5], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==5])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==6], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==6])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==7], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==7])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==8], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==8])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==9], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$SUBTOUR==1 & trips$TOURMODE==9])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_ATW_CHTS.csv")

tripModeProfile8_vis <- tripModeProfile[1:9,]
tripModeProfile8_vis$id <- row.names(tripModeProfile8_vis)
tripModeProfile8_vis <- melt(tripModeProfile8_vis, id = c("id"))
colnames(tripModeProfile8_vis) <- c("id", "purpose", "freq8")

tripModeProfile8_vis <- xtabs(freq8~id+purpose, tripModeProfile8_vis)
tripModeProfile8_vis[is.na(tripModeProfile8_vis)] <- 0
tripModeProfile8_vis <- addmargins(as.table(tripModeProfile8_vis))
tripModeProfile8_vis <- as.data.frame.matrix(tripModeProfile8_vis)

tripModeProfile8_vis$id <- row.names(tripModeProfile8_vis)
tripModeProfile8_vis <- melt(tripModeProfile8_vis, id = c("id"))
colnames(tripModeProfile8_vis) <- c("id", "purpose", "freq8")
tripModeProfile8_vis$id <- as.character(tripModeProfile8_vis$id)
tripModeProfile8_vis$purpose <- as.character(tripModeProfile8_vis$purpose)
tripModeProfile8_vis <- tripModeProfile8_vis[tripModeProfile8_vis$id!="Sum",]
tripModeProfile8_vis$purpose[tripModeProfile8_vis$purpose=="Sum"] <- "Total"

#Total                                                       
tripmode1 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==1], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==1])
tripmode2 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==2], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==2])
tripmode3 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==3], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==3])
tripmode4 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==4], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==4])
tripmode5 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==5], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==5])
tripmode6 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==6], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==6])
tripmode7 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==7], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==7])
tripmode8 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==8], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==8])
tripmode9 <- wtd.hist(trips$TRIPMODE[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==9], breaks = seq(1,12, by=1), freq = NULL, right=FALSE, weight = trips$finalweight[!is.na(trips$TRIPMODE) & trips$TRIPMODE>0  & trips$TOURMODE==9])

tripModeProfile <- data.frame(tripmode1$counts, tripmode2$counts, tripmode3$counts, tripmode4$counts,
                              tripmode5$counts, tripmode6$counts, tripmode7$counts, tripmode8$counts, tripmode9$counts)
colnames(tripModeProfile) <- c("tourmode1", "tourmode2", "tourmode3", "tourmode4", "tourmode5", "tourmode6", "tourmode7", "tourmode8", "tourmode9")
write.csv(tripModeProfile, "tripModeProfile_Total_CHTS.csv")

tripModeProfile9_vis <- tripModeProfile[1:9,]
tripModeProfile9_vis$id <- row.names(tripModeProfile9_vis)
tripModeProfile9_vis <- melt(tripModeProfile9_vis, id = c("id"))
colnames(tripModeProfile9_vis) <- c("id", "purpose", "freq9")

tripModeProfile9_vis <- xtabs(freq9~id+purpose, tripModeProfile9_vis)
tripModeProfile9_vis[is.na(tripModeProfile9_vis)] <- 0
tripModeProfile9_vis <- addmargins(as.table(tripModeProfile9_vis))
tripModeProfile9_vis <- as.data.frame.matrix(tripModeProfile9_vis)

tripModeProfile9_vis$id <- row.names(tripModeProfile9_vis)
tripModeProfile9_vis <- melt(tripModeProfile9_vis, id = c("id"))
colnames(tripModeProfile9_vis) <- c("id", "purpose", "freq9")
tripModeProfile9_vis$id <- as.character(tripModeProfile9_vis$id)
tripModeProfile9_vis$purpose <- as.character(tripModeProfile9_vis$purpose)
tripModeProfile9_vis <- tripModeProfile9_vis[tripModeProfile9_vis$id!="Sum",]
tripModeProfile9_vis$purpose[tripModeProfile9_vis$purpose=="Sum"] <- "Total"


# combine all tripmode profile for visualizer
tripModeProfile_vis <- data.frame(tripModeProfile1_vis, tripModeProfile2_vis$freq2, tripModeProfile3_vis$freq3
                                  , tripModeProfile4_vis$freq4, tripModeProfile5_vis$freq5, tripModeProfile6_vis$freq6
                                  , tripModeProfile7_vis$freq7, tripModeProfile8_vis$freq8, tripModeProfile9_vis$freq9)
colnames(tripModeProfile_vis) <- c("tripmode", "tourmode", "work", "univ", "schl", "imain", "idisc", "jmain", "jdisc", "atwork", "total")

temp <- melt(tripModeProfile_vis, id = c("tripmode", "tourmode"))
#tripModeProfile_vis <- cast(temp, tripmode+variable~tourmode)
#write.csv(tripModeProfile_vis, "tripModeProfile_vis.csv", row.names = F)
temp$grp_var <- paste(temp$variable, temp$tourmode, sep = "")

# rename tour mode to standard names
temp$tourmode[temp$tourmode=="tourmode1"] <- 'Auto SOV'
temp$tourmode[temp$tourmode=="tourmode2"] <- 'Auto 2 Person'
temp$tourmode[temp$tourmode=="tourmode3"] <- 'Auto 3+ Person'
temp$tourmode[temp$tourmode=="tourmode4"] <- 'Walk'
temp$tourmode[temp$tourmode=="tourmode5"] <- 'Bike/Moped'
temp$tourmode[temp$tourmode=="tourmode6"] <- 'Walk-Transit'
temp$tourmode[temp$tourmode=="tourmode7"] <- 'PNR-Transit'
temp$tourmode[temp$tourmode=="tourmode8"] <- 'KNR-Transit'
temp$tourmode[temp$tourmode=="tourmode9"] <- 'School Bus'

colnames(temp) <- c("tripmode","tourmode","purpose","value","grp_var")

write.csv(temp, "tripModeProfile_vis_CHTS.csv", row.names = F)

# Total number of stops, trips & tours
cat("Total number of stops : ", sum(stops$finalweight[stops$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)]))
cat("Total number of trips : ", sum(trips$finalweight[trips$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)]))
cat("Total number of tours : ", sum(tours$finalweight[tours$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)]))

# output total numbers in a file
total_population <- sum(pertypeDistbn$freq)
total_households <- sum(hh$finalweight)
total_stops <- sum(stops$finalweight[stops$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)])
total_trips <- sum(trips$finalweight[trips$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)])
total_tours <- sum(tours$finalweight[tours$TOURPURP %in% c(1,2,3,4,5,6,7,8,9,10)])

trips$num_travel[trips$TRIPMODE==1] <- 1
trips$num_travel[trips$TRIPMODE==2] <- 2
trips$num_travel[trips$TRIPMODE==3] <- 3.5
trips$num_travel[is.na(trips$num_travel)] <- 0

total_vmt <- sum((trips$finalweight[trips$TRIPMODE>0 & trips$TRIPMODE<=3]*trips$od_dist[trips$TRIPMODE>0 & trips$TRIPMODE<=3])/trips$num_travel[trips$TRIPMODE>0 & trips$TRIPMODE<=3])


totals_var <- c("total_population", "total_households", "total_tours", "total_trips", "total_stops", "total_vmt")
totals_val <- c(total_population,total_households, total_tours, total_trips, total_stops, total_vmt)

totals_df <- data.frame(name = totals_var, value = totals_val)

write.csv(totals_df, "totals.csv", row.names = F)

# HH Size distribution
hhSizeDist <- count(hh[!is.na(hh$HHSIZE),], c("HHSIZE"), "finalweight")
write.csv(hhSizeDist, "hhSizeDist.csv", row.names = F)

# Active Persons by person type
actpertypeDistbn <- count(per[(!is.na(per$PERTYPE) & (per$DAP!="H")),], c("PERTYPE"), "finalweight")
write.csv(actpertypeDistbn, "activePertypeDistbn.csv", row.names = TRUE)

# Non-drive and drive tours to parking constraint zone
tours$access_mode[tours$TOURMODE==6] <- "walk"
tours$access_mode[tours$TOURMODE==7] <- "pnr"
tours$access_mode[tours$TOURMODE==8] <- "knr"
tours$dest_park <- mazData$parkConstraint[match(tours$dest_mgra, mazData$MAZ)]

work_Tours <- tours[tours$dest_park==1 & tours$TOURPURP==1,]
write.table("work_driveTours", "work_Tours.csv", sep = ",")
write.table(sum(work_Tours$finalweight[work_Tours$TOURMODE %in% c(1,2,3)]), "work_Tours.csv", sep = ",", row.names = F, append = T)
write.table("work_driveTours", "work_Tours.csv", sep = ",", row.names = F, append = T)
write.table(sum(work_Tours$finalweight[!work_Tours$TOURMODE %in% c(1,2,3)]), "work_Tours.csv", sep = ",", row.names = F, append = T)


### County-County trip flow by Tour Purpose and Trip Mode
trips_sample <- trips[,c("OCOUNTY", "DCOUNTY", "TRIPMODE", "TOURPURP", "SUBTOUR", "finalweight")]

# Recode tour purpose into unique market segmentations
# Work         - [No Subtours ], [All], [TOURPURP - (1,10)] 
# University   - [No Subtours ], [All], [TOURPURP - (2)   ] 
# School       - [No Subtours ], [All], [TOURPURP - (3)   ]  
# Escort       - [No Subtours ], [All], [TOURPURP - (4)   ]   
# Shop         - [No Subtours ], [All], [TOURPURP - (5)   ]   
# Maintenance  - [No Subtours ], [All], [TOURPURP - (6)   ]       
# Eating Out   - [No Subtours ], [All], [TOURPURP - (7)   ]
# Visiting     - [No Subtours ], [All], [TOURPURP - (8)   ]   
# Discretionary- [No Subtours ], [All], [TOURPURP - (9)   ]   
# Work-based   - [All Subtours], [All], [TOURPURP - (All) ]    

trips_sample$tour_purpose <- "Other"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(1,10)] <- "Work"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(2)]    <- "University"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(3)]    <- "School"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(4)]    <- "Escort"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(5)]    <- "Shop"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(6)]    <- "Maintenance"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(7)]    <- "Eating Out"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(8)]    <- "Visiting"
trips_sample$tour_purpose[trips_sample$SUBTOUR==0 & trips_sample$TOURPURP %in% c(9)]    <- "Discretionary"
trips_sample$tour_purpose[trips_sample$SUBTOUR==1]                                      <- "Work-based"

# delete other purpose and records with missing values
trips_sample <- trips_sample[trips_sample$tour_purpose != "Other",]
trips_sample <- trips_sample[trips_sample$OCOUNTY!="Missing" & trips_sample$DCOUNTY!="Missing",]
trips_sample <- trips_sample[trips_sample$TRIPMODE>0 & trips_sample$TRIPMODE<10,]

tripModeNames <- c('Auto SOV','Auto 2 Person','Auto 3+ Person','Walk','Bike/Moped','Walk-Transit','PNR-Transit','KNR-Transit','School Bus')
tripModeCodes <- c(1, 2, 3, 4, 5, 6, 7, 8, 9)
tripMode_df <- data.frame(tripModeCodes, tripModeNames)
trips_sample$trip_mode <- tripMode_df$tripModeNames[match(trips_sample$TRIPMODE, tripMode_df$tripModeCodes)]

trips_sample <- trips_sample[,c("OCOUNTY", "DCOUNTY", "trip_mode", "tour_purpose", "finalweight")]
trips_sample <- data.table(trips_sample)

trips_flow <- trips_sample[, .(count = sum(finalweight)), by = list(OCOUNTY, DCOUNTY, trip_mode, tour_purpose)]
trips_flow_total <- data.table(trips_flow[,c("OCOUNTY", "DCOUNTY", "trip_mode", "count")])
trips_flow_total <- trips_flow_total[, (tot = sum(count)), by = list(OCOUNTY, DCOUNTY, trip_mode)]
trips_flow_total$tour_purpose <- "Total"
names(trips_flow_total)[names(trips_flow_total) == "V1"] <- "count"
trips_flow <- rbind(trips_flow, trips_flow_total[,c("OCOUNTY", "DCOUNTY", "trip_mode", "tour_purpose", "count")])

trips_flow_total <- data.table(trips_flow[,c("OCOUNTY", "DCOUNTY", "tour_purpose", "count")])
trips_flow_total <- trips_flow_total[, (tot = sum(count)), by = list(OCOUNTY, DCOUNTY, tour_purpose)]
trips_flow_total$trip_mode <- "Total"
names(trips_flow_total)[names(trips_flow_total) == "V1"] <- "count"
trips_flow <- rbind(trips_flow, trips_flow_total[,c("OCOUNTY", "DCOUNTY", "trip_mode", "tour_purpose", "count")])


write.table(trips_flow, paste(WD,"trips_flow.csv", sep = "//"), sep = ",", row.names = F)


### County-County trip flow by Tour Purpose and Trip Mode (added by khademul)
sample_xwalk <- xwalk_SDist[,c("TAZ", "SDISTNAME")]
sample_xwalk <- unique(sample_xwalk[, 1:2])
sample_xwalk$ORIG_TAZ <- sample_xwalk$TAZ
sample_xwalk$DEST_TAZ <- sample_xwalk$TAZ
sample_xwalk$TAZ <- NULL
sample_xwalk_ORIG <- sample_xwalk[,c("ORIG_TAZ", "SDISTNAME")]
names(sample_xwalk_ORIG)[names(sample_xwalk_ORIG) == "SDISTNAME"] <- "OSDIST"
sample_xwalk_DEST <- sample_xwalk[,c("DEST_TAZ", "SDISTNAME")]
names(sample_xwalk_DEST)[names(sample_xwalk_DEST) == "SDISTNAME"] <- "DSDIST"

trips_sample_S <- merge(x = trips, y = sample_xwalk_ORIG, by = "ORIG_TAZ", all.x = TRUE)
trips_sample_S <- merge(x = trips_sample_S, y = sample_xwalk_DEST, by = "DEST_TAZ", all.x = TRUE)
trips_sample_S$OSDIST[is.na(trips_sample_S$OSDIST)] <- "Missing"
trips_sample_S$DSDIST[is.na(trips_sample_S$DSDIST)] <- "Missing"

trips_sample_S <- trips_sample_S[,c("OSDIST", "DSDIST", "TRIPMODE", "TOURPURP", "SUBTOUR", "finalweight")]

# Recode tour purpose into unique market segmentations
# Work         - [No Subtours ], [All], [TOURPURP - (1,10)] 
# University   - [No Subtours ], [All], [TOURPURP - (2)   ] 
# School       - [No Subtours ], [All], [TOURPURP - (3)   ]  
# Escort       - [No Subtours ], [All], [TOURPURP - (4)   ]   
# Shop         - [No Subtours ], [All], [TOURPURP - (5)   ]   
# Maintenance  - [No Subtours ], [All], [TOURPURP - (6)   ]       
# Eating Out   - [No Subtours ], [All], [TOURPURP - (7)   ]
# Visiting     - [No Subtours ], [All], [TOURPURP - (8)   ]   
# Discretionary- [No Subtours ], [All], [TOURPURP - (9)   ]   
# Work-based   - [All Subtours], [All], [TOURPURP - (All) ]    

trips_sample_S$tour_purpose <- "Other"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(1,10)] <- "Work"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(2)]    <- "University"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(3)]    <- "School"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(4)]    <- "Escort"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(5)]    <- "Shop"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(6)]    <- "Maintenance"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(7)]    <- "Eating Out"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(8)]    <- "Visiting"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==0 & trips_sample_S$TOURPURP %in% c(9)]    <- "Discretionary"
trips_sample_S$tour_purpose[trips_sample_S$SUBTOUR==1]                                        <- "Work-based"

# delete other purpose and records with missing values
trips_sample_S <- trips_sample_S[trips_sample_S$tour_purpose != "Other",]
trips_sample_S <- trips_sample_S[trips_sample_S$OSDIST!="Missing" & trips_sample_S$DSDIST!="Missing",]
trips_sample_S <- trips_sample_S[trips_sample_S$TRIPMODE>0 & trips_sample_S$TRIPMODE<10,]

trips_sample_S$trip_mode <- tripMode_df$tripModeNames[match(trips_sample_S$TRIPMODE, tripMode_df$tripModeCodes)]

trips_sample_S <- trips_sample_S[,c("OSDIST", "DSDIST", "trip_mode", "tour_purpose", "finalweight")]
trips_sample_S <- data.table(trips_sample_S)

trips_flow_S <- trips_sample_S[, .(count = sum(finalweight)), by = list(OSDIST, DSDIST, trip_mode, tour_purpose)]
trips_flow_total_S <- data.table(trips_flow_S[,c("OSDIST", "DSDIST", "trip_mode", "count")])
trips_flow_total_S <- trips_flow_total_S[, (tot = sum(count)), by = list(OSDIST, DSDIST, trip_mode)]
trips_flow_total_S$tour_purpose <- "Total"
names(trips_flow_total_S)[names(trips_flow_total_S) == "V1"] <- "count"
trips_flow_S <- rbind(trips_flow_S, trips_flow_total_S[,c("OSDIST", "DSDIST", "trip_mode", "tour_purpose", "count")])

trips_flow_total_S <- data.table(trips_flow_S[,c("OSDIST", "DSDIST", "tour_purpose", "count")])
trips_flow_total_S <- trips_flow_total_S[, (tot = sum(count)), by = list(OSDIST, DSDIST, tour_purpose)]
trips_flow_total_S$trip_mode <- "Total"
names(trips_flow_total_S)[names(trips_flow_total_S) == "V1"] <- "count"
trips_flow_S <- rbind(trips_flow_S, trips_flow_total_S[,c("OSDIST", "DSDIST", "trip_mode", "tour_purpose", "count")])

write.table(trips_flow_S, paste(WD,"trips_flow_S.csv", sep = "//"), sep = ",", row.names = F)


### Employer Parking Provision
place_raw[is.na(place_raw)] <- 0

workTrips <- trips[trips$DEST_PURP==1,]
workTrips$DEST_MAZ[is.na(workTrips$DEST_MAZ)] <- 0
workTrips$dest_park <- mazData$parkarea[match(workTrips$DEST_MAZ, mazData$MAZ_ORIGINAL)]
workTrips <- workTrips[workTrips$dest_park==1, ]

workTrips$parked_payed <- place_raw$parked_payed[match(paste(workTrips$HH_ID, workTrips$PER_ID, workTrips$DEST_PLACENO, sep = "-"), 
                                                       paste(place_raw$sampno, place_raw$perno, place_raw$plano, sep = "-"))]

workTrips$fp_choice[workTrips$TOURMODE<=3 & workTrips$parked_payed==1] <- 3  # reimburse
workTrips$fp_choice[workTrips$TOURMODE<=3 & workTrips$parked_payed==2] <- 1  # free
workTrips$fp_choice[workTrips$TOURMODE>3 ] <- 2  # pay

xtabs(finalweight~fp_choice, data = workTrips)






#finish
