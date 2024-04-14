# Calculate Safe1 metrics -- fatalities and injuries -- from MTC model outputs
#
# Pass two arguments to the script:
# 1) Project (one of NGF, PBA50 or PBA50+)
# 2) MODEL_RUN_ID_NO_PROjeCT
# 3) MODEL_RUN_ID_SCENARIO
#
# For no project only, you can pass MODEL_RUN_ID_SCENARIO == MODEL_RUN_ID_NO_PROjeCT.
#
#
# This script implements two corrections to the fatalities and injuries as they were originally calculated (in this same directory):
# 1) General correction: this is based on the difference between the modeled fatalites/injuries (which is itself based on VMT by facilty type and area type)
#    to determine factors to make the 2015 modeled fatalies and injuries match the observed.
# 
# 2) The second correction is to account for reduced speeds, and it applies a correction based on literature to decrease
#    fatality and injury rates.  This correction is based upon:
#    
#       The Power Model of the relationship between speed and road safety
#       a report from the Institute of Transport Economics (TOI) by Run Elvik from October 2009
#       https://www.toi.no/getfile.php?mmfileid=13206
#
#    This report is also discussed in the US Federal Highway Administration Report:
#       Self-Enforcing Roadways: A Guidance Report (Publication Number: FHWA-HRT-17-098, Date: January 2018)
#       Chapter 2. Relationship between Speed and Safety
#       https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm
#
#    Documentation on how this speed correction factor was applied for Plan Bay Area 2050 can be found on page 49 of the 
#       Plan Bay Area 2050 Performance Report (October 2021)
#       https://www.planbayarea.org/sites/default/files/documents/Plan_Bay_Area_2050_Performance_Report_October_2021.pdf
# 
# Script history:
#   - The original R script was created by Raleigh and used for PBA50.
#     Source: https://mtcdrive.box.com/s/nzm9twmohfblc35vddlnv9wd6zw04zdv.
# 
# In the Next Generation Freeway project, script was updated to
# - split fatalities and injuries by facility type (freeway and non-freeway)
# - split fatalities and injuries by geography (Equity Priority Communities (EPCs) and non-EPCs)
# - split fatalities and injuries by geography and faclity type (local streets in Equity Priority Communities (EPCs) and local streets in non-EPCs): 
#   https://app.asana.com/0/0/1204858461227642/f
# 
# Inputs:
#   1) TAZ_EPC_LOOKUP: 
#       For NGF: X:\travel-model-one-master\utilities\NextGenFwys\metrics\Input Files\taz_epc_crosswalk.csv
#       For PBA50: M:\Application\Model One\RTP2021\Blueprint\INPUT_DEVELOPMENT\metrics\metrics_FinalBlueprint\CommunitiesOfConcern.csv
#       For PBA50+: M:\Application\Model One\RTP2025\INPUT_DEVELOPMENT\metrics\metrics_01\taz1454_epcPBA50plus_2024_02_23.csv"
#   3) For base year and forecast year
#      a) INPUT\landuse\tazData.csv - for population
#      b) OUTPUT\avgload5period.csv - for loaded network VMT
#      c) OUTPUT\shapefile\network_links_TAZ.csv - used with TAZ_EPC_LOOKUP associate links to EPC
#         This is not used for base year.  Use cube-to-shapefile\correspond_link_to_TAZ.py to generate this
#   4) Additionally, for the base year, the observed values. See observed_fatalities_injuries()
#
#  Output files:
#   1) results:  MODEL_RUN_ID\OUTPUT\metrics\fatalies_injuries.csv
#   2) log file: MODEL_RUN_ID\OUTPUT\metrics\fatalies_injuries.log
# 

library(dplyr)
library(tidyr)
library(stringr)
library(readxl)

options(
  scipen=999, # disable sci notation
  width=150,
  pillar.print_max=50,
  dplyr.print_max=50,
  tibble.print_max=50,
  pillar.sigfig = 6
)

args = commandArgs(trailingOnly=TRUE)
if (length(args) != 3) {
  stop("Three arguments are required: PROJECT (NGF, PBA50 or PBA50+), MODEL_RUN_ID_NO_PROjeCT and MODEL_RUN_ID_SCENARIO")
}
PROJECT                 <- args[1]
MODEL_RUN_ID_NO_PROjeCT <- args[2]
MODEL_RUN_ID_SCENARIO   <- args[3]
FORECAST_YEAR           <- strtoi(substr(MODEL_RUN_ID_SCENARIO, start=1, stop=4))

# PROJECT must be one of NGF or PBA50+
stopifnot(PROJECT %in% list("NGF","PBA50","PBA50+"))

