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

temp1 <- cbind(incommute_share,industry_share) %>% 
  mutate(in_agrempn=in_agrempn*Share_Incommute,
         in_fpsempn=in_fpsempn*Share_Incommute,
         in_herempn=in_herempn*Share_Incommute,
         in_mwtempn=in_mwtempn*Share_Incommute,
         in_othempn=in_othempn*Share_Incommute,
         in_retempn=in_retempn*Share_Incommute)

# Summarize industry totals by composite superdistrict

temp2 <- employment %>% 
  group_by(Comp_SD) %>% 
  summarize(A_ESRI_SUM=sum(A_ESRI),A_LODES_SUM=sum(A_LODES), A_NETS_SUM=sum(A_NETS),A_NETS_NOSOLE_SUM=sum(A_NETS_NOSOLE),
            F_ESRI_SUM=sum(F_ESRI),F_LODES_SUM=sum(F_LODES), F_NETS_SUM=sum(F_NETS),F_NETS_NOSOLE_SUM=sum(F_NETS_NOSOLE),
            H_ESRI_SUM=sum(H_ESRI),H_LODES_SUM=sum(H_LODES), H_NETS_SUM=sum(H_NETS),H_NETS_NOSOLE_SUM=sum(H_NETS_NOSOLE),
            M_ESRI_SUM=sum(M_ESRI),M_LODES_SUM=sum(M_LODES), M_NETS_SUM=sum(M_NETS),M_NETS_NOSOLE_SUM=sum(M_NETS_NOSOLE),
            O_ESRI_SUM=sum(O_ESRI),O_LODES_SUM=sum(O_LODES), O_NETS_SUM=sum(O_NETS),O_NETS_NOSOLE_SUM=sum(O_NETS_NOSOLE),
            R_ESRI_SUM=sum(R_ESRI),R_LODES_SUM=sum(R_LODES), R_NETS_SUM=sum(R_NETS),R_NETS_NOSOLE_SUM=sum(R_NETS_NOSOLE))

# Join temp1 and temp2 and create composite superdistrict incommute adjustment factors to apply to TAZ-level employment
# Agricultural sector data is poor and uneven, in some instances showing higher incommute than total employment (different sources)
# For agricultural sector, if the factor computes to less than zero, overwrite as 1

temp3 <- left_join(temp1,temp2,by="Comp_SD") %>% mutate(
  A_ESRI_FACTOR               =if_else((1-(in_agrempn/A_ESRI_SUM))>0,1-(in_agrempn/A_ESRI_SUM),1),
  A_LODES_FACTOR              =if_else((1-(in_agrempn/A_LODES_SUM))>0,1-(in_agrempn/A_LODES_SUM),1),  
  A_NETS_FACTOR               =if_else((1-(in_agrempn/A_NETS_SUM))>0,1-(in_agrempn/A_NETS_SUM),1),
  A_NETS_NOSOLE_FACTOR        =if_else((1-(in_agrempn/A_NETS_NOSOLE_SUM))>0,1-(in_agrempn/A_NETS_NOSOLE_SUM),1),
  F_ESRI_FACTOR               =1-(in_fpsempn/F_ESRI_SUM),
  F_LODES_FACTOR              =1-(in_fpsempn/F_LODES_SUM),
  F_NETS_FACTOR               =1-(in_fpsempn/F_NETS_SUM),
  F_NETS_NOSOLE_FACTOR        =1-(in_fpsempn/F_NETS_NOSOLE_SUM),
  H_ESRI_FACTOR               =1-(in_herempn/H_ESRI_SUM),
  H_LODES_FACTOR              =1-(in_herempn/H_LODES_SUM),
  H_NETS_FACTOR               =1-(in_herempn/H_NETS_SUM),
  H_NETS_NOSOLE_FACTOR        =1-(in_herempn/H_NETS_NOSOLE_SUM),
  M_ESRI_FACTOR               =1-(in_mwtempn/M_ESRI_SUM),
  M_LODES_FACTOR              =1-(in_mwtempn/M_LODES_SUM),
  M_NETS_FACTOR               =1-(in_mwtempn/M_NETS_SUM),
  M_NETS_NOSOLE_FACTOR        =1-(in_mwtempn/M_NETS_NOSOLE_SUM),
  O_ESRI_FACTOR               =1-(in_othempn/O_ESRI_SUM),
  O_LODES_FACTOR              =1-(in_othempn/O_LODES_SUM),
  O_NETS_FACTOR               =1-(in_othempn/O_NETS_SUM),
  O_NETS_NOSOLE_FACTOR        =1-(in_othempn/O_NETS_NOSOLE_SUM),
  R_ESRI_FACTOR               =1-(in_retempn/R_ESRI_SUM),
  R_LODES_FACTOR              =1-(in_retempn/R_LODES_SUM),
  R_NETS_FACTOR               =1-(in_retempn/R_NETS_SUM),
  R_NETS_NOSOLE_FACTOR        =1-(in_retempn/R_NETS_NOSOLE_SUM))

