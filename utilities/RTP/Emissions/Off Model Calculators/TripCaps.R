#
# This R script distills the model outputs into the versions used by ICF calculator: "Trip caps v8.xlsx"
#

library(dplyr)
library(reshape2)
options(width = 180)

USERNAME            <- Sys.getenv("USERNAME")
BOX_BASE_DIR        <- file.path("C:/Users", USERNAME, "Box/Horizon and Plan Bay Area 2050/Blueprint/CARB SCS Evaluation")
MODEL_DATA_BASE_DIRS<- c(IP            ="M:/Application/Model One/RTP2021/IncrementalProgress",
                         DraftBlueprint="M:/Application/Model One/RTP2021/Blueprint",
                         FinalBlueprint="M:/Application/Model One/RTP2021/Blueprint")
OUTPUT_DIR          <- file.path(BOX_BASE_DIR, "Final Blueprint/OffModel_FBP/ModelData")
OUTPUT_FILE         <- file.path(OUTPUT_DIR, "Model Data - Trip Caps.csv")

# this is the currently running script
SCRIPT                <- "X:/travel-model-one-master/utilities/RTP/Emissions/Off Model Calculators/TripCaps.R"
# the model runs are RTP/ModelRuns.csv
model_runs          <- read.table(file.path(dirname(SCRIPT),"..","..","ModelRuns.csv"), header=TRUE, sep=",", stringsAsFactors = FALSE)

# filter to the current runs
model_runs          <- model_runs[ which(model_runs$status == "current"), ]

print(paste("MODEL_DATA_BASE_DIRS = ",MODEL_DATA_BASE_DIRS))
print(paste("OUTPUT_DIR          = ",OUTPUT_DIR))
print(model_runs)

# Calculator constants
# Criteria for applying trip caps
K_ONLY_EMPCENTER  <- TRUE   # Trip caps apply only in employment centers (areas with more jobs than households)
K_ONLY_URBSUBURB  <- TRUE   # Trip caps apply only in urban/suburban areas
K_ONLY_COMMGROWTH <- FALSE   # Trip caps apply only in areas that experience growth in zoned commercial space

# Effectiveness of programs
K_TRIPCAP_FROM_MTNVIEW <- -0.396971007  # Change in average trips per day per employee due to trip caps, based on Mountain View
K_COMPLIANCE           <-  1.0          # Assumed compliance with trip caps in areas where they are applicable
K_AVG_CARPOOL_OCC      <- 2.581396053   # Average carpool occupancy

# Read tazdata
TAZDATA_FIELDS <- c("ZONE", "SD", "COUNTY", "TOTEMP", "TOTHH", "CIACRE", "AREATYPE") # only care about these fields
tazdata_df     <- data.frame()
for (i in 1:nrow(model_runs)) {
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
  tazdata_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"INPUT","landuse", "tazData.csv")
  tazdata_file_df <- read.table(tazdata_file, header=TRUE, sep=",")
  tazdata_file_df <- tazdata_file_df[, TAZDATA_FIELDS] %>%
    mutate(year      = model_runs[i,"year"],
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
  tazdata_df      <- rbind(tazdata_df, tazdata_file_df)
}
remove(tazdata_file, tazdata_file_df)

# TAZ data vs 2015
# Keep total employment, total households, and commercial/industrial acres
# http://analytics.mtc.ca.gov/foswiki/Main/TazData
# TODO: update to RTP2021 2015 when we have one
tazdata_2015_df <- read.table("M:/Application/Model One/RTP2017/Scenarios/2015_06_002/OUTPUT/tazData.csv", header=TRUE, sep=",")
tazdata_2015_df <- tazdata_2015_df[, c("ZONE", "TOTEMP", "TOTHH", "CIACRE", "AREATYPE")] %>%
  rename(TOTEMP_2015=TOTEMP, TOTHH_2015=TOTHH, CIACRE_2015=CIACRE, AREATYPE_2015=AREATYPE)

tazdata_df <- left_join(tazdata_df, tazdata_2015_df, by=c("ZONE")) %>%
  mutate(TOTEMP_diff_from_2015 = TOTEMP-TOTEMP_2015,
         CIACRE_diff_from_2015 = CIACRE-CIACRE_2015)

