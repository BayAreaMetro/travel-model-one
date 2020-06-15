#
# Short Summaries
#
# Creates condensed summaries of very high level numbers for viewing across many model runs.
#
# See also summarizeAcrossScenariosUnion.bat
# (https://github.com/BayAreaMetro/travel-model-one/blob/master/utilities/CoreSummaries/summarizeAcrossScenariosUnion.bat)
#

.libPaths(Sys.getenv("R_LIB"))

library(scales)
library(dplyr)
library(reshape2)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

print(paste("TARGET_DIR  =", TARGET_DIR ))
print(paste("ITER        =", ITER       ))
print(paste("SAMPLESHARE =", SAMPLESHARE))

# if there is an OUTPUT subdirectory then we're working on M
ON_M           <- ifelse(dir.exists(file.path(TARGET_DIR, "OUTPUT")), TRUE, FALSE)
INPUT_FULLCOPY <- ifelse(dir.exists(file.path(TARGET_DIR, "INPUT_fullcopy")), TRUE, FALSE)
print(paste("ON_M        =", ON_M))
print(paste("INPUT_FULLCOPY =", INPUT_FULLCOPY))

# this is our short output file
OUTPUT_FILE    <- ifelse(ON_M,
                         file.path(TARGET_DIR, "OUTPUT", "metrics", "topsheet.csv"),
                         file.path(TARGET_DIR, "metrics", "topsheet.csv"))
print(paste("OUTPUT_FILE =", OUTPUT_FILE))

short_summary  <- list("directory"=basename(TARGET_DIR))

###############
# The land use file: https://github.com/BayAreaMetro/modeling-website/wiki/TazData
TAZDATA_FILE   <- ifelse(ON_M, 
                         ifelse(INPUT_FULLCOPY, 
                                file.path(TARGET_DIR,"INPUT_fullcopy","landuse","tazData.csv"),
                                file.path(TARGET_DIR,"INPUT",         "landuse","tazData.csv")),
                                file.path(TARGET_DIR,                 "landuse","tazData.csv"))
print(paste("TAZDATA_FILE=", TAZDATA_FILE))

tazData           <- read.table(file=TAZDATA_FILE, header=TRUE, sep=",")
names(tazData)    <- toupper(names(tazData))

short_summary$'tazdata tothh'  <- sum(tazData$TOTHH)
short_summary$'tazdata totpop' <- sum(tazData$TOTPOP)
short_summary$'tazdata totemp' <- sum(tazData$TOTEMP)
short_summary$'tazdata empres' <- sum(tazData$EMPRES)

###############
## Read the households and person files for length
HH_FILE   <- file.path(TARGET_DIR,"popsyn","hhFile.csv")
PERS_FILE <- file.path(TARGET_DIR,"popsyn","personFile.csv")
if (ON_M) {
  if (INPUT_FULLCOPY) {
    HH_FILE   <- Sys.glob(file.path(TARGET_DIR,"INPUT_fullcopy","popsyn","hh*.csv"))[[1]]
    PERS_FILE <- Sys.glob(file.path(TARGET_DIR,"INPUT_fullcopy","popsyn","pers*.csv"))[[1]]
  } else {
    HH_FILE   <- Sys.glob(file.path(TARGET_DIR,"INPUT","popsyn","hh*.csv"))[[1]]
    PERS_FILE <- Sys.glob(file.path(TARGET_DIR,"INPUT","popsyn","pers*.csv"))[[1]]
  }
}
print(paste("HH_FILE     =", HH_FILE  ))
print(paste("PERS_FILE   =", PERS_FILE))

input.pop.households <- read.table(file = HH_FILE, header=TRUE, sep=",")
short_summary$'popsyn tothh'  <- nrow(input.pop.households)
remove(input.pop.households) # it's big

input.pop.persons    <- read.table(file = PERS_FILE, header=TRUE, sep=",")
input.pop.persons$is_worker <- ifelse(input.pop.persons$ptype==1, 1, 0)

short_summary$'popsyn totpop' <- nrow(input.pop.persons)
short_summary$'popsyn empres' <- sum(input.pop.persons$is_worker)

