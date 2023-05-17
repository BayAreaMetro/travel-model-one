library(dplyr)
library(tidyr)
library(readxl)

# disable sci notation
options(scipen=999)

# path for 2015 run
Path_2015 = "M:/Application/Model One/RTP2021/IncrementalProgress/2015_TM152_IPA_17/"

# path for 2050 No project run
#Path_2050_NP = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_DBP_NoProject_08/"
Path_2050_NP = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_NoProject_24/"


# path for 2050 BP run
#Path_2050_BP = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_DBP_PlusCrossing_08/"
Path_2050_BP = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_FBP_PlusCrossing_24/"

# Alt 1 2050
Path_2050_Alt1 = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt1_05/"

# Alt 2 2050
Path_2050_Alt2 = "M:/Application/Model One/RTP2021/Blueprint/2050_TM152_EIR_Alt2_05/"



# assumptions
N_days_per_year = 300 # assume 300 days per year (outputs are for one day)
Obs_N_motorist_fatalities_15 = 301
Obs_N_ped_fatalities_15 = 127
Obs_N_bike_fatalities_15 = 27
Obs_N_motorist_injuries_15 = 1338
Obs_N_ped_injuries_15 = 379
Obs_N_bike_injuries_15 = 251
Obs_injuries_15 = 1968


collisionrates = read_excel("C:/Users/rmccoy/Box/Other Performance Projects/Research & Development/Safety Research/LookupTable/CollisionLookupFINAL.xlsx", sheet = "Lookup Table")%>%rename(
 serious_injury_rate = a, fatality_rate = k, ped_fatality = k_ped, motorist_fatality = k_motor, bike_fatality = k_bike)%>%select(
    at, ft, fatality_rate, serious_injury_rate,  motorist_fatality, ped_fatality, bike_fatality)  


# calculate for 2015
df_15 = read.csv(paste0(Path_2015,"OUTPUT/avgload5period.csv"))%>%mutate(ft_collision = ft, at_collision = at)

df_15$ft_collision[df_15$ft_collision==1] = 2 
df_15$ft_collision[df_15$ft_collision==8] = 2
df_15$ft_collision[df_15$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
df_15$ft_collision[df_15$lanes<=0] = -1
df_15$ft_collision[df_15$ft_collision>4] = 4

df_15$at_collision[df_15$at_collision<3] = 3 
df_15$at_collision[df_15$at_collision>4] = 4 

df_15 = df_15%>%rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)

