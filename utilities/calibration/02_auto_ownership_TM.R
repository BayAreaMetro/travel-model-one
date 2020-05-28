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

WORKBOOK       <- "M:\\Development\\Travel Model One\\Calibration\\Version 1.5.2\\02 Automobile Ownership\\02_AutoOwnership.xlsx"
WORKBOOK       <- gsub("\\\\","/",WORKBOOK  ) # switch slashes around
WORKBOOK_TEMP  <- gsub(".xlsx","_temp.xlsx", WORKBOOK)
WORKBOOK_BLANK <- file.path(CODE_DIR, "workbook_templates","02_AutoOwnership_blank.xlsx")
calib_workbook <- loadWorkbook(file=WORKBOOK_BLANK)
calib_sheets   <- getSheets(calib_workbook)

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

######### counties
LOOKUP_COUNTY        <- data.frame(COUNTY=c(1,2,3,4,5,6,7,8,9),
                                   county_name=c("San Francisco","San Mateo","Santa Clara","Alameda",
                                                 "Contra Costa","Solano","Napa","Sonoma","Marin"))
LOOKUP_COUNTY$COUNTY      <- as.integer(LOOKUP_COUNTY$COUNTY)
LOOKUP_COUNTY$county_name <- as.character(LOOKUP_COUNTY$county_name)



input.pop.households <- read.table(file = file.path(TARGET_DIR,"INPUT","popsyn","hhFile.2015.csv"),
                                   header=TRUE, sep=",") %>% select(HHID, TAZ, PERSONS)

tazData              <- read.table(file=file.path(TARGET_DIR,"INPUT","landuse","tazData.csv"), header=TRUE, sep=",")

ao_results           <- read.table(file=file.path(TARGET_DIR,paste0("OUTPUT_",CALIB_ITER),"main","aoResults.csv"), header=TRUE, sep=",")

# stopifnot(nrow(input.pop.households) == nrow(ao_results))

# add TAZ, PERSONS
ao_results <- left_join(ao_results, input.pop.households)
# add COUNTY
ao_results <- left_join(ao_results, rename(select(tazData, ZONE, COUNTY), TAZ=ZONE)) %>% left_join(LOOKUP_COUNTY)

# summarize to (county, Auto Ownership)
ao_county  <- group_by(ao_results, COUNTY, county_name, AO) %>% summarise(num_hh=n())
# divide by SAMPLESHARE
ao_county  <- mutate(ao_county, num_hh=num_hh/SAMPLESHARE)

ao_county_spread <- spread(ao_county, key=AO, value=num_hh)

# save it
outfile <- file.path(OUTPUT_DIR,"02_auto_ownership_TM.csv")
write.table(ao_county_spread, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))

# save it (along with source label) to calibration workbook
addDataFrame(as.data.frame(ao_county_spread), calib_sheets$modeldata, startRow=3, startColumn=1, row.names=FALSE)
source_cell <- getCells( getRows(calib_sheets$modeldata, rowIndex=1:1), colIndex=1:1 )
setCellValue(source_cell[[1]], paste("Source: ",outfile))

saveWorkbook(calib_workbook, WORKBOOK_TEMP)
forceFormulaRefresh(WORKBOOK_TEMP, WORKBOOK, verbose=TRUE)
print(paste("Wrote",WORKBOOK))

# summarize to (taz, Auto Ownership)
ao_taz <- group_by(ao_results, TAZ, AO) %>% summarize(num_hh=n())
# divide by SAMPLESHARE
ao_taz  <- mutate(ao_taz, num_hh=num_hh/SAMPLESHARE, source="Model") %>% 
  rename(num_vehicles=AO)

# save it
outfile <- file.path(OUTPUT_DIR,"02_auto_ownership_TAZ_TM_long.csv")
write.table(ao_taz, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))

ao_taz_spread <- spread(ao_taz, key=num_vehicles, value=num_hh)
outfile <- file.path(OUTPUT_DIR,"02_auto_ownership_TAZ_TM.csv")
write.table(ao_taz_spread, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))

# copy the observed ACS file here to union
file.copy("M:/Data/Census/ACS/ACS2013-2017/B08201 Household Size by Vehicles Available/vehiclesAvailableByTazACS_long.csv",
          file.path(OUTPUT_DIR, "02_auto_ownership_TAZ_ACS.csv"))