library(dplyr)
library(tidyr)
options(java.parameters = "-Xmx8000m")  # xlsx uses java and can run out of memory
library(xlsx)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling
CODE_DIR     <- Sys.getenv("CODE_DIR")    # location of utilitiles\calibration code
CALIB_ITER   <- Sys.getenv("CALIB_ITER")  # calibration iteration

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
CODE_DIR     <- gsub("\\\\","/",CODE_DIR  ) # switch slashes around
OUTPUT_DIR   <- file.path(TARGET_DIR, paste0("OUTPUT_",CALIB_ITER), "calibration")
if (!file.exists(OUTPUT_DIR)) { dir.create(OUTPUT_DIR) }

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)
stopifnot(nchar(CODE_DIR    )>0)
stopifnot(nchar(CALIB_ITER  )>0)

SAMPLESHARE <- as.numeric(SAMPLESHARE)

print(paste0("TARGET_DIR  = ",TARGET_DIR ))
print(paste0("ITER        = ",ITER       ))
print(paste0("SAMPLESHARE = ",SAMPLESHARE))
print(paste0("CODE_DIR    = ",CODE_DIR   ))
print(paste0("CALIB_ITER  = ",CALIB_ITER ))

WORKBOOK       <- "M:\\Development\\Travel Model One\\Calibration\\Version 1.5.2\\04 Coordinated Daily Activity Pattern\\04_CoordinatedDailyActivityPattern.xlsx"
WORKBOOK       <- gsub("\\\\","/",WORKBOOK  ) # switch slashes around
WORKBOOK_TEMP  <- gsub(".xlsx","_temp.xlsx", WORKBOOK)
WORKBOOK_BLANK <- file.path(CODE_DIR, "workbook_templates", "04_CoordinatedDailyActivityPattern_blank.xlsx")
calib_workbook <- loadWorkbook(file=WORKBOOK_BLANK)
calib_sheets   <- getSheets(calib_workbook)

cdap_results <- read.table(file=file.path(TARGET_DIR,paste0("OUTPUT_",CALIB_ITER),"main","cdapResults.csv"), header=TRUE, sep=",")

# summarize to (county, Auto Ownership)
cdap_ptype  <- group_by(cdap_results, PersonType, ActivityString) %>% summarise(num_pers=n())
# divide by SAMPLESHARE
cdap_ptype  <- mutate(cdap_ptype, num_pers=num_pers/SAMPLESHARE)

cdap_ptype_spread <- spread(cdap_ptype, key=ActivityString, value=num_pers)

# save it
outfile <- file.path(OUTPUT_DIR, paste0("04_daily_activity_pattern_TM.csv"))
write.table(cdap_ptype_spread, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))

# save it (along with source label) to calibration workbook
addDataFrame(as.data.frame(cdap_ptype_spread), calib_sheets$modeldata, startRow=2, startColumn=1, row.names=FALSE)
source_cell <- getCells( getRows(calib_sheets$modeldata, rowIndex=1:1), colIndex=1:1 )
setCellValue(source_cell[[1]], paste("Source: ",outfile))

saveWorkbook(calib_workbook, WORKBOOK_TEMP)
forceFormulaRefresh(WORKBOOK_TEMP, WORKBOOK, verbose=TRUE)
print(paste("Wrote",WORKBOOK))