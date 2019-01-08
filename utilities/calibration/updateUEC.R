library(dplyr)
library(tidyr)
options(java.parameters = "-Xmx8000m")  # xlsx uses java and can run out of memory
library(xlsx)

CALIB_DIR  <- "M:\\Development\\Travel Model One\\Calibration\\Version 1.5.0"
UEC_DIR    <- "X:\\travel-model-one-calibration\\model-files\\model"
CALIB_DIR  <- gsub("\\\\","/",CALIB_DIR) # switch slashes around
UEC_DIR    <- gsub("\\\\","/",UEC_DIR)   # switch slashes around

args = commandArgs(trailingOnly=TRUE)

if (length(args)<2) {
  stop("Two arguments required: submodel and version.\n")
}

SUBMODEL = args[1]
VERSION  = args[2]

print(paste0("SUBMODEL = ",SUBMODEL))
print(paste0("VERSION  = ",VERSION))

if (SUBMODEL=="UsualWorkAndSchoolLocation") {

  CALIB_WORKBOOK   <- file.path(CALIB_DIR, "01 Usual Work and School Location", "01_UsualWorkAndSchoolLocation.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "DestinationChoice.xls")
  
  # sheet, column, startRow, endRow
  COPY_SRC <- list("work"       =c("calibration", 4, 4, 8),
                   "work_county"=c("calibration",10, 4,10),
                   "university" =c("calibration",16, 4, 8),
                   "highschool" =c("calibration",33, 4, 8),
                   "gradeschool"=c("calibration",34, 4, 8))

  COPY_DST <- list("work"       =c(       "Work", 7,22,26),
                   "work_county"=c(       "Work", 7,38,44),
                   "university" =c( "University", 7,12,16),
                   "highschool" =c( "HighSchool", 7,12,16),
                   "gradeschool"=c("GradeSchool", 7,12,16))

} else if (SUBMODEL=="AutomobileOwnership") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "02 Automobile Ownership", "02_AutoOwnership.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "AutoOwnership.xls")

  # sheet, column, startRow, endRow
  COPY_SRC <- list("1_car_a"   =c("calibration", 4, 18, 19),
                   "2_cars_a"  =c("calibration", 5, 18, 19),
                   "3_cars_a"  =c("calibration", 6, 18, 19),
                   "4+_cars_a" =c("calibration", 7, 18, 19),
                   "1_car_b"   =c("calibration", 4, 24, 27),
                   "2_cars_b"  =c("calibration", 5, 24, 27),
                   "3_cars_b"  =c("calibration", 6, 24, 27),
                   "4+_cars_b" =c("calibration", 7, 24, 27))

  COPY_DST <- list("1_car_a"   =c("Auto ownership", 8, 53, 54,
                                  "Auto ownership", 9, 53, 54),
                   "2_cars_a"  =c("Auto ownership",10, 53, 54,
                                  "Auto ownership",11, 53, 54,
                                  "Auto ownership",12, 53, 54),
                   "3_cars_a"  =c("Auto ownership",13, 53, 54,
                                  "Auto ownership",14, 53, 54,
                                  "Auto ownership",15, 53, 54,
                                  "Auto ownership",16, 53, 54),
                   "4+_cars_a" =c("Auto ownership",17, 53, 54),
                   
                   "1_car_b"   =c("Auto ownership", 8, 55, 58,
                                  "Auto ownership", 9, 55, 58),
                   "2_cars_b"  =c("Auto ownership",10, 55, 58,
                                  "Auto ownership",11, 55, 58,
                                  "Auto ownership",12, 55, 58),
                   "3_cars_b"  =c("Auto ownership",13, 55, 58,
                                  "Auto ownership",14, 55, 58,
                                  "Auto ownership",15, 55, 58,
                                  "Auto ownership",16, 55, 58),
                   "4+_cars_b" =c("Auto ownership",17, 55, 58))
  
} else if (SUBMODEL=="TourModeChoice") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "11 Tour Mode Choice", "11_TourModeChoice.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "ModeChoice.xls")

  # sheet, column, startRow, endRow
  COPY_SRC <- list("work"      =c( "constants", 4,   3,  64),
                   "university"=c( "constants", 8,   3,  64),
                   "school"    =c( "constants",12,   3,  64),
                   "escort"    =c( "constants",16,   3,  64),
                   "shopping"  =c( "constants",20,   3,  64),
                   "eatout"    =c( "constants",24,   3,  64),
                   "othmaint"  =c( "constants",28,   3,  64),
                   "social"    =c( "constants",32,   3,  64),
                   "othdiscr"  =c( "constants",36,   3,  64),
                   "workbased" =c( "constants",40,   3,  64))

  COPY_DST <- list("work"      =c(      "Work", 5, 404, 465),
                   "university"=c("University", 5, 404, 465),
                   "school"    =c(    "School", 5, 404, 465),
                   "escort"    =c(    "Escort", 5, 404, 465),
                   "shopping"  =c(  "Shopping", 5, 404, 465),
                   "eatout"    =c(    "EatOut", 5, 404, 465),
                   "othmaint"  =c(  "OthMaint", 5, 404, 465),
                   "social"    =c(    "Social", 5, 404, 465),
                   "othdiscr"  =c(  "OthDiscr", 5, 404, 465),
                   "workbased" =c( "WorkBased", 5, 407, 468))
  
} else if (SUBMODEL=="TripModeChoice") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "15 Trip Mode Choice", "15_TripModeChoice.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "TripModeChoice.xls")
  
} else {
  stop(paste0("Don't understand SUBMODEL [",SUBMODEL,"]"))
}

