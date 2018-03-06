#
# This R script distills the model outputs into the versions used by ICF calculator: "Smart Driving v2.xlsx"
#

library(dplyr)
library(reshape2)

MODEL_DATA_BASE_DIR <-"M:/Application/Model One/RTP2017/Scenarios"
OUTPUT_FILE         <-"C:/Users/lzorn/Box/ICF Calculators/Model Data/Model Data - Smart Driving.csv"

# this is the currently running script
SCRIPT                <- (function() {attr(body(sys.function()), "srcfile")})()$filename
SCRIPT                <- normalizePath(SCRIPT)
# the model runs are in the parent folder
model_runs            <- read.table(file.path(dirname(SCRIPT),"..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# want:
# - average distance of drive alone shopping trip
# - total daily VMT
# - total number of autos

# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  # We don't need past years for Smart Driving
  if (model_runs[i,"category"]=="Past year") next
  
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

# drive alone shopping and auto VMT
tripdist_df <- mutate(tripdist_df,
                      sov_shopping_trips = estimated_trips*(substr(mode_name,1,11)=="Drive alone")*(tour_purpose=="shopping"),
                      sov_shopping_dist  = estimated_trips*(substr(mode_name,1,11)=="Drive alone")*(tour_purpose=="shopping")*mean_distance,
                      auto_dist          = estimated_trips*((substr(mode_name,1,11)=="Drive alone")|
                                                            (substr(mode_name,1,11)=="Shared ride"))*mean_distance)

summary_df <- summarise(group_by(tripdist_df, year, category, directory),
                        sov_shopping_trips = sum(sov_shopping_trips),
                        sov_shopping_dist  = sum(sov_shopping_dist),
                        auto_dist          = sum(auto_dist)) %>%
  mutate(sov_shopping_avg_dist = sov_shopping_dist/sov_shopping_trips) %>%
  select(-sov_shopping_dist, -sov_shopping_trips)

# Read auto ownership
auto_own_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  # We don't need past years for Smart Driving
  if (model_runs[i,"category"]=="Past year") next
  
  auto_own_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","core_summaries","AutomobileOwnership.csv")
  if (!file.exists(auto_own_file)) {
    stop(paste0("File [",auto_own_file,"] does not exist"))
  }
  auto_own_file_df <- read.table(auto_own_file, header=TRUE, sep=",", stringsAsFactors=FALSE) %>% 
    mutate(year      = model_runs[i,"year"],
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
  auto_own_df      <- rbind(auto_own_df, auto_own_file_df)
}
remove(i, auto_own_file, auto_own_file_df)

# sum total autos
auto_own_df <- mutate(auto_own_df, total_autos = freq*autos)
summary_auto_df <- summarise(group_by(auto_own_df, year, category, directory), total_autos = sum(total_autos))

# put summaries together and output
summary_df <- left_join(summary_df, summary_auto_df)

# columns are: year, category, directory, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory"))

# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","variable","value")]

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)