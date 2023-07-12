# Create 2023 TAZ Data from 2020 Vintage.R
# Create "2023" TAZ data by inflating values from the 2020 dataset 
# SI

# Notes

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set up directories, import TAZ/census block equivalence, install census key, set ACS year,set CPI inflation

employment_2015_data           <- "M:/Data/BusinessData/Employment_by_TAZ_industry/BusinessData_2015_TAZ_industry_noincommute.csv"

USERPROFILE          <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
PETRALE              <- file.path(USERPROFILE,"Documents","GitHub","Petrale","Applications","travel_model_lu_inputs")

# Bring in TAZ 2020 dataset, dataframe is named "final_2020"

load(file.path(Petrale,"2020","TAZ Land Use File 2020.rdata"))

# Bring in California Department of Finance 2023/2020 scaling values for counties

DOF_scaling <- read_excel(file.path(Petrale,"2023","P2A_County_Total.xlsx"),sheet = "2023_2020 Ratio")

# Select out scaling vars, apply scaling factors and round values

scaling_vars <- final_2020 %>% select("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name",
   "HSENROLL", "COLLFTE", "COLLPTE",  "TOTHH", "HHPOP", "EMPRES", "HHINCQ1", "HHINCQ2", 
  "HHINCQ3", "HHINCQ4", "AGE0004", "AGE0519", "AGE2044", "AGE4564", 
  "AGE65P", "SFDU", "MFDU", "hh_size_1", "hh_size_2", "hh_size_3", 
  "hh_size_4_plus", "hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus", 
  "hh_kids_yes", "hh_kids_no", "AGE62P", "gq_type_univ", "gq_type_mil", 
  "gq_type_othnon", "gqpop", "pers_occ_management", "pers_occ_professional", 
  "pers_occ_services", "pers_occ_retail", "pers_occ_manual", "pers_occ_military", 
  "white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic", 
   "TOTPOP", "emp_sec11", "emp_sec21", 
  "emp_sec22", "emp_sec23", "emp_sec3133", "emp_sec42", "emp_sec4445", 
  "emp_sec4849", "emp_sec51", "emp_sec52", "emp_sec53", "emp_sec54", 
  "emp_sec55", "emp_sec56", "emp_sec61", "emp_sec62", "emp_sec71", 
  "emp_sec72", "emp_sec81", "emp_sec92", "emp_sec99", "TOTEMP", 
  "AGREMPN", "FPSEMPN", "HEREMPN", "MWTEMPN", "OTHEMPN", "RETEMPN")

non_scaling_vars <- final_2020 %>% select("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name",
  "TOTACRE", "RESACRE", "CIACRE", "PRKCST", "OPRKCST", "AREATYPE","TOPOLOGY", "TERMINAL", "ZERO", 
  "SHPOP62P")

scaling_vars_updated <- left_join(scaling_vars,DOF_scaling[,c("County_Name","Ratio_2023_2020")],by=c("County_Name")) %>% 
  mutate_at(c(6:77),~.*Ratio_2023_2020) %>% 
  select(-Ratio_2023_2020) %>% 
  mutate_at(c(6:77),~round(.,0))

 
