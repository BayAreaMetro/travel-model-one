# ----------------------------------------------------------------------------------------------------------------
# travel-cost-by-income-driving-households.r
#
# Summarize transportation costs by the following new segmentation of households:
#   incQ, incQ_lable: income group
#   home_taz: taz of household
#   hhld_travel: household type, one of [auto_and_transit, auto_no_transit, transit_no_auto, no_auto_no_transit]
#      for segmentation purposes,
#         auto trips include personal auto trips (but *not* taxi, TNC) and drive-to-transit trips
#         transit trips include walk-to-transit trips and drive-to-transit trips
#         so a household with a single drive-to-transit trip is in auto_and_transit
# Data columns:
#   num_hhlds:          number of households
#   num_persons:        number of persons in those households
#   num_auto_trips:     number of auto trips taken by those households
#   num_transit_trips:  number of transit trips taken by those households
#     (Note the same classifications of auto and transit apply as were used in the segmentation
#      so there IS double counting -- a drive-to-transit trip is counted twice)
#   total_hhld_autos:   total number of household autos for these households
#   total_hhd_income:   total household income for these households (in 2000 dollars)
#   ========= Initial *simple* costs from CoreSummaries: ====
#     total_auto_cost:    total daily auto cost for these trips (in 2000 cents)
#                         NOTE that these have means-based discounts applied incorrectly
#     total_transit_cost: total daily transit cost for these trips (in 2000 cents)
#     total_cost:         total daily cost (in 2000 cents)
#   ========= Added 5/2/2023 *detailed* costs skims: ====
#      total_parking_cost:          parking cost
#      total_auto_op_cost:          total auto operating cost, from distance x AOC
#      total_bridge_toll:           bridge tolls, not including cordon tolls
#      total_cordon_toll:           cordon tolls, including means-based discounts
#      total_value_toll:            value tolls, including means-based discounts
#      total_detailed_auto_cost:    sum of parking, auto op, bridge, cordon, and value tolls
#      total_fare:                  transit fare, including means-based discounts
#      total_drv_trn_op_cost:       auto operating cost, from drive to transit distance x AOC
#      total_detailed_transit_cost: sum of transit fare and drive-to-transit auto operating cost
#
# See asana task: Affordable 1 (transportation costs / share of income) and subtasks
# https://app.asana.com/0/0/1204323747319792/f
#
# Input:   
#   (1) TARGET_DIR: environment variable; should be the model run dir on a modeling machine
#   (2) %TARGET_DIR%\INPUT\params.properties file - model parameters defining costs
#   (3) %TARGET_DIR%\INPUT\landuse\tazData.csv - tazData for Cordon, Cordon Cost, parking cost information
#   (4) %TARGET_DIR%\updated_output\trips.rdata - trips combined with other info from CoreSummaries.R
#   (5) %TARGET_DIR%\skims\HWYSKM_cost_[EA,AM,MD,PM,EV].csv - roadway cost skims exported
#   (6) %TARGET_DIR%\skims\trnskm_cost_[EA,AM,MD,PM,EV].csv - transit cost skims exported
# Output:  
#   (1) %TARGET_DIR%\updated_output\trips_with_detailed_cost.rdata - trips with detailed cost columns added
#   (2) %TARGET_DIR%\core_summaries\travel-cost-hhldtraveltype.csv - table with columns listed above
#   (3) %TARGET_DIR%\core_summaries\travel-cost-hhldtraveltype-[auto,transit].csv - pivoted
#       version for tableau exploration
#
#  See also:
#   (1) tallyParking.R
#   (2) extract_cost_skims.job
#   (3) ngfs_metrics.py
# ----------------------------------------------------------------------------------------------------------------

# modeling machines have R_LIB setup
.libPaths(Sys.getenv("R_LIB"))

library(readr)
library(stringr)
library(dplyr)
library(tidyr)

#### Mode look-up table
LOOKUP_MODE <- data.frame(
    trip_mode = c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21),
    mode_name = factor(c("Drive alone - free", "Drive alone - pay", 
                  "Shared ride two - free", "Shared ride two - pay",
                  "Shared ride three - free", "Shared ride three - pay",
                  "Walk", "Bike",
                  "Walk to local bus", "Walk to light rail or ferry", "Walk to express bus", 
                  "Walk to heavy rail", "Walk to commuter rail",
                  "Drive to local bus", "Drive to light rail or ferry", "Drive to express bus", 
                  "Drive to heavy rail", "Drive to commuter rail",
                  "Taxi", "TNC", "TNC shared")),
    is_auto =    c(TRUE, TRUE, TRUE, TRUE, TRUE, TRUE,       # DAx2, SR2x2, SR3x2
                   FALSE, FALSE,                             # walk, bike
                   FALSE, FALSE, FALSE, FALSE, FALSE,        # walk to transit
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # drive to transit
                   FALSE, FALSE, FALSE),                     # taxi, tnc; auto=personal vehicle?
    is_transit = c(FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, # DAx2, SR2x2, SR3x2
                   FALSE, FALSE,                             # walk, bike
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # walk to transit
                   TRUE,  TRUE,  TRUE,  TRUE,  TRUE,         # drive to transit
                   FALSE, FALSE, FALSE)                      # taxi, tnc; drive=personal vehicle
        
    )
