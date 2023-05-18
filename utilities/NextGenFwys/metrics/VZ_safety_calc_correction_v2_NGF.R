library(dplyr)
library(tidyr)
library(readxl)

# disable sci notation
options(scipen=999)

# project setting
project <- 'NGF'


# assumptions
N_days_per_year = 300 # assume 300 days per year (outputs are for one day)
Obs_N_motorist_fatalities_15 = 301
Obs_N_ped_fatalities_15 = 127
Obs_N_bike_fatalities_15 = 27
Obs_N_motorist_injuries_15 = 1338
Obs_N_ped_injuries_15 = 379
Obs_N_bike_injuries_15 = 251
Obs_injuries_15 = 1968

# collision look up table: seethe full research here: https://mtcdrive.box.com/s/vww1t4g169dv0f016f7o1k3qt1e32kx2
collisionrates = read_excel("X:/travel-model-one-master/utilities/RTP/metrics/CollisionLookupFINAL.xlsx", sheet = "Lookup Table")%>%rename(
 serious_injury_rate = a, fatality_rate = k, ped_fatality = k_ped, motorist_fatality = k_motor, bike_fatality = k_bike)%>%select(
    at, ft, fatality_rate, serious_injury_rate,  motorist_fatality, ped_fatality, bike_fatality)  

####### Calculate for 2015 #######
MODEL_DIR <- "2015_TM152_NGF_05"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)

df_15 <- read.csv(file.path(NETWORK_DIR, "OUTPUT", "avgload5period.csv")) %>%
  mutate(ft_collision = ft, at_collision = at)

df_15$ft_collision[df_15$ft_collision==1] = 2 
df_15$ft_collision[df_15$ft_collision==8] = 2
df_15$ft_collision[df_15$ft_collision==5] = 2 # pending review
df_15$ft_collision[df_15$ft_collision==7] = 4 # pending review
df_15$ft_collision[df_15$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
df_15$ft_collision[df_15$lanes<=0] = -1
df_15$ft_collision[df_15$ft_collision>4] = 4

df_15$at_collision[df_15$at_collision<3] = 3 
df_15$at_collision[df_15$at_collision>4] = 4 

df_15 <- df_15%>%rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)

