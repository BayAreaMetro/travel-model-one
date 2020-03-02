#
# quick script to join logsums files
#
# Gets directories from COMBINED_DIR/ScenarioKey.csv
# Reads logsum files from within and joins (with labels derived from years)
# Outputs files with same names into COMBINED_DIR
#
library(dplyr)
library(stringr)
library(tidyr)

USAGE        <- "RScript joinLogsums.R"
COMBINED_DIR <- Sys.getenv("COMBINED_DIR")  # The location of the input files
COMBINED_DIR <- gsub("\\\\","/",COMBINED_DIR) # switch slashes around

worklogsum_joined <- data.frame()
shoplogsum_joined <- data.frame()

scenario_key <- read.table(file = file.path(COMBINED_DIR,"ScenarioKey.csv"), header=TRUE, sep=",")
scenario_key <- mutate(scenario_key, year=str_extract(Scenario, "\\d+"))
# print(scenario_key)

for (row in 1:nrow(scenario_key)) {
  label  <- scenario_key[row, "year"]
  in_dir <- scenario_key[row, "src"]

  print(paste("Processing",label,"from",in_dir))
  
  worklogsum_file <- file.path(in_dir, "OUTPUT", "logsums", "person_workDCLogsum.csv")
  shoplogsum_file <- file.path(in_dir, "OUTPUT", "logsums", "tour_shopDCLogsum.csv")
  
  worklogsum <- read.table(file = worklogsum_file, header=TRUE, sep=",")
  shoplogsum <- read.table(file = shoplogsum_file, header=TRUE, sep=",")
  
  # append label to last cols
  cols <- colnames(worklogsum)
  cols[length(cols)] <- paste(cols[length(cols)], label)
  colnames(worklogsum) <- cols

  cols <- colnames(shoplogsum)
  cols[length(cols)] <- paste(cols[length(cols)], label)
  colnames(shoplogsum) <- cols

  # join
  if (nrow(worklogsum_joined) == 0) {
    worklogsum_joined <- worklogsum
  } else {
    worklogsum_joined <- left_join(worklogsum_joined, worklogsum)
  }

  if (nrow(shoplogsum_joined) == 0) {
    shoplogsum_joined <- shoplogsum
  } else {
    shoplogsum_joined <- left_join(shoplogsum_joined, shoplogsum)
  }
}

worklogsum_file <- file.path(COMBINED_DIR, "person_workDCLogsum.csv")
shoplogsum_file <- file.path(COMBINED_DIR, "tour_shopDCLogsum.csv")

write.table(worklogsum_joined, worklogsum_file, sep=",", row.names=FALSE)
write.table(shoplogsum_joined, shoplogsum_file, sep=",", row.names=FALSE)
