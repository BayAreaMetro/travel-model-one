# this script generates an output that is similar to the core summary output of CommuteByIncomeHousehold.csv, except that time period information is added
# ie. commute characteristics by household location. Sum(freq) = commute tours
# Input : updated_output\commute_tours.rdata
# Output: core_summaries\CommuteByIncomeByTPHousehold.csv


library(dplyr)

TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
UPDATED_DIR <- file.path(TARGET_DIR,"updated_output")
RESULTS_DIR <- file.path(TARGET_DIR,"core_summaries")

SAMPLESHARE <- 0.5

load(file=file.path(UPDATED_DIR,"commute_tours.rdata"))

commute_inc_timeCodeHwNum_summary_byres <- summarise(group_by(commute_tours, res_COUNTY, res_county_name, res_SD, orig_taz,
                                                tour_mode, incQ, incQ_label, timeCodeHwNum),
                                       freq         = n(),
                                       totCost      = mean(totCost, na.rm=TRUE),
                                       cost         = mean(cost,    na.rm=TRUE),
                                       parking_cost = mean(parking_cost),
                                       distance     = mean(distance),
                                       duration     = mean(time,    na.rm=TRUE),
                                       cost_fail    = sum(cost_fail),
                                       time_fail    = sum(time_fail))
commute_inc_timeCodeHwNum_summary_byres$freq <- commute_inc_timeCodeHwNum_summary_byres$freq / SAMPLESHARE
write.table(commute_inc_timeCodeHwNum_summary_byres, file.path(RESULTS_DIR,"CommuteByIncomeByTPHousehold.csv"), sep=",", row.names=FALSE)
print(paste("Wrote",prettyNum(nrow(commute_inc_timeCodeHwNum_summary_byres),big.mark=","),"rows of commute_inc_timeCodeHwNum_summary_byres"))

# a sample output is here:
# //MODEL2-D/Model2D-Share/Projects/2035_TM152_NGF_NP07_Path1b_01_LowestTolls03/core_summaries/CommuteByIncomeByTPHousehold.csv