# use the right version
CALIB_WORKBOOK <- gsub(".xlsx",paste0("_",VERSION,".xlsx"),CALIB_WORKBOOK)
UEC_DST_WORKBOOK <- gsub("TM1.0 version/","",UEC_SRC_WORKBOOK)
# UEC_DST_WORKBOOK <- gsub(".xls", "_temp.xls", UEC_DST_WORKBOOK)

print(paste0("CALIB_WORKBOOK   = ",CALIB_WORKBOOK))
print(paste0("UEC_SRC_WORKBOOK = ",UEC_SRC_WORKBOOK))
print(paste0("UEC_DST_WORKBOOK = ",UEC_DST_WORKBOOK))

# open the calibration workbook
calib_workbook <- loadWorkbook(file=CALIB_WORKBOOK)
calib_sheets   <- getSheets(calib_workbook)

# open the UEC SRC   
uec_workbook <- loadWorkbook(file=UEC_SRC_WORKBOOK)
uec_sheets   <- getSheets(uec_workbook)

for (name in names(COPY_SRC)) {
  calib_sheetname     <- COPY_SRC[[name]][1]
  calib_column        <- strtoi(COPY_SRC[[name]][2])
  calib_start_row     <- strtoi(COPY_SRC[[name]][3])
  calib_end_row       <- strtoi(COPY_SRC[[name]][4])

  print(paste0("Reading ",name," from sheet ",calib_sheetname,
               " @ (",calib_start_row,",",calib_column,") - (",
               calib_end_row,",",calib_column,")"))
  
  calib_sheet <- calib_sheets[[calib_sheetname]]
  data <- readColumns(calib_sheet,
                      startColumn=calib_column, endColumn=calib_column,
                      startRow=calib_start_row, endRow=calib_end_row,
                      header=FALSE, colClasses=c("numeric"))
  print(data)
  
  for (copynum in 1:(length(COPY_DST[[name]])/4)) {
    print(paste0("Copying set ",copynum))
    uec_sheetname    <- COPY_DST[[name]][(copynum-1)*4 + 1]
    uec_column       <- strtoi(COPY_DST[[name]][(copynum-1)*4 + 2])
    uec_start_row    <- strtoi(COPY_DST[[name]][(copynum-1)*4 + 3])
    uec_end_row      <- strtoi(COPY_DST[[name]][(copynum-1)*4 + 4])
    uec_suffix_row   <- uec_end_row+1
    
    print(paste0("Copying to ",uec_sheetname,
                 " @ (",uec_start_row,",",uec_column,") - (",
                 uec_end_row,",",uec_column,")"))

    uec_sheet <- uec_sheets[[uec_sheetname]]
    # addDataFrame adds a blank cell so fetch the value so we can put it back
    cell_after_last     <- getCells( getRows(uec_sheet, rowIndex=uec_suffix_row:uec_suffix_row), 
                                     colIndex=uec_column:uec_column )
    cell_after_last_val <- getCellValue(cell_after_last[[1]])
    print(paste0("Cell after last: ",cell_after_last_val))
    
    addDataFrame(data, sheet=uec_sheet, col.names=FALSE, row.names=FALSE,
                 startRow=uec_start_row, startColumn=uec_column)

    # put this back if it's not na
    if (!is.na(cell_after_last_val)) {
      setCellValue(cell_after_last[[1]], cell_after_last_val)
    }
  }
}

saveWorkbook(uec_workbook, UEC_DST_WORKBOOK)
#forceFormulaRefresh(WORKBOOK_TEMP, WORKBOOK, verbose=TRUE)
cat("Wrote ",UEC_DST_WORKBOOK,"\n")