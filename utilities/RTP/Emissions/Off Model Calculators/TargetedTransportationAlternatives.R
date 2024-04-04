#
# This R script distills the model outputs into the versions used by ICF calculator: "Targeted Transportation Alternatives v4.xlsx"
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
OUTPUT_FILE         <-file.path(OUTPUT_DIR, "Model Data - Targeted Transportation Alternatives.csv")

# this is the currently running script
SCRIPT              <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/TargetedTransportationAlternatives.R"
model_runs          <- read_excel(MODEL_RUNS_FILE)

# filter to the current runs
model_runs          <- model_runs[ which((model_runs$status == "current") | (model_runs$status == "DEIR")), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)


# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY", "TOTEMP", "TOTHH", "CIACRE", "AREATYPE") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
  if (model_runs[[i,"directory"]]=="2015_UrbanSim_FBP") { next }
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[[i,"run_set"]]]
  tazdata_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[[i,"directory"]],"INPUT","landuse","tazData.csv")
  tazdata_file_df <- read.table(tazdata_file, header=TRUE, sep=",")
  tazdata_file_df <- tazdata_file_df[, TAZDATA_FIELDS] %>%
    mutate(year      = model_runs[[i,"year"]],
           directory = model_runs[[i,"directory"]],
           category  = model_runs[[i,"category"]])
  tazdata_df      <- rbind(tazdata_df, tazdata_file_df)
}
remove(tazdata_file, tazdata_file_df)


# TAZ data rollups
tazdata_summary_df <- summarise(group_by(tazdata_df, year, category, directory),
                                total_households = sum(TOTHH),
                                total_jobs       = sum(TOTEMP))


# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  if (model_runs[[i,"directory"]]=="2015_UrbanSim_FBP") { next }
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[[i,"run_set"]]]
  tripdist_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[[i,"directory"]],"OUTPUT","bespoke","trip-distance-by-mode-superdistrict.csv")
  if (!file.exists(tripdist_file)) {
    stop(paste0("File [",tripdist_file,"] does not exist"))
  }
  tripdist_file_df <- read.table(tripdist_file, header=TRUE, sep=",") %>% 
    mutate(year      = model_runs[[i,"year"]],
           directory = model_runs[[i,"directory"]],
           category  = model_runs[[i,"category"]])
  tripdist_df      <- rbind(tripdist_df, tripdist_file_df)
}
remove(i, tripdist_file, tripdist_file_df)

# trip-distance-by-mode-superdistrict rollups
# tour_purpose and trip_mode coding: http://analytics.mtc.ca.gov/foswiki/Main/IndividualTrip
# QUESTION: why is commute (for Trip Caps v5) = work_ and school_grade?  why not school_high and university?
tripdist_df <- mutate(tripdist_df,
                      total_distance = mean_distance*estimated_trips,
                      work_trip      = substr(tour_purpose,1,5)=="work_",
                      drive_alone    = substr(mode_name,1,11)=="Drive alone") %>%
  mutate(total_distance_work_da  = total_distance*work_trip*drive_alone,
         estimated_trips_work_da = estimated_trips*work_trip*drive_alone)

tripdist_summary_df <- summarize(group_by(tripdist_df, year, category, directory),
                                 total_distance          = sum(total_distance),
                                 estimated_trips         = sum(estimated_trips),
                                 total_distance_work_da  = sum(total_distance_work_da),
                                 estimated_trips_work_da = sum(estimated_trips_work_da)) %>%
  mutate(avg_trip_length            = total_distance/estimated_trips,
         avg_trip_length_work_da    = total_distance_work_da/estimated_trips_work_da)

# Put them together
summary_df <- left_join(tazdata_summary_df, tripdist_summary_df)

# keep only the columns we want
summary_df <- summary_df[,c("year","category","directory",
                            "total_households","total_jobs","avg_trip_length","avg_trip_length_work_da")]

# columns are: year, category, directory, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","variable","value")]
# print(summary_melted_df)

# prepend note
prepend_note = paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)