print("LOOKUP_MODE:")
print(LOOKUP_MODE)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
SAMPLESHARE  <- 0.5
TAZDATA_FILE <- file.path(TARGET_DIR, "INPUT", "landuse", "tazData.csv")
OUTPUT_FILE  <- file.path(TARGET_DIR, "core_summaries", "travel-cost-hhldtraveltype.csv")

# from TripModeChoice UEC
COST_SHARE_SR2 = 1.75
COST_SHARE_SR3 = 2.50

# constructor
new_model_parameters <- function(x=list()) {
    stopifnot((x$auto_op_cost                      >  0.0) & (x$auto_op_cost                      <= 100.0))
    stopifnot((x$taxi_base_fare                    >  0.0) & (x$taxi_base_fare                     <= 100.0))
    stopifnot((x$taxi_cost_per_mile                >  0.0) & (x$taxi_cost_per_mile                <= 100.0))
    stopifnot((x$TNC_single_base_fare              >  0.0) & (x$TNC_single_base_fare               <= 100.0))
    stopifnot((x$TNC_single_cost_per_mile          >  0.0) & (x$TNC_single_cost_per_mile          <= 100.0))
    stopifnot((x$TNC_shared_baseFare               >  0.0) & (x$TNC_shared_baseFare               <= 100.0))
    stopifnot((x$TNC_shared_cost_per_mile          >  0.0) & (x$TNC_shared_cost_per_mile          <= 100.0))

    stopifnot((x$means_based_toll_q1_factor        >= 0.0) & (x$means_based_toll_q1_factor        <= 1.0))
    stopifnot((x$means_based_toll_q2_factor        >= 0.0) & (x$means_based_toll_q2_factor        <= 1.0))
    stopifnot((x$means_based_cordon_toll_q1_factor >= 0.0) & (x$means_based_cordon_toll_q1_factor <= 1.0))
    stopifnot((x$means_based_cordon_toll_q2_factor >= 0.0) & (x$means_based_cordon_toll_q2_factor <= 1.0))
    stopifnot((x$means_based_fare_q1_factor        >= 0.0) & (x$means_based_fare_q1_factor        <= 1.0))
    stopifnot((x$means_based_fare_q2_factor        >= 0.0) & (x$means_based_fare_q2_factor        <= 1.0))
    stopifnot((x$means_based_cordon_fare_q1_factor >= 0.0) & (x$means_based_cordon_fare_q1_factor <= 1.0))
    stopifnot((x$means_based_cordon_fare_q2_factor >= 0.0) & (x$means_based_cordon_fare_q2_factor <= 1.0))

    # TODO: AV factors are not included because disaggregate trip data is missing useOwnedAV -- so assuming no AV!
    structure(x, class = "model_parameters")
}

# helper
model_parameters <- function(target_dir) {
    # read params.properties file
    params_lines <- readLines(file.path(target_dir,"INPUT","params.properties"))

    param_to_regex <- c(
        "auto_op_cost"                      ="^AutoOpCost\\s*=\\s*([[:digit:].]+)\\s*.*$",
        # tax/tnc
        "taxi_base_fare"                    ="^taxi.baseFare\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "taxi_cost_per_mile"                ="^taxi.costPerMile\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "taxi_cost_per_minute"              ="^taxi.costPerMinute\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_single_base_fare"              ="^TNC.single.baseFare\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_single_cost_per_mile"          ="^TNC.single.costPerMile\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_single_cost_per_minute"        ="^TNC.single.costPerMinute\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_shared_baseFare"               ="^TNC.shared.baseFare\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_shared_cost_per_mile"          ="^TNC.shared.costPerMile\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "TNC_shared_cost_per_minute"        ="^TNC.shared.costPerMinute\\s*=\\s*([[:digit:].]+)\\s*.*$",
        #means-based discount factors
        "means_based_toll_q1_factor"        ="^Means_Based_Tolling_Q1Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_toll_q2_factor"        ="^Means_Based_Tolling_Q2Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_toll_q2_factor"        ="^Means_Based_Tolling_Q2Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_cordon_toll_q1_factor" ="^Means_Based_Cordon_Tolling_Q1Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_cordon_toll_q2_factor" ="^Means_Based_Cordon_Tolling_Q2Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_fare_q1_factor"        ="^Means_Based_Fare_Q1Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_fare_q2_factor"        ="^Means_Based_Fare_Q2Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_cordon_fare_q1_factor" ="^Means_Based_Cordon_Fare_Q1Factor\\s*=\\s*([[:digit:].]+)\\s*.*$",
        "means_based_cordon_fare_q2_factor" ="^Means_Based_Cordon_Fare_Q2Factor\\s*=\\s*([[:digit:].]+)\\s*.*$"
    )

    params <- list()

    for (param_name in names(param_to_regex)) {
        # extract from the lines in paramaeters file
        param_list <- str_extract(params_lines, param_to_regex[param_name], group=1)
        # narrow down to the ones that matched
        param_value <- param_list[!is.na(param_list)]
        stopifnot(length(param_value) == 1)
        # set it
        params[param_name]  <- as.numeric(param_value)
    }

    # call constructor
    new_model_parameters(params)
}

