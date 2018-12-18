########################################################################################
# AVs vs HVs ownership summary
########################################################################################
library(dplyr)

# Remove all files from the workspace
rm(list = ls())

# Read the household data file
# M:\Application\Model One\Mock Futures\AVs\run_car_own_only\2015_06_01_carownonly\householdData_3.csv
Hhld_file <-file.path("M:", "Application", "Model One", "Mock Futures", "AVs", "run_car_own_only", "2015_06_01_carownonly", "householdData_1.csv")
Hhld_df <-read.csv(file=Hhld_file, header=TRUE, sep=",")
Out_file <-file.path("M:", "Application", "Model One", "Mock Futures", "AVs", "run_car_own_only", "2015_06_01_carownonly", "carown_summary.csv")

Hhld_df$carown <- paste(Hhld_df$humanVehicles, "HV-", Hhld_df$autonomousVehicles, "AV", sep="")


Hhld_df <- Hhld_df %>%
	mutate(carown_labels = recode(carown,
                   "0HV-0AV" = "Alt01 0 car",
                   "1HV-0AV" = "Alt02 1 car - 1HV",
                   "0HV-1AV" = "Alt03 1 car - 1AV",
                   "2HV-0AV" = "Alt04 2 cars - 2HVs",
                   "0HV-2AV" = "Alt05 2 cars - 2AVs",
                   "1HV-1AV" = "Alt06 2 cars - 1HV1AV",
                   "3HV-0AV" = "Alt07 3 cars - 3HVs",
                   "0HV-3AV" = "Alt08 3 cars - 3AVs",
                   "2HV-1AV" = "Alt09 3 cars - 2HVs1AV",
                   "1HV-2AV" = "Alt10 3 cars - 1HV2AVs",
                   "4HV-0AV" = "Alt11 4 cars - 4HVs"))


carown_summary <- Hhld_df  %>%
               group_by(carown_labels) %>%
	       summarise(nhhld = n())


# write out the results
write.table(carown_summary, file=(Out_file), sep = ",", row.names=FALSE, col.names=TRUE)