if (PROJECT == "NGF") {
  ##################################### NextGen Fwy settings #####################################
  TAZ_EPC_FILE <- "X:/travel-model-one-master/utilities/NextGenFwys/metrics/Input Files/taz_epc_crosswalk.csv"

  # Scenario Directory on L or M
  PROJECT_SCENARIOS_DIR     <- "L:/Application/Model_One/NextGenFwys/Scenarios"

  # BASE YEAR -- required for 1) General correction
  BASE_YEAR                 <- 2015
  MODEL_RUN_ID_BASE_YEAR    <- "2015_TM152_NGF_05"
  MODEL_FULL_DIR_BASE_YEAR  <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
}
if (PROJECT == "PBA50") {
  ##################################### PBA50 settings #####################################
  # to replicate PBA50 results (without corrections updates)
  TAZ_EPC_FILE <- "M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/metrics/metrics_FinalBlueprint/CommunitiesOfConcern.csv"

  # Scenario Directory on L or M
  PROJECT_SCENARIOS_DIR     <- "M:/Application/Model One/RTP2021/Blueprint"

  # BASE YEAR -- required for 1) General correction
  BASE_YEAR                 <- 2015
  MODEL_RUN_ID_BASE_YEAR    <- "2015_TM152_IPA_17"

  # IPA runs
  if (str_detect(MODEL_RUN_ID_SCENARIO, "IPA")) {
    PROJECT_SCENARIOS_DIR     <- str_replace(PROJECT_SCENARIOS_DIR, "Blueprint", "IncrementalProgress")
    MODEL_FULL_DIR_BASE_YEAR  <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
  }
  # for other runs, the base year is still in IncrementalProgress
  else {
    MODEL_FULL_DIR_BASE_YEAR  <- file.path(
      str_replace(PROJECT_SCENARIOS_DIR, "Blueprint","IncrementalProgress"),
      MODEL_RUN_ID_BASE_YEAR)
  }
}
if (PROJECT == "PBA50+") {
  ##################################### PBA50+ settings #####################################
  TAZ_EPC_FILE <- "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/metrics/metrics_01/taz1454_epcPBA50plus_2024_02_23.csv"

  # Scenario Directory on L or M
  PROJECT_SCENARIOS_DIR     <- "M:/Application/Model One/RTP2025/Blueprint"

  # BASE YEAR -- required for 1) General correction
  BASE_YEAR                 <- 2015
  MODEL_RUN_ID_BASE_YEAR    <- "2015_TM160_IPA_06"

  # IPA runs
  if (str_detect(MODEL_RUN_ID_SCENARIO, "IPA")) {
    PROJECT_SCENARIOS_DIR     <- str_replace(PROJECT_SCENARIOS_DIR, "Blueprint", "IncrementalProgress")
    MODEL_FULL_DIR_BASE_YEAR  <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_BASE_YEAR)
  }
  # for other runs, the base year is still in IncrementalProgress
  else {
    MODEL_FULL_DIR_BASE_YEAR  <- file.path(
      str_replace(PROJECT_SCENARIOS_DIR, "Blueprint","IncrementalProgress"),
      MODEL_RUN_ID_BASE_YEAR)
  }
}
COLLISION_RATES_EXCEL     <- "X:/travel-model-one-master/utilities/RTP/metrics/CollisionLookupFINAL.xlsx"
OUTPUT_FILE               <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries.csv")
LOG_FILE                  <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", "fatalities_injuries.log")

stopifnot(nchar(MODEL_RUN_ID_NO_PROjeCT)>0)
stopifnot(nchar(MODEL_RUN_ID_SCENARIO)>0)

print(paste("Writing to", LOG_FILE))

# Write to log file
sink(file=LOG_FILE, type=c("output","message"))

print(paste("This file is written by travel-model-one/utilities/RTP/metrics/VZ_safety_calc_correction_V2.R"))
print(paste("                  PROJECT:",PROJECT))
print(paste("             TAZ_EPC_FILE:",TAZ_EPC_FILE))
print(paste("    PROJECT_SCENARIOS_DIR:",PROJECT_SCENARIOS_DIR))
print(paste("                BASE_YEAR:",BASE_YEAR))
print(paste("   MODEL_RUN_ID_BASE_YEAR:",MODEL_RUN_ID_BASE_YEAR))
print(paste(" MODEL_FULL_DIR_BASE_YEAR:",MODEL_FULL_DIR_BASE_YEAR))
print(paste("            FORECAST_YEAR:",FORECAST_YEAR))
print(paste("  MODEL_RUN_ID_NO_PROjeCT:",MODEL_RUN_ID_NO_PROjeCT))
print(paste("    MODEL_RUN_ID_SCENARIO:",MODEL_RUN_ID_SCENARIO))

# assumptions
# TODO: why 300?
N_days_per_year = 300 # assume 300 days per year (outputs are for one day)

ONE_HUNDRED_THOUSAND = 100000
ONE_MILLION          = 1000000
ONE_HUNDRED_MILLION  = 100000000
print(paste("     ONE_HUNDRED_THOUSAND:", format(ONE_HUNDRED_THOUSAND, big.mark=",")))
print(paste("              ONE_MILLION:", format(ONE_MILLION, big.mark=",")))
print(paste("      ONE_HUNDRED_MILLION:", format(ONE_HUNDRED_MILLION, big.mark=",")))

# collision look up table: see the full research here: https://mtcdrive.box.com/s/vww1t4g169dv0f016f7o1k3qt1e32kx2
collision_rates_df = read_excel(COLLISION_RATES_EXCEL, sheet = "Lookup Table") %>%
  rename(
    ft_collision = ft,                # Aggregated: 2 = freeway, 3 = expressway, 4 = collector / arterial
    at_collision = at,                # Aggregated: 3 = urban, 4 = suburban and rural
    serious_injury_rate = a,          # Count per 1 million vehicle miles traveled
    fatality_rate = k,                # Count per 1 million vehicle miles traveled
    fatality_rate_ped = k_ped,        # Count per 1 million vehicle miles traveled
    fatality_rate_motorist = k_motor, # Count per 1 million vehicle miles traveled
    fatality_rate_bike = k_bike       # Count per 1 million vehicle miles traveled
  ) %>% select(ft_collision, at_collision, fatality_rate, serious_injury_rate, fatality_rate_motorist, fatality_rate_ped, fatality_rate_bike)
  print("head(collision_rates_df):")
  print(head(collision_rates_df))

