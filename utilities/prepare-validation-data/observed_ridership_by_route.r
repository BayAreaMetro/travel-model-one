# -----------------------------------------------------------------------------------------------
#
# A very simple script to output observed ridership by route from the consolidated onboard survey
#
# -----------------------------------------------------------------------------------------------

library(dplyr)

setwd("L:/Application/Model_One/NextGenFwys/2015_TM152_NGF_01/OUTPUT/validation/explore_consolidated_onboard_survey")


F_INPUT_SURVEY_DIR         = "M:/Data/OnBoard/Data and Reports/_data Standardized/share_data/model_version"
F_INPUT_CONSOLIDATED_RDATA = file.path(F_INPUT_SURVEY_DIR, "TPS_Model_Version_PopulationSim_Weights2021-09-02.Rdata")

load(F_INPUT_CONSOLIDATED_RDATA)

# look at the weight variables
grep('weight', names(TPS), ignore.case=TRUE, value=TRUE)

RidershipByRoute_df <- TPS %>%
   group_by(survey_year, operator, route) %>%
   summarise(observed_boardings = sum(final_boardWeight_2015))

write.csv(RidershipByRoute_df, "ridership_by_route.csv")

