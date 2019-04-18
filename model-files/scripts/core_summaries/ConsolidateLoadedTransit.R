#
# Simple script to consolidate loaded transit files
#

# Overhead
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

# For RStudio, these can be set in the .Rprofile
MODEL_DIR        <- Sys.getenv("TARGET_DIR")  # The location of the input file
MODEL_DIR        <- gsub("\\\\","/",MODEL_DIR) # switch slashes around
LINE_COL_NAMES   <- c("name","mode","owner","frequency","line time","line dist","total boardings","passenger miles","passenger hours","path id")
LINK_COL_NAMES   <- c("A", "B", "time", "mode", "plot", "stopA","stopB","distance","name","owner","AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB","BA_VOL","BA_BRDA","BA_XITA","BA_BRDB","BA_XITB","prn")
ITER             <- Sys.getenv("ITER")

# this is required
stopifnot(nchar(MODEL_DIR  )>0)

all_trnline_data <- data.frame()
all_trnlink_data <- data.frame()

for (timeperiod in c("ea","am","md","pm","ev")) {
  for (submode in c("loc","lrf","exp","hvy","com")) {
    for (acc_egr in list( c("wlk","wlk"), c("drv","wlk"), c("wlk","drv"))) {
        # line file
        filename <- paste0("trnline",timeperiod,"_",acc_egr[1],"_",submode,"_",acc_egr[2],".csv")
        fullfile <- file.path(MODEL_DIR, "trn", paste0("TransitAssignment.iter",ITER), filename)
        trndata  <- read.csv(file=fullfile, col.names=LINE_COL_NAMES, header=FALSE, sep=",", check.names=FALSE)
        all_trnline_data <- rbind(all_trnline_data, trndata)
        print(paste("Read ",fullfile))
        
        # link file
        filename <- paste0("trnlink",timeperiod,"_",acc_egr[1],"_",submode,"_",acc_egr[2],".csv")
        fullfile <- file.path(MODEL_DIR, "trn", paste0("TransitAssignment.iter",ITER), filename)
        trndata  <- read.csv(file=fullfile, col.names=LINK_COL_NAMES, header=FALSE, sep=",", check.names=FALSE)
        trndata$timeperiod <- timeperiod

        # this one is long, so drop those with is.na(AB_VOL)
        trndata  <- trndata[ which(is.na(trndata$AB_VOL)==FALSE),]
        if (nrow(trndata) == 0) {
            print(paste("No rows with volume in", fullfile))
            next
        }
        trndata$source <- filename
        all_trnlink_data <- rbind(all_trnlink_data, trndata)
        print(paste("Read ",fullfile))
    }
  }
}

# write it
outfile <- file.path(MODEL_DIR, "trn", "trnline.csv")
write.csv(all_trnline_data, file=outfile, row.names=FALSE, quote=FALSE)
print(paste("Wrote",outfile))

outfile <- file.path(MODEL_DIR, "trn", "trnlink.csv")
write.csv(all_trnlink_data, file=outfile, row.names=FALSE, quote=FALSE)
print(paste("Wrote",outfile))

library(foreign)

# split into timeperiods and write dbfs for quickboards
for (my_tp in c("ea","am","md","pm","ev")) {
    trndata_tp <- subset(all_trnlink_data, timeperiod == my_tp)

    trndata_tp$TIME  <- as.integer(trndata_tp$time*100)
    trndata_tp$DIST  <- as.integer(trndata_tp$distance*100)
    trndata_tp$FREQ  <- 10.0 # todo - get from dbf?
    trndata_tp$SEQ   <- 1    # todo - get from dbf?
    trndata_tp[ which(trndata_tp$mode < 10), "SEQ"] <- 0  # make it zero for support links
    trndata_tp$SEQ   <- as.integer(trndata_tp$SEQ)
    trndata_tp$COLOR <- as.integer(0)
    trndata_tp$OWNER <- as.character(trndata_tp$owner)

    colnames(trndata_tp)[colnames(trndata_tp)=="mode"  ] <- "MODE"
    colnames(trndata_tp)[colnames(trndata_tp)=="plot"  ] <- "PLOT"
    colnames(trndata_tp)[colnames(trndata_tp)=="stopA" ] <- "STOP_A"
    colnames(trndata_tp)[colnames(trndata_tp)=="stopB" ] <- "STOP_B"
    colnames(trndata_tp)[colnames(trndata_tp)=="name"  ] <- "NAME"

    # fill blanks with zero
    cols <- c("AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")
    trndata_tp[cols][is.na(trndata_tp[cols])] <- 0

    # print(colnames(trndata_tp))
    trndata_tp <- trndata_tp[c("A","B","TIME","MODE","FREQ","PLOT","COLOR",
                               "STOP_A","STOP_B","DIST","NAME","SEQ","OWNER",
                               "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")]

    print(str(trndata_tp))

    outfile <- file.path(MODEL_DIR, "trn", paste0("trnlink", my_tp,"_withSupport.dbf"))
    write.dbf(trndata_tp, file=outfile)
    print(paste("Wrote", outfile))
}