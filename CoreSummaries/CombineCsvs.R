# 
# This script 
#  * reads the summary files from `%TARGET_DIR%\summary`
#  * adds a new column, "runname", with `%RUN_NAME%`
#  * appends the rows to the the summary files in `%COMBINED_DIR%\summary` of the same name.
#
# Note: R is not nec the best choice for this, but it works and the summary scripts are in R.
#

TARGET_DIR   <- Sys.getenv("TARGET_DIR")
RUN_NAME     <- Sys.getenv("RUN_NAME")
COMBINED_DIR <- Sys.getenv("COMBINED_DIR")

# make sure these are set
stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(RUN_NAME    )>0)
stopifnot(nchar(COMBINED_DIR)>0)

# deal with slashy stuff
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR)
COMBINED_DIR <- gsub("\\\\","/",COMBINED_DIR)

if (!file.exists(file.path(COMBINED_DIR,"summary"))) {
  print(paste("Creating directory ",file.path(COMBINED_DIR,"summary")))
  dir.create(file.path(COMBINED_DIR,"summary"), recursive=TRUE)
}

# lets go!
library(dplyr)
print(paste("Going through files in ",file.path(TARGET_DIR,"summary")))
target_files <- list.files(path=file.path(TARGET_DIR,"summary"), pattern="*.csv")
for (target_file in target_files) {
  # read the table to append
  print(paste("Reading ",file.path(TARGET_DIR,"summary",target_file)))
  append_csvTable <- read.table(file=file.path(TARGET_DIR,"summary",target_file), header=TRUE, sep=",")
  append_csvTable <- mutate(append_csvTable, runname=RUN_NAME)
  
  # read the original (if it exists) and combine
  if (file.exists(path=file.path(COMBINED_DIR,"summary",target_file))) {
    print(paste("  Reading ",file.path(COMBINED_DIR,"summary",target_file)))
    orig_csvTable <- read.table(file=file.path(COMBINED_DIR,"summary",target_file), header=TRUE, sep=",")
    csvTable      <- rbind(orig_csvTable, append_csvTable)
  } else {
    csvTable      <- append_csvTable
  }
  
  # write to temp file: new_[target_file]
  write.table(csvTable, file.path(COMBINED_DIR,"summary", paste0("new_",target_file)), sep=",", row.names=FALSE)
  # move the new one over
  file.rename(from=file.path(COMBINED_DIR,"summary", paste0("new_",target_file)),
              to  =file.path(COMBINED_DIR,"summary", target_file))
  print(paste("  Wrote ",file.path(COMBINED_DIR,"summary", target_file)))
}
