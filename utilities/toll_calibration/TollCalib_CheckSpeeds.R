#############################################################
#
# summarize the speed of express lanes and their corresponding general purpose lanes
# and calculate new tolls
#
# can be run by the batch script, TollCalib_RunModel.bat:
# call "%R_HOME%\bin\x64\Rscript.exe" "\\mainmodel\MainModelShare\travel-model-one-master\utilities\toll_calibration\TollCalib_CheckSpeeds.R"
#
# can be run stand alone as well, but users need to define:
# ITER, PROJECT_DIR, UNLOADED_NETWORK_DBF
#
#############################################################

library(foreign) # read dbf from shapefile
library(dplyr)
library(readxl)

ITER <- Sys.getenv("ITER")        # The iteration of model outputs to be read
ITER <- as.numeric(ITER)

# THRESHOLD_SPEED and MAX_TOLL would be defined by TOLL_DESIGNATIONS_XLSX
# THRESHOLD_SPEED <- Sys.getenv("THRESHOLD_SPEED")
# THRESHOLD_SPEED <- as.numeric(THRESHOLD_SPEED)
#
# MAX_TOLL <- Sys.getenv("MAX_TOLL")
# MAX_TOLL <- as.numeric(MAX_TOLL)

HOV2_discount_factor <- Sys.getenv("DiscountFactor_HOV2")
HOV2_discount_factor <- as.numeric(HOV2_discount_factor)

HOV3_discount_factor <- Sys.getenv("DiscountFactor_HOV3")
HOV3_discount_factor <- as.numeric(HOV3_discount_factor)

#############################################################
# specify the loaded network, unloaded network and other inputs
#############################################################

PROJECT_DIR           <- Sys.getenv("PROJECT_DIR")
PROJECT_DIR           <- gsub("\\\\","/",PROJECT_DIR) # switch slashes around

# for the loaded network, use different path for full runs and extracted output folders
if (dir.exists(file.path(PROJECT_DIR, "CTRAMP"))) {
    LOADED_NETWORK_CSV    <- file.path(PROJECT_DIR, "hwy", paste0("iter",ITER),"avgload5period.csv")
} else {
    LOADED_NETWORK_CSV    <- file.path(PROJECT_DIR, "OUTPUT","avgload5period.csv")
}

UNLOADED_NETWORK_DBF  <- Sys.getenv("UNLOADED_NETWORK_DBF") # from cube_to_shapefile.py
UNLOADED_NETWORK_DBF  <- gsub("\\\\","/",UNLOADED_NETWORK_DBF) # switch slashes around


# for the toll file, use different path for full runs, extracted output folders of baseline runs, and extracted output folders of project runs
if (dir.exists(file.path(PROJECT_DIR, "CTRAMP"))) {
    # full runs
    TOLLS_CSV             <- file.path(PROJECT_DIR, "hwy", "tolls.csv")
} else {
    if (dir.exists(file.path(PROJECT_DIR, "INPUT"))) {
        # extracted output folders of baseline runs
        TOLLS_CSV             <- file.path(PROJECT_DIR, "INPUT", "hwy", "tolls.csv")
    } else {
        # extracted output folders of project runs
        TOLLS_CSV             <- file.path(PROJECT_DIR, "hwy", "tolls.csv")
    }
}

# this file indicates which facilities have mandatory s2 tolls
TOLL_DESIGNATIONS_XLSX <- Sys.getenv("TOLL_DESIGNATIONS_XLSX")
TOLL_DESIGNATIONS_XLSX <- gsub("\\\\","/",TOLL_DESIGNATIONS_XLSX) # switch slashes around
TOLL_DESIGNATIONS_DF <- read_excel(TOLL_DESIGNATIONS_XLSX, sheet = "Inputs_for_tollcalib")
TOLL_DESIGNATIONS_DF <- select(TOLL_DESIGNATIONS_DF, -c(Grouping major, Grouping minor)) #delete columns not used in this process

