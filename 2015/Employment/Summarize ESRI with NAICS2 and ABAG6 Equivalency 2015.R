# Summarize ESRI with NAICS2 and ABAG6 Equivalency 2015.R
# Sum ESRI 2015 data to TAZ levelfor NAICS2 and use equivalency for ABAG6 categories
# Scale to regional total (4,005,318, from https://mtcdrive.app.box.com/file/654134152628)
# Remove incommuters, using incommute shares to superdistricts to account for non-uniform incommuting rates around region

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

# Data locations

USERPROFILE             <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
esri_location           <- file.path(USERPROFILE,"Box", "esri", "ESRI_2015_Disaggregate.Rdata")
incommute_eq_location   <- paste0(wd,"2012-2016 CTPP Places to Superdistrict Equivalency.xlsx")
incommute_tot_location  <- paste0(wd,"ACS 2013-2017 Incommute by Industry.xlsx")

reg_total = 4005318          # 2015 regional jobs total from https://mtcdrive.app.box.com/file/654134152628

# Bring in data, deal with missing values

load(esri_location)
incommute_eq      <- read_excel (incommute_eq_location,sheet="TAZ Incommute Equivalence") 
incommute_share   <- read_excel (incommute_eq_location,sheet="Comp_SD Incommute Equivalence")
incommute_total   <- read_excel (incommute_tot_location,sheet="Incommute_Total")

temp  <- ESRI_2015_Disaggregate %>%     # Remove missing cases
  filter(naics2 !=0)
  
esri  <- temp %>% mutate(               # Change name of sector codes for later manipulation (list to matrix)
  naics2=case_when(
    naics2==11   ~ "emp_sec11",
    naics2==21   ~ "emp_sec21",
    naics2==22   ~ "emp_sec22",
    naics2==23   ~ "emp_sec23",
    naics2==42   ~ "emp_sec42",
    naics2==51   ~ "emp_sec51",
    naics2==52   ~ "emp_sec52",
    naics2==53   ~ "emp_sec53",
    naics2==54   ~ "emp_sec54",
    naics2==55   ~ "emp_sec55",
    naics2==56   ~ "emp_sec56",
    naics2==61   ~ "emp_sec61",
    naics2==62   ~ "emp_sec62",
    naics2==71   ~ "emp_sec71",
    naics2==72   ~ "emp_sec72",
    naics2==81   ~ "emp_sec81",
    naics2==92   ~ "emp_sec92",
    naics2==3133 ~ "emp_sec3133",
    naics2==4445 ~ "emp_sec4445",
    naics2==4849 ~ "emp_sec4849",
    TRUE         ~ "Not coded"
  )
)

# Summarize by naics2, spread to matrix format

esri_taz_naics2 <- esri %>% 
  group_by(TAZ1454,naics2) %>% 
  summarize(employment=sum(EMPNUM)) %>% 
  spread(naics2,employment,fill=0) 

# Create row for San Quentin zero employment, merge employment data for ABAG6 and NAICS2 categories

quentin2 <- data.frame(
  TAZ1454   = 1439,
  emp_sec11 = 0,
  emp_sec21 = 0,
  emp_sec22 = 0,
  emp_sec23 = 0,
  emp_sec42 = 0,
  emp_sec51 = 0,
  emp_sec52 = 0,
  emp_sec53 = 0,
  emp_sec54 = 0,
  emp_sec55 = 0,
  emp_sec56 = 0,
  emp_sec61 = 0,
  emp_sec62 = 0,
  emp_sec71 = 0,
  emp_sec72 = 0,
  emp_sec81 = 0,
  emp_sec92 = 0,
  emp_sec3133 = 0,
  emp_sec4445 = 0,
  emp_sec4849 = 0)

esri_all <- rbind(as.data.frame(esri_taz_naics2),quentin2)  %>%          # Append data and sort by TAZ
  arrange(TAZ1454) %>% mutate(
    TOTEMP=emp_sec11+emp_sec21+emp_sec22+emp_sec23+emp_sec42+emp_sec51+  # Sum total employment from categories
      emp_sec52+emp_sec53+emp_sec54+emp_sec55+emp_sec56+emp_sec61+
      emp_sec62+emp_sec71+emp_sec72+emp_sec81+emp_sec92+emp_sec3133+
      emp_sec4445+emp_sec4849)

# Now create scale function to apply to all ESRI employment categories