# Now make fix small variations due to rounding for precisely-matching totals
# Find max value in categorical data to adjust totals so they match univariate totals
# For example, the households by income across categories should sum to equal total HHs
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total
final_2023 <- scaling_vars_updated %>%       
   mutate (
    max_age    = max.col(.[c("AGE0004","AGE0519","AGE2044","AGE4564","AGE65P")],     ties.method="first"),
    max_gq     = max.col(.[c("gq_type_univ","gq_type_mil","gq_type_othnon")],        ties.method="first"),
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
  
  select(-max_age,-max_gq,-max_size,-max_workers,-max_kids,-max_income,-max_occ, -max_eth) %>% 
  
# Join with non-scaled vars
  
  left_join(.,non_scaling_vars,by=c("ZONE", "DISTRICT", "SD", "COUNTY", "County_Name"))

### End of recoding

# Write out ethnic variables

ethnic <- temp_rounded_adjusted %>% 
  select(TAZ1454,hispanic, white_nonh,black_nonh,asian_nonh,other_nonh,TOTPOP, COUNTY, County_Name)

write.csv (ethnic,file = "TAZ1454_Ethnicity.csv",row.names = FALSE)

# Read in old PBA data sets and select variables for joining to new 2015 dataset
# Bring in updated 2020 employment for joining
# Bring in school and parking data from PBA 2040, 2015 TAZ data 
# Add HHLDS variable (same as TOTHH), select new 2015 output

PBA2015_joiner <- PBA2015%>%
  select(ZONE,DISTRICT,SD,TOTACRE,RESACRE,CIACRE,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TOPOLOGY,TERMINAL, ZERO)

#employment_2015 <- read.csv(employment_2015_data,header=TRUE) 


joined_15_20      <- left_join(PBA2015_joiner,temp_rounded_adjusted, by=c("ZONE"="TAZ1454")) # Join 2015 topology, parking, enrollment
joined_employment <- left_join(joined_15_20,employment_2015, by=c("ZONE"="TAZ1454"))        # Join employment

# Save R version of data for 2020 to later inflate to 2023


# Write out subsets of final 2020 data
 
New2020 <- joined_employment %>%
  mutate(hhlds=TOTHH) %>%
  select(ZONE,DISTRICT,SD,COUNTY,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,TOTACRE,
         RESACRE,CIACRE,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TERMINAL,TOPOLOGY,ZERO,hhlds,
         gqpop) 

# Summarize ACS and employment data by superdistrict for both 2015 and 2020

summed15 <- PBA2015 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=TOTPOP-HHPOP) %>% 
  ungroup()

summed20 <- New2020 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=sum(gqpop)) %>% 
  ungroup()

# Export new 2020 data, 2015 and 2020 district summary data

write.csv(New2020, "TAZ1454 2020 Land Use.csv", row.names = FALSE, quote = T)
write.csv(summed15, "TAZ1454 2015 District Summary.csv", row.names = FALSE, quote = T)
write.csv(summed20, "TAZ1454 2020 District Summary.csv", row.names = FALSE, quote = T)

# Select out PopSim variables and export to separate csv

popsim_vars <- temp_rounded_adjusted %>% 
  rename(TAZ=TAZ1454,gq_tot_pop=gqpop)%>%
  select(TAZ,TOTHH,TOTPOP,hh_size_1,hh_size_2,hh_size_3,hh_size_4_plus,hh_wrks_0,hh_wrks_1,hh_wrks_2,hh_wrks_3_plus,
         hh_kids_no,hh_kids_yes,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,
         gq_tot_pop,gq_type_univ,gq_type_mil,gq_type_othnon)

write.csv(popsim_vars, "TAZ1454 2020 Popsim Vars.csv", row.names = FALSE, quote = T)

# region popsim vars
popsim_vars_region <- popsim_vars %>% 
  mutate(REGION=1) %>%
  group_by(REGION) %>%
  summarize(gq_num_hh_region=sum(gq_tot_pop))

write.csv(popsim_vars_region, "TAZ1454 2020 Popsim Vars Region.csv", row.names = FALSE, quote = T)

# county popsim vars
popsim_vars_county <- joined_15_20 %>%
  group_by(COUNTY) %>% summarize(
    pers_occ_management  =sum(pers_occ_management),
    pers_occ_professional=sum(pers_occ_professional),
    pers_occ_services    =sum(pers_occ_services),
    pers_occ_retail      =sum(pers_occ_retail),
    pers_occ_manual      =sum(pers_occ_manual),
    pers_occ_military    =sum(pers_occ_military))

write.csv(popsim_vars_county, "TAZ1454 2020 Popsim Vars County.csv", row.names = FALSE, quote = T)


