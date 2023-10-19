# Summarize ESRI with NAICS2 and ABAG6 Equivalency 2015.R
# Sum ESRI 2015 data to TAZ levelfor NAICS2 and use equivalency for ABAG6 categories
# Scale to regional total from
# https://github.com/BayAreaMetro/regional_forecast/blob/master/to_baus/s24/employment_controls_s24.csv
#
# Output: 
#  0) BusinessData_{BIZDATA_YEAR}_TAZ_industry_unscaled.csv
#        business data summed to TAZ by industry (NAICS2 & ABAG6), not scaled to regional total
#  1) BusinessData_{BIZDATA_YEAR}_TAZ_industry.csv
#        same as 0, but scaled to regional total
#        NOTE: these are not rounded, so values are float
#  2) BusinessData_{BIZDATA_YEAR}_TAZ_industry_noincommute.csv 
#       same as 1, but with incommute jobs removed, using incommute shares to superdistricts to account
#       for non-uniform incommuting rates around region
# See M:\Data\BusinessData\Employment_by_TAZ_industry for output 

suppressMessages(library(tidyverse))
library(readxl)

# Data locations
BIZDATA_DIR             <- "M:/Data/BusinessData"
BIZDATA_YEAR            <- Sys.getenv("BIZDATA_YEAR")
stopifnot(BIZDATA_YEAR %in% c("2015", "2017", "2019", "2020") )
bizdata_location        <- file.path(BIZDATA_DIR, paste0("Businesses_",BIZDATA_YEAR,"_BayArea_wcountyTAZ.csv"))      

# regional totals
SCENARIO_NUM            <- 24 # final blueprint
reg_total_location      <- paste0("X:/regional_forecast/to_baus/s",SCENARIO_NUM,"/employment_controls_s",SCENARIO_NUM,".csv")
taz_county_location     <- "X:/travel-model-one-master/utilities/geographies/taz-superdistrict-county.csv"

# incommute processsing
SCRIPT_PATH             <- "X:/petrale/applications/travel_model_lu_inputs/2015/Employment"
incommute_eq_location   <- file.path(SCRIPT_PATH, "Incommute","2012-2016 CTPP Places to Superdistrict Equivalency.xlsx")
incommute_tot_location  <- file.path(SCRIPT_PATH, "Incommute","ACS 2013-2017 Incommute by Industry.xlsx")

# output files
output_taz_industry_file  <- paste0("BusinessData_",BIZDATA_YEAR,"_TAZ_industry.csv")

# Read business data, create naics2 string
bizdata <- read_csv(bizdata_location) %>%
  mutate(naics_str = as.character(NAICS),
         naics2    = substr(naics_str, 0, 2),
         naics2    = recode(naics2,  # combine a few
                            "31"="3133","32"="3133","33"="3133",
                            "44"="4445","45"="4445",
                            "48"="4849","49"="4849"),
         naics2    = paste0("emp_sec",naics2))
print("Business data NAICS2:")
print(table(bizdata$naics2))

# Summarize by naics2, spread to matrix format
bizdata_taz_naics2 <- bizdata %>% 
  group_by(TAZ1454,naics2) %>% 
  summarize(employment=sum(EMPNUM)) %>% 
  spread(naics2,employment,fill=0)

# # emp_sec_cols = emp_sec11, emp_sec21, ...
emp_sec_cols     <- colnames(bizdata_taz_naics2)
emp_sec_cols     <- emp_sec_cols[ emp_sec_cols != "TAZ1454" ]

# and get total
bizdata_taz <- bizdata %>% 
  group_by(TAZ1454) %>% 
  summarize(TOTEMP=sum(EMPNUM))

# put them together
bizdata_taz_naics2 <- merge(bizdata_taz_naics2, bizdata_taz, all=TRUE)

# Ensure all TAZs covered by joining to full TAZ list
taz_county <- read_csv(taz_county_location) %>% 
  rename(TAZ1454=ZONE, County_Name=COUNTY_NAME) %>% 
  subset(COUNTY<10) # create list of bay area TAZs to ensure coverage