incommute_factors <- temp3 %>% 
  select(Comp_SD,A_ESRI_FACTOR,A_LODES_FACTOR,A_NETS_FACTOR,A_NETS_NOSOLE_FACTOR,
         F_ESRI_FACTOR,F_LODES_FACTOR,F_NETS_FACTOR,F_NETS_NOSOLE_FACTOR,
         H_ESRI_FACTOR,H_LODES_FACTOR,H_NETS_FACTOR,H_NETS_NOSOLE_FACTOR,
         M_ESRI_FACTOR,M_LODES_FACTOR,M_NETS_FACTOR,M_NETS_NOSOLE_FACTOR,
         O_ESRI_FACTOR,O_LODES_FACTOR,O_NETS_FACTOR,O_NETS_NOSOLE_FACTOR,
         R_ESRI_FACTOR,R_LODES_FACTOR,R_NETS_FACTOR,R_NETS_NOSOLE_FACTOR)


# Join incommute adjustment factors to employment TAZ dataset, by composite superdistrict
# Calculate new variable values by dataset and industrial sector, at the TAZ level, using incommute factors
# Add self-employment back into LODES_SELF variable
# Calculate totals by industrial sector and dataset for no-incommute TAZ-level values (e.g., T_ESRI_NOIN)
# Select out variables of interest

