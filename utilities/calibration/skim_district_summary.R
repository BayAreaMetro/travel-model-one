library(dplyr)
library(tidyr)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
OUTPUT_DIR   <- file.path(TARGET_DIR, "OUTPUT", "skims")


stopifnot(nchar(TARGET_DIR  )>0)
cat("TARGET_DIR  = ",TARGET_DIR, "\n")

districts <- read.table(file=file.path("X:","travel-model-one-calibration","utilities","geographies","taz-superdistrict-county.csv"), 
                        header=TRUE, sep=",")


skim_tables <- data.frame()

for (skimtype in c("HWYSKMMD","TRNSKMMD_WLK_TRN_WLK")) {
  timeperiod = "MD"
  if (skimtype == "HWYSKMMD") {
    tables = c("DISTDA","TIMEDA")
  }
  else {
    tables = c("IVT","IWAIT","WACC","WEGR")
  }
  
  # read the skims and combine them into one table
  for (table in tables) {
    cat(paste0("Reading ",skimtype,"_",table,".csv\n"))
    skim_table <- read.table(file=file.path(TARGET_DIR, "OUTPUT", "skims", 
                                            paste0(skimtype,"_",table,".csv")),
                           header=FALSE, col.names=c("OTAZ","DTAZ","ones",table), sep=",") %>% 
      select(-ones) %>%
      mutate(timeperiod=timeperiod)
    
    if (nrow(skim_tables) == 0) {
      skim_tables <- skim_table
    } else {
      skim_tables <- full_join(skim_tables, skim_table)
    }
    cat(paste0("Have  ",nrow(skim_tables)," rows\n"))
  }
}

# join to district for origin and destination
skim_tables <- left_join(skim_tables, districts, by=c("OTAZ"="ZONE")) %>% 
  rename(OSD=SD, OCOUNTY=COUNTY, OSD_NAME=SD_NAME, OCOUNTY_NAME=COUNTY_NAME)
skim_tables <- left_join(skim_tables, districts, by=c("DTAZ"="ZONE")) %>% 
  rename(DSD=SD, DCOUNTY=COUNTY, DSD_NAME=SD_NAME, DCOUNTY_NAME=COUNTY_NAME)
cat(paste0("Have  ",nrow(skim_tables)," rows\n"))

# aggregate to districts
skim_tables_od <- group_by(skim_tables, 
                           OCOUNTY, OCOUNTY_NAME, OSD, OSD_NAME, 
                           DCOUNTY, DCOUNTY_NAME, DSD, DSD_NAME) %>% 
  summarise(DA_PATHS =sum(!is.na(DISTDA)),
            TIMEDA   =mean(TIMEDA, na.rm=TRUE),
            DISTDA   =mean(DISTDA, na.rm=TRUE),
            TRN_PATHS=sum(!is.na(IVT)),
            IVT      =mean(IVT, na.rm=TRUE),
            IWAIT    =mean(IWAIT, na.rm=TRUE),
            WACC     =mean(WACC, na.rm=TRUE),
            WEGR     =mean(WEGR, na.rm=TRUE))

skim_tables_od <- mutate(skim_tables_od, run=basename(TARGET_DIR))
write.table(skim_tables_od, file.path(OUTPUT_DIR, "skim_OD_districts.csv"), sep=",", row.names=FALSE)