COLLISION_FT <- data.frame(ft = integer(), fatality_exponent = numeric(), injury_exponent = numeric(), 
  fwy_non=character(), ft_collision = integer())
# Maps facility type (ft) to aggregate version used for collision lookup (ft_collision/)
# https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
# 
# Also maps to fwy or non_fwy for segmentation
# And fatality / injury exponents for speed corrections; see 2) in header description
#
#                       ft |fatality| injury | fwy_non  | ft_collision
#                          |exponent|exponent|          | (2 = freeway, 3 = expressway, 4 = collector / arterial)
COLLISION_FT[ 1,] <- c(  1,      4.6,     3.5, "fwy",      2)  # freeway-to-freeway connector
COLLISION_FT[ 2,] <- c(  2,      4.6,     3.5, "fwy",      2)  # freeway
COLLISION_FT[ 3,] <- c(  3,      4.6,     3.5, "non_fwy",  3)  # expressway
COLLISION_FT[ 4,] <- c(  4,      3.0,     2.0, "non_fwy",  4)  # collector
COLLISION_FT[ 5,] <- c(  5,      4.6,     3.5, "fwy",      2)  # freeway ramp
COLLISION_FT[ 6,] <- c(  6,        0,       0, "non_fwy", -1)  # dummy link
COLLISION_FT[ 7,] <- c(  7,      3.0,     2.0, "non_fwy",  4)  # major arterial
COLLISION_FT[ 8,] <- c(  8,      4.6,     3.5, "fwy",      2)  # managed freeway
COLLISION_FT[ 9,] <- c(  9,        0,       0, "non_fwy", -1)  # special facility -- what are these? omit for now
COLLISION_FT[10,] <- c( 10,        0,       0, "fwy",      2)  # toll plaza
COLLISION_FT$ft                <- as.numeric(COLLISION_FT$ft)
COLLISION_FT$fatality_exponent <- as.numeric(COLLISION_FT$fatality_exponent)
COLLISION_FT$injury_exponent   <- as.numeric(COLLISION_FT$injury_exponent)
COLLISION_FT$fwy_non           <- factor(COLLISION_FT$fwy_non)
COLLISION_FT$ft_collision      <- as.numeric(COLLISION_FT$ft_collision)
# TODO: This implements PBA50 errors for PBA50
if (PROJECT == "PBA50") {
  COLLISION_FT[ 5, "ft_collision"] <- 4 # freeway ramp
  COLLISION_FT[ 9, "ft_collision"] <- 4 # special facility
  COLLISION_FT[10, "ft_collision"] <- 4 # toll plaza
  # PBA50 assigns exponent *after* renaming ft=ft_collision but I don't think that's on purpose
  COLLISION_FT$fatality_exponent <- 0.0
  COLLISION_FT$fatality_exponent[ COLLISION_FT$ft_collision %in% c(1,2,3,5,6,8)] <- 4.6 # only -1,2,3,4 are valid
  COLLISION_FT$fatality_exponent[ COLLISION_FT$ft_collision %in% c(4,7)        ] <- 3.0 # only -1,2,3,4 are valid
  COLLISION_FT$injury_exponent <- 0.0
  COLLISION_FT$injury_exponent[ COLLISION_FT$ft_collision %in% c(1,2,3,5,6,8)] <- 3.5 # only -1,2,3,4 are valid
  COLLISION_FT$injury_exponent[ COLLISION_FT$ft_collision %in% c(4,7)        ] <- 2.0 # only -1,2,3,4 are valid
  
}
print("COLLSION_FT")
print(COLLISION_FT)
# print(str(COLLISION_FT))

COLLISION_AT <- data.frame(at = numeric(), at_collision = numeric())
# Maps area type (at) to aggregate version used for collision lookup (at_collision)
# https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-at
#
#                     at, at_collision: 3 = urban, 4 = suburban and rural
COLLISION_AT[ 1,] <- c(  0,  3)  # Regional Core
COLLISION_AT[ 2,] <- c(  1,  3)  # Central business district
COLLISION_AT[ 3,] <- c(  2,  3)  # Urban business
COLLISION_AT[ 4,] <- c(  3,  3)  # Urban
COLLISION_AT[ 5,] <- c(  4,  4)  # Suburban
COLLISION_AT[ 6,] <- c(  5,  4)  # Rural
print("COLLISION_AT:")
print(COLLISION_AT)

# columns are TAZ1454, taz_epc (which is either 0 or 1)
TAZ_EPC_LOOKUP_DF <- read.csv(TAZ_EPC_FILE)
print(paste("Read",nrow(TAZ_EPC_LOOKUP_DF), "lines of TAZ_EPC_LOOKUP from",TAZ_EPC_FILE))
# make PBA50 version compatible
if (PROJECT=="PBA50") {
  TAZ_EPC_LOOKUP_DF <- rename(TAZ_EPC_LOOKUP_DF, TAZ1454=taz, taz_epc = in_set)
}
print("head(TAZ_EPC_LOOKUP_DF):")
print(head(TAZ_EPC_LOOKUP_DF))
# create a simple list-based class to hold these
# http://adv-r.had.co.nz/S3.html
# constructor
# fatalities_injuries is a class (based on a named list) with the variables:
#  year
#  type = observed|modeled
#  network_summary_df = data.frame with columns
#     N_fatalities_motorist
#     N_fatalities_ped
#     N_fatalities_bike
#     N_serious_injuries
#     N_fatalities_total
#     per 100k capita and per 100M VMT versions of the above
new_fatalities_injuries <- function(x=list()) {
    structure(x, class = "fatalities_injuries")
}

