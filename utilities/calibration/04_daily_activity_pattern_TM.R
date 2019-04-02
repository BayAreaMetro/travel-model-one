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

print(paste0("TARGET_DIR  = ",TARGET_DIR ))
print(paste0("ITER        = ",ITER       ))
print(paste0("SAMPLESHARE = ",SAMPLESHARE))

cdap_results <- read.table(file=file.path(TARGET_DIR,"OUTPUT","main","cdapResults.csv"), header=TRUE, sep=",")

# summarize to (county, Auto Ownership)
cdap_ptype  <- group_by(cdap_results, PersonType, ActivityString) %>% summarise(num_pers=n())
# divide by SAMPLESHARE
cdap_ptype  <- mutate(cdap_ptype, num_pers=num_pers/SAMPLESHARE)

cdap_ptype_spread <- spread(cdap_ptype, key=ActivityString, value=num_pers)

# save it
outfile <- file.path(OUTPUT_DIR, paste0("04_daily_activity_pattern_TM.csv"))
write.table(cdap_ptype_spread, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))