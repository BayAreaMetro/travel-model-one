# Summarize ESRI with NAICS2 and ABAG6 Equivalency 2015 Not Accounting for Incommute (All Jobs).R
# Sum ESRI 2015 data to TAZ levelfor NAICS2 and use equivalency for ABAG6 categories
# Scale to regional total (4,005,318, from https://mtcdrive.app.box.com/file/654134152628)

# Import Libraries

suppressMessages(library(tidyverse))

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

# Data locations

USERPROFILE             <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
esri_location           <- file.path(USERPROFILE,"Box", "esri", "ESRI_2015_Disaggregate.Rdata")
write_location          <- file.path(dirname(wd), "..", "..", "..", "basemap","imputation_and_siting","employment")

BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
PBA_TAZ_2010         <- file.path(BOX_TM, "Share Data",   "plan-bay-area-2040", "2010_06_003","tazData.csv")
 
reg_total = 4005318          # 2015 regional jobs total from https://mtcdrive.app.box.com/file/654134152628

# Bring in data, deal with missing values

load(esri_location)

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

# Bring in PBA TAZ equivalencies to join counties 

PBA2010 <- read.csv(PBA_TAZ_2010,header=TRUE) 

PBA2010_county <- PBA2010 %>%                                    # Create and join TAZ/county equivalence
    mutate(County_Name=case_when(
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
  select(TAZ1454=ZONE,County_Name) 

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
              "TOTEMP"), scale_reg) %>% mutate(

  
# Calculate ABAG6 values from NAICS2 industries (equivalency comes from NAICS_to_EMPSIX.xlsx in folder)

AGREMPN = emp_sec11 + emp_sec21, 
FPSEMPN = emp_sec52 + emp_sec53   + emp_sec54 + emp_sec55   + emp_sec56,
HEREMPN = emp_sec61 + emp_sec62   + emp_sec71 + emp_sec72   + emp_sec81,
MWTEMPN = emp_sec22 + emp_sec3133 + emp_sec42 + emp_sec4849,
OTHEMPN = emp_sec23 + emp_sec51   + emp_sec92,
RETEMPN = emp_sec4445) %>% 
  
# Join county names with final file
  
left_join(.,PBA2010_county,by="TAZ1454")

# Export to csv

write.csv(esri_scaled, paste0(write_location,"/","ESRI 2015 NAICS2 and ABAG6 total jobs.csv"), row.names = FALSE, quote = T)