# this file specify which facilities is NOT dynamically tolled (thus don't need toll calibration)
if (dir.exists(file.path(PROJECT_DIR, "CTRAMP"))) {
    # full runs
    NON_DYNA_TOLL_CSV             <- file.path(PROJECT_DIR, "hwy", "NonDynamicTollFacilities.csv")
} else {
    if (dir.exists(file.path(PROJECT_DIR, "INPUT"))) {
        # extracted output folders of baseline runs
        NON_DYNA_TOLL_CSV             <- file.path(PROJECT_DIR, "INPUT", "hwy", "NonDynamicTollFacilities.csv")
    } else {
        # extracted output folders of project runs
        NON_DYNA_TOLL_CSV             <- file.path(PROJECT_DIR, "hwy", "NonDynamicTollFacilities.csv")
    }
}

# specify the following instead, if run as a stand alone script
# rm(list=ls()) # remove all variables from the r environment
# ITER <- 3
# PROJECT_DIR           <- "L:/RTP2021_PPA/Projects/2050_TM151_PPA_CG_16/2050_TM151_PPA_CG_16_preTollCalib" # note direction of the slash
# LOADED_NETWORK_CSV    <- file.path(PROJECT_DIR, "OUTPUT","avgload5period.csv")
# UNLOADED_NETWORK_DBF  <- file.path("L:/RTP2021_PPA/Projects/2050_TM151_PPA_CG_16/2050_TM151_PPA_CG_16_preTollCalib/INPUT/shapefiles", "network_links.dbf") # from cube_to_shapefile.py
# TOLLS_CSV             <- file.path(PROJECT_DIR, "INPUT", "hwy", "tolls.csv")
# TOLL_DESIGNATIONS_XLSX <- "L:/Application/Model_One/NextGenFwys/Tollclass_Designations/TOLLCLASS_Designations(forNoProject).xlsx"
# NON_DYNA_TOLL_CSV <- "M:/Application/Model One/RTP2021/Blueprint/Input_calibration/toll_optimization/NonDynamicTollFacilities.csv"
# MAX_TOLL <- .01
# THRESHOLD_SPEED <- 35
# if running this script on a project directory on L, you'll also need to change the path for the tolls.csv output in the end.

# specify the names of the outputs
OUTPUT_LINK_SPD_CSV             <- paste0("el_gp_link_speed_iter",ITER,".csv")
OUTPUT_AVG_SPD_CSV              <- paste0("el_gp_avg_speed_iter",ITER,".csv")
OUTPUT_NEW_TOLLS_CSV            <- paste0("tolls_iter",ITER+1,".csv")

unloaded_network_df      <- read.dbf(UNLOADED_NETWORK_DBF, as.is=TRUE) %>% select(A,B,USE,FT,TOLLCLASS)

# firstvalue should be consistent with what is defined in the hwy param block
# https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/hwyParam.block#L13
FIRSTVALUE <- 31

el_links_df    <-  filter(unloaded_network_df , TOLLCLASS>=FIRSTVALUE & TOLLCLASS<700000) # assume all all-lane-tolling links will be coded with tollclass > 700000
gp_links_df     <- filter(unloaded_network_df , USE==1 & (FT<=3 | FT==5 | FT==8 | FT==10))
notruck_links_df <- filter(unloaded_network_df , USE==4 & TOLLCLASS==0)
gp_notruck_links_df <-  bind_rows(gp_links_df, notruck_links_df) # links that are in parallel to EL links in a model network



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