employment_no_incommute <- left_join(employment,incommute_factors,by="Comp_SD") %>% mutate(
  A_ESRI_NOIN              =A_ESRI          *A_ESRI_FACTOR,       
  A_LODES_NOIN      	     =A_LODES         *A_LODES_FACTOR,
  A_LODES_SELF_NOIN        =A_LODES_NOIN    +A_ACS_Self_Emp,
  A_NETS_NOIN       	     =A_NETS          *A_NETS_FACTOR,       
  A_NETS_NOSOLE_NOIN	     =A_NETS_NOSOLE   *A_NETS_NOSOLE_FACTOR,
  F_ESRI_NOIN       	     =F_ESRI          *F_ESRI_FACTOR,       
  F_LODES_NOIN      	     =F_LODES         *F_LODES_FACTOR, 
  F_LODES_SELF_NOIN        =F_LODES_NOIN    +F_ACS_Self_Emp,
  F_NETS_NOIN       	     =F_NETS          *F_NETS_FACTOR,       
  F_NETS_NOSOLE_NOIN	     =F_NETS_NOSOLE   *F_NETS_NOSOLE_FACTOR,
  H_ESRI_NOIN       	     =H_ESRI          *H_ESRI_FACTOR,       
  H_LODES_NOIN      	     =H_LODES         *H_LODES_FACTOR,  
  H_LODES_SELF_NOIN        =H_LODES_NOIN    +H_ACS_Self_Emp,
  H_NETS_NOIN       	     =H_NETS          *H_NETS_FACTOR,       
  H_NETS_NOSOLE_NOIN	     =H_NETS_NOSOLE   *H_NETS_NOSOLE_FACTOR,
  M_ESRI_NOIN       	     =M_ESRI          *M_ESRI_FACTOR,       
  M_LODES_NOIN      	     =M_LODES         *M_LODES_FACTOR,  
  M_LODES_SELF_NOIN        =M_LODES_NOIN    +M_ACS_Self_Emp,
  M_NETS_NOIN       	     =M_NETS          *M_NETS_FACTOR,       
  M_NETS_NOSOLE_NOIN	     =M_NETS_NOSOLE   *M_NETS_NOSOLE_FACTOR,
  O_ESRI_NOIN       	     =O_ESRI          *O_ESRI_FACTOR,       
  O_LODES_NOIN      	     =O_LODES         *O_LODES_FACTOR, 
  O_LODES_SELF_NOIN        =O_LODES_NOIN    +O_ACS_Self_Emp,
  O_NETS_NOIN       	     =O_NETS          *O_NETS_FACTOR,       
  O_NETS_NOSOLE_NOIN	     =O_NETS_NOSOLE   *O_NETS_NOSOLE_FACTOR,
  R_ESRI_NOIN       	     =R_ESRI          *R_ESRI_FACTOR,       
  R_LODES_NOIN      	     =R_LODES         *R_LODES_FACTOR,
  R_LODES_SELF_NOIN        =R_LODES_NOIN    +R_ACS_Self_Emp,
  R_NETS_NOIN       	     =R_NETS          *R_NETS_FACTOR,       
  R_NETS_NOSOLE_NOIN	     =R_NETS_NOSOLE   *R_NETS_NOSOLE_FACTOR) %>% 
  rename(TAZ=ZONE,County=county) %>% 
  select(TAZ,County,
         A_ESRI,A_ACS_Self_Emp,A_LODES,A_LODES_SELF,A_NETS,A_NETS_NOSOLE, 
         F_ESRI,F_ACS_Self_Emp,F_LODES,F_LODES_SELF,F_NETS,F_NETS_NOSOLE, 
         H_ESRI, H_ACS_Self_Emp, H_LODES, H_LODES_SELF,H_NETS,H_NETS_NOSOLE,
         M_ESRI, M_ACS_Self_Emp, M_LODES, M_LODES_SELF,M_NETS,M_NETS_NOSOLE,
         O_ESRI, O_ACS_Self_Emp, O_LODES, O_LODES_SELF,O_NETS,O_NETS_NOSOLE,
         R_ESRI, R_ACS_Self_Emp, R_LODES, R_LODES_SELF,R_NETS,R_NETS_NOSOLE,
         T_ESRI, T_ACS_Self_Emp, T_LODES, T_LODES_SELF,T_NETS,T_NETS_NOSOLE,
         
         A_ESRI_NOIN,A_LODES_NOIN,A_LODES_SELF_NOIN,A_NETS_NOIN,A_NETS_NOSOLE_NOIN,
         F_ESRI_NOIN,F_LODES_NOIN,F_LODES_SELF_NOIN,F_NETS_NOIN,F_NETS_NOSOLE_NOIN,
         H_ESRI_NOIN,H_LODES_NOIN,H_LODES_SELF_NOIN,H_NETS_NOIN,H_NETS_NOSOLE_NOIN,
         M_ESRI_NOIN,M_LODES_NOIN,M_LODES_SELF_NOIN,M_NETS_NOIN,M_NETS_NOSOLE_NOIN,
         O_ESRI_NOIN,O_LODES_NOIN,O_LODES_SELF_NOIN,O_NETS_NOIN,O_NETS_NOSOLE_NOIN,
         R_ESRI_NOIN,R_LODES_NOIN,R_LODES_SELF_NOIN,R_NETS_NOIN,R_NETS_NOSOLE_NOIN) %>% mutate(
           
         T_ESRI_NOIN=A_ESRI_NOIN+F_ESRI_NOIN+H_ESRI_NOIN+M_ESRI_NOIN+O_ESRI_NOIN+R_ESRI_NOIN,
         T_LODES_NOIN=A_LODES_NOIN+F_LODES_NOIN+H_LODES_NOIN+M_LODES_NOIN+O_LODES_NOIN+R_LODES_NOIN,
         T_LODES_SELF_NOIN=A_LODES_SELF_NOIN+F_LODES_SELF_NOIN+H_LODES_SELF_NOIN+M_LODES_SELF_NOIN+O_LODES_SELF_NOIN+R_LODES_SELF_NOIN,
         T_NETS_NOIN=A_NETS_NOIN+F_NETS_NOIN+H_NETS_NOIN+M_NETS_NOIN+O_NETS_NOIN+R_NETS_NOIN,
         T_NETS_NOSOLE_NOIN=A_NETS_NOSOLE_NOIN+F_NETS_NOSOLE_NOIN+H_NETS_NOSOLE_NOIN+M_NETS_NOSOLE_NOIN+O_NETS_NOSOLE_NOIN+R_NETS_NOSOLE_NOIN)

write.csv(employment_no_incommute, "Employment data by sector with and wo incommute 032420.csv", row.names = FALSE, quote = T)