# print method for fatalities_injuries object
print.fatalities_injuries <- function(fatal_inj) {
  print(paste("fatalities_injuries for", fatal_inj$year,"--",fatal_inj$model_run_id))
  print("=================================================================")
  print(paste("annual_VMT:", format(fatal_inj$annual_VMT, nsmall=0, big.mark=",")))
  print(paste("population:", format(fatal_inj$population, nsmall=0, big.mark=",")))

  # convert wide table to long
  if (is.null(fatal_inj$network_group_by_col)) {
    # this is a one-row table so just pivot to long
    network_summary_long_df <- pivot_longer(fatal_inj$network_summary_df, everything())
  } else {
    # this has one row per value of network_group_by_col so pivot long and then wide
    network_summary_long_df <- pivot_longer(fatal_inj$network_summary_df, !fatal_inj$network_group_by_col)
    network_summary_long_df <- pivot_wider(network_summary_long_df, names_from=fatal_inj$network_group_by_col)
  }
  print(network_summary_long_df)

  if (!is.null(fatal_inj$model_network_df)) {
    print(paste("-- model_network_df has",nrow(fatal_inj$model_network_df),"rows"))
  }

  if (!is.null(fatal_inj$correct_N_fatalities_motorist)) {
    print("-- Correction (to observed) factors:")
    print(paste("  correct_N_fatalities_motorist = ", format(fatal_inj$correct_N_fatalities_motorist, digits=5)))
    print(paste("  correct_N_fatalities_ped      = ", format(fatal_inj$correct_N_fatalities_ped     , digits=5)))
    print(paste("  correct_N_fatalities_bike     = ", format(fatal_inj$correct_N_fatalities_bike    , digits=5)))
    print(paste("  correct_N_serious_injuries    = ", format(fatal_inj$correct_N_serious_injuries   , digits=5)))
  }
}

# calculate_per_capita (and per_VMT)
calculate_per_capita <- function(...) UseMethod("calculate_per_capita")

# calcualtes per 100M VMT fatalities and injuries 
# as well as per 100K population fatalities and injuries 
calculate_per_capita.fatalities_injuries <- function(fatal_inj) {
  # TODO: For metrics using a with a groupby column, the denominator here could be 1) annual_VMT for the 
  # TODO: full network OR 2) annual_VMT for the subset of links.
  # TODO: I think 1) makes more sense so they will sum to the the metrics for the full network.
  # TODO: I don't think it's logical to do 2) since I think the point of the breakdown is to split the full rate.
  #
  # TODO: Currently, this is implemented consistently with the previous version as 2)
  # TODO: To convert to 1), change annual_VMT_100M to fatal_inj$annual_VMT/ONE_HUNDRED_MILLION
  # add this column if it's not there already
  if (!("annual_VMT_100M" %in% colnames(fatal_inj$network_summary_df))) {
    fatal_inj$network_summary_df <- mutate(fatal_inj$network_summary_df, annual_VMT_100M = fatal_inj$annual_VMT / ONE_HUNDRED_MILLION)
  }
  # per 100M VMT
  fatal_inj$network_summary_df <- mutate(fatal_inj$network_summary_df,
    N_fatalities_per_100M_VMT_motorist   = N_fatalities_motorist / (annual_VMT_100M),
    N_fatalities_per_100M_VMT_ped        = N_fatalities_ped      / (annual_VMT_100M),
    N_fatalities_per_100M_VMT_bike       = N_fatalities_bike     / (annual_VMT_100M),
    N_fatalities_per_100M_VMT_total      = N_fatalities_total    / (annual_VMT_100M),
    N_serious_injuries_per_100M_VMT      = N_serious_injuries    / (annual_VMT_100M)
  )
  # TODO: For the EPC, the existing code uses population in the EPC tazs
  # TODO: I don't think this makes sense -- the EPC population are not generating this VMT so I think
  # TODO: the full population should be the denominator
  # per 100K population
  fatal_inj$network_summary_df <- mutate(fatal_inj$network_summary_df,
    N_fatalities_per_100K_pop_motorist   = N_fatalities_motorist / (fatal_inj$population/ONE_HUNDRED_THOUSAND ),
    N_fatalities_per_100K_pop_ped        = N_fatalities_ped      / (fatal_inj$population/ONE_HUNDRED_THOUSAND ),
    N_fatalities_per_100K_pop_bike       = N_fatalities_bike     / (fatal_inj$population/ONE_HUNDRED_THOUSAND ),
    N_fatalities_per_100K_pop_total      = N_fatalities_total    / (fatal_inj$population/ONE_HUNDRED_THOUSAND ),
    N_serious_injuries_per_100K_pop      = N_serious_injuries    / (fatal_inj$population/ONE_HUNDRED_THOUSAND )
  )
  fatal_inj
}

# helper for creating instance of observed
observed_fatalities_injuries <- function(observed_year, annual_VMT_arg, population_arg) {
  if (observed_year != 2015) {
    stop("observed_fatalities_injuries() not implemented for observed_year != 2015")
  }

  if (observed_year == 2015)
    network_summary_df <- data.frame(
      # 2015 Observed
      # TODO: Please document source for these numbers
      N_fatalities_motorist = c(301),
      N_fatalities_ped      = c(127),
      N_fatalities_bike     = c(27),
      # N_injuries_motorist = 1338,
      # N_injuries_ped      = 379,
      # N_injuries_bike     = 251
      N_serious_injuries    = c(1968)
    ) %>% mutate(
      N_fatalities_total = N_fatalities_motorist + N_fatalities_ped + N_fatalities_bike
    )

    observed <- list(
      model_run_id          = "observed",
      year                  = 2015,
      population            = population_arg,
      annual_VMT            = annual_VMT_arg, # full network-level
      network_summary_df    = network_summary_df
    )

    # call constructor
    calculate_per_capita(new_fatalities_injuries(observed))
}

