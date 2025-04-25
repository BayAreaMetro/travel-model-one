library(dplyr)
library(sf)

# example call:
  # set PATH=%PATH%;C:\Program Files\R\R-3.6.2\bin
  # Rscript X:\travel-model-one-master\utilities\RTP\metrics\vmt_per_capita.r 2025

#########################################################################
# Calculates VMT per capita by place of residence and place of work
# for VMT Maps on arcgis online
# RTP 2013:
#   VMT by Place of Residence: 
#     https://mtc.maps.arcgis.com/home/item.html?id=5b11f6b61be344cdb13ffd5eacfba5eb (feature layer)
#     https://mtc.maps.arcgis.com/home/item.html?id=034f499840964a979a1572a25ac07681 (web map)
#   VMT by Place of Work:
#     https://mtc.maps.arcgis.com/home/item.html?id=24b46bec2e794a90b4aaba335b60c3bc (feature layer)
#     https://mtc.maps.arcgis.com/home/item.html?id=ece1f7085d2c4985b29d4953b63d94bb (web map)
#
# RTP 2017:
#   VMT by Place of Residence:
#     https://mtc.maps.arcgis.com/home/item.html?id=6d25504c0fde416a995d52c62a5d9e4c (feature layer)
#     https://mtc.maps.arcgis.com/home/item.html?id=2bddae2c822146a7a8e98892a6d4ee2f (web map)
#   VMT by Place of Work:
#     https://mtc.maps.arcgis.com/home/item.html?id=5264fa93cf7648469221d1405f6a3174 (feature layer)
#     https://mtc.maps.arcgis.com/home/item.html?id=6253e74fca1d463c92c15011a12a4a69 (web map)
#########################################################################

args = commandArgs(trailingOnly=TRUE)
print(args)
if (length(args) != 1) {
  stop("One arguments is required: RTP number, e.g. 2025")
}

# VMT data from model output
RTP <- args[1]
RTP_DIR    <- paste0("M:/Application/Model One/RTP",RTP)
if (RTP==2013) { SCEN_DIR <- file.path(RTP_DIR, "Scenarios","Round 05 -- Final")}
if (RTP==2017) { SCEN_DIR <- file.path(RTP_DIR, "Scenarios")}
if (RTP==2021) { SCEN_DIR <- RTP_DIR}
if (RTP==2025) { SCEN_DIR <- RTP_DIR}

if ((RTP==2021) || (RTP==2025)) {
  OUTPUT_DIR <- file.path(SCEN_DIR, "Blueprint", "VMT per capita or worker")
} else {
  OUTPUT_DIR <- file.path(RTP_DIR, "VMT per capita or worker")}

OUTPUT_GIS_DIR <- file.path(OUTPUT_DIR, "GIS")

if (RTP==2013) {
  # MODEL_RUN_IDS <- c("2020_03_116", "2030_03_116", "2040_03_116")
  # 2040 is the only one with core_summaires
  MODEL_RUN_IDS <- c("2040_03_116")
} else if (RTP==2017) {
  MODEL_RUN_IDS <- c("2015_06_002", "2020_06_694", "2030_06_694", "2040_06_694_Amd1")
} else if (RTP==2021) {
  MODEL_RUN_IDS <- c("2015_TM152_IPA_17",
                     "2025_TM152_FBP_Plus_22",
                     "2030_TM152_FBP_Plus_23",
                     "2035_TM152_FBP_NoProject_24", "2035_TM152_FBP_Plus_24",
                     "2035_TM152_EIR_Alt1_06", "2035_TM152_EIR_Alt2_04",
                     "2040_TM152_FBP_Plus_24",
                     "2050_TM152_FBP_NoProject_24", "2050_TM152_FBP_PlusCrossing_24",
                     "2050_TM152_EIR_Alt1_06", "2050_TM152_EIR_Alt2_05")
} else if (RTP==2025) {
  MODEL_RUN_IDS <- c("2005_TM161_IPA_01",
                     "2015_TM161_IPA_09",
                     "2023_TM161_IPA_35",
                     "2035_TM160_DBP_Plan_08b",
                     "2050_TM160_DBP_Plan_08b",
                     "2035_TM161_FBP_NoProject_13",
                     "2035_TM161_FBP_NPtoPlan_13_seq2",
                     "2035_TM161_FBP_NPtoPlan_13_seq3",
                     "2035_TM161_FBP_NPtoPlan_13_seq4",
                     "2035_TM161_FBP_NPtoPlan_13_seq5",
                     "2035_TM161_FBP_NPtoPlan_13_seq6",
                     "2035_TM161_FBP_NPtoPlan_13_seq7",
                     "2035_TM161_FBP_Plan_13",
                     "2050_TM161_FBP_NoProject_13",
                     "2050_TM161_FBP_NPtoPlan_13_seq2")
}


# TAZ1454 spatial data
taz_shp <- st_read('M:\\Data\\GIS layers\\Travel_Analysis_Zones_(TAZ1454)\\Travel Analysis Zones.shp')


