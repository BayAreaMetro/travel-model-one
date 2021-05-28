#
# This R script opens the output network csvs
# and left_joins them to the emissions rates based on county, model year, care/non-care
# where "Speed" is joined on int(CSPD)
#
# PlanBayArea2050 / RTP2021 Asana Task: https://app.asana.com/0/316552326098022/1200007791721297/f

library(dplyr)
library(tidyr)
library(stringr)
library(readxl)

LOOKUP_COUNTY <- data.frame(county2      =c("AL", "CC", "MA", "NA", "SF", "SM", "SC", "SL", "SN"),
                            county_census=c("001","013","041","055","075","081","085","095","097"),
                            county_name  =c("Alameda", "Contra Costa", "Marin", "Napa", "San Francisco", "San Mateo", "Santa Clara", "Solano", "Sonoma"),
                            stringsAsFactors = FALSE)
MODEL_DIRS <- 
  c(IP_2015  ="M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_16",
    NP_2050  ="M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_NoProject_22",
    FBP_2050 ="M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_21",
    Alt1_2050="M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt1_03",
    Alt2_2050="M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt2_02")

# these are the shapefile exports of the inputs used in the above directories, corresponded to CARE and counties (link_to_COUNTY_CARE.csv)
NETWORK_CARE_DIRS <-
  c(IP_2015  ="M:/Application/Model One/RTP2021/IncrementalProgress/Networks/network_2015_03/shapefile",
    NP_2050  ="M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_53/net_2050_Baseline/shapefile",
    FBP_2050 ="M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_53/net_2050_Blueprint Plus Crossing/shapefile",
    Alt1_2050="M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_56/net_2050_Alt1/shapefile",
    Alt2_2050="M:/Application/Model One/RTP2021/Blueprint/INPUT_DEVELOPMENT/Networks/BlueprintNetworks_58/net_2050_Alt2/shapefile")

# all files are expected to be here (note R's preference for slashes)
if (Sys.getenv("USERNAME") == "lzorn") {
  BASE_DIR <- "C:/Users/lzorn/Box/CARE Communities/CARE-Data-PBA50"
} else {
  BASE_DIR <- "~/Desktop/CARE-Data_R"
}

# for avgload5period_vehclasses.csv
index_cols   <- c("a","b")
special_cols <- c("distance","lanes","ft","at","tollclass","ffs")

