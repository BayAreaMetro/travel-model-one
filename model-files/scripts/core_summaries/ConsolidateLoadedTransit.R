#
# Simple script to consolidate loaded transit files
# RSG 2022-01-21 TM1.5 add advanced air mobility mode

# Overhead
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

library(foreign)
library(dplyr)

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
trnlink_dbf_data <- data.frame()

for (timeperiod in c("ea","am","md","pm","ev")) {
  # read the input dbfs
  filename <- paste0("trnlink",timeperiod,"_ALLMSA.dbf")
  fullfile <- file.path(MODEL_DIR, "trn", filename)
  trndata  <- read.dbf(file=fullfile, as.is=TRUE)
  trndata$timeperiod <- timeperiod

  # this one is long, so drop those with is.na(AB_VOL)
  trndata  <- trndata[ which(is.na(trndata$AB_VOL)==FALSE),]
  if (nrow(trndata) == 0) {
    print(paste("No rows with volume in", fullfile))
    next
  }
  trndata$source <- filename
  trnlink_dbf_data <- rbind(trnlink_dbf_data, trndata)
  print(paste("Read ",fullfile))

  for (submode in c("loc","lrf","exp","hvy","com","aam")) {
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

# split into timeperiods and write dbfs for quickboards
for (my_tp in c("ea","am","md","pm","ev")) {
    # columns: A, B, TIME, MODE, FREQ, PLOT, COLOR, STOP_A, STOP_B, DIST, NAME, SEQ, OWNER, AB, ABNAMESEQ, 
    # FULLNAME, SYSTEM, GROUP, VEHTYPE, VEHCAP, PERIODCAP, LOAD, 
    # AB_VOL, AB_BRDA, AB_XITA, AB_BRDB, AB_XITB,
    # BA_VOL, BA_BRDA, BA_XITA, BA_BRDB, BA_XITB, timeperiod, source
    trndata_tp <- subset(trnlink_dbf_data, timeperiod == my_tp)
    # columns: A, B, time, mode, plot, stopA, stopB, distance, name, owner,
    # AB_VOL, AB_BRDA, AB_XITA, AB_BRDB, AB_XITB,
    # BA_VOL, BA_BRDA, BA_XITA, BA_BRDB, BA_XITB, prn, timeperiod, source
    supdata_tp <- subset(all_trnlink_data, (timeperiod == my_tp) & (mode < 10))
    # print(head(trndata_tp))
    # print(head(supdata_tp))

    # set support link fields
    supdata_tp$TIME  <- as.integer(supdata_tp$time*100)
    supdata_tp$DIST  <- as.integer(supdata_tp$distance*100)
    supdata_tp$FREQ  <- 0.0
    supdata_tp$SEQ   <- as.integer(0)
    supdata_tp$COLOR <- as.integer(0)
    supdata_tp$OWNER <- as.character(supdata_tp$owner)

    colnames(supdata_tp)[colnames(supdata_tp)=="mode"  ] <- "MODE"
    colnames(supdata_tp)[colnames(supdata_tp)=="plot"  ] <- "PLOT"
    colnames(supdata_tp)[colnames(supdata_tp)=="stopA" ] <- "STOP_A"
    colnames(supdata_tp)[colnames(supdata_tp)=="stopB" ] <- "STOP_B"
    colnames(supdata_tp)[colnames(supdata_tp)=="name"  ] <- "NAME"

    # fill blanks with zero
    cols <- c("AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")
    supdata_tp[cols][is.na(supdata_tp[cols])] <- 0

    supdata_tp <- group_by(supdata_tp, A, B, MODE) %>% 
        summarise(TIME   =first(TIME),  FREQ   =first(FREQ),   PLOT   =first(PLOT),  COLOR  =first(COLOR),
                  STOP_A =first(STOP_A),STOP_B =first(STOP_B), DIST   =first(DIST),  NAME   =first(NAME),  SEQ =first(SEQ),     OWNER  =first(OWNER),
                  AB_VOL =sum(AB_VOL),  AB_BRDA=sum(AB_BRDA),  AB_XITA=sum(AB_XITA), AB_BRDB=sum(AB_BRDB), AB_XITB=sum(AB_XITB))
    supdata_tp$NAME <- as.character(supdata_tp$NAME)

    trndata_tp <- trndata_tp[c("A","B","TIME","MODE","FREQ","PLOT","COLOR",
                               "STOP_A","STOP_B","DIST","NAME","SEQ","OWNER",
                               "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")]

    # print("supdata_tp!!")
    # print(head(supdata_tp))
    # print(str(supdata_tp))

    # print("trndata_tp!!")
    # print(head(trndata_tp))
    # print(str(trndata_tp))

    # put trndata and supdata together
    trndata_tp <- bind_rows(supdata_tp, trndata_tp)
    # print(head(trndata_tp))

    # print(colnames(trndata_tp))
    trndata_tp <- trndata_tp[c("A","B","TIME","MODE","FREQ","PLOT","COLOR",
                               "STOP_A","STOP_B","DIST","NAME","SEQ","OWNER",
                               "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")]

    # print(str(trndata_tp))

    outfile <- file.path(MODEL_DIR, "trn", paste0("trnlink", my_tp,"_withSupport.dbf"))
    write.dbf(as.data.frame(trndata_tp), file=outfile)
    print(paste("Wrote", outfile))
}