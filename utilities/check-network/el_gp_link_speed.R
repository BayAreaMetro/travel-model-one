#############################################################
#
# summarize the speed of express lanes and their corresponding general purpose lanes
# and calculate new tolls
#
#############################################################

library(foreign) # read dbf from shapefile
library(dplyr)

# remove all variables from the r environment
rm(list=ls())

# the loaded network
# note direction of the slash
PROJECT_DIR           <- "L:/RTP2021_PPA/Projects/2050_TM151_PPA_BF_06"
LOADED_NETWORK_CSV    <- file.path(PROJECT_DIR, "OUTPUT", "avgload5period.csv")
UNLOADED_NETWORK_DBF  <- file.path("L:/RTP2021_PPA/Projects/2050_TM151_PPA_BF_06/INPUT/shapefiles", "network_links.dbf") # from cube_to_shapefile.py
TOLLS_CSV             <- file.path(PROJECT_DIR, "INPUT", "hwy", "tolls.csv")
BRIDGE_TOLLS_CSV      <- "M:/Application/Model One/NetworkProjects/Bridge_Toll_Updates/tolls_2050.csv"

OUTPUT_LINK_SPD_CSV             <- "el_gp_link_speed.csv"
OUTPUT_AVG_SPD_CSV              <- "el_gp_avg_speed.csv"
OUTPUT_NEW_TOLLS_CSV            <- "tolls_iterX.csv"

unloaded_network_df      <- read.dbf(UNLOADED_NETWORK_DBF, as.is=TRUE) %>% select(A,B,USE,FT,TOLLCLASS)

el_links_df    <-  filter(unloaded_network_df , TOLLCLASS>9 )
gp_links_df     <- filter(unloaded_network_df , USE==1 & (FT<=3 | FT==5 | FT==8 | FT==10))


#############################################################
# Finding the corresponding GP link for each EL link
#############################################################
# first, try to find roadway links with dummy link connectors
dummy_links     <- filter(unloaded_network_df , FT==6)

# dummy B => el A, "A target" is the first point of dummy access link
el_group1_df   <- inner_join(el_links_df,
                              select(dummy_links, A,B),
                              by=c("A"="B"), suffix=c("","_GP")) # dummy B => el A
# el B => dummy A, "B target" is the second point of dummy egress link
el_group1_df   <- inner_join(el_group1_df,
                              select(dummy_links, A,B),
                              by=c("B"="A"), suffix=c("","_GP")) # el B   => dummy A

el_group1_df   <- inner_join(el_group1_df, gp_links_df,
                              by=c("A_GP"="A", "B_GP"="B"),
                              suffix=c("","_GP"))

print(paste("Group1: found general purpose links for", nrow(el_group1_df), "links"))

# join gp to el_links
el_gp_links_df <- left_join(el_links_df, select(el_group1_df, A,B,A_GP,B_GP))

# add a A_B field for EL and GP
el_gp_links_df <- mutate(el_gp_links_df, A_B=paste0(A,"_",B), A_B_GP=paste0(A_GP,"_",B_GP))


#############################################################
# join to loaded network
#############################################################
loaded_network_df          <-  read.csv(file=LOADED_NETWORK_CSV, header=TRUE, sep=",")

loaded_network_df          <- loaded_network_df  %>% select(a, b, ffs, cspdEA, cspdAM, cspdMD, cspdPM, cspdEV,  volEA_tot,  volAM_tot,  volMD_tot,  volPM_tot,  volEV_tot)

el_gp_loaded_df <- el_gp_links_df %>% left_join(loaded_network_df,
                                      by=c("A"="a", "B"="b"))

el_gp_loaded_df <- el_gp_loaded_df  %>% left_join(loaded_network_df,
                                      by=c("A_GP"="a", "B_GP"="b"),
                                      suffix=c("","_GP"))
# reorder columns
el_gp_loaded_df <- el_gp_loaded_df %>%
                   select(TOLLCLASS, A, B, A_B, A_GP, B_GP, A_B_GP, ffs, ffs_GP, cspdEA, cspdEA_GP, cspdAM, cspdAM_GP, cspdMD, cspdMD_GP, cspdPM, cspdPM_GP, cspdEV, cspdEV_GP, volEA_tot, volEA_tot_GP, volAM_tot, volAM_tot_GP, volMD_tot, volMD_tot_GP, volPM_tot, volPM_tot_GP, volEV_tot, volEV_tot_GP, everything())