# print method for the class
print.model_parameters <- function(params) {
    print("model_parameters - general")
    print(paste("  auto_op_cost                      =",params$auto_op_cost))
    print("model_parameters - tax/TNC")
    print(paste("  taxi_base_fare                    =",params$taxi_base_fare))
    print(paste("  taxi_cost_per_mile                =",params$taxi_cost_per_mile))
    print(paste("  taxi_cost_per_minute              =",params$taxi_cost_per_minute))
    print(paste("  TNC_single_base_fare              =",params$TNC_single_base_fare))
    print(paste("  TNC_single_cost_per_mile          =",params$TNC_single_cost_per_mile))
    print(paste("  TNC_single_cost_per_minute        =",params$TNC_single_cost_per_minute))
    print(paste("  TNC_shared_baseFare               =",params$TNC_shared_baseFare))
    print(paste("  TNC_shared_cost_per_mile          =",params$TNC_shared_cost_per_mile))
    print(paste("  TNC_shared_cost_per_minute        =",params$TNC_shared_cost_per_minute))
    print("model_parameters - means-based discounts")
    print(paste("  means_based_toll_q1_factor        =",params$means_based_toll_q1_factor))
    print(paste("  means_based_toll_q2_factor        =",params$means_based_toll_q2_factor))
    print(paste("  means_based_cordon_toll_q1_factor =",params$means_based_cordon_toll_q1_factor))
    print(paste("  means_based_cordon_toll_q2_factor =",params$means_based_cordon_toll_q2_factor))
    print(paste("  means_based_fare_q1_factor        =",params$means_based_fare_q1_factor))
    print(paste("  means_based_fare_q2_factor        =",params$means_based_fare_q2_factor))
    print(paste("  means_based_cordon_fare_q1_factor =",params$means_based_cordon_fare_q1_factor))
    print(paste("  means_based_cordon_fare_q2_factor =",params$means_based_cordon_fare_q2_factor))
} 

print_cost_summary <- function(trips) {
    # quick summary of costs so far
    print(group_by(trips, timeCode, trip_mode, mode_name) %>% 
        summarise(
            auto_op_cost_is_na      = sum(is.na(auto_op_cost)),
            auto_op_cost_mean       = mean(auto_op_cost, na.rm=TRUE),
            bridge_toll_is_na       = sum(is.na(bridge_toll)),
            bridge_toll_mean        = mean(bridge_toll, na.rm=TRUE),
            value_toll_is_na        = sum(is.na(value_toll)),
            value_toll_mean         = mean(value_toll, na.rm=TRUE),
            fare_is_na              = sum(is.na(fare)),
            fare_mean               = mean(fare, na.rm=TRUE),
            drv_trn_op_cost_is_na   = sum(is.na(drv_trn_op_cost)),
            drv_trn_op_cost_mean    = mean(drv_trn_op_cost, na.rm=TRUE)            
        ))
}

