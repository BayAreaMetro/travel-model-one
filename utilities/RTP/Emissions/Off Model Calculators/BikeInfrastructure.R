#
# This R script distills the model outputs into the versions used by ICF calculator: "Bike Infrastructure.xlsx"
#

library(dplyr)
library(reshape2)
options(width = 180)

USERNAME            <- Sys.getenv("USERNAME")
BOX_BASE_DIR        <- file.path("C:/Users", USERNAME, "Box/Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation")
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint")
OUTPUT_DIR          <- file.path(BOX_BASE_DIR, "Draft Blueprint/ModelData")
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - Bike Infrastructure.csv")

# this is the currently running script
SCRIPT              <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/BikeInfrastructure.R"
# the model runs are RTP/ModelRuns.csv
model_runs          <- read.table(file.path(dirname(SCRIPT),"..","..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# filter to the current runs
model_runs          <- model_runs[ which(model_runs$status == "current"), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY","TOTPOP","TOTACRE") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
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

# summarise population by superdistrict
tazdata_sd_df  <- summarise(group_by(tazdata_df, year, category, directory, SD, COUNTY),
                           total_population = sum(TOTPOP),
                           total_square_miles = sum(TOTACRE)/640.0)
tazdata_all_df <- summarise(group_by(tazdata_df, year, category, directory),
                            total_population = sum(TOTPOP),
                            total_square_miles = sum(TOTACRE)/640.0) %>%
  mutate(SD=0, COUNTY=0)

tazdata_sd_df <- rbind(tazdata_sd_df, tazdata_all_df)

# incorporate county population
tazdata_county_df <- summarise(group_by(tazdata_df, year, category, directory, COUNTY),
                               total_population_county = sum(TOTPOP))

# summarise at superdistrict level
tazdata_sd_df <- left_join(tazdata_sd_df,
                           tazdata_county_df,
                           by=c("year","category","directory","COUNTY")) %>%
  mutate(population_county_share = total_population/total_population_county)
remove(tazdata_county_df)


# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
  tripdist_file       <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","bespoke","trip-distance-by-mode-superdistrict.csv")
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

# For Bike Infrastructure, calculate bike and SOV trip mode share, and average bike trip distance
tripdist_df <- mutate(tripdist_df,
                      bike_trips = estimated_trips*(mode_name=="Bike"),
                      bike_dist  = estimated_trips*(mode_name=="Bike")*mean_distance,
                      sov_trips  = estimated_trips*(substr(mode_name,1,11)=="Drive alone"))

# summarise at superdistrict level
tripdist_sd_summary_df <- summarize(group_by(tripdist_df, year, category, directory, dest_sd),
                                    bike_trips      = sum(bike_trips),
                                    bike_dist       = sum(bike_dist),
                                    sov_trips       = sum(sov_trips),
                                    estimated_trips = sum(estimated_trips)) %>%
  mutate(bike_trip_mode_share = bike_trips/estimated_trips,
         bike_avg_trip_dist   = bike_dist/bike_trips,
         sov_trip_mode_share  = sov_trips/estimated_trips)

# and overall
tripdist_all_summary_df <- summarize(group_by(tripdist_df, year, category, directory),
                                     bike_trips      = sum(bike_trips),
                                     bike_dist       = sum(bike_dist),
                                     sov_trips       = sum(sov_trips),
                                     estimated_trips = sum(estimated_trips)) %>%
  mutate(bike_trip_mode_share = bike_trips/estimated_trips,
         bike_avg_trip_dist   = bike_dist/bike_trips,
         sov_trip_mode_share  = sov_trips/estimated_trips,
         dest_sd              = 0)

tripdist_sd_summary_df <- rbind(tripdist_sd_summary_df, tripdist_all_summary_df)

# select out needed fields of tazdata and tripdist table and put them together
summary_df <- left_join(tazdata_sd_df,
                        tripdist_sd_summary_df,
                        by=c("year","directory","category","SD"="dest_sd")) %>%
  rename(superdistrict=SD) %>%
  select(-bike_trips, -sov_trips, -COUNTY) # these were just intermediate


# columns are: year, category, directory, superdistrict, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory","superdistrict"))

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