# Create_2035_land_use_for_updated_RGF.R
# Scale 2035 land use for the Plan Bay Area 2050+ updated regional growth forecast
# SI

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set up directories

USERPROFILE     <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BAUS            <- file.path(USERPROFILE,"Box","Modeling and Surveys","Urban Modeling","Bay Area UrbanSim")
BAUS_FOLDER     <- file.path(BAUS,"PBA50","Final Blueprint runs","Final Blueprint (s24)","BAUS v2.25 - FINAL VERSION")
taz_in          <- file.path(BAUS_FOLDER,"run182_taz_summaries_2035_UBI.csv")
county_in       <- file.path(BAUS_FOLDER,"run182_county_summaries_2035.csv")
GROWTH_FOLDER   <- file.path(USERPROFILE,"Box","Plan Bay Area 2050+","Regional Growth Forecast","Presentations and Attachments","supporting_data")
rgf_in          <- file.path(GROWTH_FOLDER, "Draft Regional Growth Forecast_091423_RPP3.xlsx")
output          <- "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/LandUse_n_Popsyn/2035_v01"

# Bring in PBA 2050 TAZ 2035 datasets, remove row number variable
# Bring in county marginals
# Bring in PBA 2050+ Regional Growth Forecast tabs, excerpting rows/columns with relevant values

taz_in_2035     <- read.csv(taz_in) %>% select(-X)
county_in_2035  <- read.csv(county_in) 
rgf_main        <- read_excel(rgf_in,sheet = "MAIN")[1:5,c(1,5)]
rgf_income      <- (read_excel(rgf_in,sheet = "Households by Income"))[c(3,6),1:6]
rgf_age         <- read_excel(rgf_in,sheet = "Population by Age Detail")[5,2:7]
rgf_jobs        <- read_excel(rgf_in,sheet = "Jobs by Sector")[1:6,c(1,5)]

# Export names to retain same order/selection of final datasets

taz_order    <- names(taz_in_2035)
county_order <- names(county_in_2035)

# Calculate households by income scalers, total households will be summed from components

income1_scale <- as.numeric(rgf_income[2,2])/sum(taz_in_2035$HHINCQ1)
income2_scale <- as.numeric(rgf_income[2,3])/sum(taz_in_2035$HHINCQ2)
income3_scale <- as.numeric(rgf_income[2,4])/sum(taz_in_2035$HHINCQ3)
income4_scale <- as.numeric(rgf_income[2,5])/sum(taz_in_2035$HHINCQ4)

# Calculate persons by age scalers, total employment will be summed from components

age0004_scale <- as.numeric(rgf_age[1,2])/sum(taz_in_2035$AGE0004)
age0519_scale <- as.numeric(rgf_age[1,3])/sum(taz_in_2035$AGE0519)
age2044_scale <- as.numeric(rgf_age[1,4])/sum(taz_in_2035$AGE2044)
age4564_scale <- as.numeric(rgf_age[1,5])/sum(taz_in_2035$AGE4564)
age65p_scale  <- as.numeric(rgf_age[1,6])/sum(taz_in_2035$AGE65P)

# Calculate jobs by sector scalers, total jobs will be summed from components

agrempn_scale <- as.numeric(rgf_jobs[1,2])/sum(taz_in_2035$AGREMPN)
fpsempn_scale <- as.numeric(rgf_jobs[2,2])/sum(taz_in_2035$FPSEMPN)
herempn_scale <- as.numeric(rgf_jobs[3,2])/sum(taz_in_2035$HEREMPN)
mwtempn_scale <- as.numeric(rgf_jobs[4,2])/sum(taz_in_2035$MWTEMPN)
othempn_scale <- as.numeric(rgf_jobs[5,2])/sum(taz_in_2035$OTHEMPN)
retempn_scale <- as.numeric(rgf_jobs[6,2])/sum(taz_in_2035$RETEMPN)

# Calculate employed residents scaler

empres_scale  <- as.numeric(rgf_main[5,2])/sum(taz_in_2035$EMPRES)

# Adjust units

units_scale   <- as.numeric(rgf_main[3,2])/sum(taz_in_2035$RES_UNITS)


# Start adjustments, calling updated dataset taz_in_2035p to represent 2050+ values
# Sum select totals from components as described above (e.g., households by income)


