library(dplyr)
library(tidyr)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
OUTPUT_DIR   <- file.path(TARGET_DIR, "OUTPUT", "calibration")
if (!file.exists(OUTPUT_DIR)) { dir.create(OUTPUT_DIR) }

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

SAMPLESHARE <- as.numeric(SAMPLESHARE)

cat("TARGET_DIR  = ",TARGET_DIR, "\n")
cat("ITER        = ",ITER,       "\n")
cat("SAMPLESHARE = ",SAMPLESHARE,"\n")

######### counties
LOOKUP_COUNTY        <- data.frame(COUNTY=c(1,2,3,4,5,6,7,8,9),
                                   county_name=c("San Francisco","San Mateo","Santa Clara","Alameda",
                                                 "Contra Costa","Solano","Napa","Sonoma","Marin"))
LOOKUP_COUNTY$COUNTY      <- as.integer(LOOKUP_COUNTY$COUNTY)
LOOKUP_COUNTY$county_name <- as.character(LOOKUP_COUNTY$county_name)



input.pop.households <- read.table(file = file.path(TARGET_DIR,"INPUT","popsyn","hhFile.calib.2015.csv"),
                                   header=TRUE, sep=",") %>% select(HHID, TAZ, PERSONS)

tazData              <- read.table(file=file.path(TARGET_DIR,"INPUT","landuse","tazData.csv"), header=TRUE, sep=",")

ao_results           <- read.table(file=file.path(TARGET_DIR,"OUTPUT","main","aoResults.csv"), header=TRUE, sep=",")

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
write.table(ao_county_spread, file.path(OUTPUT_DIR,"02_auto_ownership_TM.csv"), sep=",", row.names=FALSE)
cat("Wrote ",file.path(OUTPUT_DIR,"02_auto_ownership_TM.csv\n"))
