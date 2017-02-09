
library(plyr)

#
# This R script opens the following csvs:
#
network_csv_files <- c("2015.csv",
                       "2040_694.csv",
                       "2040_690.csv",
                       "2040_691.csv",
                       "2040_693.csv",
                       "2040_696.csv")
# and left_joins them to the emissions rates in
emission_rates_file <- "EmissionRates.csv"
# where "Speed" is joined on int(CSPD[AM,MD,PM,EV,EA])

# and writes the file
OUTPUT_FILE <- "analysis_allscenarios_2040.csv"

# all files are expected to be here (note R's preference for slashes)
BASE_DIR <- "C:/Users/lzorn/Box Sync/CARE Communities"


# loop through each file
all_networks_df <- data.frame()
for (network_csv_file in network_csv_files) {
  # read the network file
  network_fullpath_file <- file.path(BASE_DIR, network_csv_file)
  cat(paste0("Reading [",network_fullpath_file,"]\n"))
  network_df <- read.table(network_fullpath_file, header=TRUE, sep=",")
  
  # note which file it came from
  network_df$scenario_str <- substr(network_csv_file,0,nchar(network_csv_file)-4)
  # add to all networks
  all_networks_df <- rbind(all_networks_df, network_df)
}

# read the emissions file
emission_fullpath_file <- file.path(BASE_DIR, emission_rates_file)
cat(paste0("Reading [",emission_fullpath_file,"]\n"))
emission_rates_df <- read.table(emission_fullpath_file, header=TRUE, sep=",")
emission_cols <- names(emission_rates_df)

# for each time period
TIMEPERIODS <- c("EA","AM","MD","PM","EV")
for (timeperiod in TIMEPERIODS) {

  # rename the emissions columns for this timeperiod
  emission_cols_tp <- emission_cols
  for (colnum in 1:length(emission_cols)) {
    if (emission_cols[colnum] == "Speed") {
      emission_cols_tp[colnum] = paste0("CSPD",timeperiod,"_int")
    } else {
      emission_cols_tp[colnum] = paste0(emission_cols[colnum]," ",timeperiod)
    }
  }
  emission_rates_tp_df <- emission_rates_df 
  names(emission_rates_tp_df) <- emission_cols_tp
  
  # create integerized cspd column
  cspd_float_col <- paste0("CSPD",timeperiod)
  cspd_int_col   <- paste0("CSPD",timeperiod,"_int")
  all_networks_df[[cspd_int_col]] <- trunc(all_networks_df[[cspd_float_col]])
  
  # join to emissions
  all_networks_df <- left_join(all_networks_df, emission_rates_tp_df)
}

# write the result
output_fullpath <- file.path(BASE_DIR, OUTPUT_FILE)
write.table(all_networks_df, output_fullpath, sep=",", row.names=FALSE)