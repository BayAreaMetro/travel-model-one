# Apply Incommute Shares.R
# Apply incommute shares to employment data
# March 22, 2020
# SI

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set working directory

wd <- "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment"
setwd(wd)

# Location of data files

employment_data     = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/taz_esri_lodes_nets032320.xlsx"
incommute_data      = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/2012-2016 CTPP Places to Superdistrict Equivalency.xlsx"
industry_share_data = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/ACS 2013-2017 Incommute by Industry.xlsx"

# Bring in employment data

employment        <- read_excel (employment_data,sheet="Summary_SingleHeader") %>% rename(ZONE=zone_id)
incommute_eq      <- read_excel (incommute_data,sheet="TAZ Incommute Equivalence") 
incommute_share   <- read_excel (incommute_data,sheet="Comp_SD Incommute Equivalence")
industry_share    <- read_excel (industry_share_data,sheet="Ind_Incommute_Values")

# Join incommute equivalency, distribute industry shares of incommute across composite superdistricts

employment <- left_join(employment,incommute_eq,by="ZONE")

temp <- cbind(incommute_share,industry_share) %>% 
  mutate(in_agrempn=in_agrempn*Share_Incommute,
         in_fpsempn=in_fpsempn*Share_Incommute,
         in_herempn=in_herempn*Share_Incommute,
         in_mwtempn=in_mwtempn*Share_Incommute,
         in_othempn=in_othempn*Share_Incommute,
         in_retempn=in_retempn*Share_Incommute)

# Summarize industry totals by composite superdistrict

temp <- employment %>% 
  group_by(Comp_SD) %>% 
  summarize(A_ESRI_SUM=sum(A_ESRI),A_LODES_SUM=sum(A_LODES), A_NETS_SUM=sum(A_NETS),A_NETS_NOSOLE_SUM=sum(A_NETS_NOSOLE),
            F_ESRI_SUM=sum(F_ESRI),F_LODES_SUM=sum(F_LODES), F_NETS_SUM=sum(F_NETS),F_NETS_NOSOLE_SUM=sum(F_NETS_NOSOLE),
            H_ESRI_SUM=sum(H_ESRI),H_LODES_SUM=sum(H_LODES), H_NETS_SUM=sum(H_NETS),H_NETS_NOSOLE_SUM=sum(H_NETS_NOSOLE),
            M_ESRI_SUM=sum(M_ESRI),M_LODES_SUM=sum(M_LODES), M_NETS_SUM=sum(M_NETS),M_NETS_NOSOLE_SUM=sum(M_NETS_NOSOLE),
            O_ESRI_SUM=sum(O_ESRI),O_LODES_SUM=sum(O_LODES), O_NETS_SUM=sum(O_NETS),O_NETS_NOSOLE_SUM=sum(O_NETS_NOSOLE),
            R_ESRI_SUM=sum(R_ESRI),R_LODES_SUM=sum(R_LODES), R_NETS_SUM=sum(R_NETS),R_NETS_NOSOLE_SUM=sum(R_NETS_NOSOLE))

# Join summary by composite superdistrict and industry share variables,
# reduce employment by respective incommute share

employment <- left_join(employment,temp,by="Comp_SD") %>% 
  cbind(.,industry_share)

write.csv(employment, "trial.csv", row.names = FALSE, quote = T)






employment <- cbind(employment, industry_share)