####################################### add_detailed_cost ###########################################
#
# Similar to CoreSummaries.R add_cost, but uses the detailed cost output from skim exports
# generated by extract_cost_skims.job rather than the simple cost skim databases
#
add_detailed_cost <- function(model_params, this_timeperiod, input_trips) {
    print(paste("add_detailed_cost() for", this_timeperiod))

    # separate the relevant and irrelevant tours/trips
    relevant   <- input_trips %>% filter(timeCode == this_timeperiod)
    irrelevant <- input_trips %>% filter(timeCode != this_timeperiod)

    # roadway
    skim_file <- file.path(TARGET_DIR, "skims", paste0("HWYSKM_cost_",this_timeperiod,".csv"))
    cost_skims <- read_csv(file = skim_file, col_types=cols(
        orig     = col_integer(), 
        dest     = col_integer(), 
        one_a    = col_skip(),
        one_b    = col_skip(),
        .default = col_double()
    ))
    print(paste("Read",nrow(cost_skims),"lines from",skim_file))
    cost_skims <- mutate_all(cost_skims, ~if_else(is.na(.), 0, .)) # cube outputs zeros as blank
    # print(paste("str(cost_skims) for", this_timeperiod))
    # print(str(cost_skims))

    # Left join trips to the skims
    relevant <- left_join(relevant, cost_skims, by=c("orig_taz"="orig","dest_taz"="dest"))
    # print(str(relevant))

    # Add initial versions of Auto Operating cost, Bridge tolls, Value tolls
    relevant <- mutate(relevant,
        # this is in 2000 cents
        auto_op_cost = case_when(
            mode_name == "Drive alone - free"       ~ model_params$auto_op_cost*DISTDA,
            mode_name == "Drive alone - pay"        ~ model_params$auto_op_cost*TOLLDISTDA,      # c_cost*(costPerMile*SOVTOLL_DIST[tripPeriod])*autoCPMFactor
            mode_name == "Shared ride two - free"   ~ model_params$auto_op_cost*DISTS2,
            mode_name == "Shared ride two - pay"    ~ model_params$auto_op_cost*TOLLDISTS2,
            mode_name == "Shared ride three - free" ~ model_params$auto_op_cost*DISTS3,
            mode_name == "Shared ride three - pay"  ~ model_params$auto_op_cost*TOLLDISTS3,
            # c_cost*(costInitialTaxi + HOV2TOLL_DIST[tripPeriod] * costPerMileTaxi + HOV2TOLL_DIST[tripPeriod] * costPerMinuteTaxi )*100
            # TODO: second use of TOLLDISTS2 here is wrong but reflects UEC error: https://github.com/BayAreaMetro/travel-model-one/issues/57
            mode_name == "Taxi"         ~ (model_params$taxi_base_fare       + (model_params$taxi_cost_per_mile      *TOLLDISTS2) + (model_params$taxi_cost_per_minute      *TOLLDISTS2))*100, 
            mode_name == "TNC"          ~ (model_params$TNC_single_base_fare + (model_params$TNC_single_cost_per_mile*TOLLDISTS2) + (model_params$TNC_single_cost_per_minute*TOLLDISTS2))*100, 
            mode_name == "TNC shared"   ~ (model_params$TNC_shared_baseFare  + (model_params$TNC_shared_cost_per_mile*TOLLDISTS2) + (model_params$TNC_shared_cost_per_minute*TOLLDISTS2))*100, 
            .default = NA
        ),  # c_cost*(costPerMile*SOVTOLL_DIST[tripPeriod])*autoCPMFactor
        # this is in 2000 cents - start with just skim value
        bridge_toll = case_when(
            mode_name == "Drive alone - free"       ~ BTOLLDA,
            mode_name == "Drive alone - pay"        ~ TOLLBTOLLDA,
            mode_name == "Shared ride two - free"   ~ BTOLLS2,
            mode_name == "Shared ride two - pay"    ~ TOLLBTOLLS2,
            mode_name == "Shared ride three - free" ~ BTOLLS3,
            mode_name == "Shared ride three - pay"  ~ TOLLBTOLLS3,
            mode_name == "Taxi"                     ~ TOLLBTOLLS2, # c_cost*HOV2TOLL_BTOLL[tripPeriod]
            mode_name == "TNC"                      ~ TOLLBTOLLS2, # c_cost*(HOV2TOLL_BTOLL[tripPeriod] + HOV2TOLL_BTOLL[tripPeriod])
            mode_name == "TNC shared"               ~ TOLLBTOLLS2, # c_cost*(HOV2TOLL_BTOLL[tripPeriod] + HOV2TOLL_BTOLL[tripPeriod])
            .default = NA
        ),  
        # this is in 2000 cents - start with just skim value
        value_toll = case_when(
            mode_name == "Drive alone - free"       ~ 0,
            mode_name == "Drive alone - pay"        ~ TOLLVTOLLDA,
            mode_name == "Shared ride two - free"   ~ 0,
            mode_name == "Shared ride two - pay"    ~ TOLLVTOLLS2,
            mode_name == "Shared ride three - free" ~ 0,
            mode_name == "Shared ride three - pay"  ~ TOLLVTOLLS3,
            mode_name == "Taxi"                     ~ TOLLVTOLLS2,
            mode_name == "TNC"                      ~ TOLLVTOLLS2,
            mode_name == "TNC shared"               ~ TOLLVTOLLS2,
            .default = NA
        ),
        fare = NA,
        drv_trn_op_cost = NA
    )
    # delete cost_skim columns; we're done with them
    relevant <- select(relevant, ! any_of(colnames(cost_skims)))

    # summarize initial new columns
    # print_cost_summary(relevant)

    # Left join tours to the REVERSE skims for TNC bridge tolls
    relevant <- left_join(relevant, cost_skims, by=c("orig_taz"="dest","dest_taz"="orig"))
    relevant <- mutate(relevant,
        bridge_toll = case_when(
            mode_name == "TNC"                      ~ bridge_toll + TOLLBTOLLS2, # c_cost*(HOV2TOLL_BTOLL[tripPeriod] + HOV2TOLL_BTOLL[tripPeriod])
            mode_name == "TNC shared"               ~ bridge_toll + TOLLBTOLLS2, # c_cost*(HOV2TOLL_BTOLL[tripPeriod] + HOV2TOLL_BTOLL[tripPeriod])
            .default = bridge_toll
        )
    )
    # delete cost_skim columns; we're done with them
    relevant <- select(relevant, ! any_of(colnames(cost_skims)))

    # summarize with TNC reverse bridge tolls
    # print_cost_summary(relevant)

    # initialize cordon tolls for AM and PM only
    if ((this_timeperiod == "AM") | (this_timeperiod == "PM")) {
        # these are skimmed as a bridge_toll; move to cordon_toll
        relevant <- mutate(relevant,
            cordon_toll = ifelse(CORDON_dest > 0, CORDONCOST_dest, 0),
            bridge_toll = ifelse(CORDON_dest > 0, bridge_toll - CORDONCOST_dest, bridge_toll)
        )
        # apply means-based cordon toll discount factor
        relevant <- mutate(relevant,
            cordon_toll = ifelse(incQ == 1, model_params$means_based_cordon_toll_q1_factor*cordon_toll, cordon_toll),
            cordon_toll = ifelse(incQ == 2, model_params$means_based_cordon_toll_q2_factor*cordon_toll, cordon_toll)
        )
    }
    else {
        relevant <- mutate(relevant, cordon_toll=NA)
    }
    # apply means-based value toll factor
    relevant <- mutate(relevant,
        value_toll = ifelse(incQ == 1, model_params$means_based_toll_q1_factor*value_toll, value_toll),
        value_toll = ifelse(incQ == 2, model_params$means_based_toll_q1_factor*value_toll, value_toll)
    )

    # summarize with means-based toll factors
    # print_cost_summary(relevant)

    # transit
    skim_file <- file.path(TARGET_DIR, "skims", paste0("TRNSKM_cost_",this_timeperiod,".csv"))
    cost_skims <- read_csv(file = skim_file, col_types=cols(
        orig     = col_integer(), 
        dest     = col_integer(), 
        one_a    = col_skip(),
        one_b    = col_skip(),
        .default = col_double()
    ))
    print(paste("Read",nrow(cost_skims),"lines from",skim_file))
    cost_skims <- mutate_all(cost_skims, ~if_else(is.na(.), 0, .)) # cube outputs zeros as blank

    # print(paste("str(cost_skims) for", this_timeperiod))
    # print(str(cost_skims))

    # Left join trips to the skims
    relevant <- left_join(relevant, cost_skims, by=c("orig_taz"="orig","dest_taz"="dest"))
    # print(str(relevant))

    # Add initial versions of Fare, drive to transit auto operating cost
    # c_cost*(DRV_LOC_WLK_FAR[tripPeriod]*
    #   if(hhIncomeQ1=1, if((origCordon+destCordon)>0, %Means_Based_Cordon_Fare_Q1Factor%, %Means_Based_Fare_Q1Factor%), 1)*
    #   if(hhIncomeQ2=1, if((origCordon+destCordon)>0, %Means_Based_Cordon_Fare_Q2Factor%, %Means_Based_Fare_Q2Factor%), 1)+
    # (DRV_LOC_WLK_DDIST[tripPeriod]/100*costPerMile))
    relevant <- mutate(relevant,
        fare = case_when(
            mode_name == "Walk to local bus"               ~ fare_wlk_loc_wlk,
            mode_name == "Walk to light rail or ferry"     ~ fare_wlk_lrf_wlk,
            mode_name == "Walk to express bus"             ~ fare_wlk_exp_wlk,
            mode_name == "Walk to heavy rail"              ~ fare_wlk_hvy_wlk,
            mode_name == "Walk to commuter rail"           ~ fare_wlk_com_wlk,
            # outbound
            (inbound == 0) & (mode_name == "Drive to local bus"          ) ~ fare_drv_loc_wlk,
            (inbound == 0) & (mode_name == "Drive to light rail or ferry") ~ fare_drv_lrf_wlk,
            (inbound == 0) & (mode_name == "Drive to express bus"        ) ~ fare_drv_exp_wlk,
            (inbound == 0) & (mode_name == "Drive to heavy rail"         ) ~ fare_drv_hvy_wlk,
            (inbound == 0) & (mode_name == "Drive to commuter rail"      ) ~ fare_drv_com_wlk,
            # inbound
            (inbound == 1) & (mode_name == "Drive to local bus"          ) ~ fare_wlk_loc_drv,
            (inbound == 1) & (mode_name == "Drive to light rail or ferry") ~ fare_wlk_lrf_drv,
            (inbound == 1) & (mode_name == "Drive to express bus"        ) ~ fare_wlk_exp_drv,
            (inbound == 1) & (mode_name == "Drive to heavy rail"         ) ~ fare_wlk_hvy_drv,
            (inbound == 1) & (mode_name == "Drive to commuter rail"      ) ~ fare_wlk_com_drv,
            .default = NA
        ),
        # save as drv_trn_op_cost to distinguish from auto modes
        drv_trn_op_cost = case_when(
            # outbound
            (inbound == 0) & (mode_name == "Drive to local bus"          ) ~ (ddist_drv_loc_wlk/100.0)*model_params$auto_op_cost,
            (inbound == 0) & (mode_name == "Drive to light rail or ferry") ~ (ddist_drv_lrf_wlk/100.0)*model_params$auto_op_cost,
            (inbound == 0) & (mode_name == "Drive to express bus"        ) ~ (ddist_drv_exp_wlk/100.0)*model_params$auto_op_cost,
            (inbound == 0) & (mode_name == "Drive to heavy rail"         ) ~ (ddist_drv_hvy_wlk/100.0)*model_params$auto_op_cost,
            (inbound == 0) & (mode_name == "Drive to commuter rail"      ) ~ (ddist_drv_com_wlk/100.0)*model_params$auto_op_cost,
            # inbound
            (inbound == 1) & (mode_name == "Drive to local bus"          ) ~ (ddist_wlk_loc_drv/100.0)*model_params$auto_op_cost,
            (inbound == 1) & (mode_name == "Drive to light rail or ferry") ~ (ddist_wlk_lrf_drv/100.0)*model_params$auto_op_cost,
            (inbound == 1) & (mode_name == "Drive to express bus"        ) ~ (ddist_wlk_exp_drv/100.0)*model_params$auto_op_cost,
            (inbound == 1) & (mode_name == "Drive to heavy rail"         ) ~ (ddist_wlk_hvy_drv/100.0)*model_params$auto_op_cost,
            (inbound == 1) & (mode_name == "Drive to commuter rail"      ) ~ (ddist_wlk_com_drv/100.0)*model_params$auto_op_cost,
            .default = NA  # otherwise use value that is set already
        )
    )
    # delete cost_skim columns; we're done with them
    relevant <- select(relevant, ! any_of(colnames(cost_skims)))

    # apply means based transit fare factors
    # c_cost*WLK_LOC_WLK_FAR[tripPeriod]*
    #     if(hhIncomeQ1=1, if((origCordon+destCordon)>0, %Means_Based_Cordon_Fare_Q1Factor%, %Means_Based_Fare_Q1Factor%), 1)*
    #     if(hhIncomeQ2=1, if((origCordon+destCordon)>0, %Means_Based_Cordon_Fare_Q2Factor%, %Means_Based_Fare_Q2Factor%), 1)
    relevant <- mutate(relevant,
        fare = ifelse(incQ == 1, ifelse( (CORDON_orig>0)|(CORDON_dest>0), model_params$means_based_cordon_fare_q1_factor, model_params$means_based_fare_q1_factor)*fare, fare),
        fare = ifelse(incQ == 2, ifelse( (CORDON_orig>0)|(CORDON_dest>0), model_params$means_based_cordon_fare_q2_factor, model_params$means_based_fare_q2_factor)*fare, fare)
    )

    # cost sharing applies to SR2, SR3 for Bridge tolls (and therefore Cordon tolls), Value tolls, but *not* auto operating costs
    relevant <- mutate(relevant,
        bridge_toll = ifelse( (mode_name=="Shared ride two - free")  |(mode_name=="Shared ride two - pay"  ), bridge_toll/COST_SHARE_SR2, bridge_toll ),
        bridge_toll = ifelse( (mode_name=="Shared ride three - free")|(mode_name=="Shared ride three - pay"), bridge_toll/COST_SHARE_SR3, bridge_toll ),
        cordon_toll = ifelse( (mode_name=="Shared ride two - free")  |(mode_name=="Shared ride two - pay"  ), cordon_toll/COST_SHARE_SR2, cordon_toll ),
        cordon_toll = ifelse( (mode_name=="Shared ride three - free")|(mode_name=="Shared ride three - pay"), cordon_toll/COST_SHARE_SR3, cordon_toll ),
        value_toll  = ifelse( (mode_name=="Shared ride two - free")  |(mode_name=="Shared ride two - pay"  ), value_toll /COST_SHARE_SR2, value_toll  ),
        value_toll  = ifelse( (mode_name=="Shared ride three - free")|(mode_name=="Shared ride three - pay"), value_toll /COST_SHARE_SR3, value_toll  )
    )
    # final version for this time period
    # print_cost_summary(relevant)

    return(bind_rows(relevant, irrelevant))
}

