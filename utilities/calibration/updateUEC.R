library(dplyr)
library(tidyr)
options(java.parameters = "-Xmx8000m")  # xlsx uses java and can run out of memory
library(xlsx)

CALIB_DIR  <- "M:\\Development\\Travel Model One\\Calibration\\Version 1.5.2"
UEC_DIR    <- "X:\\travel-model-one-calib1.5.2\\model-files\\model"
CALIB_DIR  <- gsub("\\\\","/",CALIB_DIR) # switch slashes around
UEC_DIR    <- gsub("\\\\","/",UEC_DIR)   # switch slashes around

BOX_DIR  <- "C:\\Users\\lzorn\\Box\\Modeling and Surveys\\Development\\Travel Model 1.5\\Calibration\\workbooks_TM1.5.2"
BOX_DIR  <- gsub("\\\\","/",BOX_DIR) # switch slashes around


args = commandArgs(trailingOnly=TRUE)

if (length(args)<2) {
  stop("Two arguments required: submodel and version.\n")
}

SUBMODEL = args[1]
VERSION  = args[2]

print(paste0("SUBMODEL = ",SUBMODEL))
print(paste0("VERSION  = ",VERSION))

if (SUBMODEL=="DestinationChoice") {

  # note this includes UsualWorkAndSchoolLocation AND NonWorkDestinationChoice
  # so the workbook numbers need to be in sync
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "DestinationChoice_TM1.xls")
  CALIB_WORKBOOK   <- file.path(CALIB_DIR, "01 Usual Work and School Location", "01_UsualWorkAndSchoolLocation.xlsx")
  
  # sheet, column, startRow, endRow
  COPY_SRC <- list("work"       =c("calibration", 4, 4, 8),
                   "work_county"=c("calibration",10, 4,13),
                   "university" =c("calibration",16, 4, 8),
                   "highschool" =c("calibration",33, 4, 8),
                   "gradeschool"=c("calibration",34, 4, 8))

  COPY_DST <- list("work"       =c(       "Work", 7,22,26),
                   "work_county"=c(       "Work", 7,38,47),
                   "university" =c( "University", 7,12,16),
                   "highschool" =c( "HighSchool", 7,12,16),
                   "gradeschool"=c("GradeSchool", 7,12,16))

  
  CALIB_WORKBOOK2   <- file.path(CALIB_DIR, "09 Non-Work Destination Choice", "09_NonWorkDestinationChoice.xlsx")
  # sheet, column, startRow, endRow
  COPY_SRC2 <- list("escort1"    =c("calibration", 5, 4, 8),
                    "escort2"    =c("calibration", 5, 4, 8),
                    "shopping"   =c("calibration",17, 4, 8),
                    "maint"      =c("calibration",29, 4, 8),
                    "eatout"     =c("calibration",41, 4, 8),
                    "social"     =c("calibration",53, 4, 8),
                    "discr"      =c("calibration",65, 4, 8),
                    "atwork"     =c("calibration",77, 4, 8))
  
  COPY_DST2 <- list("escort1"    =c(  "EscortKids", 7,12,16),
                    "escort2"    =c("EscortNoKids", 7,12,16),
                    "shopping"   =c(    "Shopping", 7,12,16),
                    "maint"      =c(    "OthMaint", 7,12,16),
                    "eatout"     =c(      "EatOut", 7,12,16),
                    "social"     =c(      "Social", 7,12,16),
                    "discr"      =c(    "OthDiscr", 7,12,16),
                    "atwork"     =c(   "WorkBased", 7,12,16))

  CONFIG <- list(CALIB_WORKBOOK,  COPY_SRC,  COPY_DST,
                 CALIB_WORKBOOK2, COPY_SRC2, COPY_DST2)
  
} else if (SUBMODEL=="AutomobileOwnership") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "02 Automobile Ownership", "02_AutoOwnership.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.0 version", "AutoOwnership_TM1.xls")

  # sheet, column, startRow, endRow
  COPY_SRC <- list("1_car_a"   =c("calibration", 4, 18, 19),
                   "2_cars_a"  =c("calibration", 5, 18, 19),
                   "3_cars_a"  =c("calibration", 6, 18, 19),
                   "4+_cars_a" =c("calibration", 7, 18, 19),
                   "1_car_sc"  =c("calibration", 4, 21, 21),
                   "2_cars_sc" =c("calibration", 5, 21, 21),
                   "3_cars_sc" =c("calibration", 6, 21, 21),
                   "4+_cars_sc"=c("calibration", 7, 21, 21),
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

                   "1_car_sc"  =c("Auto ownership", 8, 59, 59,
                                  "Auto ownership", 9, 59, 59),
                   "2_cars_sc" =c("Auto ownership",10, 59, 59,
                                  "Auto ownership",11, 59, 59,
                                  "Auto ownership",12, 59, 59),
                   "3_cars_sc" =c("Auto ownership",13, 59, 59,
                                  "Auto ownership",14, 59, 59,
                                  "Auto ownership",15, 59, 59,
                                  "Auto ownership",16, 59, 59),
                   "4+_cars_sc"=c("Auto ownership",17, 59, 59),
                   
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

  CONFIG <- list(CALIB_WORKBOOK, COPY_SRC, COPY_DST)
  
} else if (SUBMODEL=="TourModeChoice") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "11 Tour Mode Choice", "11_TourModeChoice.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.5.1 version", "ModeChoice_TM1.5.1.xls")

  # sheet, column, startRow, endRow
  COPY_SRC <- list("work"          =c( "constants", 4,   3,  64),
                   "university"    =c( "constants", 8,   3,  64),
                   "school"        =c( "constants",12,   3,  64),
                   "escort"        =c( "constants",16,   3,  64),
                   "shopping"      =c( "constants",20,   3,  64),
                   "eatout"        =c( "constants",24,   3,  64),
                   "othmaint"      =c( "constants",28,   3,  64),
                   "social"        =c( "constants",32,   3,  64),
                   "othdiscr"      =c( "constants",36,   3,  64),
                   "workbased"     =c( "constants",40,   3,  64),

                   "cbd_work"      =c(    "CBD_SF", 9,   3,   8),
                   "cbd_university"=c(    "CBD_SF", 9,   9,  14),
                   "cbd_school"    =c(    "CBD_SF", 9,  15,  20),
                   "cbd_escort"    =c(    "CBD_SF", 9,  21,  26),
                   "cbd_shopping"  =c(    "CBD_SF", 9,  21,  26),
                   "cbd_eatout"    =c(    "CBD_SF", 9,  27,  32),
                   "cbd_othmaint"  =c(    "CBD_SF", 9,  21,  26),
                   "cbd_social"    =c(    "CBD_SF", 9,  27,  32),
                   "cbd_othdiscr"  =c(    "CBD_SF", 9,  27,  32),
                   "cbd_workbased" =c(    "CBD_SF", 9,  33,  38))

  COPY_DST <- list("work"          =c(      "Work", 5, 408, 469),
                   "university"    =c("University", 5, 408, 469),
                   "school"        =c(    "School", 5, 408, 469),
                   "escort"        =c(    "Escort", 5, 408, 469),
                   "shopping"      =c(  "Shopping", 5, 408, 469),
                   "eatout"        =c(    "EatOut", 5, 408, 469),
                   "othmaint"      =c(  "OthMaint", 5, 408, 469),
                   "social"        =c(    "Social", 5, 408, 469),
                   "othdiscr"      =c(  "OthDiscr", 5, 408, 469),
                   "workbased"     =c( "WorkBased", 5, 411, 472),

                   "cbd_work"      =c(      "Work", 5, 470, 475),
                   "cbd_university"=c("University", 5, 470, 475),
                   "cbd_school"    =c(    "School", 5, 470, 475),
                   "cbd_escort"    =c(    "Escort", 5, 470, 475),
                   "cbd_shopping"  =c(  "Shopping", 5, 470, 475),
                   "cbd_eatout"    =c(    "EatOut", 5, 470, 475),
                   "cbd_othmaint"  =c(  "OthMaint", 5, 470, 475),
                   "cbd_social"    =c(    "Social", 5, 470, 475),
                   "cbd_othdiscr"  =c(  "OthDiscr", 5, 470, 475),
                   "cbd_workbased" =c( "WorkBased", 5, 473, 478))

  CONFIG <- list(CALIB_WORKBOOK, COPY_SRC, COPY_DST)
  
} else if (SUBMODEL=="TripModeChoice") {

  CALIB_WORKBOOK <- file.path(CALIB_DIR, "15 Trip Mode Choice", "15_TripModeChoice.xlsx")
  UEC_SRC_WORKBOOK <- file.path(UEC_DIR, "TM1.5.1 version", "TripModeChoice_TM1.5.1.xls")

  # sheet, column, startRow, endRow
  COPY_SRC <- list("work"      =c( "constants", 7,   3,  36),
                   "university"=c( "constants",15,   3,  36),
                   "school"    =c( "constants",23,   3,  36),
                   "escort"    =c( "constants",31,   3,  36), # indiv maint, indiv
                   "shopping"  =c( "constants",31,   3,  62), # indiv maint, joint
                   "eatout"    =c( "constants",39,   3,  62), # indiv disc, joint
                   "othmaint"  =c( "constants",31,   3,  62), # indiv maint, joint
                   "social"    =c( "constants",39,   3,  62), # indiv disc, joint
                   "othdiscr"  =c( "constants",39,   3,  62), # indiv disc
                   "workbased" =c( "constants",47,   3,  36)) # at work

  COPY_DST <- list("work"      =c(      "Work", 5, 509, 542),
                   "university"=c("University", 5, 512, 545),
                   "school"    =c(    "School", 5, 512, 545),
                   "escort"    =c(    "Escort", 5, 512, 545),
                   "shopping"  =c(  "Shopping", 5, 512, 571),
                   "eatout"    =c(    "EatOut", 5, 512, 571),
                   "othmaint"  =c(  "OthMaint", 5, 512, 571),
                   "social"    =c(    "Social", 5, 512, 571),
                   "othdiscr"  =c(  "OthDiscr", 5, 512, 571),
                   "workbased" =c( "WorkBased", 5, 511, 544))

  CONFIG <- list(CALIB_WORKBOOK, COPY_SRC, COPY_DST)

} else {
  stop(paste0("Don't understand SUBMODEL [",SUBMODEL,"]"))
}