scale_reg <- function(x) (x*reg_total/sum(esri_all$TOTEMP))   # Scale regional total from REMI over ESRI employment
esri_scaled <- esri_all %>% 
  mutate_at(c("emp_sec11",
              "emp_sec21",
              "emp_sec22",
              "emp_sec23",
              "emp_sec42",
              "emp_sec51",
              "emp_sec52",
              "emp_sec53",
              "emp_sec54",
              "emp_sec55",
              "emp_sec56",
              "emp_sec61",
              "emp_sec62",
              "emp_sec71",
              "emp_sec72",
              "emp_sec81",
              "emp_sec92",
              "emp_sec3133",
              "emp_sec4445",
              "emp_sec4849",
              "TOTEMP"), scale_reg)

# Distribute incommute and reduce regional employment totals by incommute total
# CTPP data were used to distribute the incommute - place-to-place data were smallest home-to-work geo available
# Tract-to-tract data have missing geocoded data and are unreliable
# Workers at work at the place level minus regional workers at work equals incommuters, roughly
# Places were matched to superdistricts or "composite superdistricts" - groups of superdistricts
# Incommuters were distributed across superdistricts or composite superdistricts according to calculated shares

esri_scaled_eq <- left_join(esri_scaled,incommute_eq, by=c("TAZ1454" = "ZONE")) # Join equivalency

temp_incommute <- cbind(incommute_share,incommute_total) %>%    # Calculate number of incommuters by 
  mutate(Incommute_Portion=Share_Incommute*Incommute_Total)     # Superdistrict or composite superdistrict

temp_esri_sum <- esri_scaled_eq %>% 
  group_by(Comp_SD) %>%                 # Calculate scaling factors for each TAZ within a SD or composite SD
  summarize(Comp_SD_Total=sum(TOTEMP))  # Within respective SDs or composite SDs, TAZ factors are uniform                        
            
incommute_factors <- left_join(temp_incommute,temp_esri_sum,by="Comp_SD") %>% mutate(
 Incommute_Factor =1-(Incommute_Portion/Comp_SD_Total)) %>%     # Join factors to TAZs
  select(Comp_SD,Incommute_Factor)

esri_no_incommute <- left_join(esri_scaled_eq,incommute_factors,by="Comp_SD") %>% mutate(
  TOTEMP      =  round((TOTEMP*Incommute_Factor),0),
  emp_sec11   =  round((emp_sec11*Incommute_Factor),0),
  emp_sec21   =  round((emp_sec21*Incommute_Factor),0),   # Apply factors and round resultant values
  emp_sec22   =  round((emp_sec22*Incommute_Factor),0),
  emp_sec23   =  round((emp_sec23*Incommute_Factor),0),
  emp_sec42   =  round((emp_sec42*Incommute_Factor),0),
  emp_sec51   =  round((emp_sec51*Incommute_Factor),0),
  emp_sec52   =  round((emp_sec52*Incommute_Factor),0),
  emp_sec53   =  round((emp_sec53*Incommute_Factor),0),
  emp_sec54   =  round((emp_sec54*Incommute_Factor),0),
  emp_sec55   =  round((emp_sec55*Incommute_Factor),0),
  emp_sec56   =  round((emp_sec56*Incommute_Factor),0),
  emp_sec61   =  round((emp_sec61*Incommute_Factor),0),
  emp_sec62   =  round((emp_sec62*Incommute_Factor),0),
  emp_sec71   =  round((emp_sec71*Incommute_Factor),0),
  emp_sec72   =  round((emp_sec72*Incommute_Factor),0),
  emp_sec81   =  round((emp_sec81*Incommute_Factor),0),
  emp_sec92   =  round((emp_sec92*Incommute_Factor),0),
  emp_sec3133 =  round((emp_sec3133*Incommute_Factor),0),
  emp_sec4445 =  round((emp_sec4445*Incommute_Factor),0),
  emp_sec4849 =  round((emp_sec4849*Incommute_Factor),0),
  max_naics2  = max.col(.[c("emp_sec11","emp_sec21","emp_sec22","emp_sec23","emp_sec42","emp_sec51","emp_sec52",  
                            "emp_sec53","emp_sec54","emp_sec55","emp_sec56","emp_sec61","emp_sec62","emp_sec71",  
                            "emp_sec72","emp_sec81","emp_sec92","emp_sec3133","emp_sec4445","emp_sec4849")],        
                            ties.method="first")) %>%   # Find max column for later adjustment
                                                        # This ensures that marginal employment matches subtotals