taz_in_2035p <- taz_in_2035 %>% 
  mutate(HHINCQ1      = round(HHINCQ1*income1_scale,0),         # Households by income
         HHINCQ2      = round(HHINCQ2*income2_scale,0),
         HHINCQ3      = round(HHINCQ3*income3_scale,0),
         HHINCQ4      = round(HHINCQ4*income4_scale,0),
         
         TOTHH        = HHINCQ1 + HHINCQ2 + HHINCQ3 + HHINCQ4)   # Sum total households for this variable and later calcs

# HH scale for other HH components

hh_scale     <- sum(taz_in_2035p$TOTHH)/sum(taz_in_2035$TOTHH)    
         
# Apply HH scale to remaining household components

taz_in_2035p <- taz_in_2035p %>% 
  mutate(hh_kids_no   = round(hh_kids_no*hh_scale,0),           # Households with and without kids
         hh_kids_yes  = round(hh_kids_yes*hhscale,0),
         
         hh_wrks_0       = round(hh_wrks_0*hh_scale,0),         # Households by number of workers
         hh_wrks_1       = round(hh_wrks_1*hh_scale,0),
         hh_wrks_2       = round(hh_wrks_2*hh_scale,0),
         hh_wrks_3_plus  = round(hh_wrks_3_plus*hh_scale,0),
         
         hh_size_1       = round(hh_size_1*hh_scale,0),         # Households by size
         hh_size_2       = round(hh_size_2*hh_scale,0),
         hh_size_3       = round(hh_size_3*hh_scale,0),
         hh_size_4_plus  = round(hh_size_4_plus*hh_scale,0),
         
# Apply age scalers and sum to total population
         
         AGE0004         = round(AGE0004*age0004_scale,0),
         AGE0519         = round(AGE0519*age0519_scale,0),
         AGE2044         = round(AGE2044*age2044_scale,0),
         AGE4564         = round(AGE4564*age4564_scale,0),
         AGE65P          = round(AGE65P*age65p_scale,0),

         TOTPOP          = sum(AGE0004 + AGE0519 + AGE2044 + AGE4564 + AGE65P)

         




)


















pop_scaling_vars <- final_2020 %>% select("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name",
                                          "TOTHH", "HHPOP", "HHINCQ1", "HHINCQ2","HHINCQ3", 
                                          "HHINCQ4", "AGE0004", "AGE0519", "AGE2044", "AGE4564", 
                                          "AGE65P", "SFDU", "MFDU", "hh_size_1", "hh_size_2", "hh_size_3", 
                                          "hh_size_4_plus", "hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus", 
                                          "hh_kids_yes", "hh_kids_no", "AGE62P", "gq_type_univ", "gq_type_mil", 
                                          "gq_type_othnon", "gqpop", "white_nonh", "black_nonh", "asian_nonh", 
                                          "other_nonh", "hispanic", "TOTPOP", "hh_own","hh_rent")