# CONFIG should be in sets of three -- calib workbook, copy_src, copy_dst
if (length(CONFIG) %% 3 != 0) {
  stop(paste0("Don't understand CONFIG length ",length(CONFIG)))
}

# open the UEC SRC
uec_workbook <- loadWorkbook(file=UEC_SRC_WORKBOOK)
uec_sheets   <- getSheets(uec_workbook)
print(paste0("UEC_SRC_WORKBOOK = ",UEC_SRC_WORKBOOK))

UEC_DST_WORKBOOK <- gsub("TM1.0 version/","",UEC_SRC_WORKBOOK)
UEC_DST_WORKBOOK <- gsub("TM1.5.1 version/","",UEC_SRC_WORKBOOK)
UEC_DST_WORKBOOK <- gsub("_TM1.5.1","",UEC_DST_WORKBOOK)
UEC_DST_WORKBOOK <- gsub("_TM1","",UEC_DST_WORKBOOK)
print(paste0("UEC_DST_WORKBOOK = ",UEC_DST_WORKBOOK))

for (config_num in seq(length(CONFIG)/3)) {
  CALIB_WORKBOOK <- CONFIG[[3*(config_num-1)+1]]
  COPY_SRC       <- CONFIG[[3*(config_num-1)+2]]
  COPY_DST       <- CONFIG[[3*(config_num-1)+3]]
  
  # use the right version
  CALIB_WORKBOOK <- gsub(".xlsx",paste0("_",VERSION,".xlsx"),CALIB_WORKBOOK)


  print("-----------------------------------------------")
  print(paste0("CALIB_WORKBOOK   = ",CALIB_WORKBOOK))

  # open the calibration workbook
  calib_workbook <- loadWorkbook(file=CALIB_WORKBOOK)
  calib_sheets   <- getSheets(calib_workbook)

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
    # error out if any NA
    if (any(is.na(data))) {
      stop("Data contains NA")
    }
  
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
      cell_after_last_val <- NA
      if (is.null(cell_after_last)) {
        print(paste0("Cell after last is null"))
      } else {
        cell_after_last_val <- getCellValue(cell_after_last[[1]])
        print(paste0("Cell after last: ",cell_after_last_val))
      }

      addDataFrame(data, sheet=uec_sheet, col.names=FALSE, row.names=FALSE,
                   startRow=uec_start_row, startColumn=uec_column)

      # put this back if it's not na
      if (!is.na(cell_after_last_val)) {
        setCellValue(cell_after_last[[1]], cell_after_last_val)
      }
    }
  }

  CALIB_WORKBOOK_NO_VERS <- gsub(paste0("_",VERSION,".xlsx"),".xlsx",basename(CALIB_WORKBOOK))
  print(paste("Copying",CALIB_WORKBOOK,"to",file.path(BOX_DIR, CALIB_WORKBOOK_NO_VERS)))
  file.copy(from=CALIB_WORKBOOK, to=file.path(BOX_DIR, CALIB_WORKBOOK_NO_VERS), overwrite=TRUE, copy.date=TRUE)
}

saveWorkbook(uec_workbook, UEC_DST_WORKBOOK)
#forceFormulaRefresh(WORKBOOK_TEMP, WORKBOOK, verbose=TRUE)
print(paste("Wrote",UEC_DST_WORKBOOK))