emissions_rates <- list()
# use Tableau wildcard union -- no need to put these in a single file
# loop through each network file
for (network in c("IP_2015","NP_2050","FBP_2050","Alt1_2050","Alt2_2050")) {
  model_dir  <- basename(MODEL_DIRS[network])
  model_year <- substr(model_dir,0,4)
  print(paste("Processing",network," for year",model_year,":",model_dir))
  
  network_file <- file.path(MODEL_DIRS[network],"OUTPUT","avgload5period_vehclasses.csv")
  network_df   <- read.table(network_file, header=TRUE, sep=",", stringsAsFactors=TRUE)
  print(paste(" Read",nrow(network_df),"rows from",network_file))
  print(str(network_df))
  
  # keep subset of columns
  network_df <- select(network_df, c(index_cols,special_cols, 
                                     starts_with("cspd"),                             # congested speed
                                     intersect(starts_with("vol"), ends_with("tot"))  # total volume
                                    ))
  print(head(network_df))
  
  # move timeperiod to rows for cspd
  cspd_df    <- select(network_df, c(index_cols, starts_with("cspd")))
  cspd_tp_df <- pivot_longer(cspd_df, starts_with("cspd"), names_to="time_period", names_prefix="cspd", values_to="cspd")
  # create int version for joining
  cspd_tp_df <- mutate(cspd_tp_df, cspd_int=as.integer(trunc(cspd)))
  print(head(cspd_tp_df))
  
  # move timeperiod to rows for voltot
  vol_df     <- select(network_df, c(index_cols, starts_with("vol")))
  vol_tp_df  <- pivot_longer(vol_df, starts_with("vol"), names_to="time_period", names_pattern="vol(.*)_tot", values_to="voltot")
  print(head(vol_tp_df))
  stopifnot(nrow(vol_tp_df) == nrow(cspd_tp_df))
  
  # put them back together
  network_long_df <- select(network_df, c(index_cols,special_cols))
  network_long_df <- full_join(network_long_df, cspd_tp_df, by=c("a","b"))
  network_long_df <- left_join(network_long_df, vol_tp_df,  by=c("a","b","time_period"))
  # set vmt
  network_long_df <- mutate(network_long_df, vmttot=voltot*distance)
  stopifnot(nrow(network_long_df) == nrow(cspd_tp_df))
  
  # read mapping to CARE
  care_file <- file.path(NETWORK_CARE_DIRS[network],"link_to_COUNTY_CARE.csv")
  care_df   <- read.table(care_file, header=TRUE, sep=",")
  print(paste("Read", nrow(care_df), "lines from",care_file,"; head:"))
  print(head(care_df))

  # combine with network_long
  network_long_care_df <- left_join(network_long_df, 
                                    select(care_df, A, B, COUNTYCARE, linkCC_share),
                                    by=c("a"="A", "b"="B"))
  # set county,CARE from COUNTYCARRER
  network_long_care_df <- mutate(network_long_care_df, 
                                 county_census=substr(COUNTYCARE,0,3),
                                 CARE=ifelse(str_length(COUNTYCARE)>3,1,0))
  
  # filter out dummy links
  network_long_care_df <- filter(network_long_care_df, ft != 6)
  print(paste("network_long_care_df has", nrow(network_long_care_df),"rows"))
  
  # read exhaust-based emissions
  if (is.null(emissions_rates[[paste0("AL-",model_year)]])) {
    emissions_file <- file.path(BASE_DIR, "PBA50_COC_ER_Lookups", paste("Year",model_year,"MSAT Emission Rates with E2021 (PBA2050).xlsx"))
    for (county2 in LOOKUP_COUNTY$county2) {
      sheet_name   <- paste0(county2,"-",model_year,".csv")
      emissions_df <- read_excel(emissions_file, sheet=sheet_name)
      # rename "-" and "." to "_"
      emissions_df <- emissions_df %>% setNames(gsub("\\-","_",names(.))) %>% setNames(gsub("\\.","_",names(.)))
      
      index_name   <- paste0(county2,"-",model_year)
      emissions_rates[[index_name]] <- emissions_df
    }
  }
  
  # read non-exhaust-based emission rates
  index_name <- paste0("non-exhaust-",model_year)
  if (is.null(emissions_rates[[index_name]])) {
    emissions_file <- file.path(BASE_DIR, "PBA50_COC_ER_Lookups", "PM2.5 Non-Exhaust ERs (w E2021 & Mar 2021 road dust update).xlsx")
    emissions_df   <- read_excel(emissions_file, sheet=model_year, skip=1)
    emissions_df   <- emissions_df %>% setNames(gsub(" ","_",names(.)))
    
    emissions_rates[[index_name]] <- emissions_df
  }
  
  # finally, join to emissions
  network_long_care_df <- mutate(network_long_care_df, 
                                 EO_PM2_5    =0.0,
                                 EO_Benzene  =0.0,
                                 EO_Butadiene=0.0,
                                 EO_DieselPM =0.0,
                                 ##### non-exhaust #####
                                 Tire_Wear          =0.0,
                                 Brake_Wear         =0.0,
                                 Entrained_Road_Dust=0.0)
  for (row in 1:nrow(LOOKUP_COUNTY)) {
    this_county2       <- LOOKUP_COUNTY[row, "county2"]
    this_county_census <- LOOKUP_COUNTY[row, "county_census"]
    this_county_name   <- LOOKUP_COUNTY[row, "county_name"]
    
    index_name    <- paste0(this_county2,"-",model_year)
    # print(head(emissions_rates[[index_name]]))
    
    non_exhaust_rates <- filter(emissions_rates[[paste0('non-exhaust-',model_year)]], County==this_county_name)
    
    # filter for this county
    this_co_df   <- filter(network_long_care_df, county_census == this_county_census)
    other_co_df  <- filter(network_long_care_df, (county_census != this_county_census) | is.na(county_census))
    stopifnot(nrow(this_co_df) + nrow(other_co_df) == nrow(network_long_care_df))
    
    # join based on congested speed int
    this_co_df <- left_join(this_co_df, emissions_rates[[index_name]], 
                            by=c("cspd_int"="Speed"))
    this_co_df <- mutate(this_co_df, 
                         EO_PM2_5    =ifelse(CARE==1, C_EO_PM2_5,     NC_EO_PM2_5),
                         EO_Benzene  =ifelse(CARE==1, C_EO_Benzene,   NC_EO_Benzene),
                         EO_Butadiene=ifelse(CARE==1, C_EO_Butadiene, NC_EO_Butadiene),
                         EO_DieselPM =ifelse(CARE==1, C_EO_DieselPM,  NC_EO_DieselPM),
                         # non-exhaust
                         Tire_Wear          =ifelse(CARE==1, non_exhaust_rates[['C_Tire_Wear'          ]], non_exhaust_rates[['NC_Tire_Wear'          ]]),
                         Brake_Wear         =ifelse(CARE==1, non_exhaust_rates[['C_Brake_Wear'         ]], non_exhaust_rates[['NC_Brake_Wear'         ]]),
                         Entrained_Road_Dust=ifelse(CARE==1, non_exhaust_rates[['C_Entrained_Road_Dust']], non_exhaust_rates[['NC_Entrained_Road_Dust']]))
    this_co_df <- select(this_co_df, 
                         -C_EO_PM2_5,     -NC_EO_PM2_5,
                         -C_EO_Benzene,   -NC_EO_Benzene,
                         -C_EO_Butadiene, -NC_EO_Butadiene,
                         -C_EO_DieselPM,  -NC_EO_DieselPM)
    network_long_care_df <- rbind(this_co_df, other_co_df)
  }

  # write the result
  output_fullpath <- file.path(BASE_DIR, "links_CARE_EMFAC2021", paste0("links_CARE_",model_dir,".csv"))
  write.table(network_long_care_df, output_fullpath, sep=",", row.names=FALSE)
  print(paste("Wrote",nrow(network_long_care_df),"rows to",output_fullpath))
}