df_15_2 = left_join(df_15, collisionrates, by = c("ft", "at"))%>%mutate(annual_VMT = N_days_per_year * (volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
                                                                        Avg_speed = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
                                                                        N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
                                                                        N_ped_fatalities =  annual_VMT/1000000 * ped_fatality,
                                                                        N_bike_fatalities = annual_VMT/1000000 * bike_fatality,
                                                                        N_total_fatalities = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
                                                                        N_total_injuries =  annual_VMT/1000000 * serious_injury_rate)

pop_15 = (read.csv(paste0(Path_2015,"INPUT/landuse/tazData.csv"))%>%summarize(TOTPOP = sum(TOTPOP)))[1,1]

df_15_3 = df_15_2%>%summarize(N_motorist_fatalities = sum(N_motorist_fatalities, na.rm=TRUE),
                              N_bike_fatalities = sum(N_bike_fatalities, na.rm=TRUE),
                              N_ped_fatalities = sum(N_ped_fatalities, na.rm=TRUE),
                              N_fatalities = sum(N_total_fatalities, na.rm=TRUE),
                              N_injuries = sum(N_total_injuries, na.rm=TRUE),
                              annual_VMT = sum(annual_VMT, na.rm=TRUE))%>%mutate(
                                Population = pop_15
                              )

df_15_4 = df_15_3%>%mutate(N_motorist_fatalities_corrected= N_motorist_fatalities*(Obs_N_motorist_fatalities_15/df_15_3$N_motorist_fatalities),
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
  mutate(Year = 2015, modelrunID = gsub('M:/Application/Model One/RTP2021/', '', Path_2015))

# read in no project
df_np = read.csv(paste0(Path_2050_NP,"OUTPUT/avgload5period.csv"))%>%mutate(
  Avg_speed_NP = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5)%>%select(
  a,b,Avg_speed_NP)
  

# write function for adjusting fatalities based on change in speeds
fatalities_injuries_process = function(path){
  df = read.csv(paste0(path,"OUTPUT/avgload5period.csv"))%>%mutate(ft_collision = ft, at_collision = at)
  
  df$ft_collision[df$ft_collision==1] = 2 
  df$ft_collision[df$ft_collision==8] = 2
  df$ft_collision[df$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
  df$ft_collision[df$lanes<=0] = -1
  df$ft_collision[df$ft_collision>4] = 4
  
  df$at_collision[df$at_collision<3] = 3 
  df$at_collision[df$at_collision>4] = 4 
  
  
  df = df%>%rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)
  
  # calculate fatalities and injuries as they would be calculated without the speed reduction
  df2 = left_join(df, collisionrates, by = c("ft", "at"))%>%mutate(annual_VMT = N_days_per_year *(volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
                                                                   Avg_speed = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
                                                                   N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
                                                                   N_ped_fatalities = annual_VMT/1000000 * ped_fatality,
                                                                   N_bike_fatalities = annual_VMT/1000000 * bike_fatality,
                                                                   N_total_fatalities = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
                                                                   N_total_injuries = annual_VMT/1000000 * serious_injury_rate)
  
  # join average speed on each link in no project
  df3 = left_join(df2, df_np, by=c("a", "b"))%>%select(a,, b, ft, at, annual_VMT, N_motorist_fatalities, N_ped_fatalities, N_bike_fatalities, 
                                                       N_total_injuries, Avg_speed, Avg_speed_NP)
  
  
  # add attributes for fatality reduction exponent based on ft
  # exponents and methodology sourced from here: https://www.toi.no/getfile.php?mmfileid=13206 (table S1)
  # methodology cited in this FHWA resource: https://www.fhwa.dot.gov/publications/research/safety/17098/003.cfm
  df3$fatality_exponent = 0
  df3$fatality_exponent[df3$ft%in%c(1,2,3,5,6,8)] = 4.6
  df3$fatality_exponent[df3$ft%in%c(4,7)] = 3
  
  df3$injury_exponent = 0
  df3$injury_exponent[df3$ft%in%c(1,2,3,5,6,8)] = 3.5
  df3$injury_exponent[df3$ft%in%c(4,7)] = 2
  
  # adjust fatalities based on exponents and speed. 
  # if fatalities/injuries are higher because speeds are higher in FBP than NP, use pmin function to replace with originally calculated FBP fatalities/injuries before VZ adjustment (do not let fatalities/injuries increase due to VZ adjustment calculation)
  df4 = df3%>%mutate(N_motorist_fatalities_after = ifelse(N_motorist_fatalities == 0,0,pmin(N_motorist_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent, N_motorist_fatalities)),
                     N_ped_fatalities_after = ifelse(N_ped_fatalities == 0,0,pmin(N_ped_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent, N_ped_fatalities)),
                     N_bike_fatalities_after = ifelse(N_bike_fatalities == 0,0,pmin(N_bike_fatalities*(Avg_speed/Avg_speed_NP)^fatality_exponent,N_bike_fatalities)),
                     N_fatalities = N_motorist_fatalities+ N_ped_fatalities+ N_bike_fatalities,
                     N_fatalities_after = N_motorist_fatalities_after+ N_ped_fatalities_after+ N_bike_fatalities_after,
                     N_injuries = N_total_injuries,
                     N_injuries_after = ifelse(N_injuries == 0,0,pmin(N_injuries*(Avg_speed/Avg_speed_NP)^injury_exponent, N_injuries)))
  
  # in instances where a new link was added between no project and FBP, replace N_fatalities_after with N_fatalities
  #N_fatalities_after = coalesce(N_fatalities_after, N_fatalities),
  #N_motorist_fatalities_after = coalesce(N_motorist_fatalities_after, N_motorist_fatalities),
  #N_ped_fatalities_after = coalesce(N_ped_fatalities_after, N_ped_fatalities),
  #N_bike_fatalities_after = coalesce(N_bike_fatalities_after, N_bike_fatalities),
  #N_injuries_after = coalesce(N_injuries_after, N_injuries))
  
  pop_50_BP = (read.csv(paste0(path,"INPUT/landuse/tazData.csv"))%>%summarize(TOTPOP = sum(TOTPOP)))[1,1]
  
  # summarize
  df5 = df4%>%summarize(N_motorist_fatalities = sum(N_motorist_fatalities, na.rm=TRUE),
                        N_motorist_fatalities_after = sum(N_motorist_fatalities_after, na.rm=TRUE),
                        N_bike_fatalities = sum(N_bike_fatalities, na.rm=TRUE),
                        N_bike_fatalities_after = sum(N_bike_fatalities_after, na.rm=TRUE),
                        N_ped_fatalities = sum(N_ped_fatalities, na.rm=TRUE),
                        N_ped_fatalities_after = sum(N_ped_fatalities_after, na.rm=TRUE),
                        N_fatalities = sum(N_fatalities, na.rm=TRUE),
                        N_fatalities_after = sum(N_fatalities_after, na.rm=TRUE),
                        N_injuries = sum(N_injuries, na.rm=TRUE),
                        N_injuries_after = sum(N_injuries_after, na.rm=TRUE),
                        annual_VMT = sum(annual_VMT, na.rm=TRUE))%>%select(-N_motorist_fatalities, -N_bike_fatalities, -N_ped_fatalities, -N_fatalities, -N_injuries)%>%rename(
                          N_motorist_fatalities = N_motorist_fatalities_after, N_bike_fatalities = N_bike_fatalities_after,  N_ped_fatalities = N_ped_fatalities_after, 
                          N_fatalities = N_fatalities_after, N_injuries = N_injuries_after
                        )%>%mutate(Population = pop_50_BP)
  
  df6 = df5 %>%
    mutate(N_motorist_fatalities_corrected = N_motorist_fatalities*(Obs_N_motorist_fatalities_15/df_15_3$N_motorist_fatalities),
           N_ped_fatalities_corrected = N_ped_fatalities*(Obs_N_ped_fatalities_15/df_15_3$N_ped_fatalities),
           N_bike_fatalities_corrected = N_bike_fatalities*(Obs_N_bike_fatalities_15/df_15_3$N_bike_fatalities),
           N_total_fatalities_corrected = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected,
           N_injuries_corrected = N_injuries*(Obs_injuries_15/df_15_3$N_injuries),
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
  
  df7 = gather(df6, index, value, annual_VMT:N_injuries_corrected_per_100K_pop, factor_key = TRUE)%>%mutate(Year = 2050,
                                                                                                            modelrunID = gsub('M:/Application/Model One/RTP2021/Blueprint', '', path))
}

df_2050_bp = fatalities_injuries_process(Path_2050_BP)
df_2050_alt1 = fatalities_injuries_process(Path_2050_Alt1)
df_2050_alt2 = fatalities_injuries_process(Path_2050_Alt2)


# calculate for 2050 no project
df_50np = read.csv(paste0(Path_2050_NP,"OUTPUT/avgload5period.csv"))%>%mutate(ft_collision = ft, at_collision = at)

df_50np$ft_collision[df_50np$ft_collision==1] = 2 
df_50np$ft_collision[df_50np$ft_collision==8] = 2
df_50np$ft_collision[df_50np$ft_collision==6] = -1 # code says ignore ft 6 (dummy links) and lanes <= 0 by replacing the ft with -1, which won't match with anything
df_50np$ft_collision[df_50np$lanes<=0] = -1
df_50np$ft_collision[df_50np$ft_collision>4] = 4

df_50np$at_collision[df_50np$at_collision<3] = 3 
df_50np$at_collision[df_50np$at_collision>4] = 4 

df_50np = df_50np%>%rename(at_original = at, ft_original = ft, at = at_collision, ft = ft_collision)

df_50np_2 = left_join(df_50np, collisionrates, by = c("ft", "at"))%>%mutate(annual_VMT = N_days_per_year *(volEA_tot+volAM_tot+volMD_tot+volPM_tot+volEV_tot)*distance,
                                                             Avg_speed = (cspdEA + cspdAM+ cspdMD+ cspdPM+ cspdEV)/5,
                                                             N_motorist_fatalities = annual_VMT/1000000 * motorist_fatality,
                                                             N_ped_fatalities = annual_VMT/1000000 * ped_fatality,
                                                             N_bike_fatalities =  annual_VMT/1000000 * bike_fatality,
                                                             N_total_fatalities = N_motorist_fatalities + N_ped_fatalities + N_bike_fatalities,
                                                             N_total_injuries = annual_VMT/1000000 * serious_injury_rate)

pop_50_NP = (read.csv(paste0(Path_2050_NP,"INPUT/landuse/tazData.csv"))%>%summarize(TOTPOP = sum(TOTPOP)))[1,1]

df_50np_3 = df_50np_2%>%summarize(N_motorist_fatalities = sum(N_motorist_fatalities, na.rm=TRUE),
                      N_bike_fatalities = sum(N_bike_fatalities, na.rm=TRUE),
                      N_ped_fatalities = sum(N_ped_fatalities, na.rm=TRUE),
                      N_fatalities = sum(N_total_fatalities, na.rm=TRUE),
                      N_injuries = sum(N_total_injuries, na.rm=TRUE),
                      annual_VMT = sum(annual_VMT, na.rm=TRUE))%>%mutate(
                        Population = pop_50_NP
                      )

df_50np_4 = df_50np_3%>%
  mutate(N_motorist_fatalities_corrected = N_motorist_fatalities*(Obs_N_motorist_fatalities_15/df_15_3$N_motorist_fatalities),
         N_ped_fatalities_corrected = N_ped_fatalities*(Obs_N_ped_fatalities_15/df_15_3$N_ped_fatalities),
         N_bike_fatalities_corrected = N_bike_fatalities*(Obs_N_bike_fatalities_15/df_15_3$N_bike_fatalities),
         N_total_fatalities_corrected = N_motorist_fatalities_corrected + N_ped_fatalities_corrected + N_bike_fatalities_corrected,
         N_injuries_corrected = N_injuries*(Obs_injuries_15/df_15_3$N_injuries),
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

df_50np_5 = gather(df_50np_4, index, value, annual_VMT:N_injuries_corrected_per_100K_pop, factor_key = TRUE)%>%
  mutate(Year = 2050, modelrunID = gsub('M:/Application/Model One/RTP2021/Blueprint', '', Path_2050_NP))


export = rbind(df_15_5, df_50np_5, df_2050_bp, df_2050_alt1, df_2050_alt2)

# write csv
write.csv(export,"C:/Users/rmccoy/Box/Horizon and Plan Bay Area 2050/Equity and Performance/7_Analysis/Metrics/Metrics_Outputs_FinalBlueprint/Raleigh outputs/fatalities_injuries_export_0804.csv")

#### SCRATCH TO COMPARE ACROSS BLUEPRINTS

df_50np_2_join = df_50np_2%>%select("a","b", "annual_VMT",  "N_motorist_fatalities", "N_total_injuries")%>%rename(annual_VMT_NP = annual_VMT, 
                                                                                                                      N_motorist_fatalities_NP = N_motorist_fatalities, 
                                                                                                                      N_total_injuries_NP = N_total_injuries)

df4_join = df4%>%select("a", "b", "ft", "at", "annual_VMT", "Avg_speed", "Avg_speed_NP", "N_motorist_fatalities_after", "N_injuries_after")%>%rename(annual_VMT_BP = annual_VMT, 
                                                                                                                                         Avg_speed_BP = Avg_speed,
                                                                                                                                         N_motorist_fatalities_after_BP = N_motorist_fatalities_after, 
                                                                                                                                         N_injuries_after_BP = N_injuries_after)

df_np_bp = left_join(df4_join, df_50np_2_join, by=c("a", "b"))%>%mutate(inj_per_vmt_np = N_total_injuries_NP/annual_VMT_NP*100000000,
                                                                        inj_per_vmt_bp = N_injuries_after_BP/annual_VMT_BP*100000000,
                                                                        speed_bp_minus_np = Avg_speed_BP - Avg_speed_NP,
                                                                        inj_per_vmt_bp_minus_np = inj_per_vmt_bp-inj_per_vmt_np,
                                                                        speed_down_rate_up = 0)

df_15_2_join = df_15_2%>%select("a","b", "annual_VMT",  "N_motorist_fatalities", "N_total_injuries")%>%rename(annual_VMT_15 = annual_VMT, 
                                                                                                                N_motorist_fatalities_15 = N_motorist_fatalities, 
                                                                                                                N_total_injuries_15 = N_total_injuries) 

df_np_bp_15 = left_join(df_np_bp, df_15_2_join, by=c("a", "b"))%>%mutate(inj_per_vmt_15 = N_total_injuries_NP/annual_VMT_NP*100000000,
                                                                         inj_per_vmt_15 = N_injuries_after_BP/annual_VMT_BP*100000000,
                                                                         speed_bp_minus_15 = Avg_speed_BP - Avg_speed_NP)


df_np_bp$speed_down_rate_up[(df_np_bp$inj_per_vmt_bp_minus_np>0)& (df_np_bp$speed_bp_minus_np<0)] = 1
df_np_bp$speed_down_rate_up[(df_np_bp$inj_per_vmt_bp_minus_np<0)& (df_np_bp$speed_bp_minus_np>0)] = 1



df_np_bp_15_summary = df_np_bp_15%>%group_by(ft, at)%>%summarize(avg_speed_NP_wt = weighted.mean(Avg_speed_NP, annual_VMT_NP, na.rm=TRUE),
                                                          avg_speed_BP_wt = weighted.mean(Avg_speed_BP, annual_VMT_BP, na.rm=TRUE),
                                                          annual_VMT_15 = sum(annual_VMT_15, na.rm=TRUE),
                                                          annual_VMT_NP = sum(annual_VMT_NP, na.rm=TRUE),
                                                          annual_VMT_BP = sum(annual_VMT_BP, na.rm=TRUE),
                                                          N_motorist_fatalities_15 = sum(N_motorist_fatalities_15, na.rm=TRUE),
                                                          N_motorist_fatalities_NP = sum(N_motorist_fatalities_NP, na.rm=TRUE),
                                                          N_motorist_fatalities_after_BP = sum(N_motorist_fatalities_after_BP, na.rm=TRUE),
                                                          N_total_injuries_15 = sum(N_total_injuries_15, na.rm=TRUE),
                                                          N_total_injuries_NP = sum(N_total_injuries_NP, na.rm=TRUE),
                                                          N_injuries_after_BP = sum(N_injuries_after_BP, na.rm=TRUE))
                                                          

df_np_bp_summary2 = df_np_bp%>%summarize(#avg_speed_NP_wt = weighted.mean(Avg_speed_NP, annual_VMT_NP, na.rm=TRUE),
                                                 #avg_speed_BP_wt = weighted.mean(Avg_speed_BP, annual_VMT_BP, na.rm=TRUE),
                                                 annual_VMT_NP = sum(annual_VMT_NP, na.rm=TRUE),
                                                 annual_VMT_BP = sum(annual_VMT_BP, na.rm=TRUE),
                                                 N_motorist_fatalities_NP = sum(N_motorist_fatalities_NP, na.rm=TRUE),
                                                 N_motorist_fatalities_after_BP = sum(N_motorist_fatalities_after_BP, na.rm=TRUE),
                                                 N_total_injuries_NP = sum(N_total_injuries_NP, na.rm=TRUE),
                                                 N_injuries_after_BP = sum(N_injuries_after_BP, na.rm=TRUE))

