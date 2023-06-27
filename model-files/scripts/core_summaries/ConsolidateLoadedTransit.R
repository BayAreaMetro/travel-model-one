#
# Simple script to consolidate loaded transit files
#

# Overhead
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

library(foreign)
library(dplyr)

write.dbfMODIF <- function (dataframe, file, factor2char = TRUE, max_nchar = 254)
{
  allowed_classes <- c("logical", "integer", "numeric", "character",
                       "factor", "Date")
  if (!is.data.frame(dataframe))
    dataframe <- as.data.frame(dataframe)     
  if (any(sapply(dataframe, function(x) !is.null(dim(x)))))
      stop("cannot handle matrix/array columns")     
  cl <- sapply(dataframe, function(x) class(x[1L]))     
  asis <- cl == "AsIs"
      
  cl[asis & sapply(dataframe, mode) == "character"] <- "character"     
  if (length(cl0 <- setdiff(cl, allowed_classes)))
        stop("data frame contains columns of unsupported class(es) ",
             paste(cl0, collapse = ","))
      
  m <- ncol(dataframe)
      
  DataTypes <- c(logical = "L", integer = "N", numeric = "F", 
                 character = "C", factor = if (factor2char) "C" else "N",
                 Date = "D")[cl]
      
  for (i in seq_len(m)) {
        
    x <- dataframe[[i]]
    if (is.factor(x))
      dataframe[[i]] <- 
        if (factor2char) as.character(x) else as.integer(x)
        
    else if (inherits(x, "Date"))
      dataframe[[i]] <- format(x, "%Y%m%d")
    }

  precision <- integer(m)
  scale <- integer(m)
  dfnames <- names(dataframe)
  for (i in seq_len(m)) {
    nlen <- nchar(dfnames[i], "b")
    x <- dataframe[, i]
    if (is.logical(x)) {
      precision[i] <- 1L
      scale[i] <- 0L 
      }
    else if (is.integer(x)) {
      if (dfnames[i] == "TIME") {
        precision[i] <- 5L
        scale[i] <- 0L
      } else if (dfnames[i] == "MODE"){
        precision[i] <- 3L
        scale[i] <- 0L
      } else if (dfnames[i] == "PLOT"){
        precision[i] <- 1L
        scale[i] <- 0L
      } else if (dfnames[i] == "COLOR"){
        precision[i] <- 2L
        scale[i] <- 0L
      } else if (dfnames[i] == "STOP_A"){
        precision[i] <- 1L
        scale[i] <- 0L
      } else if (dfnames[i] == "STOP_B"){
        precision[i] <- 1L
        scale[i] <- 0L
      } else if (dfnames[i] == "DIST"){
        precision[i] <- 4L
        scale[i] <- 0L
      } else if (dfnames[i] == "SEQ"){
        precision[i] <- 3L
        scale[i] <- 0L
      } else {
        precision[i] <- 7L
        scale[i] <- 0L
      }
    }
    else if (is.double(x)) {
      #"AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB"
      if (dfnames[i] == "FREQ"){
        precision[i] <- 6L
        scale[i] <- 2L
      } else {
        precision[i] <- 9L
        scale[i] <- 2L}
    } else if (is.character(x)) {
      mf <- max(nchar(x[!is.na(x)], "b"))
      p <- max(nlen, mf)
      if(p > max_nchar)
        warning(gettextf("character column %d will be truncated to %d bytes", i, max_nchar), domain = NA)
      precision[i] <- min(p, max_nchar)
      scale[i] <- 0L
    } else stop("unknown column type in data frame")
      }
      
  if (any(is.na(precision))) stop("NA in precision")
      
  if (any(is.na(scale))) stop("NA in scale")
      
  invisible(.Call(foreign:::DoWritedbf, 
                  as.character(file), 
                  dataframe,
                  as.integer(precision), 
                  as.integer(scale), 
                  as.character(DataTypes))) }

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
#,"AM","MD","PM","EV"
for (timeperiod in c("AM","MD","PM","EV", "EA")) {
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
#,"AM","MD","PM","EV"
# split into timeperiods and write dbfs for quickboards
for (my_tp in c("AM","MD","PM","EV", "EA")) {
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
    supdata_tp$FREQ  <- as.integer(0)
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
                               "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB")]%>%
      #mutate(across(c("DIST", "AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB"), round, 2)) %>%
      mutate(across(c("TIME","DIST","MODE","PLOT","COLOR","SEQ","STOP_A","STOP_B"),
             as.integer))%>%
      mutate(across(c("FREQ","AB_VOL","AB_BRDA","AB_XITA","AB_BRDB","AB_XITB"),
             as.double))


    # print(str(trndata_tp))

    outfile <- file.path(MODEL_DIR, "trn", paste0("trnlink", my_tp,"_withSupport.dbf"))
    write.dbfMODIF(as.data.frame(trndata_tp), file=outfile)
    print(paste("Wrote", outfile))
}