# Creates and returns an instance of modeled fatalities and injuries
# 
# Args:
#   model_run_id:          string, the model run ID for legibility
#   model_year:            the year the model is representing
#   model_network_df:      data.frame of avgload5period.csv, so those are the columns expected
#   population:            total regional population for per 100k residents calculations
#   network_group_by_col:  pass a column in model_network_df to additionally perform a group_by operation, 
#   no_project_network_df: pass this to do speed corrections based on no project link speeds
#
modeled_fatalities_injuries <- function(model_run_id, model_year, model_network_df, population, network_group_by_col=NULL, network_no_project_df=NULL) {
  # print(paste("modeled_fatalities_injuries() with network_group_by_col:",network_group_by_col))

  # create copy for use
  model_network_df <- data.frame(model_network_df)
  # drop ctim, vc cols
  model_network_df <- select(model_network_df, -ctimEA, -ctimAM, -ctimMD, -ctimPM, -ctimEV)
  model_network_df <- select(model_network_df, -vcEA,   -vcAM,   -vcMD,   -vcPM,   -vcEV)
  # print(str(model_network_df))

  # add avg_speed column
  model_network_df <- mutate(model_network_df,
    avg_speed   = (cspdEA + cspdAM + cspdMD + cspdPM + cspdEV)/5.0
  )

  # move time period to column for volumn and cspd
  n_row_before <- nrow(model_network_df)
  vol_df <- pivot_longer(select(model_network_df,a,b,volEA_tot,volAM_tot,volMD_tot,volPM_tot,volEV_tot),
    cols          =starts_with("vol"),
    names_to      ="timeperiod",
    names_pattern ="vol(.*)_tot",
    values_to     ="vol"
  )
  cspd_df <- pivot_longer(select(model_network_df,a,b,cspdEA,cspdAM,cspdMD,cspdPM,cspdEV),
    cols          =starts_with("cspd"),
    names_to      ="timeperiod",
    names_pattern ="cspd(.*)",
    values_to     ="cspd"
  )
  vol_cspd_df <- inner_join(vol_df, cspd_df, by=c("a","b", "timeperiod"))
  stopifnot(nrow(vol_cspd_df) == 5*n_row_before)

  # combine with non-timeperiod based columns
  model_network_df <- left_join(
    vol_cspd_df, 
    select(model_network_df, # select out timeperiod_based columns
      -volEA_tot,-volAM_tot,-volMD_tot,-volPM_tot,-volEV_tot,
      -cspdEA,-cspdAM,-cspdMD,-cspdPM,-cspdEV),
     by=c("a","b"))
  stopifnot(nrow(model_network_df) == 5*n_row_before)

  # recode ft and at by joining with COLLISION_FT and COLLISION_AT  
  model_network_df <- left_join(model_network_df, COLLISION_FT, by=c("ft"))
  model_network_df <- left_join(model_network_df, COLLISION_AT, by=c("at"))
  # print("ft_collision x at_collision:")
  # print(table(model_network_df$ft_collision, model_network_df$at_collision))

  # add annual_VMT column (timeperiod-based)
  model_network_df <- mutate(model_network_df,
    annual_VMT = N_days_per_year*vol*distance)

  if (!is.null(network_no_project_df)) {
    print("Adding speed correction columns from no project")
    model_network_df <- add_speed_correction_columns(model_network_df, network_no_project_df)
  } else {
    model_network_df <- mutate(model_network_df,
      fatality_speed_correction_tp  = 1.0,
      fatality_speed_correction_avg = 1.0,
      injury_speed_correction_tp    = 1.0,
      injury_speed_correction_avg   = 1.0
    )
  }

  # join to collision rates and calculate annual VMT, avg speed, fatalies, injuries by link
  # TODO: This is applying the speed correction from average speeds across all time periods
  # TODO: I think it would be more appropriate to use the timeperiod-based speed
  # TODO: e.g., fatality_speed_correction_tp instead of fatality_speed_correction_avg
  model_network_df <- left_join(model_network_df, collision_rates_df, by=c("ft_collision","at_collision"))
  model_network_df <- mutate(model_network_df,
      N_fatalities_motorist = fatality_speed_correction_avg * (annual_VMT/ONE_MILLION) * fatality_rate_motorist,
      N_fatalities_ped      = fatality_speed_correction_avg * (annual_VMT/ONE_MILLION) * fatality_rate_ped,
      N_fatalities_bike     = fatality_speed_correction_avg * (annual_VMT/ONE_MILLION) * fatality_rate_bike,
      N_fatalities_total    = N_fatalities_motorist + N_fatalities_ped + N_fatalities_bike,
      N_serious_injuries    = injury_speed_correction_avg * (annual_VMT/ONE_MILLION) * serious_injury_rate
    )

  # save for debugging
  debug_file <- file.path(PROJECT_SCENARIOS_DIR, MODEL_RUN_ID_SCENARIO, "OUTPUT", "metrics", paste0("fatalities_injuries_debug_", model_run_id, ".csv"))
  write.csv(model_network_df, debug_file, row.names=FALSE)
  print(paste("Wrote debug file:", debug_file))

  model_network_grouped_df <- model_network_df
  if (!is.null(network_group_by_col)) {
    # do the groupby
    model_network_grouped_df <- group_by_at(model_network_df, c(network_group_by_col))
  }
  model_summary_df <- summarise(model_network_grouped_df,
    .groups = "keep",
    annual_VMT_100M       = sum(annual_VMT,            na.rm=TRUE) / ONE_HUNDRED_MILLION,
    N_fatalities_motorist = sum(N_fatalities_motorist, na.rm=TRUE),
    N_fatalities_ped      = sum(N_fatalities_ped,      na.rm=TRUE),
    N_fatalities_bike     = sum(N_fatalities_bike,     na.rm=TRUE),
    N_serious_injuries    = sum(N_serious_injuries,    na.rm=TRUE)
  ) %>% mutate(
    N_fatalities_total = N_fatalities_motorist + N_fatalities_ped + N_fatalities_bike
  )

  modeled <- list(
    model_run_id          = model_run_id,
    year                  = model_year,
    population            = population,
    annual_VMT            = sum(model_network_df$annual_VMT, na.rm=TRUE), # this is always for the entire network
    model_network_df      = model_network_df,    # keep reference to this
    network_summary_df    = model_summary_df,    # keep reference to this
    network_group_by_col  = network_group_by_col # store the groupby col
  )

  # call constructor
  calculate_per_capita(new_fatalities_injuries(modeled))
}

