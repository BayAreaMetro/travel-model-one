#
# This R script distills the model outputs into the versions used by ICF calculator: "CBO v2.xlsx"
#

library(dplyr)
library(reshape2)
options(width = 180)

USERNAME            <- Sys.getenv("USERNAME")
BOX_BASE_DIR        <- file.path("C:/Users", USERNAME, "Box/Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation")
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         FinalBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         EIR           ="M:/Application/Model One/RTP2021/Blueprint")
OUTPUT_DIR          <- file.path(BOX_BASE_DIR, "Final Blueprint/OffModel_FBP/ModelData")
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - CBO.csv")

# this is the currently running script
SCRIPT                <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/deprecated/CBO.R"

# the model runs are RTP/ModelRuns.csv
model_runs          <- read.table(file.path(dirname(SCRIPT),"..","..","..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# filter to the current runs
model_runs          <- model_runs[ which((model_runs$status == "current") | (model_runs$status == "DEIR")), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# want:
# Total employment by superdistrict

# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY","TOTEMP") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
  if (model_runs[i,"directory"]=="2015_UrbanSim_FBP") next

  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
  tazdata_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"INPUT","landuse","tazData.csv")
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
# print(summary_melted_df)

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)