# sort by toll class
el_gp_loaded_df <- el_gp_loaded_df %>% arrange(TOLLCLASS)


# there are some NA in the GP columns, because in some cases a single EL link corresponds to multiple GP links
# there are only a few of them (60 out of 1157 links in Baseline 06) - okay to ignore for toll calibration purposes
# drop where GP is NA
el_gp_loaded_nan_df <- na.omit(el_gp_loaded_df)

#############################################################
# summarize average speed at facility level
#############################################################

el_gp_summary_df <- el_gp_loaded_nan_df %>%
                    group_by(TOLLCLASS) %>%
                    summarise(avgspeed_EA    = mean(cspdEA),
                              avgspeed_EA_GP = mean(cspdEA_GP),
                              avgspeed_AM    = mean(cspdAM),
                              avgspeed_AM_GP = mean(cspdAM_GP),
                              avgspeed_MD    = mean(cspdMD),
                              avgspeed_MD_GP = mean(cspdMD_GP),
                              avgspeed_PM    = mean(cspdPM),
                              avgspeed_PM_GP = mean(cspdPM_GP),
                              avgspeed_EV    = mean(cspdEV),
                              avgspeed_EV_GP = mean(cspdEV_GP))

# Determine scenarios:
#        EL_speed	   GP_speed
# Case1	  <=45	        any	        EL too slow. Need to increase toll
# Case2	  >=45	        <=40	      GP too slow. Need to decrease toll (but still keep EL speed above 45 mph)
# Case3	  45-60	        40-60	      OK, as long as EL speed > GP speed in AM, MD and PM.  If not, need to increase toll.
# Case4	  >60	          40-60	      GP a bit slow. Maybe decrease toll, depend on how large the difference is.
# Case5	  >45	          >60	        Set toll to minimum

#AM
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_AM = case_when(avgspeed_AM_GP>60                                                            ~ "Case5 - set to min",
                                                                avgspeed_AM>60                      & avgspeed_AM_GP>40 & avgspeed_AM_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_AM>45 & avgspeed_AM<=60    & avgspeed_AM_GP>40 & avgspeed_AM_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_AM>45                      & avgspeed_AM_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_AM<=45                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                         ~ "Undefined"))

#MD
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_MD = case_when(avgspeed_MD_GP>60                                                            ~ "Case5 - set to min",
                                                                avgspeed_MD>60                      & avgspeed_MD_GP>40 & avgspeed_MD_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_MD>45 & avgspeed_MD<=60    & avgspeed_MD_GP>40 & avgspeed_MD_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_MD>45                      & avgspeed_MD_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_MD<=45                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                         ~ "Undefined"))
#PM
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_PM = case_when(avgspeed_PM_GP>60                                                            ~ "Case5 - set to min",
                                                                avgspeed_PM>60                      & avgspeed_PM_GP>40 & avgspeed_PM_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_PM>45 & avgspeed_PM<=60    & avgspeed_PM_GP>40 & avgspeed_PM_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_PM>45                      & avgspeed_PM_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_PM<=45                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                         ~ "Undefined"))

#############################################################
# merge in the existing toll rates
#############################################################
toll_rates_df          <- read.csv(file=TOLLS_CSV, header=TRUE, sep=",")
toll_rates_df          <- toll_rates_df  %>% select(tollclass, facility_name, tollam_da, tollmd_da, tollpm_da)

el_gp_summary_df <- el_gp_summary_df %>% left_join(toll_rates_df,
                                         by=c("TOLLCLASS"="tollclass"))

# determine new toll rates
el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollam_da_new = case_when(Case_AM == "Case1 - raise tolls"         ~ tollam_da + round(((45 - avgspeed_AM)/100), digits=2),
                                                                     Case_AM == "Case2 - drop tolls"          ~ max(tollam_da - round(((40 - avgspeed_AM_GP)/100), digits=2), 0.03),
                                                                     Case_AM == "Case3 - ok"                  ~ tollam_da,
                                                                     Case_AM == "Case4 - drop tolls slightly" ~ max(tollam_da - round(((avgspeed_AM - avgspeed_AM_GP)/100/2), digits=2), 0.03),
                                                                     Case_AM == "Case5 - set to min"          ~ 0.03))