el_group1_df   <- inner_join(el_group1_df, gp_notruck_links_df,
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
# summarize average speed at facility level and determine scenario
#############################################################

el_gp_summary_df <- el_gp_loaded_nan_df %>%
                    group_by(TOLLCLASS, USE) %>%
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


#---------------------------------------------------------------#
# all lane tolling doesn't have EL vs GP, so just set the "EL speed" to be the same as "GP speed"
#---------------------------------------------------------------#
# assume all all lane tolling links will be coded with tollclass > 700000
# previously:
# el_links_df    <-  filter(unloaded_network_df , TOLLCLASS>=FIRSTVALUE )
# el_links_df    <-  filter(unloaded_network_df , TOLLCLASS>=FIRSTVALUE & TOLLCLASS<700000) # assume all all-lane-tolling links will be coded with tollclass > 700000
# loaded_network_df          <- loaded_network_df  %>% select(a, b, ffs, cspdEA, cspdAM, cspdMD, cspdPM, cspdEV,  volEA_tot,  volAM_tot,  volMD_tot,  volPM_tot,  volEV_tot)

# merge tollclasses from unloaded network to the loaded network
# (because the toll classes on the loaded network shows up as ****)
loaded_network_df <- loaded_network_df %>% left_join(unloaded_network_df,
                                      by=c("a"="A", "b"="B"))

alllanetolling_links_df    <-  filter(loaded_network_df , TOLLCLASS>700000)

alllanetolling_summary_df <- alllanetolling_links_df %>%
                             group_by(TOLLCLASS, USE) %>%
                             summarise(avgspeed_EA    = mean(cspdEA),
                                       avgspeed_EA_GP = mean(cspdEA),
                                       avgspeed_AM    = mean(cspdAM),
                                       avgspeed_AM_GP = mean(cspdAM),
                                       avgspeed_MD    = mean(cspdMD),
                                       avgspeed_MD_GP = mean(cspdMD),
                                       avgspeed_PM    = mean(cspdPM),
                                       avgspeed_PM_GP = mean(cspdPM),
                                       avgspeed_EV    = mean(cspdEV),
                                       avgspeed_EV_GP = mean(cspdEV))

# add all lane tolling summary to the el gp summary
el_gp_summary_df <-  bind_rows(el_gp_summary_df, alllanetolling_summary_df)
# Get THRESHOLD_SPEED for each facility from TOLL_DESIGNATIONS_XLSX
el_gp_summary_df <- left_join(el_gp_summary_df, TOLL_DESIGNATIONS_DF, by=c("TOLLCLASS"="tollclass"))
#---------------------------------------------------------------#

# Determine scenarios:
#        EL_speed	   GP_speed
# Case1	  <=THRESHOLD_SPEED	        any	        EL too slow. Need to increase toll
# Case2	  >THRESHOLD_SPEED	          <=40	      GP too slow. Need to decrease toll (but still keep EL speed above THRESHOLD_SPEED mph)
# Case3	  THRESHOLD_SPEED-60	        40-60	      OK, as long as EL speed > GP speed in AM, MD and PM.  If not, need to increase toll.
# Case4	  >60	                    40-60	      GP a bit slow. Maybe decrease toll, depend on how large the difference is.
# Case5	  >THRESHOLD_SPEED	          >60	        Set toll to minimum

#AM
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_AM = case_when(avgspeed_AM>THRESHOLD_SPEED                      & avgspeed_AM_GP>60                      ~ "Case5 - set to min",
                                                                avgspeed_AM>60                                & avgspeed_AM_GP>40 & avgspeed_AM_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_AM>THRESHOLD_SPEED & avgspeed_AM<=60    & avgspeed_AM_GP>40 & avgspeed_AM_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_AM>THRESHOLD_SPEED                      & avgspeed_AM_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_AM<=THRESHOLD_SPEED                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                                   ~ "Undefined"))

#MD
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_MD = case_when(avgspeed_MD>THRESHOLD_SPEED                      & avgspeed_MD_GP>60                      ~ "Case5 - set to min",
                                                                avgspeed_MD>60                                & avgspeed_MD_GP>40 & avgspeed_MD_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_MD>THRESHOLD_SPEED & avgspeed_MD<=60    & avgspeed_MD_GP>40 & avgspeed_MD_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_MD>THRESHOLD_SPEED                      & avgspeed_MD_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_MD<=THRESHOLD_SPEED                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                                   ~ "Undefined"))
