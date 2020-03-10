
# 2015 unit person and HH balancing.R
# Balance units and households across TAZs, matching 2015 county-level totals,
# and ensuring that no TAZ has a lower total in 2015 than they do in 2010
# SI
# November 25, 2019

# Notes

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- dirname(rstudioapi::getActiveDocumentContext()$path)
setwd(wd)

"

1. 
"
# Import Libraries

suppressMessages(library(tidyverse))

# Establish file paths

USERPROFILE           <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM                <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
PBA_2010              <- file.path(BOX_TM, "Share Data",   "plan-bay-area-2040", "2010_06_003","tazData.csv")
Original_2015         <- "TAZ1454 2015 Land Use.csv"

# Bring in 2010 and 2015 data and keep/rename relevant variables to separate 2010 and 2015 fields

land_use_2010        <- read.csv(PBA_2010,header=TRUE) %>% 
  rename(TOTHH_2010=TOTHH,
         HHPOP_2010=HHPOP,
         TOTPOP_2010=TOTPOP, 	
         SFDU_2010=SFDU, 	
         MFDU_2010=MFDU, 	
         HHINCQ1_2010=HHINCQ1, 
         HHINCQ2_2010=HHINCQ2, 
         HHINCQ3_2010=HHINCQ3, 
         HHINCQ4_2010=HHINCQ4, 
         SHPOP62P_2010=SHPOP62P,
         AGE0004_2010=AGE0004, 
         AGE0519_2010=AGE0519, 
         AGE2044_2010=AGE2044, 
         AGE4564_2010=AGE4564, 
         AGE65P_2010=AGE65P, 	
         HHLDS_2010=hhlds, 	
         GQPOP_2010=gqpop) %>% 
  select(ZONE,
         DISTRICT,
         COUNTY,
         TOTHH_2010,   
         HHPOP_2010,   
         TOTPOP_2010,  
         SFDU_2010,    
         MFDU_2010,    
         HHINCQ1_2010, 
         HHINCQ2_2010, 
         HHINCQ3_2010, 
         HHINCQ4_2010, 
         SHPOP62P_2010,
         AGE0004_2010, 
         AGE0519_2010, 
         AGE2044_2010, 
         AGE4564_2010, 
         AGE65P_2010,  
         HHLDS_2010,   
         GQPOP_2010)

land_use_2015        <- read.csv(Original_2015,header=TRUE) %>% 
  rename(TOTHH_2015=TOTHH,
         HHPOP_2015=HHPOP,
         TOTPOP_2015=TOTPOP, 	
         SFDU_2015=SFDU, 	
         MFDU_2015=MFDU, 	
         HHINCQ1_2015=HHINCQ1, 
         HHINCQ2_2015=HHINCQ2, 
         HHINCQ3_2015=HHINCQ3, 
         HHINCQ4_2015=HHINCQ4, 
         SHPOP62P_2015=SHPOP62P,
         AGE0004_2015=AGE0004, 
         AGE0519_2015=AGE0519, 
         AGE2044_2015=AGE2044, 
         AGE4564_2015=AGE4564, 
         AGE65P_2015=AGE65P, 	
         HHLDS_2015=hhlds, 	
         GQPOP_2015=gqpop) %>% 
  select(ZONE,
         DISTRICT,
         COUNTY,
         TOTHH_2015,   
         HHPOP_2015,   
         TOTPOP_2015,  
         SFDU_2015,    
         MFDU_2015,    
         HHINCQ1_2015, 
         HHINCQ2_2015, 
         HHINCQ3_2015, 
         HHINCQ4_2015, 
         SHPOP62P_2015,
         AGE0004_2015, 
         AGE0519_2015, 
         AGE2044_2015, 
         AGE4564_2015, 
         AGE65P_2015,  
         HHLDS_2015,   
         GQPOP_2015)

# Join 2010 amd 2015 files together to support comparisons 

combined <- left_join(land_use_2010, land_use_2015, by=c("ZONE","DISTRICT","COUNTY")) 

# Add variable that measures differences between 2010 and 2015 households

combined <- combined %>% mutate(TOTHH_10_15 = TOTHH_2015-TOTHH_2010)

# Export a quick summary comparing 2010/2015 units/hhs

quick_summary <- combined %>%
  mutate(total_units_2010=MFDU_2010+SFDU_2010,total_units_2015=MFDU_2015+SFDU_2015,
  County_Name=case_when(
    COUNTY==1 ~ "San Francisco",
    COUNTY==2 ~ "San Mateo",
    COUNTY==3 ~ "Santa Clara",
    COUNTY==4 ~ "Alameda",
    COUNTY==5 ~ "Contra Costa",
    COUNTY==6 ~ "Solano",
    COUNTY==7 ~ "Napa",
    COUNTY==8 ~ "Sonoma",
    COUNTY==9 ~ "Marin"
  )) %>% 
  group_by(COUNTY,County_Name) %>% 
  summarize(total_units_2010=sum(total_units_2010),total_units_2015=sum(total_units_2015),TOTHH_2010=sum(TOTHH_2010),
            TOTHH_2015=sum(TOTHH_2015))