emp_scaling_vars <- final_2020 %>% select("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name","EMPRES",  
                                          "pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                                          "pers_occ_retail", "pers_occ_manual", "pers_occ_military")

non_scaling_vars <- final_2020 %>% select("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name",
  "TOTACRE", "RESACRE", "CIACRE", "PRKCST", "OPRKCST", "AREATYPE","TOPOLOGY", "TERMINAL", "ZERO", 
  "SHPOP62P","HSENROLL", "COLLFTE", "COLLPTE")

pop_scaling_vars_updated <- left_join(pop_scaling_vars,DOF_scaling[,c("County_Name","Ratio_2023_2020")],by=c("County_Name")) %>% 
  mutate_at(c(6:41),~.*Ratio_2023_2020) %>% 
  select(-Ratio_2023_2020) %>% 
  mutate_at(c(6:41),~round(.,0))

emp_scaling_vars_updated <- emp_scaling_vars %>% 
  mutate_at(c(6:12),~.*Employ_ratio_2023_2020) %>% 
  mutate_at(c(6:12),~round(.,0))

# Join everything back together and append 2023 employment file too

scaling_vars_updated <- left_join(pop_scaling_vars_updated,emp_scaling_vars_updated,
                                  by=c("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name")) %>% 
                        left_join(.,non_scaling_vars,by=c("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name")) %>% 
                        left_join(.,employment_2023,by=c("ZONE"="TAZ1454"))
  
# Now make fix small variations due to rounding for precisely-matching totals
# Find max value in categorical data to adjust totals so they match univariate totals
# For example, the households by income across categories should sum to equal total HHs
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total
final_2023 <- scaling_vars_updated %>%       
   mutate (
    max_age    = max.col(.[c("AGE0004","AGE0519","AGE2044","AGE4564","AGE65P")],     ties.method="first"),
    max_gq     = max.col(.[c("gq_type_univ","gq_type_mil","gq_type_othnon")],        ties.method="first"),
    max_tenure = max.col(.[c("hh_own","hh_rent")],                                   ties.method="first"),
    max_size   = max.col(.[c("hh_size_1","hh_size_2","hh_size_3","hh_size_4_plus")], ties.method="first"),
    max_workers= max.col(.[c("hh_wrks_0","hh_wrks_1","hh_wrks_2","hh_wrks_3_plus")], ties.method="first"),
    max_kids   = max.col(.[c("hh_kids_yes","hh_kids_no")],                           ties.method="first"),
    max_income = max.col(.[c("HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4")],              ties.method="first"),
    max_occ    = max.col(.[c("pers_occ_management","pers_occ_professional",
                             "pers_occ_services","pers_occ_retail",
                             "pers_occ_manual","pers_occ_military")],                ties.method="first"),
    max_eth    = max.col(.[c("white_nonh","black_nonh","asian_nonh","other_nonh",
                             "hispanic")],                                           ties.method="first"),
    
# Now use max values determined above to find appropriate column for adjustment
    
    # Balance population by age
    
    AGE0004 = if_else(max_age==1,AGE0004+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE0004),
    AGE0519 = if_else(max_age==2,AGE0519+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE0519),
    AGE2044 = if_else(max_age==3,AGE2044+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE2044),
    AGE4564 = if_else(max_age==4,AGE4564+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE4564),
    AGE65P  = if_else(max_age==5,AGE65P +(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE65P), 
    
    # Balance population by ethnicity
    
    white_nonh = if_else(max_eth==1,white_nonh+(TOTPOP-(white_nonh+black_nonh+asian_nonh+other_nonh+
                                                          hispanic)),white_nonh),
    black_nonh = if_else(max_eth==2,black_nonh+(TOTPOP-(white_nonh+black_nonh+asian_nonh+other_nonh+
                                                          hispanic)),black_nonh),
    asian_nonh = if_else(max_eth==3,asian_nonh+(TOTPOP-(white_nonh+black_nonh+asian_nonh+other_nonh+
                                                          hispanic)),asian_nonh),
    other_nonh = if_else(max_eth==4,other_nonh+(TOTPOP-(white_nonh+black_nonh+asian_nonh+other_nonh+
                                                          hispanic)),other_nonh),
    hispanic = if_else(max_eth==5,hispanic+(TOTPOP-(white_nonh+black_nonh+asian_nonh+other_nonh+
                                                          hispanic)),hispanic),
    
    # Balance GQ population by type
    
    gq_type_univ   = if_else(max_gq==1,gq_type_univ+(gqpop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_univ),
    gq_type_mil    = if_else(max_gq==2,gq_type_mil+(gqpop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_mil),
    gq_type_othnon = if_else(max_gq==3,gq_type_othnon+(gqpop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_othnon),

    #Balance HH tenure categories

    hh_own         = if_else(max_tenure==1,hh_own       +(TOTHH-(hh_own+hh_rent)),hh_own),
    hh_rent        = if_else(max_tenure==2,hh_rent      +(TOTHH-(hh_own+hh_rent)),hh_rent),
   
    #Balance HH size categories
    
    hh_size_1      = if_else(max_size==1,hh_size_1     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_1),
    hh_size_2      = if_else(max_size==2,hh_size_2     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_2),
    hh_size_3      = if_else(max_size==3,hh_size_3     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_3),
    hh_size_4_plus = if_else(max_size==4,hh_size_4_plus+(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_4_plus),
    
    #Balance HH worker categories
    
    hh_wrks_0      = if_else(max_workers==1,hh_wrks_0+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_0),
    hh_wrks_1      = if_else(max_workers==2,hh_wrks_1+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_1),
    hh_wrks_2      = if_else(max_workers==3,hh_wrks_2+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_2),
    hh_wrks_3_plus = if_else(max_workers==4,hh_wrks_3_plus+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_3_plus),
    
    #Balance HH kids categories
    
    hh_kids_yes = if_else(max_kids==1,hh_kids_yes+(TOTHH-(hh_kids_yes+hh_kids_no)),hh_kids_yes),
    hh_kids_no  = if_else(max_kids==2,hh_kids_no +(TOTHH-(hh_kids_yes+hh_kids_no)),hh_kids_no),
    
    # Balance HH income categories
    
    HHINCQ1 = if_else(max_income==1,HHINCQ1+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ1),
    HHINCQ2 = if_else(max_income==2,HHINCQ2+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ2),
    HHINCQ3 = if_else(max_income==3,HHINCQ3+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ3),
    HHINCQ4 = if_else(max_income==4,HHINCQ4+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ4),

    # Balance workers by occupation categories
    
    pers_occ_management   = if_else(max_occ==1,pers_occ_management+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_management),
    pers_occ_professional = if_else(max_occ==2,pers_occ_professional+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_professional),
    pers_occ_services     = if_else(max_occ==3,pers_occ_services+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_services),
    pers_occ_retail       = if_else(max_occ==4,pers_occ_retail+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_retail),
    pers_occ_manual       = if_else(max_occ==5,pers_occ_manual+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_manual),
    pers_occ_military     = if_else(max_occ==6,pers_occ_military+(EMPRES-(pers_occ_management+pers_occ_professional+
                                      pers_occ_services+pers_occ_retail+pers_occ_manual+pers_occ_military)),pers_occ_military)
) %>% 
  
# Remove max variables
  
  select(-max_age,-max_gq,-max_size,-max_workers,-max_kids,-max_income,-max_occ, -max_eth, -max_tenure) 
  
### End of recoding
# Write out subsets of final 2020 data
 
New2023 <- final_2023 %>%
  mutate(hhlds=TOTHH) %>%
  select(ZONE,DISTRICT,SD,COUNTY,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,TOTACRE,
         RESACRE,CIACRE,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TERMINAL,TOPOLOGY,ZERO,hhlds,
         gqpop) 

# Summarize ACS and employment data by superdistrict for both 2015 and 2020

summed23 <- New2023 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=sum(gqpop)) %>% 
  ungroup()

# Export new 2020 data, 2015 and 2020 district summary data

write.csv(New2023, "TAZ1454 2023 Land Use.csv", row.names = FALSE, quote = T)
write.csv(summed23, "TAZ1454 2023 District Summary.csv", row.names = FALSE, quote = T)

# Select out PopSim variables and export to separate csv

popsim_vars <- final_2023 %>% 
  rename(TAZ=ZONE,gq_tot_pop=gqpop)%>%
  select(TAZ,TOTHH,TOTPOP,hh_own,hh_rent,hh_size_1,hh_size_2,hh_size_3,hh_size_4_plus,hh_wrks_0,hh_wrks_1,hh_wrks_2,hh_wrks_3_plus,
         hh_kids_no,hh_kids_yes,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,
         gq_tot_pop,gq_type_univ,gq_type_mil,gq_type_othnon)

write.csv(popsim_vars, "TAZ1454 2023 Popsim Vars.csv", row.names = FALSE, quote = T)

# region popsim vars
popsim_vars_region <- popsim_vars %>% 
  mutate(REGION=1) %>%
  group_by(REGION) %>%
  summarize(gq_num_hh_region=sum(gq_tot_pop))

write.csv(popsim_vars_region, "TAZ1454 2023 Popsim Vars Region.csv", row.names = FALSE, quote = T)

# county popsim vars
popsim_vars_county <- final_2023 %>%
  group_by(COUNTY) %>% summarize(
    pers_occ_management  =sum(pers_occ_management),
    pers_occ_professional=sum(pers_occ_professional),
    pers_occ_services    =sum(pers_occ_services),
    pers_occ_retail      =sum(pers_occ_retail),
    pers_occ_manual      =sum(pers_occ_manual),
    pers_occ_military    =sum(pers_occ_military))

write.csv(popsim_vars_county, "TAZ1454 2023 Popsim Vars County.csv", row.names = FALSE, quote = T)

# Bring in superdistrict name for joining

superdistrict <- read_excel(file.path(BASEYEAR,"2015","TAZ1454 2015 Land Use.xlsx"),sheet="2010 District Summary") %>% 
  select("DISTRICT","DISTRICT_NAME"="DISTRICT NAME") %>% 
  filter(!(DISTRICT=="Bay Area")) %>% 
  mutate(DISTRICT=as.numeric(DISTRICT))

# Output into Tableau-friendly long format

New2023_long <- New2023 %>%
  left_join(.,county_joiner,by="ZONE") %>% 
  left_join(.,superdistrict,by="DISTRICT") %>% 
  mutate(Year=2023) %>% 
  select(ZONE,DISTRICT,DISTRICT_NAME,COUNTY,County_Name,Year,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

write.csv(New2023_long,"TAZ1454_2023_long.csv",row.names = F)



