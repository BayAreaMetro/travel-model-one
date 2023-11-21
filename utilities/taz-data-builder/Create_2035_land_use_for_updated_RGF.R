# Create_2035_land_use_for_updated_RGF.R
# Scale 2035 land use for the Plan Bay Area 2050+ updated regional growth forecast
# SI

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set up directories

USERPROFILE     <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_FOLDER      <- file.path(USERPROFILE,"Box")
# for VM-users, Box is typically in E: because C: is too small
if (USERPROFILE %in% c("C:/Users/lzorn")) {
  BOX_FOLDER    <- file.path("E:/Box")
}
BAUS            <- file.path(BOX_FOLDER,"Modeling and Surveys","Urban Modeling","Bay Area UrbanSim")
BAUS_FOLDER     <- file.path(BAUS,"PBA50","Final Blueprint runs","Final Blueprint (s24)","BAUS v2.25 - FINAL VERSION")
taz_in          <- file.path(BAUS_FOLDER,"run182_taz_summaries_2035_UBI.csv")
county_in       <- file.path(BAUS_FOLDER,"run182_county_summaries_2035.csv")
GROWTH_FOLDER   <- file.path(BOX_FOLDER,"Plan Bay Area 2050+","Regional Growth Forecast","Presentations and Attachments","supporting_data")
rgf_in          <- file.path(GROWTH_FOLDER, "Draft Regional Growth Forecast_091423_RPP3.xlsx")
output          <- "M:/Application/Model One/RTP2025/INPUT_DEVELOPMENT/LandUse_n_Popsyn/2035_v01/Create_2035_land_use_for_updated_RGF"
print(BAUS_FOLDER)

# relative to here
COUNTY_NUM      <- file.path("..","geographies","superdistrict-county.csv")

# Bring in PBA 2050 TAZ 2035 datasets, remove row number variable
# Bring in county marginals
# Bring in PBA 2050+ Regional Growth Forecast tabs, excerpting rows/columns with relevant values

taz_in_2035     <- read.csv(taz_in) %>% select(-X)
county_in_2035  <- read.csv(county_in) 
rgf_main        <- read_excel(rgf_in,sheet = "MAIN")[1:5,c(1,5)]
rgf_income      <- read_excel(rgf_in,sheet = "Households by Income")[c(3,6),1:6]
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

# Calculate persons by age scalers, total population will be summed from components

age0004_scale <- as.numeric(rgf_age[1,2])/sum(taz_in_2035$AGE0004)
age0519_scale <- as.numeric(rgf_age[1,3])/sum(taz_in_2035$AGE0519)
age2044_scale <- as.numeric(rgf_age[1,4])/sum(taz_in_2035$AGE2044)
age4564_scale <- as.numeric(rgf_age[1,5])/sum(taz_in_2035$AGE4564)
age65p_scale  <- as.numeric(rgf_age[1,6])/sum(taz_in_2035$AGE65P)

# Calculate jobs by sector scalers, total employment will be summed from components

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
         hh_kids_yes  = round(hh_kids_yes*hh_scale,0),
         
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

         TOTPOP          = AGE0004 + AGE0519 + AGE2044 + AGE4564 + AGE65P)


# Calculate total population scale for other population components

pop_scale     <- sum(taz_in_2035p$TOTPOP)/sum(taz_in_2035$TOTPOP)  

# Scale remaining population variables
# gt_tot_pop calculated by summing group quarters components

taz_in_2035p <- taz_in_2035p %>% 
  mutate(HHPOP          = round(HHPOP*pop_scale,0),
         GQPOP          = round(GQPOP*pop_scale,0),
         gq_type_univ   = round(gq_type_univ*pop_scale,0),
         gq_type_mil    = round(gq_type_mil*pop_scale,0),
         gq_type_othnon = round(gq_type_othnon*pop_scale,0),
         
         gq_tot_pop     = gq_type_univ + gq_type_mil + gq_type_othnon,
         
# Adjust the units

         RES_UNITS      = round(RES_UNITS*units_scale,0),
         MFDU           = round(MFDU*units_scale,0),
         SFDU           = round(SFDU*units_scale,0),

# Adjust the employed residents

         EMPRES         = round(EMPRES*empres_scale,0),

# Adjust the jobs by sector using individual component scalers
# Sum total employment

         AGREMPN        = round(AGREMPN*agrempn_scale,0),
         FPSEMPN        = round(FPSEMPN*fpsempn_scale,0),
         HEREMPN        = round(HEREMPN*herempn_scale,0),
         RETEMPN        = round(RETEMPN*retempn_scale,0),
         MWTEMPN        = round(MWTEMPN*mwtempn_scale,0),
         OTHEMPN        = round(OTHEMPN*othempn_scale,0),

         TOTEMP         = AGREMPN + FPSEMPN + HEREMPN + RETEMPN + MWTEMPN + OTHEMPN)

# Marginal totals were summed from components for three categories:
# Persons by age, households by income, and jobs by sector 
# For the other marginals, components need to be reconciled so they cleanly add to total values
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total

