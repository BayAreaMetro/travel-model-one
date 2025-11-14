#############################################################
#
# transit validation
# summarize observed and modelled ridership by operator and technology
# using data from the consolidated onboard survey
#
# This script replaces \utilities\prepare-validation-data\Prepare Observed Transit Summaries.R which uses legacy onboard survey data
# (note that Prepare Observed Transit Summaries.R has been renamed to Prepare Observed Transit Summaries (using LEGACY DATA).R
#
#############################################################

library(dplyr)

##################
# Specify inputs
##################

# Run this from the [M_run_dir]\OUTPUT\validation\transit
# That is the working dir

# typically, users do not need to specify other input paths, as they do not change across model runs
# onboard survey data
F_INPUT_SURVEY_DIR         <- "M:/Data/OnBoard/Data and Reports/_data_Standardized/share_data/model_version"
F_INPUT_CONSOLIDATED_RDATA <- file.path(F_INPUT_SURVEY_DIR, "TPS_Model_Version_PopulationSim_Weights2021-09-02.Rdata")

# file specifying how the operators are grouped
ConsolidatedDB_OperatorGroups_CSV    <- "X:/travel-model-one-master/utilities/prepare-validation-data/ConsolidatedDB_OperatorGroups.csv"

# file with modelled boardings
trnline_CSV    <- file.path("..","..","trn","trnline.csv")

# file specifying how the transit modes in the model are grouped
TransitMode_OperatorGroups_CSV    <- "X:/travel-model-one-master/utilities/prepare-validation-data/TransitMode_OperatorGroups.csv"

##################
# Analyse observed data
##################
# Loads a data.frame named TPS with detailed Transit Passenger Survey data:
# operator, surey_year, SURVEY_MODE, access_mode, depart_hour, etc.
# These are individual survey records so it is large: 130k rows
load(F_INPUT_CONSOLIDATED_RDATA)
print(paste("TPS has",nrow(TPS),"rows with final_boardWeight_2015 total",sum(TPS$final_boardWeight_2015)))

# columns: operator_in_consolidated_database, operator_in_legacy_database, technology_6groups, operator_group
ConsolidatedDB_OperatorGroups_df <- read.csv(ConsolidatedDB_OperatorGroups_CSV, header=TRUE, sep=",")

# join TPS to add technology_6groups, operator_group
TPS_df <- left_join(TPS, ConsolidatedDB_OperatorGroups_df,
                    by=c("operator"="operator_in_consolidated_database"))

Observed_ByOperatorTech_df <- TPS_df %>%
   group_by(operator, operator_group, technology_6groups) %>%
   summarise(observed_boardings = sum(final_boardWeight_2015), .groups="keep")
print(paste("Observed_ByOperatorTech_df has",nrow(Observed_ByOperatorTech_df),
   "rows with final_boardWeight_2015 total",sum(Observed_ByOperatorTech_df$observed_boardings)))

# The "technology" variable in the consolidated database was not useful. Somehow there were lots of NA.
# For example, technology was NA for both SamTrans [EXPRESS] and SamTrans [LOCAL]

##################
# SamTrans Express Bus Observed Data Patch
##################
# Asana task: https://app.asana.com/0/1201809392759895/1202118527990873
# In 2015, SamTrans has only one express bus - the KX. It goes from Redwood City downtown to San Francisco downtown, and has only 4 runs in the mornings and 4 runs in the afternoon.
# The onboard survey data for SamTrans was from 2013
# Back in 2013, the KX was a very different service. It starts from Palo Alto Stanford Shopping Centre (instead of Redwood City downtown) and has runs through the day. So, the ridership of this line changed drastically.
# We contacted SamTrans about the KX and they us provided with average daily ridership data for the KX in 2015. The data was collected from GFI.
# The figure below represent the average daily riders on the KX in Oct 2015

# overwrite the SamTrans express bus observed_boardings value
Observed_ByOperatorTech_df$observed_boardings[ 
   (Observed_ByOperatorTech_df$operator_group=="SamTrans") &
   (Observed_ByOperatorTech_df$technology_6groups=="express bus")
] <- 146


##################
# AC Transit Observed Data Patch
##################
# Asana task: https://app.asana.com/0/1201809392759895/1202440674530061/f
# AC Transit shared the route-level automatic passenger counter (APC) data for 2015, so the validation table is patched to use the APC data.
# The AC Transit APC data are stored in: \Box\Modeling and Surveys\Share Data\Transit\AC Transit Ridership\Ending December 2015 Service Statistics.xls
# (Alternative file path: https://mtcdrive.app.box.com/folder/165188436123)

# Express bus is defined as routes labeled by AC Transit as "Transbay". 
# However, Dumbarton Express (DB and DB1) is not included in the APC data provided and its ridership has to come from the onboard survey.
# The express bus total in "Ending December 2015 Service Statistics.xls" is 18,344.
# From the onboard survey, the ridership for DB is 630 per day and that for DB1 is 748 per day.
# So, final express bus total = 18,344 + 630 + 748 = 19,722

# Local bus is defined as all other labels, although school routes are excluded.
# The total in "Ending December 2015 Service Statistics.xls" is 170,499.

# overwrite the AC Transit local bus and express bus with observed_boardings value
Observed_ByOperatorTech_df$observed_boardings[ 
   (Observed_ByOperatorTech_df$operator_group=="AC Transit") &
   (Observed_ByOperatorTech_df$technology_6groups=="local bus")
] <- 170499

# overwrite the AC Transit local bus and express bus with observed_boardings value
Observed_ByOperatorTech_df$observed_boardings[ 
   (Observed_ByOperatorTech_df$operator_group=="AC Transit") &
   (Observed_ByOperatorTech_df$technology_6groups=="express bus")
] <- 19722

# sort the data frame
Observed_ByOperatorTech_df <- arrange(
   Observed_ByOperatorTech_df,
   operator_group, 
   technology_6groups)

##################
# Analyse modeled data
##################
trnline_df <-  read.csv(trnline_CSV, header=TRUE, sep=",")

# columns: mode_code, operator_in_legacy_database, operator_in_consolidated_database, technology_6groups
# Note that a number of these have operator_in_consolidated_database = "NA" because they weren't surveyed in
# that database
TransitMode_OperatorGroups_df <- read.csv(TransitMode_OperatorGroups_CSV, header=TRUE, sep=",")

# add operator_in_legacy_database, operator_in_consolidated_database, technology_6groups,operator_group to trnline_df
trnline_df <- left_join(
   trnline_df, TransitMode_OperatorGroups_df,
   by=c("mode"="mode_code"))

# report which modelled operators are NA
print("trnline_df with NA operator_in_consolidated_database:")
Modelled_Lines_Not_In_Observed <- filter(trnline_df, is.na(operator_in_consolidated_database))
print(table(Modelled_Lines_Not_In_Observed$mode_name))

Modelled_ByOperatorTech_df <- trnline_df %>%
   group_by(operator_in_consolidated_database, operator_group, technology_6groups) %>%
   summarise(modelled_boardings = sum(total.boardings), .groups="keep")

##################
# Compare observed and modelled side-by-side  
##################
compare_df <- full_join(
   Observed_ByOperatorTech_df,
   Modelled_ByOperatorTech_df,
   by=c(
      "operator"="operator_in_consolidated_database",
      "operator_group",
      "technology_6groups")
)

# output the observed vs modelled table
OUTPUT_FILE <- file.path("ridership_observed_vs_modelled.csv")
write.csv(compare_df, OUTPUT_FILE, row.names = FALSE)
print(paste("Wrote", OUTPUT_FILE))