# use correct_to_observed.fatalities_injuries as a class method 
create_correction_factors_for_observed <- function(...) UseMethod("create_correction_factors_for_observed")

# This updates the modeled fatalities and injuries to match that of the observed by determining
# and storing correction foractors for each of the four types of fatalities/injuries
create_correction_factors_for_observed.fatalities_injuries <- function(modeled_fatal_inj, obs_fatal_inj) {
  # years must match
  stopifnot(modeled_fatal_inj$year == obs_fatal_inj$year)
  # network summary should have single row
  stopifnot(nrow(modeled_fatal_inj$network_summary_df) == 1)
  stopifnot(nrow(obs_fatal_inj$network_summary_df)     == 1)
  print(paste("create_correction_factors_for_observed() fatalities and injuries for year",modeled_fatal_inj$year))

  # determine correction factors and store them as their own variables
  modeled_fatal_inj$correct_N_fatalities_motorist <- obs_fatal_inj$network_summary_df[[1,"N_fatalities_motorist"]] / modeled_fatal_inj$network_summary_df[[1,"N_fatalities_motorist"]]
  modeled_fatal_inj$correct_N_fatalities_ped      <- obs_fatal_inj$network_summary_df[[1,"N_fatalities_ped"     ]] / modeled_fatal_inj$network_summary_df[[1,"N_fatalities_ped"     ]]
  modeled_fatal_inj$correct_N_fatalities_bike     <- obs_fatal_inj$network_summary_df[[1,"N_fatalities_bike"    ]] / modeled_fatal_inj$network_summary_df[[1,"N_fatalities_bike"    ]]
  modeled_fatal_inj$correct_N_serious_injuries    <- obs_fatal_inj$network_summary_df[[1,"N_serious_injuries"   ]] / modeled_fatal_inj$network_summary_df[[1,"N_serious_injuries"   ]]

  modeled_fatal_inj
}

# use correct_using_observed_factors.fatalities_injuries as a class method 
correct_using_observed_factors <- function(...) UseMethod("correct_using_observed_factors")
# This applies the correction factors from comparing modeling vs observed
# e.g., the correction factors created via create_correction_factors_for_observed() which are stored in corrective_fatal_inj are applied
correct_using_observed_factors.fatalities_injuries <- function(modeled_fatal_inj, corrective_fatal_inj) {
  print("correct_using_observed_factors(): correcting fatalities/injuries")
  print(paste("  for",modeled_fatal_inj$year,"--",modeled_fatal_inj$model_run_id))
  print(paste("  using",corrective_fatal_inj$year,"--",corrective_fatal_inj$model_run_id))

  # apply the correction factors
  modeled_fatal_inj$network_summary_df <- mutate(modeled_fatal_inj$network_summary_df,
    N_fatalities_motorist = N_fatalities_motorist * corrective_fatal_inj$correct_N_fatalities_motorist,
    N_fatalities_ped      = N_fatalities_ped      * corrective_fatal_inj$correct_N_fatalities_ped,
    N_fatalities_bike     = N_fatalities_bike     * corrective_fatal_inj$correct_N_fatalities_bike,
    N_serious_injuries    = N_serious_injuries    * corrective_fatal_inj$correct_N_serious_injuries,
    N_fatalities_total    = N_fatalities_motorist + N_fatalities_ped + N_fatalities_bike
  )

  # recalculate per capita
  calculate_per_capita(modeled_fatal_inj)
}