#PM
el_gp_summary_df <- el_gp_summary_df %>%
                                     mutate(Case_PM = case_when(avgspeed_PM>THRESHOLD_SPEED                      & avgspeed_PM_GP>60                      ~ "Case5 - set to min",
                                                                avgspeed_PM>60                                & avgspeed_PM_GP>40 & avgspeed_PM_GP<=60 ~ "Case4 - drop tolls slightly",
                                                                avgspeed_PM>THRESHOLD_SPEED & avgspeed_PM<=60    & avgspeed_PM_GP>40 & avgspeed_PM_GP<=60 ~ "Case3 - ok",
                                                                avgspeed_PM>THRESHOLD_SPEED                      & avgspeed_PM_GP<=40                     ~ "Case2 - drop tolls",
                                                                avgspeed_PM<=THRESHOLD_SPEED                                                              ~ "Case1 - raise tolls",
                                                                TRUE                                                                                   ~ "Undefined"))

#############################################################
# merge in the existing toll rates and determine toll adjustment
#############################################################
toll_rates_df          <- read.csv(file=TOLLS_CSV, header=TRUE, sep=",")
toll_rates_df          <- toll_rates_df  %>% select(tollclass, facility_name, use, tollam_da, tollmd_da, tollpm_da)

el_gp_summary_df <- el_gp_summary_df %>% left_join(toll_rates_df %>% select(-facility_name),
                                                   by=c("TOLLCLASS"="tollclass", "USE"="use"))

# determine new toll rates
el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollam_da_new = case_when(Case_AM == "Case1 - raise tolls"         ~ tollam_da + round(((60 - avgspeed_AM)/100), digits=2),
                                                                     Case_AM == "Case2 - drop tolls"          ~ pmax((tollam_da - round((avgspeed_AM - THRESHOLD_SPEED)/100*2, digits=2)), MIN_TOLL),
                                                                     Case_AM == "Case3 - ok"                  ~ pmax(tollam_da, MIN_TOLL),
                                                                     Case_AM == "Case4 - drop tolls slightly" ~ pmax((tollam_da - round((avgspeed_AM - avgspeed_AM_GP)/100/2, digits=2)), MIN_TOLL),
                                                                     Case_AM == "Case5 - set to min"          ~ MIN_TOLL))

el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollmd_da_new = case_when(Case_MD == "Case1 - raise tolls"          ~ tollmd_da + round(((60 - avgspeed_MD)/100), digits=2),
                                                                     Case_MD == "Case2 - drop tolls"           ~ pmax((tollmd_da - round((avgspeed_MD - THRESHOLD_SPEED)/100*2, digits=2)), MIN_TOLL),
                                                                     Case_MD == "Case3 - ok"                   ~ pmax(tollmd_da, MIN_TOLL),
                                                                     Case_MD == "Case4 - drop tolls slightly"  ~ pmax((tollmd_da - round((avgspeed_MD - avgspeed_MD_GP)/100/2, digits=2)), MIN_TOLL),
                                                                     Case_MD == "Case5 - set to min"           ~ MIN_TOLL))

el_gp_summary_df <- el_gp_summary_df %>%
                                    mutate(tollpm_da_new = case_when(Case_PM == "Case1 - raise tolls"          ~ tollpm_da + round(((60 - avgspeed_PM)/100), digits=2),
                                                                     Case_PM == "Case2 - drop tolls"           ~ pmax((tollpm_da - round((avgspeed_PM - THRESHOLD_SPEED)/100*2, digits=2)), MIN_TOLL),
                                                                     Case_PM == "Case3 - ok"                   ~ pmax(tollpm_da, MIN_TOLL),
                                                                     Case_PM == "Case4 - drop tolls slightly"  ~ pmax((tollpm_da - round((avgspeed_PM - avgspeed_PM_GP)/100/2, digits=2)), MIN_TOLL),
                                                                     Case_PM == "Case5 - set to min"           ~ MIN_TOLL))

# set maximum new toll for each tolling period
el_gp_summary_df$tollam_da_new[el_gp_summary_df$tollam_da_new > el_gp_summary_df$MAX_TOLL] <- el_gp_summary_df$MAX_TOLL
el_gp_summary_df$tollmd_da_new[el_gp_summary_df$tollmd_da_new > el_gp_summary_df$MAX_TOLL] <- el_gp_summary_df$MAX_TOLL
el_gp_summary_df$tollpm_da_new[el_gp_summary_df$tollpm_da_new > el_gp_summary_df$MAX_TOLL] <- el_gp_summary_df$MAX_TOLL

