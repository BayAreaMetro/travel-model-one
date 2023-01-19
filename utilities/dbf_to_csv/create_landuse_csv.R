library(foreign)
args=commandArgs(trailingOnly=TRUE)

landuse_dir <-args[1]
landuse_dbf <- "ZMAST15.DBF"
landuse_csv <- "tazData.csv"
df <- read.dbf(paste(landuse_dir, landuse_dbf, sep=""))
df2 <- df[rowSums(is.na(df)) != ncol(df), ]
write.csv(df2, paste(landuse_dir, landuse_csv, sep=""), row.names=FALSE)