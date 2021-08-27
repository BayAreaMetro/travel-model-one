#
# Joins trips with skims
# Input:  updated_data/trips.rds
# Output: updated_data/trips_with_skims.rds
#

library(tidyverse)
library(plyr)

datestampr <- function(myusername = FALSE) {
    # returns something like 20210819_1723_lzorn
    # ignores args other than myusername

    datestampr <- format(Sys.time(), "%Y%m%d_%H%M")
    if (myusername) {
        datestampr <- paste0(datestampr,"_",Sys.getenv("USERNAME"))
    }
    return(datestampr)
}

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
    
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

datestring <- datestampr(myusername=FALSE)
mylogfilename <- paste0("join_trips_with_skims_", datestring,".log")
sink()
sink(mylogfilename, split=TRUE)
cat(paste0("A log of the output will be saved to ", mylogfilename, ". \n \n"))

print(paste("Script started at", Sys.time()))

UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")
trips_todo  <- readRDS(file=file.path(UPDATED_DIR, "trips.rds"))
trips_done  <- tibble()
total_trips <- nrow(trips_todo)

for (timeperiod in c("EA","AM","MD","PM","EV")) {
    # transit first
    for (acc_egr in c("wlk_wlk", "wlk_drv", "drv_wlk")) {
        for (tech in c("com","hvy","exp","lrf","loc")) {
            trn_skims_mode <- paste0(substr(acc_egr,0,3),"_",tech,"_",substr(acc_egr,5,7))
            # split trips into working set and set left to do
            trips_working   <- filter(trips_todo, (timeCode==timeperiod)&(skims_mode==trn_skims_mode))
            trips_todo      <- filter(trips_todo, (timeCode!=timeperiod)|(skims_mode!=trn_skims_mode))
            stopifnot(nrow(trips_working) + nrow(trips_todo) + nrow(trips_done) == total_trips)

            # read skims, keep only some columns
            trn_skims <- read.table(file=file.path(TARGET_DIR,"database",paste0("trnskm", tolower(timeperiod), "_", trn_skims_mode, ".csv")),
                                    header=TRUE, sep=",", fill=TRUE) %>%
                         mutate(distance=distLOC+distLRF+distEXP+distHVY+distCOM,
                                walktime=wacc+waux+wegr) %>%
                         select(-ivtLOC,-ivtLRF,-ivtEXP,-ivtHVY,-ivtCOM,-ivtFerry,-ivtMUNILoc,-ivtMUNIMet, # combined ivt is sufficient
                                -distLOC,-distLRF,-distEXP,-distHVY,-distCOM,-distFerry,                   # combined distance is sufficient
                                -iwait, -xwait,                                                            # combined wait is sufficient
                                -wacc,-waux,-wegr,                                                         # combined walktime is sufficient
                                -firstMode)
            # verify the column, one, is in fact all ones so we're parsing the file correctly
            bad_rows <- filter(trn_skims, one != 1)
            if (nrow(bad_rows) > 1) {
                print(bad_rows)
                stop(paste("Found bad rows in timeperiod",timeperiod,"skims for",trn_skims_mode))
            }
            trn_skims <- select(trn_skims, -one)

            trips_working <- left_join(trips_working, trn_skims, by=c("orig_taz"="orig", "dest_taz"="dest"))

            # put it in the done pile
            trips_done <- rbind(trips_done, trips_working)
            print(paste("Joined", timeperiod, "skims for skims_mode",trn_skims_mode,"=> processed ", prettyNum(nrow(trips_done),big.mark=","), "trips"))
        }
    }
    # print(head(trips_done))

    # then all others
    trips_working   <- filter(trips_todo, (timeCode==timeperiod))
    trips_todo      <- filter(trips_todo, (timeCode!=timeperiod))
    stopifnot(nrow(trips_working) + nrow(trips_todo) + nrow(trips_done) == total_trips)

    for (skim_type in c("Time","Cost","Distance")) {
        # make these consistent with transit column names
        if      (skim_type == "Time")     { col_name = "ivt"      } 
        else if (skim_type == "Cost")     { col_name = "fare"     } 
        else if (skim_type == "Distance") { col_name = "distance" }

        skims <- read.table(file=file.path(TARGET_DIR,"database",paste0(skim_type,"SkimsDatabase",timeperiod,".csv")), header=TRUE, sep=",")
        # these columns don't exist so make them zero
        if (skim_type == "Cost") {
            skims <- mutate(skims, bike=0, walk=0)
        }

        trips_working <- left_join(trips_working, skims, by=c("orig_taz"="orig", "dest_taz"="dest"))
        trips_working <- mutate(trips_working, skim_value=case_when(
                                skims_mode=="da"         ~ da,
                                skims_mode=="daToll"     ~ daToll,
                                skims_mode=="s2"         ~ s2,
                                skims_mode=="s2Toll"     ~ s2Toll,
                                skims_mode=="s3"         ~ s3,
                                skims_mode=="s3Toll"     ~ s3Toll,
                                skims_mode=="walk"       ~ walk,
                                skims_mode=="bike"       ~ bike,
                                skims_mode=="Taxi"       ~ s2Toll,
                                skims_mode=="TNC_single" ~ s2Toll,
                                skims_mode=="TNC_shared" ~ s2Toll,
                                TRUE                     ~ 0)) %>%
                        # If travel between two points by the mode in question is not possible
                        # (or highly unlikely, e.g. a transit trip that would take 5 hours), the skim data contains a value of -999. 
                        mutate(skim_value = replace(skim_value, skim_value==-999, NA)) %>%
                        dplyr::rename(!!col_name:=skim_value) %>%
                        # remove these and don't error if they're not there
                        select_if(!names(.) %in% c('da','daToll','s2','s2Toll','s3','s3Toll','walk','bike','wTrnW','wTrnD','dTrnW')) 
        print(paste("Joined", timeperiod, "skims for skim_type",skim_type," (", prettyNum(nrow(trips_working),big.mark=","), ") trips"))

        # costs are in 2000 cents, convert to dollars
        # https://github.com/BayAreaMetro/modeling-website/wiki/SimpleSkims#cost-skims
        if (skim_type == "Cost") {
            trips_working <- mutate(trips_working, fare=0.01*fare)
        }

        # print(head(trips_working)) 
    }
    # put it in the done pile
    trips_done <- rbind.fill(trips_done, trips_working)
    print(paste("Joined", timeperiod, "skims for non transit modes => processed ", prettyNum(nrow(trips_done),big.mark=","), "trips"))

}

print(paste("Saving trips_with_skims.rds with",prettyNum(nrow(trips_done),big.mark=","),"rows and",ncol(trips_done),"columns; expecting", 
      prettyNum(total_trips,big.mark=","), "rows"))
saveRDS(trips_done, file=file.path(UPDATED_DIR, "trips_with_skims.rds"))

print(paste("Script completed at", Sys.time()))