####################################### add_parking_cost ###########################################
# 
# Copied (! I know!) on tallyParking.R
add_parking_cost <- function(trips) {
    print("add_parking_cost()")

    # find first and last stop in the tour
    print("Finding first and last stop for each tour leg")
    first_last_stop <- group_by(trips, hh_id, person_id, tour_id, inbound) %>% 
        summarise(first_stop = min(stop_id),
                    last_stop  = max(stop_id))

    # and merge it back in, set stopIsFirst and stopIsLast
    trips <- left_join(trips, first_last_stop, by=c("hh_id","person_id","tour_id","inbound"))
    trips <- mutate(trips, 
        stopIsFirst = (stop_id==first_stop),
        stopIsLast  = (stop_id==last_stop)
    )
    # replication originDuration/destDuration from TripModeChoice UEC
    trips <- mutate(trips,
        originDuration = case_when(
          (inbound==0)&(stopIsFirst) ~ 0.0,           # if origin is at home
          (inbound==1)&(stopIsFirst) ~ tour_duration, # if origin is tour primary destination
          (stopIsFirst==FALSE)       ~ 1.0            # if origin is intermediate stop
        ),
        destDuration = case_when(
          (inbound==1)&(stopIsLast) ~ 0.0,            # if destination is at home
          (inbound==0)&(stopIsLast) ~ tour_duration,  # if destination is tour primary destination
          (stopIsLast==FALSE)       ~ 1.0             # if destination is intermediate stop
        ))

    trips <- mutate(trips, 
        originParkingCost=originDuration*PRKCST_orig,
        destParkingCost  =destDuration  *PRKCST_dest,
        totalParkingCost =(originParkingCost+destParkingCost)/2.0)

    # divide out costs for SR2 and SR3 (note: for tours, CoreSummaries.R does this but for the trips version, it's here)
    # no special treatment for joint trips
    trips <- mutate(trips,
        originParkingCost = case_when(
          (trip_mode==3)|(trip_mode==4) ~ originParkingCost/COST_SHARE_SR2,
          (trip_mode==5)|(trip_mode==6) ~ originParkingCost/COST_SHARE_SR3,
          .default = originParkingCost
        ),
        destParkingCost = case_when(
          (trip_mode==3)|(trip_mode==4) ~ destParkingCost/COST_SHARE_SR2,
          (trip_mode==5)|(trip_mode==6) ~ destParkingCost/COST_SHARE_SR3,
          .default = destParkingCost
        ),
        totalParkingCost = case_when(
          (trip_mode==3)|(trip_mode==4) ~ totalParkingCost/COST_SHARE_SR2,
          (trip_mode==5)|(trip_mode==6) ~ totalParkingCost/COST_SHARE_SR3,
          .default = totalParkingCost
        ))

    # note: we do NOT convert to 2000 dollars; we'll keep in cents
    # trips <- mutate(trips,
    #    originParkingCost = originParkingCost*0.01,
    #    destParkingCost   = destParkingCost*0.01,
    #    totalParkingCost  = totalParkingCost*0.01)

    # zero out for non auto trips
    trips <- mutate(trips, 
        originParkingCost=ifelse(trip_mode>6,0,originParkingCost),
        destParkingCost  =ifelse(trip_mode>6,0,destParkingCost  ),
        totalParkingCost =ifelse(trip_mode>6,0,totalParkingCost ))
    # zero out for work tours if person has fp_choice
    trips <- mutate(trips,
        originParkingCost=ifelse((substr(tour_purpose,0,4)=='work')&(fp_choice==1),0.0,originParkingCost),
        destParkingCost  =ifelse((substr(tour_purpose,0,4)=='work')&(fp_choice==1),0.0,destParkingCost),
        totalParkingCost =ifelse((substr(tour_purpose,0,4)=='work')&(fp_choice==1),0.0,totalParkingCost))
    return(trips)
}