el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollmd_da_new = case_when(Case_PM == "Case1 - raise tolls"          ~ tollmd_da + round(((45 - avgspeed_PM)/100), digits=2),
                                                                     Case_PM == "Case2 - drop tolls"           ~ max(tollmd_da - round(((40 - avgspeed_PM_GP)/100), digits=2), 0.03),
                                                                     Case_PM == "Case3 - ok"                   ~ tollmd_da,
                                                                     Case_PM == "Case4 - drop tolls slightly"  ~ max(tollmd_da - round(((avgspeed_PM - avgspeed_PM_GP)/100/2), digits=2), 0.03),
                                                                     Case_PM == "Case5 - set to min"           ~ 0.03))

el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollpm_da_new = case_when(Case_PM == "Case1 - raise tolls"          ~ tollpm_da + round(((45 - avgspeed_PM)/100), digits=2),
                                                                     Case_PM == "Case2 - drop tolls"           ~ max(tollpm_da - round(((40 - avgspeed_PM_GP)/100), digits=2), 0.03),
                                                                     Case_PM == "Case3 - ok"                   ~ tollpm_da,
                                                                     Case_PM == "Case4 - drop tolls slightly"  ~ max(tollpm_da - round(((avgspeed_PM - avgspeed_PM_GP)/100/2), digits=2), 0.03),
                                                                     Case_PM == "Case5 - set to min"           ~ 0.03))


#############################################################
# write the new toll rates to a new tolls.csv
#############################################################
tolls_new_df <- el_gp_summary_df  %>% select(TOLLCLASS, facility_name, tollam_da_new, tollmd_da_new, tollpm_da_new)

tolls_new_df <- tolls_new_df  %>%
                              mutate(fac_index = TOLLCLASS * 1000 + 4,
                                     tollclass = TOLLCLASS,
                                     tollseg   = 0,
                                     tolltype  = "expr_lane",
                                     use       = 4,
                                     tollea_da = 0,
                                     tollam_da = tollam_da_new,
                                     tollmd_da = tollmd_da_new,
                                     tollpm_da = tollpm_da_new,
                                     tollev_da = 0,
                                     tollea_s2 = 0,
                                     tollam_s2 = 0,
                                     tollmd_s2 = 0,
                                     tollpm_s2 = 0,
                                     tollev_s2 = 0,
                                     tollea_s3 = 0,
                                     tollam_s3 = 0,
                                     tollmd_s3 = 0,
                                     tollpm_s3 = 0,
                                     tollev_s3 = 0,
                                     tollea_vsm = 0,
                                     tollam_vsm = tollam_da_new,
                                     tollmd_vsm = tollmd_da_new,
                                     tollpm_vsm = tollpm_da_new,
                                     tollev_vsm = 0,
                                     tollea_sml = 0,
                                     tollam_sml = tollam_da_new,
                                     tollmd_sml = tollmd_da_new,
                                     tollpm_sml = tollpm_da_new,
                                     tollev_sml = 0,
                                     tollea_med = 0,
                                     tollam_med = tollam_da_new,
                                     tollmd_med = tollmd_da_new,
                                     tollpm_med = tollpm_da_new,
                                     tollev_med = 0,
                                     tollea_lrg = 0,
                                     tollam_lrg = tollam_da_new,
                                     tollmd_lrg = tollmd_da_new,
                                     tollpm_lrg = tollpm_da_new,
                                     tollev_lrg = 0)


tolls_new_df <- tolls_new_df  %>% select(-c(TOLLCLASS, tollam_da_new, tollmd_da_new, tollpm_da_new))

# append the new toll rates to the first half of the toll.csv file containing the bridge tolls
bridge_tolls_df    <- read.csv(file=BRIDGE_TOLLS_CSV, header=TRUE, sep=",")
bridge_el_tolls_df <- bind_rows(bridge_tolls_df, tolls_new_df)

#############################################################
# output
#############################################################
# output link level data to csv
write.csv(el_gp_loaded_df, file.path(PROJECT_DIR, "OUTPUT", OUTPUT_LINK_SPD_CSV), row.names = FALSE)

# output facility level summary to csv
write.csv(el_gp_summary_df, file.path(PROJECT_DIR, "OUTPUT", OUTPUT_AVG_SPD_CSV), row.names = FALSE)

# output a new tolls.csv
write.csv(bridge_el_tolls_df, file.path(PROJECT_DIR, "INPUT", "hwy", OUTPUT_NEW_TOLLS_CSV), row.names = FALSE)
