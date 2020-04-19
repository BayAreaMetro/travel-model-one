# Summarize ESRI and NETS with NAICS2 and ABAG6 2015.R
# Sum ESRI and NETS 2015 data to TAZ levelfor NAICS2 and ABAG6 categories
# Scale to regional total (4,005,318, from https://mtcdrive.app.box.com/file/654134152628)
# Apply incommute shares to superdistricts to account for non-uniform incommuting rates around region

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

# Data locations

esri_location  <- paste0(wd,"ESRI_2015_Disaggregate.Rdata")
nets_location  <- paste0(wd,"NETS_2015_Disaggregate.Rdata")
incommute_data <- paste0(wd,"2012-2016 CTPP Places to Superdistrict Equivalency.xlsx")

reg_total = 4005318          # 2015 regional jobs total from https://mtcdrive.app.box.com/file/654134152628

# Bring in data

load(esri_location)
load(nets_location)

temp  <- ESRI_2015_Disaggregate %>% mutate(
  sixcat = as.character(sixcat),                        # Convert from factor
  naics2 = if_else(sixcat=="MISSING",81,naics2),        # For NAICS2, Sector 81: Other Services (except Pub. Admin.)
  sixcat = if_else(sixcat=="MISSING","OTHEMPN",sixcat)) # Recode missing values into other ("OTHEMPN" for ABAG6)
 
esri  <- temp %>% mutate(
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

# Summarize by abag6 and naics2

esri_taz_abag6 <- esri %>% 
  rename (abag6=sixcat) %>% 
  group_by(TAZ1454,abag6) %>% 
  summarize(employment=sum(EMPNUM)) %>% 
  spread(abag6,employment,fill=0)

esri_taz_naics2 <- esri %>% 
  group_by(TAZ1454,naics2) %>% 
  summarize(employment=sum(EMPNUM)) %>% 
  spread(naics2,employment,fill=0) 

# Merge employment 

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
  
quentin6 <- data.frame(TAZ1454=1439, AGREMPN=0, FPSEMPN=0, HEREMPN=0, MWTEMPN=0, OTHEMPN=0, RETEMPN=0)

temp2 <- rbind(as.data.frame(esri_taz_naics2),quentin2) 

temp6 <- rbind(as.data.frame(esri_taz_abag6),quentin6) %>%
  mutate(totemp=agrempn+fpsempn+herempn+mwtempn+othempn+retempn) 

esri_all <- left_join(temp6,temp2,by=TAZ1454)

trial <- data.frame(TAZ1454=1439)
list <- (1439, 2:21=0)
    
nets2 <- nets %>%              #Filter out sole proprietors and summarize to TAZ
  filter(emp>1) %>% 
  group_by(zone_id,naics_mtc) %>% 
  summarize(total=sum(emp)) %>% 
  spread(naics_mtc,total,fill=0) 



# Append zero values for San Quentin TAZ and append to full data, re-sort dataset, write it out

quentin <- data.frame(zone_id=1439, agrempn=0, fpsempn=0, herempn=0, mwtempn=0, othempn=0, retempn=0)

final <- rbind(as.data.frame(nets2),quentin) %>%
  mutate(totemp=agrempn+fpsempn+herempn+mwtempn+othempn+retempn) %>% 
  arrange(zone_id) 

write.csv(final, "2015 NETS without sole proprietors.csv", row.names = FALSE, quote = T)