# trip cap criteria
# see areatype codes: http://analytics.mtc.ca.gov/foswiki/Main/TazData
tazdata_df <- mutate(tazdata_df,
                     empcenter_2015=(TOTEMP_2015>TOTHH_2015),                # 2015 employment > households
                     urbsuburb_2015=((AREATYPE_2015==3)|(AREATYPE_2015==4)), # 2015 areatype is 3 (urban) or 4 (suburban)
                     commgrowth    =(CIACRE_diff_from_2015>0))               # growth in commercial/industrial acres from 2015

# if the tripcap criteria are on, then they're required to be 1 to apply them.
tazdata_df <- mutate(tazdata_df,
                     apply_tripcap_bool= ((!K_ONLY_EMPCENTER )|empcenter_2015)&
                                         ((!K_ONLY_URBSUBURB )|urbsuburb_2015)&
                                         ((!K_ONLY_COMMGROWTH)|commgrowth)) %>%
              mutate(apply_tripcap_compliance =K_COMPLIANCE*apply_tripcap_bool)

# Read trip-distance-by-mode-superdistrict.csv
tripdist_df <- data.frame()
for (i in 1:nrow(model_runs)) {
  MODEL_DATA_BASE_DIR <- MODEL_DATA_BASE_DIRS[model_runs[i,"run_set"]]
  tripdist_file    <- file.path(MODEL_DATA_BASE_DIR, model_runs[i,"directory"],"OUTPUT","bespoke","trip-distance-by-mode-superdistrict.csv")
  if (!file.exists(tripdist_file)) {
    stop(paste0("File [",tripdist_file,"] does not exist"))
  }
  tripdist_file_df <- read.table(tripdist_file, header=TRUE, sep=",") %>% 
    mutate(year      = model_runs[i,"year"],
           directory = model_runs[i,"directory"],
           category  = model_runs[i,"category"])
  tripdist_df      <- rbind(tripdist_df, tripdist_file_df)
}
remove(i, tripdist_file, tripdist_file_df)

# calculate carpool occupancy.  tripdist is person trips
tripdist_sr2015_df <- tripdist_df[ (tripdist_df$year==2015)&(substr(tripdist_df$mode_name,1,11)=="Shared ride"), ]
tripdist_sr2015_df <- mutate(tripdist_sr2015_df,
                             carpool_occ = (substr(mode_name,1,15)=="Shared ride two"  )*2.0 +
                                           (substr(mode_name,1,17)=="Shared ride three")*3.25,
                             vehicle_trips = estimated_trips/carpool_occ)

K_AVG_CARPOOL_OCC_NEW <- sum(tripdist_sr2015_df$estimated_trips)/sum(tripdist_sr2015_df$vehicle_trips)
cat(paste("old carpool occ:",K_AVG_CARPOOL_OCC))
cat(paste("new carpool occ:",K_AVG_CARPOOL_OCC_NEW))

# trip-distance-by-mode-superdistrict rollups
# tour_purpose and trip_mode coding: http://analytics.mtc.ca.gov/foswiki/Main/IndividualTrip
tripdist_df <- mutate(tripdist_df,
                      total_distance = mean_distance*estimated_trips,
                      work_trip      = substr(tour_purpose,1,5)=="work_",
                      drive_alone    = substr(mode_name,1,11)=="Drive alone",
                      shared_ride    = substr(mode_name,1,11)=="Shared ride") %>%
               mutate(total_distance_commute_drive  = total_distance*work_trip*(drive_alone|shared_ride),
                      estimated_trips_commute_drive = estimated_trips*work_trip*(drive_alone|shared_ride),
                      estimated_trips_commute       = estimated_trips*work_trip,
                      estimated_trips_commute_da    = estimated_trips*work_trip*drive_alone,
                      estimated_trips_commute_sr    = estimated_trips*work_trip*shared_ride)

# For Trip Caps v5: need drive alone mode share of commute trips by destination superdistrict
#                        shared ride mode share of commute trips by destination superdistrict
tripdist_sd_summary_df <- summarize(group_by(tripdist_df, year, category, directory, dest_sd),
                                    total_distance_commute_drive  = sum(total_distance_commute_drive),
                                    estimated_trips_commute_drive = sum(estimated_trips_commute_drive),
                                    estimated_trips_commute       = sum(estimated_trips_commute),
                                    estimated_trips_commute_da    = sum(estimated_trips_commute_da),
                                    estimated_trips_commute_sr    = sum(estimated_trips_commute_sr)) %>%
  mutate(da_modeshare_of_commute = estimated_trips_commute_da/estimated_trips_commute,
         sr_modeshare_of_commute = estimated_trips_commute_sr/estimated_trips_commute,
         avg_commute_drive_distance = total_distance_commute_drive/estimated_trips_commute_drive)

