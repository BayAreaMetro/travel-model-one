#
# This R script distills the model outputs into the versions used by ICF calculator: "CBO v2.xlsx"
#

library(dplyr)
library(reshape2)

MODEL_DATA_BASE_DIR <-"M:/Application/Model One/RTP2017/Scenarios"
OUTPUT_FILE         <-"C:/Users/lzorn/Box Sync/ICF Calculators/Model Data/Model Data - CBO.csv"

# this is the currently running script
SCRIPT                <- (function() {attr(body(sys.function()), "srcfile")})()$filename
SCRIPT                <- normalizePath(SCRIPT)
# the model runs are in the parent folder
model_runs            <- read.table(file.path(dirname(SCRIPT),"..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# want:
# Total employment by superdistrict

# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY","TOTEMP") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
  tazdata_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","tazData.csv")
  tazdata_file_df <- read.table(tazdata_file, header=TRUE, sep=",")
  tazdata_file_df <- tazdata_file_df[, TAZDATA_FIELDS] %>%
    mutate(year      = model_runs[i,"year"],
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
  tazdata_df      <- rbind(tazdata_df, tazdata_file_df)
}
remove(i, tazdata_file, tazdata_file_df)

# summarize by superdistrict
tazdata_df <- rename(tazdata_df, superdistrict=SD)
summary_df <- summarise(group_by(tazdata_df, year, category, directory, superdistrict),
                        total_employment = sum(TOTEMP))

# columns are: year, category, directory, superdistrict, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory", "superdistrict"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",superdistrict,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","superdistrict","variable","value")]

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)
