#
# This R script distills the model outputs into the versions used by ICF calculator: "Carshare v4.xlsx"
#
# Pass two arguments to the script:
# 1) ModelRuns.xlsx with runs to process and
# 2) Output directory
#

library(dplyr)
library(reshape2)
library(readxl)
options(width = 180)

args = commandArgs(trailingOnly=TRUE)
print(args)
if (length(args) != 2) {
  stop("Two arguments are required: ModelRuns.xlsx and output_dir")
}

MODEL_DATA_BASE_DIRS<- c(RTP2021_IP    ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         RTP2021       ="M:/Application/Model One/RTP2021/Blueprint",
                         RTP2025_IP    ="M:/Application/Model One/RTP2025/IncrementalProgress",
                         RTP2025       ="M:/Application/Model One/RTP2025/Blueprint",
                         TRR           ="L:/Application/Model_One/TransitRecovery")
MODEL_RUNS_FILE     <- args[1]
OUTPUT_DIR          <- args[2]
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - Carshare.csv")

# this is the currently running script
SCRIPT              <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/CarShare.R"
model_runs          <- read_excel(MODEL_RUNS_FILE)

# filter to the current runs
model_runs          <- model_runs[ which((model_runs$status == "current") | (model_runs$status == "DEIR")), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# Calculator constants
# Criteria for applying trip caps
K_MIN_POP_DENSITY  <- 10   # Minimum density needed to be considered "urban" and support dense carshare (persons/residential acre)

# want:
# Total population
# Total population in TAZs with density >10
# Total population in TAZs with density <10
# Adult pop (age 20-64) in TAZs with density >10
# Adult pop (age 20-64) in TAZs with density <10

# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY","TOTPOP","RESACRE","AGE2044","AGE4564") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
  # We don't need past years for Car Share
  if (model_runs[[i,"year"]]<=2015) next
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[[i,"run_set"]]]

  tazdata_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[[i,"directory"]],"INPUT","landuse","tazData.csv")
  tazdata_file_df <- read.table(tazdata_file, header=TRUE, sep=",")
  tazdata_file_df <- tazdata_file_df[, TAZDATA_FIELDS] %>%
    mutate(year      = model_runs[[i,"year"]],
           directory = model_runs[[i,"directory"]],
           category  = model_runs[[i,"category"]])
  tazdata_df      <- rbind(tazdata_df, tazdata_file_df)
}
remove(i, tazdata_file, tazdata_file_df)

# population per residential acre
tazdata_df <- mutate(tazdata_df,
                     totpop_per_resacre = ifelse(RESACRE==0,0,TOTPOP/RESACRE),
                     carshare_dense     = (totpop_per_resacre > K_MIN_POP_DENSITY),
                     totpop_dense       = TOTPOP*carshare_dense,
                     totpop_sparse      = TOTPOP*(!carshare_dense),
                     adultpop_dense     = (AGE2044+AGE4564)*carshare_dense,
                     adultpop_sparse    = (AGE2044+AGE4564)*(!carshare_dense))

summary_df <- summarise(group_by(tazdata_df, year, category, directory),
                        total_population = sum(TOTPOP),
                        totpop_dense     = sum(totpop_dense),
                        totpop_sparse    = sum(totpop_sparse),
                        adultpop_dense   = sum(adultpop_dense),
                        adultpop_sparse = sum(adultpop_sparse))
# columns are: year, category, directory, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","variable","value")]
#print(summary_melted_df)

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

prepend_note <- paste0("K_MIN_POP_DENSITY,"     ,K_MIN_POP_DENSITY)
write(prepend_note, file=OUTPUT_FILE, append=TRUE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)

