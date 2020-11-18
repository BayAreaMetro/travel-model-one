#
# This R script distills the model outputs into the versions used by ICF calculator: "Employer Shuttles v2.xlsx"
#

library(dplyr)
library(reshape2)
options(width = 180)

USERNAME            <- Sys.getenv("USERNAME")
BOX_BASE_DIR        <- file.path("C:/Users", USERNAME, "Box/Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation")
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         FinalBlueprint="M:/Application/Model One/RTP2021/Blueprint")
OUTPUT_DIR          <- file.path(BOX_BASE_DIR, "Final Blueprint/OffModel_FBP/ModelData")
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - Employer Shuttles.csv")

# this is the currently running script
SCRIPT                <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/EmployerShuttles.R"
# the model runs are RTP/ModelRuns.csv
model_runs          <- read.table(file.path(dirname(SCRIPT),"..","..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# filter to the current runs
model_runs          <- model_runs[ which(model_runs$status == "current"), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  # We don't need past years for Employer Shuttles
  if (model_runs[i,"year"]<=2015) next
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
  
  tripdist_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","bespoke","trip-distance-by-mode-superdistrict.csv")
  if (!file.exists(tripdist_file)) {
    stop(paste0("File [",tripdist_file,"] does not exist"))
  }
  tripdist_file_df <- read.table(tripdist_file, header=TRUE, sep=",", stringsAsFactors=FALSE) %>% 
    mutate(year      = model_runs[i,"year"],
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
  tripdist_df      <- rbind(tripdist_df, tripdist_file_df)
}
remove(i, tripdist_file, tripdist_file_df)

simplified_mode <- data.frame(
  mode_name=c("Drive alone - free",       "Drive alone - pay",
              "Shared ride two - free",   "Shared ride two - pay",
              "Shared ride three - free", "Shared ride three - pay",
              "Walk",
              "Bike",
              "Walk  to local bus", "Walk to light rail or ferry", "Walk to express bus", "Walk to heavy rail", "Walk to commuter rail",
              "Drive  to local bus","Drive to light rail or ferry","Drive to express bus","Drive to heavy rail","Drive to commuter rail",
              "Taxi", "TNC", "TNC shared"),
  simple_mode=c("SOV",                    "SOV",
                "HOV",                    "HOV",
                "HOV 3.5",                "HOV 3.5",
                "Walk",
                "Bike",
                "Walk to transit", "Walk to transit", "Walk to transit", "Walk to transit", "Walk to transit",
                "Drive to transit","Drive to transit","Drive to transit","Drive to transit","Drive to transit",
                "Taxi/TNC", "Taxi/TNC", "Taxi/TNC"),
   stringsAsFactors = FALSE)

# add simplified mode and a couple other simple variables
tripdist_df <- left_join(tripdist_df, simplified_mode)

# add a couple other variables
tripdist_df <- mutate(tripdist_df,
                      work_purpose    = substr(tour_purpose,1,5)=="work_",
                      total_distance  = estimated_trips*mean_distance,
                      mean_dist_gt_30 = (mean_distance>30.0))


# filter to just trips to work with mean distance greater than 30 miles
long_work_tripdist_df <- tripdist_df[ (tripdist_df$work_purpose==TRUE)&(tripdist_df$mean_dist_gt_30==TRUE), ]

# summarise to mode
summary_mode_df <- summarise(group_by(long_work_tripdist_df, year, category, directory, simple_mode),
                            estimated_trips = sum(estimated_trips))
summary_all_df <- summarise(group_by(long_work_tripdist_df, year, category, directory),
                             all_mode_trips = sum(estimated_trips))

# join
summary_mode_df <- left_join(summary_mode_df, summary_all_df,
                             by=c("year","category","directory")) %>%
  mutate(mode_share = estimated_trips/all_mode_trips) %>% 
  select(-estimated_trips, -all_mode_trips) # we only need the mode share


# columns are: year, category, directory, simple_mode, variable, value
summary_melted_df <- melt(summary_mode_df, id.vars=c("year","category","directory","simple_mode"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",simple_mode,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","simple_mode","variable","value")]
# print(summary_melted_df)

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)