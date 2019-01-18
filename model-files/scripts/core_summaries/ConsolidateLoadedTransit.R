#
# Simple script to consolidate loaded transit files
#

# Overhead
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))


# For RStudio, these can be set in the .Rprofile
MODEL_DIR   <- Sys.getenv("MODEL_DIR")  # The location of the input file
MODEL_DIR   <- gsub("\\\\","/",MODEL_DIR) # switch slashes around
COL_NAMES   <- c("name","mode","owner","frequency","line time","line dist","total boardings","passenger miles","passenger hours","path id")
ITER        <- "3"

# this is required
stopifnot(nchar(MODEL_DIR  )>0)

all_trndata <- data.frame()

for (timeperiod in c("ea","am","md","pm","ev")) {
  for (submode in c("loc","lrf","exp","hvy","com")) {
    
    # wlk wlk
    filename <- paste0("trnline",timeperiod,"_wlk_",submode,"_wlk.csv")
    fullfile <- file.path(MODEL_DIR, "trn", paste0("TransitAssignment.iter",ITER), filename)
    trndata  <- read.csv(file=fullfile, col.names=COL_NAMES, header=FALSE, sep=",", check.names=FALSE)
    all_trndata <- rbind(all_trndata, trndata)
    print(paste("Read ",fullfile))
    
    # drv wlk
    filename <- paste0("trnline",timeperiod,"_drv_",submode,"_wlk.csv")
    fullfile <- file.path(MODEL_DIR, "trn", paste0("TransitAssignment.iter",ITER), filename)
    trndata  <- read.csv(file=fullfile, col.names=COL_NAMES, header=FALSE, sep=",", check.names=FALSE)
    all_trndata <- rbind(all_trndata, trndata)
    print(paste("Read ",fullfile))
    
    # wlk drv
    filename <- paste0("trnline",timeperiod,"_wlk_",submode,"_drv.csv")
    fullfile <- file.path(MODEL_DIR, "trn", paste0("TransitAssignment.iter",ITER), filename)
    trndata  <- read.csv(file=fullfile, col.names=COL_NAMES, header=FALSE, sep=",", check.names=FALSE)
    all_trndata <- rbind(all_trndata, trndata)
    print(paste("Read ",fullfile))
    
  }
}

# write it
outfile <- file.path(MODEL_DIR, "trn", "trnline.csv")
write.csv(all_trndata, file=outfile, row.names=FALSE, quote=FALSE)
print(paste("Wrote ",outfile))