remove(input.pop.persons) # it's big

###############
AVGLOAD_FILE <- file.path(TARGET_DIR, "hwy", paste0("iter",ITER), "avgload5period_vehclasses.csv")
if (ON_M) {
  AVGLOAD_FILE <- file.path(TARGET_DIR, "OUTPUT", "avgload5period_vehclasses.csv")
}
print(paste("AVGLOAD_FILE=", AVGLOAD_FILE))

loadednet <- read.table(file=AVGLOAD_FILE, header=TRUE, sep=",")
loadednet$VMT <- (loadednet$volEA_tot +
                  loadednet$volAM_tot +
                  loadednet$volMD_tot +
                  loadednet$volPM_tot +
                  loadednet$volEV_tot)*loadednet$distance

# from pre-AV (pre TM1.5) runs
if ("volAM_daav" %in% colnames(loadednet) == FALSE) {
  loadednet$volEA_daav <- 0
  loadednet$volEA_s2av <- 0
  loadednet$volEA_s3av <- 0
  loadednet$volAM_daav <- 0
  loadednet$volAM_s2av <- 0
  loadednet$volAM_s3av <- 0
  loadednet$volMD_daav <- 0
  loadednet$volMD_s2av <- 0
  loadednet$volMD_s3av <- 0
  loadednet$volPM_daav <- 0
  loadednet$volPM_s2av <- 0
  loadednet$volPM_s3av <- 0
  loadednet$volEV_daav <- 0
  loadednet$volEV_s2av <- 0
  loadednet$volEV_s3av <- 0
}
loadednet$VMT_auto <- (loadednet$volEA_da   + loadednet$volEA_daav + loadednet$volEA_dat +
                       loadednet$volEA_s2   + loadednet$volEA_s2av + loadednet$volEA_s2t +
                       loadednet$volEA_s3   + loadednet$volEA_s3av + loadednet$volEA_s3t +
                       loadednet$volAM_da   + loadednet$volAM_daav + loadednet$volAM_dat +
                       loadednet$volAM_s2   + loadednet$volAM_s2av + loadednet$volAM_s2t +
                       loadednet$volAM_s3   + loadednet$volAM_s3av + loadednet$volAM_s3t +
                       loadednet$volMD_da   + loadednet$volMD_daav + loadednet$volMD_dat +
                       loadednet$volMD_s2   + loadednet$volMD_s2av + loadednet$volMD_s2t +
                       loadednet$volMD_s3   + loadednet$volMD_s3av + loadednet$volMD_s3t +
                       loadednet$volPM_da   + loadednet$volPM_daav + loadednet$volPM_dat +
                       loadednet$volPM_s2   + loadednet$volPM_s2av + loadednet$volPM_s2t +
                       loadednet$volPM_s3   + loadednet$volPM_s3av + loadednet$volPM_s3t +
                       loadednet$volEV_da   + loadednet$volEV_daav + loadednet$volEV_dat +
                       loadednet$volEV_s2   + loadednet$volEV_s2av + loadednet$volEV_s2t +
                       loadednet$volEV_s3   + loadednet$volEV_s3av + loadednet$volEV_s3t)*loadednet$distance

short_summary$'network VMT'      <- sum(loadednet$VMT)
short_summary$'network VMT auto' <- sum(loadednet$VMT_auto)
remove(loadednet)

###############
VMT_FILE <- file.path(TARGET_DIR, "core_summaries", "VehicleMilesTraveled.csv")
if (ON_M) {
  VMT_FILE <- file.path(TARGET_DIR, "OUTPUT", "core_summaries", "VehicleMilesTraveled.csv")
}
print(paste("VMT_FILE    =", VMT_FILE))

vmt_core_summary <- read.table(file=VMT_FILE, header=TRUE, sep=",")
vmt_core_summary$total_vmt <- vmt_core_summary$vmt * vmt_core_summary$freq

short_summary$'resident trip table VMT' <- sum(vmt_core_summary$total_vmt)

print(short_summary)

short_sum_df <- as.data.frame(short_summary)
# print(short_sum_df)

write.table(short_sum_df, file=OUTPUT_FILE, sep=",", row.names=FALSE)