write.csv(quick_summary, "Quick Total Units and HHs Comparison.csv", row.names = FALSE, quote = T)

# Adjust total households
# Also compute share of SFDU for 2015 for later application
  
temp1 <- combined %>% 
  group_by(COUNTY) %>% 
  summarize(HH_absolute_growth=sum(TOTHH_10_15))   # Get absolute growth of 2010 and 2015 HH datasets by county

temp2 <- combined %>% mutate(
  HH_positive_growth=if_else(TOTHH_10_15>0,TOTHH_10_15,0L)
) %>%
  group_by(COUNTY) %>% 
  summarize(HH_positive_growth=sum(HH_positive_growth))            # Identify TAZs with 2015 totals > 2010, sum to county

combined <- left_join(combined,temp1, by="COUNTY")                 # Join county totals to dataset
combined <- left_join(combined,temp2,by="COUNTY") %>% mutate(
  HH_growth_share=if_else(TOTHH_10_15>=0,TOTHH_10_15/HH_positive_growth,0),
  HH_distribution=if_else(TOTHH_10_15>=0,HH_absolute_growth*HH_growth_share,0),
  HH_distribution=as.integer(round(HH_distribution,0)),            # Assign share of 2010-2015 growth by relative percentages
  TOTHH_2015=TOTHH_2010+HH_distribution)                           # Calculate new totals - either 2010 if previously below, or
                                                                   # greater if 2015 totals were higher than 2010
combined <- combined %>%                                           # Remove unneeded fields
  select(-TOTHH_10_15,-HH_absolute_growth,-HH_positive_growth,-HH_growth_share,-HH_distribution)
rm(temp1,temp2)                                                    # Remove temporary datasets

# Add variable that measures differences between 2010 and 2015 units
# Adjust total units
# Compute share of SFDU for 2015 for later MFDU/SFDU distribution

combined <- combined %>% mutate(
    TOTUNITS_10 = SFDU_2010 + MFDU_2010,
    TOTUNITS_15 = SFDU_2015 + MFDU_2015,
    TOTUNITS_10_15 = TOTUNITS_15-TOTUNITS_10,
    SFDU_15_share = if_else(TOTUNITS_15!=0,SFDU_2015/TOTUNITS_15,0)) # Avoid divide by zero error

temp1 <- combined %>% 
  group_by(COUNTY) %>% 
  summarize(unit_absolute_growth=sum(TOTUNITS_10_15))   # Get absolute growth of 2010 and 2015 unit datasets by county

temp2 <- combined %>% mutate(
  unit_positive_growth=if_else(TOTUNITS_10_15>0,TOTUNITS_10_15,0L)
) %>%
  group_by(COUNTY) %>% 
  summarize(unit_positive_growth=sum(unit_positive_growth))        # Identify TAZs with 2015 totals > 2010, sum to county

combined <- left_join(combined,temp1, by="COUNTY")                 # Join county totals to dataset
combined <- left_join(combined,temp2,by="COUNTY") %>% mutate(
  unit_growth_share=if_else(TOTUNITS_10_15>=0,TOTUNITS_10_15/unit_positive_growth,0),
  unit_distribution=if_else(TOTUNITS_10_15>=0,unit_absolute_growth*unit_growth_share,0),
  unit_distribution=as.integer(round(unit_distribution,0)),        # Assign share of 2010-2015 growth by relative percentages
  TOTUNITS_15=TOTUNITS_10+unit_distribution)                       # Calculate new totals - either 2010 if previously below, or
                                                                   # greater if 2015 totals were higher than 2010
combined <- combined %>% mutate(                                   # Distribute total units into SFDU and MFDU
  SFDU_2015=as.integer(round(SFDU_15_share*TOTUNITS_15)),
  MFDU_2015=as.integer(round(TOTUNITS_15-SFDU_2015)))

combined <- combined %>%                                           # Remove unneeded fields
  select(-TOTUNITS_10,-TOTUNITS_15,-TOTUNITS_10_15,-SFDU_15_share,-unit_absolute_growth,-unit_positive_growth,
         -unit_growth_share,-unit_distribution)
rm(temp1,temp2)                                                    # Remove temporary datasets

# Export file for review

write.csv(combined, "Adjusted TAZ1454 2015 Land Use.csv", row.names = FALSE, quote = T)


  