# Now use max values determined above to find appropriate column for adjustment

mutate(
  naics2_subtotal=emp_sec11+emp_sec21+emp_sec22+emp_sec23+emp_sec42+emp_sec51+emp_sec52+emp_sec53+emp_sec54+
    emp_sec55+emp_sec56+emp_sec61+emp_sec62+emp_sec71+emp_sec72+emp_sec81+emp_sec92+emp_sec3133+emp_sec4445+
    emp_sec4849,
  
# Balance NAICS-2 categories

  emp_sec11   =  if_else(max_naics2==1, emp_sec11  +(TOTEMP-naics2_subtotal),emp_sec11),  
  emp_sec21   =  if_else(max_naics2==2, emp_sec21  +(TOTEMP-naics2_subtotal),emp_sec21),  
  emp_sec22   =  if_else(max_naics2==3, emp_sec22  +(TOTEMP-naics2_subtotal),emp_sec22),  
  emp_sec23   =  if_else(max_naics2==4, emp_sec23  +(TOTEMP-naics2_subtotal),emp_sec23),  
  emp_sec42   =  if_else(max_naics2==5, emp_sec42  +(TOTEMP-naics2_subtotal),emp_sec42),  
  emp_sec51   =  if_else(max_naics2==6, emp_sec51  +(TOTEMP-naics2_subtotal),emp_sec51),  
  emp_sec52   =  if_else(max_naics2==7, emp_sec52  +(TOTEMP-naics2_subtotal),emp_sec52),  
  emp_sec53   =  if_else(max_naics2==8, emp_sec53  +(TOTEMP-naics2_subtotal),emp_sec53),  
  emp_sec54   =  if_else(max_naics2==9, emp_sec54  +(TOTEMP-naics2_subtotal),emp_sec54),  
  emp_sec55   =  if_else(max_naics2==10,emp_sec55  +(TOTEMP-naics2_subtotal),emp_sec55),  
  emp_sec56   =  if_else(max_naics2==11,emp_sec56  +(TOTEMP-naics2_subtotal),emp_sec56),  
  emp_sec61   =  if_else(max_naics2==12,emp_sec61  +(TOTEMP-naics2_subtotal),emp_sec61),  
  emp_sec62   =  if_else(max_naics2==13,emp_sec62  +(TOTEMP-naics2_subtotal),emp_sec62),  
  emp_sec71   =  if_else(max_naics2==14,emp_sec71  +(TOTEMP-naics2_subtotal),emp_sec71),  
  emp_sec72   =  if_else(max_naics2==15,emp_sec72  +(TOTEMP-naics2_subtotal),emp_sec72),  
  emp_sec81   =  if_else(max_naics2==16,emp_sec81  +(TOTEMP-naics2_subtotal),emp_sec81),  
  emp_sec92   =  if_else(max_naics2==17,emp_sec92  +(TOTEMP-naics2_subtotal),emp_sec92),  
  emp_sec3133 =  if_else(max_naics2==18,emp_sec3133+(TOTEMP-naics2_subtotal),emp_sec3133),
  emp_sec4445 =  if_else(max_naics2==19,emp_sec4445+(TOTEMP-naics2_subtotal),emp_sec4445),
  emp_sec4849 =  if_else(max_naics2==20,emp_sec4849+(TOTEMP-naics2_subtotal),emp_sec4849)) %>% 
  
# Clean up extraneous variables

select(-SD,-Comp_SD,-Incommute_Factor,-max_naics2,-naics2_subtotal) %>% mutate(
  
# Calculate ABAG6 values from NAICS2 industries (equivalency comes from NAICS_to_EMPSIX.xlsx in folder)

AGREMPN = emp_sec11 + emp_sec21, 
FPSEMPN = emp_sec52 + emp_sec53   + emp_sec54 + emp_sec55   + emp_sec56,
HEREMPN = emp_sec61 + emp_sec62   + emp_sec71 + emp_sec72   + emp_sec81,
MWTEMPN = emp_sec22 + emp_sec3133 + emp_sec42 + emp_sec4849,
OTHEMPN = emp_sec23 + emp_sec51   + emp_sec92,
RETEMPN = emp_sec4445)

# Export to csv

write.csv(esri_no_incommute, "ESRI 2015 NAICS2 and ABAG6 noin.csv", row.names = FALSE, quote = T)


