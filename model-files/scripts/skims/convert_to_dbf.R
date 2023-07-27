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

args=commandArgs(trailingOnly=TRUE)
input_dir <- args[1]

time_period_list <- c('AM','PM','MD','EA','EV')


for (tp in time_period_list){
  
  routelink_filename <- paste('trnlink', tp, '_ALLMSA.csv', sep='')
  linksum_filename <- paste('trnlink', tp, '_ALLMSA_linksum.csv', sep='')
  
  routelink_dbf <- paste('trnlink', tp, '_ALLMSA.dbf', sep='')
  linksum_dbf <- paste('trnlink', tp, '_ALLMSA_linksum.dbf', sep='')
  
  if (file.exists(paste(input_dir, routelink_filename, sep=''))){
    
    routeLink_csv = read.csv(paste(input_dir, routelink_filename, sep=''))
    write.dbfMODIF(routeLink_csv, paste(input_dir, routelink_dbf, sep=''))
    
  } else {
      print ("MSA File does not exist")
    }
  
  if (file.exists(paste(input_dir, linksum_filename, sep=''))){
    
    linksum_csv = read.csv(paste(input_dir, linksum_filename, sep=''))
    write.dbfMODIF(linksum_csv, paste(input_dir, linksum_filename, sep=''))
    
  }else {
    print ("Linksum File does not exist")
  }
  
}