df_15_2 <- left_join(df_15, collisionrates, by = c("ft", "at"))%>%mutate(annual_VMT = N_days_per_year * (volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
                                                                        Avg_speed = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
                                                                        N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
                                                                        N_ped_fatalities =  annual_VMT/1000000 * ped_fatality,
                                                                        N_bike_fatalities = annual_VMT/1000000 * bike_fatality,
                                                                        N_total_fatalities = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
                                                                        N_total_injuries =  annual_VMT/1000000 * serious_injury_rate)

taz <- 
  read.csv(file.path(NETWORK_DIR, "INPUT", "landuse","tazData.csv"))
pop_15 <- sum(taz$TOTPOP)

df_15_3 <- df_15_2 %>% summarize(N_motorist_fatalities = sum(N_motorist_fatalities, na.rm=TRUE),
                              N_bike_fatalities = sum(N_bike_fatalities, na.rm=TRUE),
                              N_ped_fatalities = sum(N_ped_fatalities, na.rm=TRUE),
                              N_fatalities = sum(N_total_fatalities, na.rm=TRUE),
                              N_injuries = sum(N_total_injuries, na.rm=TRUE),
                              annual_VMT = sum(annual_VMT, na.rm=TRUE))%>%mutate(
                                Population = pop_15
                              )

df_15_4 <- df_15_3%>%mutate(N_motorist_fatalities_corrected= N_motorist_fatalities*(Obs_N_motorist_fatalities_15/df_15_3$N_motorist_fatalities),
                           N_ped_fatalities_corrected = N_ped_fatalities* (Obs_N_ped_fatalities_15/df_15_3$N_ped_fatalities),
                           N_bike_fatalities_corrected = N_bike_fatalities* (Obs_N_bike_fatalities_15/df_15_3$N_bike_fatalities),
                           N_injuries_corrected = N_injuries * (Obs_injuries_15/df_15_3$N_injuries),
                           N_total_fatalities_corrected = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected,
                           N_motorist_fatalities_corrected_per_100M_VMT = N_motorist_fatalities_corrected/(annual_VMT/100000000),
                           N_ped_fatalities_corrected_per_100M_VMT = N_ped_fatalities_corrected/(annual_VMT/100000000),
                           N_bike_fatalities_corrected_per_100M_VMT = N_bike_fatalities_corrected/(annual_VMT/100000000),
                           N_total_fatalities_corrected_per_100M_VMT = N_total_fatalities_corrected/(annual_VMT/100000000),
                           N_injuries_corrected_per_100M_VMT = N_injuries_corrected/(annual_VMT/100000000),
                           N_motorist_fatalities_corrected_per_100K_pop = N_motorist_fatalities_corrected/(Population/100000),
                           N_ped_fatalities_corrected_per_100K_pop = N_ped_fatalities_corrected/(Population/100000),
                           N_bike_fatalities_corrected_per_100K_pop = N_bike_fatalities_corrected/(Population/100000),
                           N_total_fatalities_corrected_per_100K_pop = N_total_fatalities_corrected/(Population/100000),
                           N_injuries_corrected_per_100K_pop = N_injuries_corrected/(Population/100000)
)%>%
  select(-N_motorist_fatalities, -N_bike_fatalities, -N_ped_fatalities, -N_fatalities, -N_injuries)

df_15_5 = gather(df_15_4, index, value, annual_VMT:N_injuries_corrected_per_100K_pop, factor_key = TRUE)%>%
  mutate(Year = 2015, modelrunID = (MODEL_DIR))

base_year_2015 <- df_15_5
base_year_2015_3 <- df_15_3
rm(df_15)
rm(df_15_2)
rm(df_15_3)
rm(df_15_4)
rm(df_15_5)





######## Calculate for other scenarios#######

# use lowness_correction on NGF No Project (2035_TM152_NGF_NP10)

# For scenarios without Vision Zero: The function for lowness correction NGF No Project (2035_TM152_NGF_NP10) and Blueprint
lowness_correction_loop = function(path)
{ 
  # EPC
  taz_epc_crosswalk <- 
    read.csv("X:/travel-model-one-master/utilities/NextGenFwys/metrics/Input Files/taz_epc_crosswalk.csv")
  
  # network_links_TAZ: this table tells us if a link is within EPC or not
  network_links_TAZ <- 
    read.csv(file.path(path, "OUTPUT", "shapefile", "network_links_TAZ.csv")) %>%
    left_join(taz_epc_crosswalk, by = "TAZ1454") %>%
    select(A, B, TAZ1454, taz_epc) %>%
    group_by(A, B) %>%
    summarise(taz_epc = max(taz_epc))
    
  
  # Network of both freeway and non-freeway facilities
  NETWORK_all <- 
    read.csv(file.path(path, "OUTPUT", "avgload5period.csv")) %>%
    left_join(network_links_TAZ, by=c('a'='A', 'b'='B')) %>%
    mutate(key = "all")
  
  # Network of freeway facilities
  NETWORK_fwy <- 
    NETWORK_all %>%
    filter(ft == 1 | ft == 2 | ft == 5 | ft == 8) %>%
    mutate(key = "fwy")
  
  # Network of non freeway facilities
  NETWORK_nonfwy <- 
    NETWORK_all %>%
    filter(ft != 1 & ft != 2 & ft != 5 & ft != 8) %>%
    mutate(key = "non_fwy")
  
  # Network of links inside of EPC
  NETWORK_EPC <- 
    NETWORK_all %>%
    filter(taz_epc == 1) %>%
    mutate(key = "EPC")
  
  # Network of links outside of EPC
  NETWORK_nonEPC <- 
    NETWORK_all %>%
    filter(taz_epc == 0 | is.na(taz_epc)) %>%
    mutate(key = "non_EPC")
  
  result <- data.frame()
  
  # loop over different networks
  for (NETWORK in list(NETWORK_all, NETWORK_fwy, NETWORK_nonfwy, NETWORK_EPC, NETWORK_nonEPC))
  {
    df_1 <- 
      NETWORK %>%
      mutate(ft_collision = ft, at_collision = at)
  
    # get the freeway facility type: https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    df_1$ft_collision[df_1$ft_collision==1] = 2 
    df_1$ft_collision[df_1$ft_collision==8] = 2
    df_1$ft_collision[df_1$ft_collision==5] = 2 # pending review
    df_1$ft_collision[df_1$ft_collision==7] = 4 # pending review
    df_1$ft_collision[df_1$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
    df_1$ft_collision[df_1$lanes<=0]        = -1
    df_1$ft_collision[df_1$ft_collision>4]  = 4
    # at
    df_1$at_collision[df_1$at_collision<3]  = 3 
    df_1$at_collision[df_1$at_collision>4]  = 4 
  
    df_1 <-
      df_1 %>%
      rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)
  
    # join with collisionrates
    # df_2 calculates the fatalities based on ft and at for every link
    df_2 <-
      left_join(df_1, collisionrates, by = c("ft", "at")) %>%
      mutate(
        # annual VMT
        annual_VMT            = N_days_per_year * (volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
        # average speed
        Avg_speed             = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
        # motorist fatalities 
        N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
        # pedestrian fatalities
        N_ped_fatalities      = annual_VMT/1000000 * ped_fatality,
        # bike fatalities
        N_bike_fatalities     = annual_VMT/1000000 * bike_fatality,
        # total fatalities
        N_total_fatalities    = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
        # total injuries
        N_total_injuries      = annual_VMT/1000000 * serious_injury_rate)
    
    # get the population
    taz <- 
      read.csv(file.path(path, "INPUT", "landuse","tazData.csv")) %>%
      left_join(taz_epc_crosswalk, by=c('ZONE'='TAZ1454')) 
    
    if (first(df_2$key) == 'EPC') {
      taz <- 
        taz %>%
        filter(taz_epc == 1)
    } else if (first(df_2$key) == 'non_EPC') {
      taz <- 
        taz %>%
        filter(taz_epc == 0)
    } else {
      taz <- taz
    }
    
    pop <- sum(taz$TOTPOP)
    
    # df_3 summarizes the fatalities for the entire network
    df_3 <- 
      df_2 %>%
      summarize(
        # lowness correction for motorist fatalities
        N_motorist_fatalities = sum(N_motorist_fatalities, na.rm=TRUE),
        # lowness correction for bike fatalities
        N_bike_fatalities     = sum(N_bike_fatalities, na.rm=TRUE),
        # lowness correction for pedestrian fatalities
        N_ped_fatalities      = sum(N_ped_fatalities, na.rm=TRUE),
        # lowness correction for total fatalities
        N_fatalities          = sum(N_total_fatalities, na.rm=TRUE),
        # lowness correction for total injuries
        N_injuries            = sum(N_total_injuries, na.rm=TRUE),
        # key
        key                   = first(key),
        # annual VMT
        annual_VMT            = sum(annual_VMT, na.rm=TRUE),
        ) %>%
      mutate(Population       = pop)
    
    # df_4 applies the lowness correction on fatalities
    df_4 <- 
      df_3 %>%
      mutate(
        # lowness correction for motorist fatalities
        N_motorist_fatalities_corrected              = N_motorist_fatalities*(Obs_N_motorist_fatalities_15/base_year_2015_3$N_motorist_fatalities),
        # lowness correction for pedestrian fatalities
        N_ped_fatalities_corrected                   = N_ped_fatalities* (Obs_N_ped_fatalities_15/base_year_2015_3$N_ped_fatalities),
        # lowness correction for bike fatalities
        N_bike_fatalities_corrected                  = N_bike_fatalities* (Obs_N_bike_fatalities_15/base_year_2015_3$N_bike_fatalities),
        # lowness correction for total fatalities
        N_total_fatalities_corrected                 = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected,
        # lowness correction for motorist fatalities per 100M VMT
        N_motorist_fatalities_corrected_per_100M_VMT = N_motorist_fatalities_corrected/(annual_VMT/100000000),
        # lowness correction for pedestrian fatalities per 100M VMT
        N_ped_fatalities_corrected_per_100M_VMT      = N_ped_fatalities_corrected/(annual_VMT/100000000),
        # lowness correction for bike fatalities per 100M VMT
        N_bike_fatalities_corrected_per_100M_VMT     = N_bike_fatalities_corrected/(annual_VMT/100000000),
        # lowness correction for total fatalities per 100M VMT
        N_total_fatalities_corrected_per_100M_VMT    = N_total_fatalities_corrected/(annual_VMT/100000000),
        # lowness correction for motorist injuries per 100K resident
        N_motorist_fatalities_corrected_per_100K_pop = N_motorist_fatalities_corrected/(Population/100000),
        # lowness correction for pedestrian injuries per 100K resident
        N_ped_fatalities_corrected_per_100K_pop      = N_ped_fatalities_corrected/(Population/100000),
        # lowness correction for bike injuries per 100K resident
        N_bike_fatalities_corrected_per_100K_pop     = N_bike_fatalities_corrected/(Population/100000),
        # lowness correction for total fatalities per 100K resident
        N_total_fatalities_corrected_per_100K_pop    = N_total_fatalities_corrected/(Population/100000),
        # lowness correction for total injuries
        N_injuries_corrected                         = N_injuries * (Obs_injuries_15/base_year_2015_3$N_injuries),
        # lowness correction for total injuries per 100M VMT
        N_injuries_corrected_per_100M_VMT            = N_injuries_corrected/(annual_VMT/100000000),
        # lowness correction for total injuries per 100K resident
        N_injuries_corrected_per_100K_pop            = N_injuries_corrected/(Population/100000)
      ) %>%
      select(-N_motorist_fatalities, -N_bike_fatalities, -N_ped_fatalities, -N_fatalities, -N_injuries)
  
  # df_5 is a long format
  df_5 <- 
    gather(df_4, index, value, annual_VMT:N_injuries_corrected_per_100K_pop, factor_key = TRUE) %>%
    mutate(modelrunID = path, key = df_4$key)
  
  result <- rbind(result, df_5)
  }
  result <-
    result %>%
    spread(key, value)
  return (result)
}

MODEL_NP_DIR <- "2035_TM152_NGF_NP10"
NETWORK_NP_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_NP_DIR)

NGF_NP10 <- lowness_correction_loop(NETWORK_NP_DIR)


# For scenarios with Vision Zero: Pathway 1-4

# write function for adjusting fatalities based on change in speeds
lowness_speed_correction_loop = function(path, NP_path = NETWORK_NP_DIR)
{
  # No Project
  df_np <- 
    read.csv(file.path(NP_path, "OUTPUT", "avgload5period.csv")) %>%
    mutate(Avg_speed_NP = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5) %>%
    select(a,b,Avg_speed_NP)
  
  # EPC
  taz_epc_crosswalk <- read.csv("X:/travel-model-one-master/utilities/NextGenFwys/metrics/Input Files/taz_epc_crosswalk.csv")
  
  # network_links_TAZ: this table tells us if a link is within EPC or not
  network_links_TAZ <- 
    read.csv(file.path(path, "OUTPUT", "shapefile", "network_links_TAZ.csv")) %>%
    left_join(taz_epc_crosswalk, by = "TAZ1454") %>%
    select(A, B, TAZ1454, taz_epc) %>%
    group_by(A, B) %>%
    summarise(taz_epc = max(taz_epc))
  
  # Network of both freeway and non-freeway facilities
  NETWORK_all <- 
    read.csv(file.path(path, "OUTPUT", "avgload5period.csv")) %>%
    left_join(network_links_TAZ, by=c('a'='A', 'b'='B')) %>%
    mutate(key = "all")
  
  # Network of freeway facilities
  NETWORK_fwy <- 
    NETWORK_all %>%
    filter(ft == 1 | ft == 2 | ft == 5 | ft == 8) %>%
    mutate(key = "fwy")
  
  # Network of non freeway facilities
  NETWORK_nonfwy <- 
    NETWORK_all %>%
    filter(ft != 1 & ft != 2 & ft != 5 & ft != 8) %>%
    mutate(key = "non_fwy")
  
  # Network of links inside of EPC
  NETWORK_EPC <- 
    NETWORK_all %>%
    filter(taz_epc == 1) %>%
    mutate(key = "EPC")
  
  # Network of links outside of EPC
  NETWORK_nonEPC <- 
    NETWORK_all %>%
    filter(taz_epc == 0 | is.na(taz_epc)) %>%
    mutate(key = "non_EPC")
  
  result <- data.frame()
  
  # loop over different networks
  for (NETWORK in list(NETWORK_all, NETWORK_fwy, NETWORK_nonfwy, NETWORK_EPC, NETWORK_nonEPC))
  {
    df_1 <- 
      NETWORK %>%
      mutate(ft_collision = ft, at_collision = at)
    
    # get the freeway facility type: https://github.com/BayAreaMetro/modeling-website/wiki/MasterNetworkLookupTables#facility-type-ft
    df_1$ft_collision[df_1$ft_collision==1] = 2 
    df_1$ft_collision[df_1$ft_collision==8] = 2
    df_1$ft_collision[df_1$ft_collision==5] = 2 # pending review
    df_1$ft_collision[df_1$ft_collision==7] = 4 # pending review
    df_1$ft_collision[df_1$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
    df_1$ft_collision[df_1$lanes<=0]        = -1
    df_1$ft_collision[df_1$ft_collision>4]  = 4
    # at
    df_1$at_collision[df_1$at_collision<3]  = 3 
    df_1$at_collision[df_1$at_collision>4]  = 4 
    
    
    df_1 <- 
      df_1 %>%
      rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)
    
    # join with collisionrates
    # df_2 calculates the fatalities based on ft and at for every link (without speed reduction) - lowness correction
    df_2 <- 
      left_join(df_1, collisionrates, by = c("ft", "at")) %>%
      mutate(
        # annual VMT
        annual_VMT            = N_days_per_year * (volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
        # average speed
        Avg_speed             = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
        # motorist fatalities 
        N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
        # pedestrian fatalities
        N_ped_fatalities      = annual_VMT/1000000 * ped_fatality,
        # bike fatalities
        N_bike_fatalities     = annual_VMT/1000000 * bike_fatality,
        # total fatalities
        N_total_fatalities    = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
        # total injuries
        N_total_injuries      = annual_VMT/1000000 * serious_injury_rate)
    
    # join average speed on each link with No Project's average speed - speed correction
    df_3 <- 
      left_join(df_2, df_np, by=c("a", "b")) %>%
      select(a, b, ft, at, key,
             annual_VMT, 
             N_motorist_fatalities, 
             N_ped_fatalities, 
             N_bike_fatalities, 
             N_total_injuries, 
             Avg_speed, 
             Avg_speed_NP)
    
    # add attributes for fatality reduction exponent based on ft
    # exponents and methodology sourced from here: https://www.toi.no/getfile.php?mmfileid=13206 (table S1)
    # methodology cited in this FHWA resource: https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm
    df_3$fatality_exponent = 0
    df_3$fatality_exponent[df_3$ft%in%c(1,2,3,5,6,8)] = 4.6
    df_3$fatality_exponent[df_3$ft%in%c(4,7)] = 3
    # injuries
    df_3$injury_exponent = 0
    df_3$injury_exponent[df_3$ft%in%c(1,2,3,5,6,8)] = 3.5
    df_3$injury_exponent[df_3$ft%in%c(4,7)] = 2
    
    # adjust fatalities based on exponents and speed. 
    # if fatalities/injuries are higher because speeds are higher in FBP than NP, use pmin function to replace with originally calculated FBP fatalities/injuries before VZ adjustment (do not let fatalities/injuries increase due to VZ adjustment calculation)
    df_4 <- 
      df_3 %>%
      mutate(
        # motorist fatalities after speed correction
        N_motorist_fatalities_after = ifelse(N_motorist_fatalities == 0,0,pmin(N_motorist_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent, N_motorist_fatalities)),
        # pedestrian fatalities after speed correction     
        N_ped_fatalities_after      = ifelse(N_ped_fatalities == 0,0,pmin(N_ped_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent, N_ped_fatalities)),
        # bike fatalities after speed correction   
        N_bike_fatalities_after     = ifelse(N_bike_fatalities == 0,0,pmin(N_bike_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent,N_bike_fatalities)),
        # total fatalities before correction          
        N_fatalities                = N_motorist_fatalities+ N_ped_fatalities+ N_bike_fatalities,
        # total fatalities after speed correction            
        N_fatalities_after          = N_motorist_fatalities_after+ N_ped_fatalities_after+ N_bike_fatalities_after,
        # total injuries before correction             
        N_injuries                  = N_total_injuries,
        # total injuries after correction 
        N_injuries_after            = ifelse(N_injuries == 0,0,pmin(N_injuries*(Avg_speed/Avg_speed_NP)^injury_exponent, N_injuries)))
    
    # in instances where a new link was added between no project and FBP, replace N_fatalities_after with N_fatalities
    #N_fatalities_after = coalesce(N_fatalities_after, N_fatalities),
    #N_motorist_fatalities_after = coalesce(N_motorist_fatalities_after, N_motorist_fatalities),
    #N_ped_fatalities_after = coalesce(N_ped_fatalities_after, N_ped_fatalities),
    #N_bike_fatalities_after = coalesce(N_bike_fatalities_after, N_bike_fatalities),
    #N_injuries_after = coalesce(N_injuries_after, N_injuries))
    
    # get the population
    taz <- 
      read.csv(file.path(path, "INPUT", "landuse","tazData.csv")) %>%
      left_join(taz_epc_crosswalk, by=c('ZONE'='TAZ1454')) 
    
    if (first(df_2$key) == 'EPC') {
      taz <- 
        taz %>%
        filter(taz_epc == 1)
    } else if (first(df_2$key) == 'non_EPC') {
      taz <- 
        taz %>%
        filter(taz_epc == 0)
    } else {
      taz <- taz
    }
    
    pop <- sum(taz$TOTPOP)
    
    # summarize
    df_5 <- 
      df_4 %>%
      summarize(
        # motorist fatalities without speed correction
        N_motorist_fatalities       = sum(N_motorist_fatalities, na.rm=TRUE),
        # motorist fatalities with speed correction                
        N_motorist_fatalities_after = sum(N_motorist_fatalities_after, na.rm=TRUE),
        # bike fatalities without speed correction
        N_bike_fatalities           = sum(N_bike_fatalities, na.rm=TRUE),
        # bike fatalities with speed correction
        N_bike_fatalities_after     = sum(N_bike_fatalities_after, na.rm=TRUE),
        # pedestrian fatalities without speed correction
        N_ped_fatalities            = sum(N_ped_fatalities, na.rm=TRUE),
        # pedestrian fatalities with speed correction
        N_ped_fatalities_after      = sum(N_ped_fatalities_after, na.rm=TRUE),
        # total fatalities without speed correction
        N_fatalities                = sum(N_fatalities, na.rm=TRUE),
        # total fatalities with speed correction
        N_fatalities_after          = sum(N_fatalities_after, na.rm=TRUE),
        # total injuries without speed correction
        N_injuries                  = sum(N_injuries, na.rm=TRUE),
        # total injuries with speed correction
        N_injuries_after            = sum(N_injuries_after, na.rm=TRUE),
        # key
        key                         = first(key),
        # annual VMT
        annual_VMT                  = sum(annual_VMT, na.rm=TRUE)) %>%
      select(-N_motorist_fatalities, -N_bike_fatalities, -N_ped_fatalities, -N_fatalities, -N_injuries ) %>%
      rename(
        N_motorist_fatalities = N_motorist_fatalities_after, 
        N_bike_fatalities = N_bike_fatalities_after,  
        N_ped_fatalities = N_ped_fatalities_after, 
        N_fatalities = N_fatalities_after, 
        N_injuries = N_injuries_after) %>%
      mutate(Population = pop)
    
    df_6 <-
      df_5 %>%
      mutate(
        # lowness and speed correction for motorist fatalities
        N_motorist_fatalities_corrected = N_motorist_fatalities*(Obs_N_motorist_fatalities_15/base_year_2015_3$N_motorist_fatalities),
        # lowness and speed correction for pedestrian fatalities      
        N_ped_fatalities_corrected = N_ped_fatalities*(Obs_N_ped_fatalities_15/base_year_2015_3$N_ped_fatalities),
        # lowness and speed correction for bike fatalities 
        N_bike_fatalities_corrected = N_bike_fatalities*(Obs_N_bike_fatalities_15/base_year_2015_3$N_bike_fatalities),
        # lowness and speed correction for total fatalities 
        N_total_fatalities_corrected = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected,
        # lowness and speed correction for motorist fatalities per 100M VMT
        N_motorist_fatalities_corrected_per_100M_VMT = N_motorist_fatalities_corrected/(annual_VMT/100000000),
        # lowness and speed correction for pedestrian fatalities per 100M VMT
        N_ped_fatalities_corrected_per_100M_VMT = N_ped_fatalities_corrected/(annual_VMT/100000000),
        # lowness and speed correction for bike fatalities per 100M VMT
        N_bike_fatalities_corrected_per_100M_VMT = N_bike_fatalities_corrected/(annual_VMT/100000000),
        # lowness and speed correction for total fatalities per 100M VMT
        N_total_fatalities_corrected_per_100M_VMT = N_total_fatalities_corrected/(annual_VMT/100000000),
        # lowness and speed correction for motorist fatalities per 100K resident
        N_motorist_fatalities_corrected_per_100K_pop = N_motorist_fatalities_corrected/(Population/100000),
        # lowness and speed correction for pedestrian fatalities per 100K resident
        N_ped_fatalities_corrected_per_100K_pop = N_ped_fatalities_corrected/(Population/100000),
        # lowness and speed correction for bike fatalities per 100K resident
        N_bike_fatalities_corrected_per_100K_pop = N_bike_fatalities_corrected/(Population/100000),
        # lowness and speed correction for total fatalities per 100K resident
        N_total_fatalities_corrected_per_100K_pop = N_total_fatalities_corrected/(Population/100000),
        # lowness and speed correction for total injuries   
        N_injuries_corrected = N_injuries*(Obs_injuries_15/base_year_2015_3$N_injuries),
        # lowness and speed correction for total injuries per 100M VMT
        N_injuries_corrected_per_100M_VMT = N_injuries_corrected/(annual_VMT/100000000),
        # lowness and speed correction for total injuries per 100K resident
        N_injuries_corrected_per_100K_pop = N_injuries_corrected/(Population/100000)
      ) %>%
      select(-N_motorist_fatalities, -N_bike_fatalities, -N_ped_fatalities, -N_fatalities, -N_injuries)
    
    df_7 <-
      gather(df_6, index, value, annual_VMT:N_injuries_corrected_per_100K_pop, factor_key = TRUE) %>%
      mutate(modelrunID = path, key = df_6$key)
    
    result <- rbind(result, df_7)
  }  
  result <-
    result %>%
    spread(key, value)
  return (result)
}

# Pathway 1a
MODEL_DIR <- "2035_TM152_NGF_NP10_Path1a_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path1a_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 1b
MODEL_DIR <- "2035_TM152_NGF_NP10_Path1b_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path1b_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 2a
MODEL_DIR <- "2035_TM152_NGF_NP10_Path2a_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path2a_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 2b
MODEL_DIR <- "2035_TM152_NGF_NP10_Path2b_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path2b_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 3a
MODEL_DIR <- "2035_TM152_NGF_NP10_Path3a_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path3a_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 3b
MODEL_DIR <- "2035_TM152_NGF_NP10_Path3b_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path3b_02 <- lowness_speed_correction_loop(NETWORK_DIR)

# Pathway 4
MODEL_DIR <- "2035_TM152_NGF_NP10_Path4_02"
NETWORK_DIR <- file.path("L:/Application/Model_One/NextGenFwys/Scenarios", MODEL_DIR)
NGF_Path4_02 <- lowness_speed_correction_loop(NETWORK_DIR)

export <- 
  rbind(
    NGF_NP10,
    NGF_Path1a_02, 
    NGF_Path1b_02, 
    NGF_Path2a_02, 
    NGF_Path2b_02,
    NGF_Path3a_02,
    NGF_Path3b_02,
    NGF_Path4_02
  )

# write csv
write.csv(export,
          "L:/Application/Model_One/NextGenFwys/metrics/Safe1/fatalities_injuries_export.csv",
          row.names = FALSE)