# adds four columns to the modeled_modeled_network_df and returns it:
#   [fatality|injury]_speed_correction_[tp,avg]: 
#       fatality or injury speed correction based on comparing congested speed to no project
#       for suffix tp, the congested speed is time period specific
#       for suffix avg, the congested speed is an average (unweighted) across all 5 timeperiods
#
add_speed_correction_columns <- function(model_network_df, network_no_project_df) {
 
  # left join model network to no project
  n_row_before <- nrow(model_network_df)
  model_network_df <- left_join(
    model_network_df, 
    select(network_no_project_df, a,b,timeperiod,cspd,avg_speed),
    by=c("a","b","timeperiod"), suffix=c("","_no_project"))
  # verify rows are unchanged
  stopifnot(nrow(model_network_df) == n_row_before)
  
  # calculate speed correction factor
  model_network_df <- mutate(model_network_df,
    # fatality
    fatality_speed_correction_tp  = (cspd/cspd_no_project)^fatality_exponent,             # based on timeperiod-specific speed
    fatality_speed_correction_avg = (avg_speed/avg_speed_no_project)^fatality_exponent,   # based on avg speed
    # injury
    injury_speed_correction_tp    = (cspd/cspd_no_project)^injury_exponent,               # based on timeperiod-specific speed
    injury_speed_correction_avg   = (avg_speed/avg_speed_no_project)^injury_exponent      # based on avg speed
  )
  # these are multiplicative so default to 1.0 in place of NA
  # TODO: PBA50 original code didn't do this but I think it should be done or the join fails get dropped
  # TODO: Keeping this bug for PBA50 only
  if (PROJECT != "PBA50") {
    model_network_df <- mutate(model_network_df,
      # fatality
      fatality_speed_correction_tp  = if_else(is.na(fatality_speed_correction_tp),  1.0, fatality_speed_correction_tp),
      fatality_speed_correction_avg = if_else(is.na(fatality_speed_correction_avg), 1.0, fatality_speed_correction_avg),
      # injury_else
      injury_speed_correction_tp    = if_else(is.na(injury_speed_correction_tp),    1.0, injury_speed_correction_tp),
      injury_speed_correction_avg   = if_else(is.na(injury_speed_correction_avg),   1.0, injury_speed_correction_avg)
    )
  }
  # save it for debugging
  # write.csv(model_network_df, paste0("corrections_",model_fatal_inj$model_run_id,".csv"))

  # this was in the original PBA50 code via pmin
  # TODO: I don't think we should do this -- if we take credit for slowing down traffic, we should also
  # TODO: take credit for speeding it up and increaasing fatalities/injuries
  # TODO: Reproducing for PBA50 only
  if (PROJECT == "PBA50") {
    # these are multiplicative so default to 1.0 in place of NA
    model_network_df <- mutate(model_network_df,
      # fatality
      fatality_speed_correction_tp  = if_else(fatality_speed_correction_tp  > 1.0,  1.0, fatality_speed_correction_tp),
      fatality_speed_correction_avg = if_else(fatality_speed_correction_avg > 1.0,  1.0, fatality_speed_correction_avg),
      # injury_else
      injury_speed_correction_tp    = if_else(injury_speed_correction_tp  > 1.0,    1.0, injury_speed_correction_tp),
      injury_speed_correction_avg   = if_else(injury_speed_correction_avg > 1.0,    1.0, injury_speed_correction_avg)
    )
  }
  # print(head(filter(model_network_df, ft != 6)))

  # return it
  model_network_df
}


####### Calculate for the base year to determine correction factors #######
tazdata_base_year_df      <- read.csv(file.path(MODEL_FULL_DIR_BASE_YEAR, "INPUT", "landuse","tazData.csv"))
network_base_year_df      <- read.csv(file.path(MODEL_FULL_DIR_BASE_YEAR, "OUTPUT", "avgload5period.csv"))

population_base_year <- sum(tazdata_base_year_df$TOTPOP)
network_base_year_df <- mutate(network_base_year_df, daily_VMT = distance*(volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot))
annual_VMT_base_year <- sum(network_base_year_df$daily_VMT, na.rm=TRUE)*N_days_per_year

OBSERVED_FATALITIES_INJURIES_BASE_YEAR <- observed_fatalities_injuries(BASE_YEAR, annual_VMT_base_year, population_base_year)
print(OBSERVED_FATALITIES_INJURIES_BASE_YEAR)

model_fatal_inj_base_year <- modeled_fatalities_injuries(MODEL_RUN_ID_BASE_YEAR, BASE_YEAR, network_base_year_df, population_base_year, network_group_by_col=NULL)
print(model_fatal_inj_base_year)

model_fatal_inj_base_year <- create_correction_factors_for_observed(model_fatal_inj_base_year, OBSERVED_FATALITIES_INJURIES_BASE_YEAR)
model_fatal_inj_base_year <- correct_using_observed_factors(model_fatal_inj_base_year, model_fatal_inj_base_year)
print("--------------------------------------")
print("AFTER CORRECTION to BASE YEAR OBSERVED")
print(model_fatal_inj_base_year)

####### Calculate for no project forecast year
MODEL_RUN_IDS             <- c(
  "NO_PROJECT" = MODEL_RUN_ID_NO_PROjeCT,
  "SCENARIO"   = MODEL_RUN_ID_SCENARIO
)

# we'll save this for SCENARIO
network_no_project_df <- NULL
model_fatal_no_project <- NULL # debug
results_df <- data.frame()