bizdata_taz_naics2 <- merge(bizdata_taz_naics2, select(taz_county, TAZ1454, County_Name), all=TRUE)
bizdata_taz_naics2[is.na(bizdata_taz_naics2)] <- 0

# Drop TAZ 0 (or bizdata with no TAZ)
print(paste("Dropping employment with no TAZ: ",subset(bizdata_taz_naics2, TAZ1454==0)))
bizdata_taz_naics2 <- subset(bizdata_taz_naics2, TAZ1454 > 0)

# Calculate ABAG6 values from NAICS2 industries (equivalency comes from NAICS_to_EMPSIX.xlsx in folder)
abag6_from_naics2 <- function(df) {
  df %>% 
    mutate(AGREMPN = emp_sec11 + emp_sec21, 
           FPSEMPN = emp_sec52 + emp_sec53   + emp_sec54 + emp_sec55   + emp_sec56,
           HEREMPN = emp_sec61 + emp_sec62   + emp_sec71 + emp_sec72   + emp_sec81,
           MWTEMPN = emp_sec22 + emp_sec3133 + emp_sec42 + emp_sec4849,
           OTHEMPN = emp_sec23 + emp_sec51   + emp_sec92 + emp_sec99,
           RETEMPN = emp_sec4445)
}
bizdata_taz_naics2 <- abag6_from_naics2(bizdata_taz_naics2)
# write this result
unscaled_output <- sub(".csv", "_unscaled.csv", output_taz_industry_file)
write.csv(bizdata_taz_naics2, unscaled_output, row.names = FALSE, quote = T)
print(paste("Wrote",unscaled_output))

# Now create scale function to apply to all ESRI employment categories

regional_totals   <- read_csv(reg_total_location) %>%
  mutate(TOTEMP=AGREMPN + MWTEMPN + RETEMPN + FPSEMPN + HEREMPN + OTHEMPN)

CONTROL_YEAR <- 2015
if (BIZDATA_YEAR > 2017) CONTROL_YEAR <- 2020

# get TOTEMP control for the CONTROL_YEAR
TOTEMP_CONTROL <- subset(regional_totals, year==CONTROL_YEAR)$TOTEMP

# Scale regional total from REMI over ESRI employment
EMP_SCALE <- TOTEMP_CONTROL/sum(bizdata_taz_naics2$TOTEMP)
print(paste("Scaling TOTAL EMPLOYMENT by", EMP_SCALE, "to hit regional control of",TOTEMP_CONTROL,"for year",CONTROL_YEAR))

# scale all the columns to that TOTEMP sums to TOTEMP_CONTROL
bizdata_taz_scaled <- bizdata_taz_naics2
for (col in c(emp_sec_cols, "TOTEMP")) {
  bizdata_taz_scaled[col] <- EMP_SCALE*bizdata_taz_naics2[col]
}

bizdata_taz_scaled <- abag6_from_naics2(bizdata_taz_scaled)

# join to county names
bizdata_taz_scaled <- left_join(bizdata_taz_scaled, select(taz_county, TAZ1454, County_Name))

# write this result
write.csv(bizdata_taz_scaled, output_taz_industry_file, row.names = FALSE, quote = T)
print(paste("Wrote",output_taz_industry_file))

# Distribute incommute and reduce regional employment totals by incommute total
# CTPP data were used to distribute the incommute - place-to-place data were smallest home-to-work geo available
# Tract-to-tract data have missing geocoded data and are unreliable
# Workers at work at the place level minus regional workers at work equals incommuters, roughly
# Places were matched to superdistricts or "composite superdistricts" - groups of superdistricts
# Incommuters were distributed across superdistricts or composite superdistricts according to calculated shares