############################################### main ################################################
options(
    pillar.width=200,
    pillar.print_max=50
)
stopifnot(nchar(TARGET_DIR)>0)

print(paste0("TARGET_DIR  = ",TARGET_DIR))
print(paste0("SAMPLESHARE = ",SAMPLESHARE))

# instantiate means_based_discount_factors for this dir
MODEL_PARAMS <- model_parameters(TARGET_DIR)
print(MODEL_PARAMS)

# read tazdata with parking costs and cordon costs
tazdata <- read_csv(file=TAZDATA_FILE) 
# print(str(tazdata))
tazdata <- select(tazdata, ZONE, PRKCST, OPRKCST, CORDON, CORDONCOST)

load(file.path(TARGET_DIR, "updated_output", "trips.rdata"))
print(str(trips))
# select only columns we need
trips <- select(trips, hh_id, person_id, incQ, incQ_label, home_taz,
    income, autos, inbound, trip_mode, cost,
    tour_purpose, tour_id, stop_id, tour_duration, fp_choice,  # parking-related
    orig_taz, dest_taz, timeCode)

# left join on lookup
trips <- left_join(trips, LOOKUP_MODE)
# print(head(trips))

# left join on taz data at origin
trips <- left_join(x=trips, y=tazdata, by=c("orig_taz"="ZONE")) %>% 
    rename(PRKCST_orig = PRKCST, OPRKCST_orig = OPRKCST, CORDON_orig = CORDON, CORDONCOST_orig = CORDONCOST)