# Loop through runs
for (MODEL_RUN_ID in MODEL_RUN_IDS) {
  print(MODEL_RUN_ID)

  # directory of core_summaries
  if ((RTP==2013) || (RTP==2017)) {
      CORE_SUMMARIES_DIR <- file.path(SCEN_DIR,MODEL_RUN_ID,"OUTPUT","core_summaries")
    } else if ((RTP==2021) && (MODEL_RUN_ID!='2015_TM152_IPA_17')) {
      CORE_SUMMARIES_DIR <- file.path(SCEN_DIR,'Blueprint', MODEL_RUN_ID,"OUTPUT","core_summaries")
    } else if ((RTP==2021) && (MODEL_RUN_ID=='2015_TM152_IPA_17')) {
      CORE_SUMMARIES_DIR <- file.path(SCEN_DIR,'IncrementalProgress', MODEL_RUN_ID,"OUTPUT","core_summaries")
    } else if ((RTP==2025) && ((MODEL_RUN_ID=='2005_TM161_IPA_01') || (MODEL_RUN_ID=='2015_TM161_IPA_09') || (MODEL_RUN_ID=='2023_TM161_IPA_35'))) {
      CORE_SUMMARIES_DIR <- file.path(SCEN_DIR,'IncrementalProgress', MODEL_RUN_ID,"OUTPUT","core_summaries")
    } else if ((RTP==2025) && (MODEL_RUN_ID!='2005_TM161_IPA_01') && (MODEL_RUN_ID!='2015_TM161_IPA_09') && (MODEL_RUN_ID!='2023_TM161_IPA_35')) {
      CORE_SUMMARIES_DIR <- file.path(SCEN_DIR,'Blueprint', MODEL_RUN_ID,"OUTPUT","core_summaries")
    }
  
  vmt_data <- file.path(CORE_SUMMARIES_DIR, "AutoTripsVMT_perOrigDestHomeWork.rdata")

  print("vmt_data")
  print(vmt_data)
  load(vmt_data)

  # sum vmt to residence and work location
  total_vmt_by_residence <- ungroup(model_summary) %>% group_by(taz) %>% summarise(total_vmt = sum(vmt))
  total_vmt_by_workplace <- ungroup(model_summary) %>% group_by(WorkLocation) %>% summarise(total_vmt = sum(vmt))
  
  persons_data <- file.path(CORE_SUMMARIES_DIR, "AutoTripsVMT_personsHomeWork.rdata")
  print("persons_data")
  print(persons_data)
  load(persons_data)

  # sum population to residence and work location
  total_pop_by_residence <- ungroup(model_summary) %>% group_by(taz) %>% summarise(total_pop = sum(freq))
  total_pop_by_workplace <- ungroup(model_summary) %>% group_by(WorkLocation) %>% summarise(total_pop = sum(freq))
  
  # join it up
  vmt_pop_by_residence <- merge(total_vmt_by_residence, total_pop_by_residence, by="taz", all=TRUE) %>%
    mutate(vmtpercapita=total_vmt/total_pop)

  vmt_pop_by_workplace <- merge(total_vmt_by_workplace, total_pop_by_workplace, by="WorkLocation", all=TRUE) %>%
    mutate(vmtperworker=total_vmt/total_pop)
  
  # write it
  home_csv = file.path(OUTPUT_DIR, paste0("Home_",MODEL_RUN_ID,".csv"))
  work_csv = file.path(OUTPUT_DIR, paste0("Work_",MODEL_RUN_ID,".csv"))
  print("write out .csv tables")
  print(home_csv)
  print(work_csv)
  if (!file.exists(home_csv)) {
    write.csv(vmt_pop_by_residence, home_csv, row.names=FALSE)
  }
  if (!file.exists(work_csv)) {
    write.csv(vmt_pop_by_workplace, work_csv, row.names=FALSE)
  }

  # join to TAZ1454 shapes
  vmt_pop_by_residence <- vmt_pop_by_residence %>% rename('TAZ1454' = 'taz')
  vmt_pop_by_workplace <- vmt_pop_by_workplace %>% rename('TAZ1454' = 'WorkLocation')
  vmt_pop_by_residence_shp <- taz_shp %>% left_join(vmt_pop_by_residence, by='TAZ1454')
  vmt_pop_by_workplace_shp <- taz_shp %>% left_join(vmt_pop_by_workplace, by='TAZ1454')
  
  # write it
  home_shp = file.path(OUTPUT_GIS_DIR, paste0("Home_",MODEL_RUN_ID,".shp"))
  work_shp = file.path(OUTPUT_GIS_DIR, paste0("Work_",MODEL_RUN_ID,".shp"))
  print("write out .shp files")
  print(home_shp)
  print(work_shp)
  if (!file.exists(home_shp)) {
    st_write(vmt_pop_by_residence_shp, home_shp)
  }
  if (!file.exists(work_shp)) {
    st_write(vmt_pop_by_workplace_shp, work_shp)
  }
  
}