# drop the toll facilities that are not dynamically tolled
non_dyna_df  <- read.csv(file=NON_DYNA_TOLL_CSV , header=TRUE, sep=",")
el_gp_summary_df <- el_gp_summary_df %>% left_join(non_dyna_df,
                                          by=c("TOLLCLASS"="tollclass"))
el_gp_summary_df <- filter(el_gp_summary_df, is.na(NonDynamicTolling))

#############################################################
# write the new toll rates to a new tolls.csv
#############################################################
tolls_new_df <- el_gp_summary_df  %>% select(TOLLCLASS, facility_name, USE, tollam_da_new, tollmd_da_new, tollpm_da_new)

tolls_new_df <- tolls_new_df  %>%
                              mutate(fac_index = TOLLCLASS * 1000 + USE,
                                     tollclass = TOLLCLASS,
                                     tollseg   = 0,
                                     tolltype  = "expr_lane",
                                     use       = USE,
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


# add s2 tolls for selected facilities

# TOLL_DESIGNATIONS_DF <- read_excel(TOLL_DESIGNATIONS_XLSX, sheet = "Inputs_for_tollcalib")
# TOLL_DESIGNATIONS_DF <- TOLL_DESIGNATIONS_DF %>%
#                                              select(tollclass,s2toll_mandatory)

tolls_new_df <- left_join(tolls_new_df, TOLL_DESIGNATIONS_DF %>% select(-facility_name), by=c("tollclass"="tollclass"))

tolls_new_df <- tolls_new_df  %>%
                             mutate(tollam_s2 = case_when(s2toll_mandatory=="Yes" ~ tollam_da_new/2,
                                                          TRUE ~ 0))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollmd_s2 = case_when(s2toll_mandatory=="Yes" ~ tollmd_da_new/2,
                                                          TRUE ~ 0))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollpm_s2 = case_when(s2toll_mandatory=="Yes" ~ tollpm_da_new/2,
                                                          TRUE ~ 0))

# add s2 tolls if the drive alone toll is greater than $1 (in 2000$)

tolls_new_df <- tolls_new_df  %>%
                             mutate(tollam_s2 = ifelse(tollam_da_new>1, tollam_da_new/2, tollam_s2))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollmd_s2 = ifelse(tollmd_da_new>1, tollmd_da_new/2, tollmd_s2))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollpm_s2 = ifelse(tollpm_da_new>1, tollpm_da_new/2, tollpm_s2))


# for all-lane tolling, s2 and s3 tolls are dependant on the HOV discount

tolls_new_df <- tolls_new_df  %>%
                             mutate(tollam_s2 = ifelse(TOLLCLASS>700000, tollam_da_new*HOV2_discount_factor, tollam_s2))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollmd_s2 = ifelse(TOLLCLASS>700000, tollmd_da_new*HOV2_discount_factor, tollmd_s2))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollpm_s2 = ifelse(TOLLCLASS>700000, tollpm_da_new*HOV2_discount_factor, tollpm_s2))

tolls_new_df <- tolls_new_df  %>%
                             mutate(tollam_s3 = ifelse(TOLLCLASS>700000, tollam_da_new*HOV3_discount_factor, tollam_s3))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollmd_s3 = ifelse(TOLLCLASS>700000, tollmd_da_new*HOV3_discount_factor, tollmd_s3))
tolls_new_df <- tolls_new_df  %>%
                             mutate(tollpm_s3 = ifelse(TOLLCLASS>700000, tollpm_da_new*HOV3_discount_factor, tollpm_s3))