# left join on taz data at dest
trips <- left_join(x=trips, y=tazdata, by=c("dest_taz"="ZONE")) %>% 
    rename(PRKCST_dest = PRKCST, OPRKCST_dest = OPRKCST, CORDON_dest = CORDON, CORDONCOST_dest = CORDONCOST)
print(head(trips))

# separate cost into auto cost versus transit fare
# Note: from SkimsDatabase.JOB, drive to transit costs are fare driven
trips <- mutate(trips,
    transit_cost = ifelse(is_transit, cost, 0),
    auto_cost    = ifelse(is_transit==FALSE, cost, 0)  # Note: Taxi/TNC included here
)

# add detailed parking cost information
trips <- add_parking_cost(trips)
# add detailed cost information
for (timeperiod in c("EA","AM","MD","PM","EV")) {
    trips <- add_detailed_cost(MODEL_PARAMS, timeperiod, trips)
}
print_cost_summary(trips)

# summarize by household on is_auto, is_transit
hhld_trips_summary <- group_by(trips, hh_id) %>%
    summarise(
        hhld_trips = n(),
        hhld_auto_trips = sum(is_auto),
        hhld_transit_trips = sum(is_transit)
    )

# summarize at household level
hhld_trips_summary <- mutate(hhld_trips_summary,
    hhld_travel = case_when(
        (hhld_auto_trips >  0) & (hhld_transit_trips  > 0) ~ "auto_and_transit",
        (hhld_auto_trips >  0) & (hhld_transit_trips == 0) ~ "auto_no_transit",
        (hhld_auto_trips == 0) & (hhld_transit_trips  > 0) ~ "transit_no_auto",
        (hhld_auto_trips == 0) & (hhld_transit_trips == 0) ~ "no_auto_no_transit"), 
    hhld_travel = factor(hhld_travel, levels=c("auto_and_transit","auto_no_transit", "transit_no_auto","no_auto_no_transit"))
)
print("hhld_trips_summary head: ")
print(head(hhld_trips_summary))