# calculate average trips per employee for the scenario
# and apply the trip cap
tripdist_sd_summary_df <- tripdist_sd_summary_df %>%
  mutate(avg_trips_per_employee = (da_modeshare_of_commute+sr_modeshare_of_commute/K_AVG_CARPOOL_OCC)*2.0,
         avg_trips_per_employee_capped = avg_trips_per_employee*(1+K_TRIPCAP_FROM_MTNVIEW))

# this is special -- keep 2015 supderdistrict 9 row (Mountain View)
tripdist_sd_summary_df_2035_sd9 <- tripdist_sd_summary_df[ (tripdist_sd_summary_df$directory=="2015_06_002")&
                                                           (tripdist_sd_summary_df$dest_sd==9), 
                                                           c("year","category","directory",
                                                             "da_modeshare_of_commute","sr_modeshare_of_commute")] %>%
  rename(da_modeshare_of_commute_sd9=da_modeshare_of_commute,
         sr_modeshare_of_commute_sd9=sr_modeshare_of_commute)

# we only want these columns
tripdist_sd_summary_df <- select(tripdist_sd_summary_df,
                                 year, directory, category, dest_sd, 
                                 avg_trips_per_employee, avg_trips_per_employee_capped, avg_commute_drive_distance)
tripdist_sd_summary_df <- data.frame(tripdist_sd_summary_df, stringsAsFactors = FALSE)

# back to tazdata -- join to the superdistrict-based trip caps
tazdata_df <- left_join(tazdata_df,
                        tripdist_sd_summary_df, by=c("year"     ="year",
                                                     "directory"="directory",
                                                     "category" ="category",
                                                     "SD"       ="dest_sd"))

# apply the tripcap to get trip reductions
tazdata_df <- mutate(tazdata_df,
                     daily_vehtrip_reduction = apply_tripcap_compliance*TOTEMP_diff_from_2015*(avg_trips_per_employee-avg_trips_per_employee_capped),
                     daily_VMT_reduction = daily_vehtrip_reduction*avg_commute_drive_distance)

# check
test <- tazdata_df[ tazdata_df$directory=="2020_06_694",]
sum(test$daily_vehtrip_reduction)
sum(test$daily_VMT_reduction)


# keep only the columns we want
summary_df <- summarise(group_by(tazdata_df, year, category, directory),
                        daily_vehtrip_reduction = sum(daily_vehtrip_reduction),
                        daily_VMT_reduction     = sum(daily_VMT_reduction))

# columns are: year, category, directory, variable, value
summary_melted_df <- melt(summary_df, id.vars=c("year","category","directory"))

# add special mountain view mode shares
tripdist_melted_df <- melt(tripdist_sd_summary_df_2035_sd9, id.vars=c("year","category","directory"))
summary_melted_df  <- rbind(summary_melted_df, tripdist_melted_df)
  
# add index column for vlookup
summary_melted_df <- mutate(summary_melted_df,
                            index = paste0(year,"-",category,"-",variable))
summary_melted_df <- summary_melted_df[order(summary_melted_df$index),
                                       c("index","year","category","directory","variable","value")]
# print(summary_melted_df)

# prepend note
prepend_note <- paste0("Output by ",SCRIPT," on ",format(Sys.time(), "%a %b %d %H:%M:%S %Y"))
write(prepend_note, file=OUTPUT_FILE, append=FALSE)

prepend_note <- paste0("K_ONLY_EMPCENTER,"      ,K_ONLY_EMPCENTER,      "\n",
                       "K_ONLY_URBSUBURB,"      ,K_ONLY_URBSUBURB,      "\n",
                       "K_ONLY_COMMGROWTH,"     ,K_ONLY_COMMGROWTH,     "\n",
                       "K_TRIPCAP_FROM_MTNVIEW,",K_TRIPCAP_FROM_MTNVIEW,"\n",
                       "K_COMPLIANCE,"          ,K_COMPLIANCE,          "\n",
                       "K_AVG_CARPOOL_OCC,"     ,K_AVG_CARPOOL_OCC)
write(prepend_note, file=OUTPUT_FILE, append=TRUE)

# output
write.table(summary_melted_df, OUTPUT_FILE, sep=",", row.names=FALSE, append=TRUE)