for (model_run_type in c("NO_PROJECT", "SCENARIO")) {
  model_run_id     <- MODEL_RUN_IDS[[model_run_type]]
  model_full_dir   <- file.path(PROJECT_SCENARIOS_DIR, model_run_id)
  tazdata_df       <- read.csv(file.path(model_full_dir, "INPUT", "landuse","tazData.csv"))
  network_df       <- read.csv(file.path(model_full_dir, "OUTPUT", "avgload5period.csv"))
  link_to_taz_df   <- read.csv(file.path(model_full_dir, "OUTPUT", "shapefile", "network_links_TAZ.csv")) %>% 
                        rename(a = A, b = B)

  # adds columns TAZ1454, link_mi, linktaz_mi, linktaz_share
  # note -- this is NOT one-to-one -- links appear in link_to_taz_df multiple times!
  # network_df <- merge(network_df, link_to_taz_df, by=c("a","b"))

  network_df <- mutate(network_df,
    annual_VMT  = N_days_per_year * (volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
    avg_speed   = (cspdEA + cspdAM + cspdMD + cspdPM + cspdEV)/5.0
  )

  # associate each link to EPC vs non-EPC
  # Note: This is assuming a link is in an EPC taz if ANY part of it is within (even a small fraction)
  link_to_taz_df <- left_join(link_to_taz_df, TAZ_EPC_LOOKUP_DF, by=c("TAZ1454"))
  link_to_epc_df <- link_to_taz_df %>% group_by(a, b) %>% summarise(taz_epc = max(taz_epc))
  network_df     <- left_join(network_df, link_to_epc_df, by=c("a","b")) %>%
                    #left_join(COLLISION_FT, by=c("ft")) %>%
                    mutate(
                      taz_epc = if_else(taz_epc==1, "EPC", "Non-EPC"),
                      taz_epc = if_else(is.na(taz_epc), "Non-EPC", taz_epc),
                      taz_epc_local = if_else(taz_epc=="EPC" & (ft == 3 | ft == 4 | ft == 6| ft == 7| ft == 9),"taz_epc_local","pass"),    #new
                      taz_epc_local = if_else(is.na(taz_epc_local), "pass", taz_epc_local),                      #new
                      Non_EPC_local = if_else(taz_epc=="Non-EPC" & (ft == 3 | ft == 4 | ft == 6| ft == 7| ft == 9),"non_epc_local","pass"),#new
                      Non_EPC_local = if_else(is.na(Non_EPC_local), "pass", Non_EPC_local)                      #new
                    ) # convert 1 -> EPC; 0 or Na -> Non-EPC
  # print(head(network_df))
  population_forecast <- sum(tazdata_df$TOTPOP)

  model_fatal_inj <- modeled_fatalities_injuries(model_run_id, FORECAST_YEAR, network_df, population_forecast, 
                          network_group_by_col=NULL, network_no_project_df=network_no_project_df)
  model_fatal_inj <- correct_using_observed_factors(model_fatal_inj, model_fatal_inj_base_year)
  if (model_run_type == "NO_PROJECT") {
    model_fatal_no_project <- model_fatal_inj
  }
  print("--------------------------------------")
  print(model_fatal_inj)


  model_fatal_inj_fwy_non <- modeled_fatalities_injuries(model_run_id, FORECAST_YEAR, network_df, population_forecast, 
                                network_group_by_col="fwy_non", network_no_project_df=network_no_project_df)
  model_fatal_inj_fwy_non <- correct_using_observed_factors(model_fatal_inj_fwy_non, model_fatal_inj_base_year)
  print("--------------------------------------")
  print(model_fatal_inj_fwy_non)

  model_fatal_inj_epc_non <- modeled_fatalities_injuries(model_run_id, FORECAST_YEAR, network_df, population_forecast, 
                                network_group_by_col="taz_epc", network_no_project_df)
  model_fatal_inj_epc_non <- correct_using_observed_factors(model_fatal_inj_epc_non, model_fatal_inj_base_year)
  print("--------------------------------------")
  print(model_fatal_inj_epc_non)
  
  model_fatal_inj_epc_local <- modeled_fatalities_injuries(model_run_id, FORECAST_YEAR, network_df, population_forecast, #new
                                                           network_group_by_col="taz_epc_local", network_no_project_df)     
  model_fatal_inj_epc_local <- correct_using_observed_factors(model_fatal_inj_epc_local, model_fatal_inj_base_year)
  print("--------------------------------------")
  print(model_fatal_inj_epc_local)
  # 
  model_fatal_inj_non_epc_local <- modeled_fatalities_injuries(model_run_id, FORECAST_YEAR, network_df, population_forecast, #new
                                                               network_group_by_col="Non_EPC_local", network_no_project_df)     
  model_fatal_inj_non_epc_local <- correct_using_observed_factors(model_fatal_inj_non_epc_local, model_fatal_inj_base_year)
  print("--------------------------------------")
  print(model_fatal_inj_non_epc_local)


  # save the fatalities & injuries results
  results_df <- rbind(
    results_df,
    mutate(model_fatal_inj$network_summary_df, key="all", model_run_type=model_run_type, model_run_id=model_run_id),
    mutate(rename(model_fatal_inj_fwy_non$network_summary_df, key=fwy_non), model_run_type=model_run_type, model_run_id=model_run_id),
    mutate(rename(model_fatal_inj_epc_non$network_summary_df, key=taz_epc), model_run_type=model_run_type, model_run_id=model_run_id),
    mutate(rename(model_fatal_inj_epc_local$network_summary_df, key=taz_epc_local), model_run_type=model_run_type, model_run_id=model_run_id),
    mutate(rename(model_fatal_inj_non_epc_local$network_summary_df, key=Non_EPC_local), model_run_type=model_run_type, model_run_id=model_run_id)
  )

  # if there's no scenario, we're done
  if (MODEL_RUN_IDS[["NO_PROJECT"]] == MODEL_RUN_IDS[["SCENARIO"]]) {
    break
  }
  # save no project for SCENARIO
  if (model_run_type == "NO_PROJECT") {
    network_no_project_df <- data.frame(model_fatal_inj$model_network_df)
  }
}

write.csv(results_df, file=OUTPUT_FILE, row.names=FALSE)
print(paste("Wrote", nrow(results_df), "rows to",OUTPUT_FILE))

sink(file=NULL, type=c("output","message"))

print(paste("Wrote", nrow(results_df), "rows to",OUTPUT_FILE))
print(paste("Wrote", LOG_FILE))