# join back to trips and summarize trip costs
trips <- left_join(trips, hhld_trips_summary)
# print(head(trips))

# need autos / income summary by household by income, home_taz, hhld_travel(segment)
hhld_autos_income_summary <- group_by(trips, hh_id, incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise( 
        hhld_autos  = max(autos),  # max, min, avg -- should all be the same
        hhld_income = max(income)  # max, min, avg -- should all be the same
    )
# zero out negative household income
hhld_autos_income_summary <- mutate(hhld_autos_income_summary,
    hhld_income = ifelse(hhld_income < 0, 0, hhld_income)
)
print("hhld_autos_income_summary:")
print(head(hhld_autos_income_summary))
# summarize again to aggregate for households
hhld_autos_income_summary <- group_by(hhld_autos_income_summary, 
    incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise( 
        total_hhld_autos  = sum(hhld_autos),
        total_hhld_income = sum(hhld_income)
    )
print("hhld_autos_income_summary:")
print(head(hhld_autos_income_summary))

# save trips with detailed cost
detailed_file <- file.path(TARGET_DIR, "updated_output", "trips_with_detailed_cost.rdata")
save(trips, file=detailed_file)
print(paste("Wrote",detailed_file))

# everything is a total so divide by sampleshare
trip_summary <- group_by(trips, incQ, incQ_label, home_taz, hhld_travel) %>%
    summarise(
        num_hhlds             = n_distinct(hh_id)     / SAMPLESHARE,
        num_persons           = n_distinct(person_id) / SAMPLESHARE,
        num_auto_trips        = sum(is_auto)          / SAMPLESHARE,
        num_transit_trips     = sum(is_transit)       / SAMPLESHARE,
        # original simple costs
        total_auto_cost       = sum(auto_cost)        / SAMPLESHARE,
        total_transit_cost    = sum(transit_cost)     / SAMPLESHARE,
        total_cost            = sum(cost)             / SAMPLESHARE,
        # detailed cost
        total_parking_cost    = sum(totalParkingCost, na.rm=T) / SAMPLESHARE,
        total_auto_op_cost    = sum(auto_op_cost,     na.rm=T) / SAMPLESHARE,
        total_bridge_toll     = sum(bridge_toll,      na.rm=T) / SAMPLESHARE,
        total_cordon_toll     = sum(cordon_toll,      na.rm=T) / SAMPLESHARE,
        total_value_toll      = sum(value_toll,       na.rm=T) / SAMPLESHARE,
        total_fare            = sum(fare,             na.rm=T) / SAMPLESHARE,
        total_drv_trn_op_cost = sum(drv_trn_op_cost,  na.rm=T) / SAMPLESHARE,
    )

print("trip_summary: ")
print(trip_summary)

# join with hhld_autos_summary
trip_summary <- left_join(trip_summary, hhld_autos_income_summary) %>%
    mutate(total_hhld_autos = total_hhld_autos / SAMPLESHARE,
           total_hhld_income = total_hhld_income/SAMPLESHARE)

# total detailed costs
trip_summary <- mutate(trip_summary,
    total_detailed_auto_cost    = total_parking_cost + total_auto_op_cost + total_bridge_toll + total_cordon_toll + total_value_toll,
    total_detailed_transit_cost = total_fare + total_drv_trn_op_cost,
)

write.csv(trip_summary, file = OUTPUT_FILE, row.names = FALSE, quote = F)
print(paste("Wrote",nrow(trip_summary),"rows to",OUTPUT_FILE))

# long version auto - for stacking in tableau
trip_summary_auto <- pivot_longer(
    select(trip_summary, 
        incQ, incQ_label, hhld_travel, 
        num_hhlds, num_persons, num_auto_trips, num_transit_trips, total_hhld_autos, total_hhld_income,
        total_parking_cost, total_auto_op_cost, total_bridge_toll, total_cordon_toll, total_value_toll),
    cols=c(total_parking_cost, total_auto_op_cost, total_bridge_toll, total_cordon_toll, total_value_toll),
    names_to="auto_cost_type",
    values_drop_na = TRUE
)
auto_output_file = str_replace(OUTPUT_FILE, ".csv", "-auto.csv")
write.csv(trip_summary_auto, file = auto_output_file, row.names = FALSE, quote = F)
print(paste("Wrote",nrow(trip_summary_auto),"rows to",auto_output_file))


# long version transit - for stacking in tableau
trip_summary_transit <- pivot_longer(
    select(trip_summary, 
        incQ, incQ_label, hhld_travel, 
        num_hhlds, num_persons, num_auto_trips, num_transit_trips, total_hhld_autos, total_hhld_income,
        total_fare, total_drv_trn_op_cost),
    cols=c(total_fare, total_drv_trn_op_cost),
    names_to="transit_cost_type",
    values_drop_na = TRUE
)
print("trip_summary_transit: ")
print(trip_summary_transit)

transit_output_file = str_replace(OUTPUT_FILE, ".csv", "-transit.csv")
write.csv(trip_summary_transit, file = transit_output_file, row.names = FALSE, quote = F)
print(paste("Wrote",nrow(trip_summary_transit),"rows to",transit_output_file))