final_taz <- taz_in_2035p %>%       
  mutate (
    max_gq     = max.col(.[c("gq_type_univ","gq_type_mil","gq_type_othnon")],        ties.method="first"),
    max_units  = max.col(.[c("MFDU","SFDU")],                                        ties.method="first"),
    max_pop    = max.col(.[c("HHPOP","GQPOP")],                                      ties.method="first"),
    max_size   = max.col(.[c("hh_size_1","hh_size_2","hh_size_3","hh_size_4_plus")], ties.method="first"),
    max_workers= max.col(.[c("hh_wrks_0","hh_wrks_1","hh_wrks_2","hh_wrks_3_plus")], ties.method="first"),
    max_kids   = max.col(.[c("hh_kids_yes","hh_kids_no")],                           ties.method="first"),

# Now use max values determined above to find appropriate column for adjustment
    
    # Balance GQ population by type
    
    gq_type_univ   = if_else(max_gq==1,gq_type_univ   +(gq_tot_pop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_univ),
    gq_type_mil    = if_else(max_gq==2,gq_type_mil    +(gq_tot_pop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_mil),
    gq_type_othnon = if_else(max_gq==3,gq_type_othnon +(gq_tot_pop-(gq_type_univ+gq_type_mil+gq_type_othnon)),gq_type_othnon),
    
    # Balance unit categories
    
    MFDU           = if_else(max_units==1,MFDU          +(RES_UNITS-(MFDU+SFDU)),MFDU),
    SFDU           = if_else(max_units==2,SFDU          +(RES_UNITS-(MFDU+SFDU)),SFDU),

    # Balance HHPOP and GQPOP

    HHPOP          = if_else(max_pop==1,HHPOP          +(TOTPOP-(HHPOP+GQPOP)),HHPOP),
    GQPOP          = if_else(max_pop==2,GQPOP          +(TOTPOP-(HHPOP+GQPOP)),GQPOP),
    
    # Balance HH size categories
    
    hh_size_1      = if_else(max_size==1,hh_size_1     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_1),
    hh_size_2      = if_else(max_size==2,hh_size_2     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_2),
    hh_size_3      = if_else(max_size==3,hh_size_3     +(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_3),
    hh_size_4_plus = if_else(max_size==4,hh_size_4_plus+(TOTHH-(hh_size_1+hh_size_2+hh_size_3+hh_size_4_plus)),hh_size_4_plus),
    
    # Balance HH worker categories
    
    hh_wrks_0      = if_else(max_workers==1,hh_wrks_0+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_0),
    hh_wrks_1      = if_else(max_workers==2,hh_wrks_1+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_1),
    hh_wrks_2      = if_else(max_workers==3,hh_wrks_2+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_2),
    hh_wrks_3_plus = if_else(max_workers==4,hh_wrks_3_plus+(TOTHH-(hh_wrks_0+hh_wrks_1+hh_wrks_2+hh_wrks_3_plus)),hh_wrks_3_plus),
    
    # Balance HH kids categories
    
    hh_kids_yes = if_else(max_kids==1,hh_kids_yes+(TOTHH-(hh_kids_yes+hh_kids_no)),hh_kids_yes),
    hh_kids_no  = if_else(max_kids==2,hh_kids_no +(TOTHH-(hh_kids_yes+hh_kids_no)),hh_kids_no),
    
) %>% 
  
  # Remove max variables from dataset
  
  select(-max_gq,-max_units, -max_size,-max_workers,-max_kids,-max_pop) 
  
# Summarize marginals at the county level
# First excerpt variables that won't change for later joining

county_vars <- county_in_2035 %>% 
  select(COUNTY_NAME,
         SHPOP62P,
         TOTACRE,
         DENSITY,
         AREATYPE,
         RESACRE_UNWEIGHTED,
         CIACRE_UNWEIGHTED,
         CIACRE,
         RESACRE)

county_sum <- final_taz %>% 
  group_by(COUNTY_NAME) %>% 
  summarize(AGREMPN   =sum(AGREMPN),
            FPSEMPN   =sum(FPSEMPN),
            HEREMPN   =sum(HEREMPN),
            RETEMPN   =sum(RETEMPN),
            MWTEMPN   =sum(MWTEMPN),
            OTHEMPN   =sum(OTHEMPN),
            TOTEMP    =sum(TOTEMP),
            HHINCQ1   =sum(HHINCQ1),
            HHINCQ2   =sum(HHINCQ2),
            HHINCQ3   =sum(HHINCQ3),
            HHINCQ4   =sum(HHINCQ4),
            HHPOP     =sum(HHPOP),
            TOTHH     =sum(TOTHH),
            GQPOP     =sum(GQPOP),
            TOTPOP    =sum(TOTPOP),
            RES_UNITS =sum(RES_UNITS),
            MFDU      =sum(MFDU),
            SFDU      =sum(SFDU),
            EMPRES    =sum(EMPRES),
            AGE0004   =sum(AGE0004),
            AGE0519   =sum(AGE0519),
            AGE2044   =sum(AGE2044),
            AGE4564   =sum(AGE4564),
            AGE65P    =sum(AGE65P)) %>% 
  ungroup()

# Join summed variables to unchanged variables, reorder variables using select function
            
final_county <- left_join(county_vars,county_sum,by="COUNTY_NAME") %>% 
  select(all_of(county_order))

# Need COUNTY number
county_num_name_df <- read.csv(COUNTY_NUM)
county_num_name_df <- select(county_num_name_df, COUNTY, COUNTY_NAME) %>%
 distinct(.keep_all = TRUE)
final_county <- left_join(final_county, county_num_name_df)

# Output files

write.csv(final_taz,   file.path(output,"PBA50_ScaleToRGF_taz_summaries_2035.csv"),row.names = F)
write.csv(final_county,file.path(output,"PBA50_ScaleToRGF_county_marginals_2035.csv"),row.names = F)

print(paste("Wrote",file.path(output,"PBA50_ScaleToRGF_taz_summaries_2035.csv")))
print(paste("Wrote",file.path(output,"PBA50_ScaleToRGF_county_marginals_2035.csv")))