incommute_eq      <- read_excel (incommute_eq_location,sheet="TAZ Incommute Equivalence") 
incommute_share   <- read_excel (incommute_eq_location,sheet="Comp_SD Incommute Equivalence")
incommute_total   <- read_excel (incommute_tot_location,sheet="5. Net_Incommute") %>% 
  select(Net_Incommute) # Keep just the net incommute value

# add SD, Comp_SD columns (Comp_SD looks like 1_2_3_4)
bizdata_taz_scale_eq <- left_join(bizdata_taz_scaled,incommute_eq, by=c("TAZ1454" = "ZONE")) # Join equivalency

# Calculate number of incommuters by composite superdistrict 
# cols: Comp_SD, Share_Incommute, Net_Incommute, Incommute_Portion
temp_incommute <- cbind(incommute_share,incommute_total) %>%    
  mutate(Incommute_Portion=Share_Incommute*Net_Incommute)       

# Sum total employment by composite superdistrict
# cols: Comp_SD, Comp_SD_Total
temp_bizdata_sum <- bizdata_taz_scale_eq %>% 
  group_by(Comp_SD) %>%                 # Calculate scaling factors for each TAZ within a SD or composite SD
  summarize(Comp_SD_Total=sum(TOTEMP))  # Within respective SDs or composite SDs, TAZ factors are uniform                        

# Calculate Incommute_Factor for each composite superdistrict, where factor = proportion of employees *not incommuters*
# cols: Comp_SD, Incommute_Factor
incommute_factors <- left_join(temp_incommute,temp_bizdata_sum,by="Comp_SD") %>% mutate(
 Incommute_Factor =1-(Incommute_Portion/Comp_SD_Total)) %>%     # Join factors to TAZs
  select(Comp_SD,Incommute_Factor)

# Apply factors to emp_sec* and TOTEMP and round resultant values
bizdata_taz_incommute <- left_join(bizdata_taz_scale_eq,incommute_factors,by="Comp_SD")
for (col in c(emp_sec_cols, "TOTEMP")) {
  bizdata_taz_incommute[col] <- round(bizdata_taz_incommute[col]*bizdata_taz_incommute$Incommute_Factor)
}

# Find max column for later adjustment to ensure that marginal employment matches subtotals
bizdata_taz_incommute <- mutate(bizdata_taz_incommute,
  max_naics2      = emp_sec_cols[max.col(select(bizdata_taz_incommute,emp_sec_cols), ties.method="first")],
  naics2_subtotal = rowSums(select(bizdata_taz_incommute, emp_sec_cols)),
  naics2_diff     = TOTEMP - naics2_subtotal)   

# If naics2_subtotal is off, make up the difference in the largest category
for (col in emp_sec_cols) {
  bizdata_taz_incommute[col] <- if_else(bizdata_taz_incommute$max_naics2==col, 
                                        bizdata_taz_incommute[[col]] + bizdata_taz_incommute[["naics2_diff"]],
                                        bizdata_taz_incommute[[col]])
}

# verify
bizdata_taz_incommute <- mutate(bizdata_taz_incommute,
                                naics2_subtotal = rowSums(select(bizdata_taz_incommute, emp_sec_cols)),
                                naics2_diff     = TOTEMP - naics2_subtotal)
stopifnot(all(bizdata_taz_incommute$naics2_diff == 0))
  
# Clean up extraneous variables

bizdata_taz_incommute <- select(bizdata_taz_incommute,
                                -SD,-Comp_SD,-Incommute_Factor,-max_naics2,-naics2_subtotal, -naics2_diff)
  
# Calculate ABAG6 values from NAICS2 industries (equivalency comes from NAICS_to_EMPSIX.xlsx in folder)

bizdata_taz_incommute <- abag6_from_naics2(bizdata_taz_incommute)

# Export to csv

noincommute_output <- sub(".csv", "_noincommute.csv", output_taz_industry_file)
write.csv(bizdata_taz_incommute, noincommute_output, row.names = FALSE, quote = T)
print(paste("Wrote",noincommute_output))