tolls_new_df <- tolls_new_df  %>% select(-c(TOLLCLASS, USE, tollam_da_new, tollmd_da_new, tollpm_da_new, s2toll_mandatory))
# TOLLCLASS is a "grouping variable" and can't be deleted unless it's ungrouped
tolls_new_df <- tolls_new_df  %>% ungroup()
tolls_new_df <- tolls_new_df  %>% select(-c(TOLLCLASS))

# make "toll_flat" equals to zero if it is an express lane
tolls_new_df <- tolls_new_df  %>% mutate(toll_flat=0)

# append the new toll rates to the first half of the toll.csv file containing the bridge tolls
old_tolls_df    <- read.csv(file=TOLLS_CSV, header=TRUE, sep=",")
bridge_tolls_df    <- filter(old_tolls_df, tollclass<FIRSTVALUE)

# also append the toll rates from the non-dynamically tolled road
nondyna_tolls_df <- old_tolls_df %>% left_join(non_dyna_df,
                                          by=c("tollclass"="tollclass"))
nondyna_tolls_df <- filter(nondyna_tolls_df, NonDynamicTolling==1)
nondyna_tolls_df <- nondyna_tolls_df  %>% select(-c(NonDynamicTolling))

bridge_el_tolls_df <- bind_rows(bridge_tolls_df, nondyna_tolls_df, tolls_new_df)


#############################################################
# output
#############################################################


# if it is running on a full model run
if (dir.exists(file.path(PROJECT_DIR, "CTRAMP"))) {

    # check if the folder "tollcalib_iter" exists, if not create one
    if (dir.exists(file.path(PROJECT_DIR, "tollcalib_iter"))) {
        # do nothing
    } else {
       dir.create(file.path(PROJECT_DIR, "tollcalib_iter"))
    }


    # output link level data to csv
    write.csv(el_gp_loaded_df, file.path(PROJECT_DIR, "tollcalib_iter", OUTPUT_LINK_SPD_CSV), row.names = FALSE)

    # output facility level summary to csv
    write.csv(el_gp_summary_df, file.path(PROJECT_DIR, "tollcalib_iter", OUTPUT_AVG_SPD_CSV), row.names = FALSE)

    # output a new tolls.csv
    write.csv(bridge_el_tolls_df, file.path(PROJECT_DIR, "hwy", OUTPUT_NEW_TOLLS_CSV), row.names = FALSE)

    # file path of the all iteration summary
    EL_GP_SUMMARY_ALL_CSV = file.path(PROJECT_DIR, "tollcalib_iter", "el_gp_summary_ALL.csv")

# if it is running on an extracted output folder
} else {


    # check if the folder "tollcalib_iter" exists, if not create one
    if (dir.exists(file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter"))) {
        # do nothing
    } else {
       dir.create(file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter"))
    }


    # output link level data to csv
    write.csv(el_gp_loaded_df, file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter", OUTPUT_LINK_SPD_CSV), row.names = FALSE)

    # output facility level summary to csv
    write.csv(el_gp_summary_df, file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter", OUTPUT_AVG_SPD_CSV), row.names = FALSE)

    # output a new tolls.csv
    write.csv(bridge_el_tolls_df, file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter", OUTPUT_NEW_TOLLS_CSV), row.names = FALSE)

    # file path of the all iteration summary
    EL_GP_SUMMARY_ALL_CSV = file.path(PROJECT_DIR, "OUTPUT", "tollcalib_iter", "el_gp_summary_ALL.csv")
}


# accumulate the speed summary from all iterations in one big file for visualization

el_gp_summary_df <- el_gp_summary_df %>% mutate(iter_num = paste0("iter",ITER))

if (file.exists(EL_GP_SUMMARY_ALL_CSV)) {
     el_gp_summary_ALL_df <- read.csv(file=EL_GP_SUMMARY_ALL_CSV, header=TRUE, sep=",")
     el_gp_summary_ALL_df <- bind_rows(el_gp_summary_ALL_df, el_gp_summary_df)
} else {
     el_gp_summary_ALL_df <- el_gp_summary_df
}

write.csv(el_gp_summary_ALL_df, file.path(EL_GP_SUMMARY_ALL_CSV), row.names = FALSE)
