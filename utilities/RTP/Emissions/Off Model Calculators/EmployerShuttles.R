#
# This R script distills the model outputs into the versions used by ICF calculator: "Employer Shuttles v2.xlsx"
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
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         FinalBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         EIR           ="M:/Application/Model One/RTP2021/Blueprint",
                         TRR           ="L:/Application/Model_One/TransitRecovery")
MODEL_RUNS_FILE     <- args[1]
OUTPUT_DIR          <- args[2]
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - Employer Shuttles.csv")

# this is the currently running script
SCRIPT              <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/EmployerShuttles.R"
model_runs          <- read_excel(MODEL_RUNS_FILE)

# filter to the current runs
model_runs          <- model_runs[ which((model_runs$status == "current") | (model_runs$status == "DEIR")), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

#### Mode look-up table
LOOKUP_MODE <- data.frame(trip_mode = c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21),
                          mode_name = c("Drive alone - free", "Drive alone - pay", 
                                        "Shared ride two - free", "Shared ride two - pay",
                                        "Shared ride three - free", "Shared ride three - pay",
                                        "Walk", "Bike",
                                        "Walk  to local bus", "Walk to light rail or ferry", "Walk to express bus", 
                                        "Walk to heavy rail", "Walk to commuter rail",
                                        "Drive  to local bus", "Drive to light rail or ferry", "Drive to express bus", 
                                        "Drive to heavy rail", "Drive to commuter rail",
                                        "Taxi", "TNC", "TNC shared"))
SAMPLING_RATE = 0.500

# read taz/SD lookup
taz_SD_df <- read.table(file = "X:/travel-model-one-master/utilities/geographies/taz-superdistrict-county.csv", header=TRUE, sep=",")

# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  # We don't need past years for Employer Shuttles
  if (model_runs[[i,"year"]]<=2015) next

  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[[i,"run_set"]]]
  trips_file <- file.path(MODEL_DATA_BASE_DIR, model_runs[[i,"directory"]], "OUTPUT", "updated_output", "trips.rdata")

  print(paste("Reading trips from",trips_file))

  # load trips
  load(trips_file)
  # drop unneeded columns
  trips <- select(trips, hh_id, tour_purpose, distance, trip_mode, orig_taz, dest_taz)

  # add origin SD and destination SD
  trips <- left_join(trips, select(taz_SD_df, ZONE, SD) %>% rename(orig_taz=ZONE, orig_sd=SD))
  trips <- left_join(trips, select(taz_SD_df, ZONE, SD) %>% rename(dest_taz=ZONE, dest_sd=SD))

  # filter to distance > 30.0
  trips <- filter(trips, distance>30.0)
  # filter to work trips
  trips <- filter(trips, substr(tour_purpose,1,5)=="work_")

  # summarize
  trips <- group_by(trips, trip_mode, tour_purpose, orig_sd, dest_sd) %>%
    summarize(simulated_trips = n(), mean_distance = mean(distance))
  trips <- left_join(trips, LOOKUP_MODE, by = c("trip_mode"))
  trips <- mutate(trips, estimated_trips = simulated_trips / SAMPLING_RATE) %>%
    select(trip_mode, mode_name, tour_purpose, orig_sd, dest_sd, simulated_trips, estimated_trips, mean_distance)
  
  trips <- trips %>%
    mutate(year      = model_runs[[i,"year"]],
           directory = model_runs[[i,"directory"]],
           category  = model_runs[[i,"category"]])

  if (nrow(tripdist_df) == 0) {
    tripdist_df <- trips
  } else {
    tripdist_df <- bind_rows(tripdist_df, trips)
  }
}
remove(i, trips)
# print(head(tripdist_df))
#        trip_mode                    mode_name    tour_purpose orig_sd dest_sd simulated_trips estimated_trips mean_distance year                      directory   category
# 1              1           Drive alone - free atwork_business       1       1             643            1286     1.2962208 2035              2035_TM152_IPA_01         IP
# 2              1           Drive alone - free atwork_business       1       2             255             510     2.9464314 2035              2035_TM152_IPA_01         IP
# 3              1           Drive alone - free atwork_business       1       3             533            1066     3.6807505 2035              2035_TM152_IPA_01         IP
# 4              1           Drive alone - free atwork_business       1       4              41              82     7.4807317 2035              2035_TM152_IPA_01         IP
# 5              1           Drive alone - free atwork_business       1       5             141             282    12.4274468 2035              2035_TM152_IPA_01         IP
# 6              1           Drive alone - free atwork_business       1       6              12              24    22.0958333 2035              2035_TM152_IPA_01         IP

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
                      total_distance  = estimated_trips*mean_distance)

# summarise to mode
summary_mode_df <- summarise(group_by(tripdist_df, year, category, directory, simple_mode),
                            estimated_trips = sum(estimated_trips))
summary_all_df <- summarise(group_by(tripdist_df, year, category, directory),
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