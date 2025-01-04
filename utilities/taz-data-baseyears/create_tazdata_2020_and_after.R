USAGE = "
  Create 202X TAZ data from ACS 5-year data.
"
# Notes
# 1. Group quarter data is not available below state level from ACS, so 2020 Decennial census numbers
#    are used instead, and then scaled (if applicable)
#
# 2. ACS data here is downloaded for relevant 5-year dataset. 
# 
# 3. ACS block group variables used in all instances where not suppressed. If suppressed at the block group 
#    level, tract-level data used instead. Suppressed variables may change if ACS_5year is changed. This 
#    should be checked, as this change could cause the script not to work.
#

options(width=500)
options(max.print=2000)
options(show.error.locations = TRUE)

# Import Libraries
suppressMessages(library(tidyverse))
library(tidycensus)
library(readxl)
library(argparser)

argparser <- arg_parser(USAGE, hide.opts=TRUE)
argparser <- add_argument(parser=argparser, arg="year", type="integer", help="Year for TAZ data")
# parse the command line arguments
argv <- parse_args(argparser)
stopifnot(argv$year %in% c(2020, 2021, 2023))
set.seed(argv$year)

# write to log
run_log <- file.path(argv$year, paste0("create_tazdata_",argv$year,".log"))
print(paste("Writing log to",run_log))
sink(run_log, append=FALSE, type = c('output', 'message'))

# Bring in common methods
source("./common.R")

# These are the most recent ACS datasets available
ACS_PUMS_5YEAR_LATEST <- 2022
ACS_PUMS_1YEAR_LATEST <- 2023
ACS_5YEAR_LATEST      <- ACS_PUMS_5YEAR_LATEST # don't use inconsistent versions

# figure out our primary datasource - which ACS5-year
ACS_5year <- argv$year + 2  # ACS 5 year would then go from argv$year - 2 to argv$year + 2
ACS_5year <- min(ACS_5year, ACS_5YEAR_LATEST)
print(paste("ACS_5year:", ACS_5year))

# Used for avg workers per 3+ person households
ACS_PUMS_1year <- min(ACS_PUMS_1YEAR_LATEST, argv$year)
ACS_PUMS_5year <- min(ACS_PUMS_5YEAR_LATEST, argv$year + 2)

# lodes year
LODES_YEAR_LATEST <- 2022
LODES_YEAR = min(argv$year, LODES_YEAR_LATEST)

# Employment numbers for workers who live AND work in the Bay Area vary significantly between
# ACS (high) and LEHD LODES (low).  This parameter is for doing a blended approach.
# Set to 0.0 to use only ACS, set to 1.0 to use only LODES; set to 0.5 to use something in between
#
# Note that currently LEHD WAC is used for employment (TOTEMP and [AGR,FPS,HER,MWT,RET,OTH]EMPN)
EMPRES_LODES_WEIGHT = 0.5

# setup paths
USERPROFILE        <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM             <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
if (Sys.getenv("USERNAME") %in% c("lzorn")) {
  BOX_TM           <- file.path("E://Box/Modeling and Surveys")
}
PBA_TAZ_2015       <- file.path(BOX_TM, "Share Data", "plan-bay-area-2050", "tazdata","PBA50_FinalBlueprintLandUse_TAZdata.xlsx")
TM1                <- file.path(".")
emp_wage_salary    <- read.csv(file.path(TM1,LODES_YEAR,paste0("lodes_wac_employment_",LODES_YEAR,".csv")),header = T)
emp_self_employed  <- read.csv(file.path(TM1,argv$year,paste0("taz_self_employed_workers_",argv$year,".csv")),header = T)
lehd_lodes         <- read.csv(file.path("M://Data/Census/LEHD/Origin-Destination Employment Statistics (LODES)",
                      sprintf("LODES_Bay_Area_county_%d.csv", LODES_YEAR)), header=T) %>% tibble()
TAZ_SD_COUNTY      <- read.csv(file.path("..","geographies","taz-superdistrict-county.csv"), header=T) %>% 
  rename(County_Name=COUNTY_NAME, DISTRICT=SD, DISTRICT_NAME=SD_NAME) %>% select(-SD_NUM_NAME, -COUNTY_NUM_NAME)
# TAZ_SD_COUNTY columns: ZONE,DISTRICT,COUNTY,DISTRICT_NAME,County_Name

# Restructure employment frame to wide format
emp_self_employed_w <- emp_self_employed %>%
  select(-c(X)) %>%
  pivot_wider(names_from = industry, values_from = value, values_fill = 0) %>%
  mutate(TOTEMP = rowSums(select(., -zone_id))) %>%
  arrange(zone_id) %>% 
  rename( c("TAZ1454" = "zone_id")) %>%
  rename_all(toupper)
print("emp_self_employed_w:")
print(emp_self_employed_w)

lehd_lodes <- lehd_lodes %>% select(-w_state, -h_state) %>%
  rename(TOTEMP = Total_Workers) %>%
  group_by(w_county,h_county) %>% 
  summarise(TOTEMP = sum(TOTEMP), .groups='drop')

# get self employment ready to add to this by summarizing to county and setting h_county = w_county
emp_self_employed_county <- left_join(
    emp_self_employed_w,
    select(TAZ_SD_COUNTY, ZONE, County_Name),
    by=c("TAZ1454"="ZONE")) %>% 
  group_by(County_Name) %>%
  summarise(TOTEMP_self=sum(TOTEMP), .groups='drop') %>%
  rename(h_county = County_Name) %>%
  mutate(w_county = h_county)
# print(emp_self_employed_county)
print(sprintf("emp_self_employed_county total: %s", format(
  emp_self_employed_county %>% summarise(TOTEMP_self=sum(TOTEMP_self)) %>% pull(TOTEMP_self),
  big.mark = ",", scientific = FALSE)))

# add estimated USPS jobs, consistent with lodes_wac_to_TAZ.py
USPS_PER_THOUSAND_JOBS = 1.83
lehd_lodes <- lehd_lodes %>% mutate(
  TOTEMP = as.integer(round(TOTEMP*(1.0 + USPS_PER_THOUSAND_JOBS/1000.0)))
)
# add self-employment to lehd lodes
lehd_lodes <- left_join(
    lehd_lodes, emp_self_employed_county, by=c("h_county","w_county")) %>%
    mutate(TOTEMP_self = replace_na(TOTEMP_self, 0))
lehd_lodes <- lehd_lodes %>%
    mutate(TOTEMP = TOTEMP + TOTEMP_self) %>%
    select(-TOTEMP_self)

# columns are w_county, h_county, TOTEMP
print(sprintf("LEHD LODES from %d (after adding self-employment):", LODES_YEAR))
print(lehd_lodes)



# Combine the two employment frames - wage/salary, and self-employment
employment <- bind_rows(emp_wage_salary, emp_self_employed_w, .id='src') %>% tibble()

# Group by TAZ1454 and calculate the sum for total employment by taz (wage/salary plus self-employment)
employment <- employment %>%
  group_by(TAZ1454) %>%
  summarize_if(is.numeric, sum, na.rm = F)
# columns are: TAZ1454, AGREMPN, FPSEMPN, HEREMPN, MWTEMPN, RETEMPN, OTHEMPN, TOTEMP
print("employment:")
print(employment)
print(sprintf("TOTEMP: %s", format(
  employment %>% summarise(TOTEMP=sum(TOTEMP)) %>% pull(TOTEMP),
  big.mark = ",", scientific = FALSE)))

# Import decennial census (DHC file) and ACS for variable inspection, use to get variable numbers
DHC_table <- load_variables(year=2020, dataset="dhc", cache=TRUE)
ACS_table <- load_variables(year=ACS_5year, dataset="acs5", cache=TRUE)

# ACS Block Group Variables

ACS_BG_variables <- c(
# total households
  tothh_        ="B19001_001",    # Total households
  hhpop_        ="B28005_001",    # Universe: Population in households

# Sex by Age; Universe = Total Population
  male0_4_      ="B01001_003",    # male aged 0 to 4 
  male5_9_      ="B01001_004",    # male aged 5 to 9 
  male10_14_    ="B01001_005",    # male aged 10 to 14
  male15_17_    ="B01001_006",    # male aged 15 to 17
  male18_19_    ="B01001_007",    # male aged 18 to 19
  male20_       ="B01001_008",    # male aged 20 
  male21_       ="B01001_009",    # male aged 21 
  male22_24_    ="B01001_010",    # male aged 22 to 24 
  male25_29_    ="B01001_011",    # male aged 25 to 29 
  male30_34_    ="B01001_012",    # male aged 30 to 34 
  male35_39_    ="B01001_013",    # male aged 35 to 39 
  male40_44_    ="B01001_014",    # male aged 40 to 44 
  male45_49_    ="B01001_015",    # male aged 45 to 49 
  male50_54_    ="B01001_016",    # male aged 50 to 54 
  male55_59_    ="B01001_017",    # male aged 55 to 59 
  male60_61_    ="B01001_018",    # male aged 60 to 61 
  male62_64_    ="B01001_019",    # male aged 62 to 64 
  male65_66_    ="B01001_020",    # male aged 65 to 66 
  male67_69_    ="B01001_021",    # male aged 67 to 69 
  male70_74_    ="B01001_022",    # male aged 70 to 74 
  male75_79_    ="B01001_023",    # male aged 75 to 79 
  male80_84_    ="B01001_024",    # male aged 80 to 84 
  male85p_      ="B01001_025",    # male aged 85+ 
  # female
  female0_4_    ="B01001_027",    # female aged 0 to 4 
  female5_9_    ="B01001_028",    # female aged 5 to 9 
  female10_14_  ="B01001_029",    # female aged 10 to 14
  female15_17_  ="B01001_030",    # female aged 15 to 17
  female18_19_  ="B01001_031",    # female aged 18 to 19
  female20_     ="B01001_032",    # female aged 20 
  female21_     ="B01001_033",    # female aged 21 
  female22_24_  ="B01001_034",    # female aged 22 to 24 
  female25_29_  ="B01001_035",    # female aged 25 to 29 
  female30_34_  ="B01001_036",    # female aged 30 to 34 
  female35_39_  ="B01001_037",    # female aged 35 to 39 
  female40_44_  ="B01001_038",    # female aged 40 to 44 
  female45_49_  ="B01001_039",    # female aged 45 to 49 
  female50_54_  ="B01001_040",    # female aged 50 to 54 
  female55_59_  ="B01001_041",    # female aged 55 to 59 
  female60_61_  ="B01001_042",    # female aged 60 to 61 
  female62_64_  ="B01001_043",    # female aged 62 to 64 
  female65_66_  ="B01001_044",    # female aged 65 to 66 
  female67_69_  ="B01001_045",    # female aged 67 to 69 
  female70_74_  ="B01001_046",    # female aged 70 to 74 
  female75_79_  ="B01001_047",    # female aged 75 to 79 
  female80_84_  ="B01001_048",    # female aged 80 to 84 
  female85p_    ="B01001_049",    # female aged 85+ 

# Household size by tenure; B25009: Tenure by Household Size. Universe = Occupied Housing Units
  own1_         ="B25009_003",    # own 1 person in HH 	     
  own2_         ="B25009_004",    # own 2 persons in HH 
  own3_         ="B25009_005",    # own 3 persons in HH 
  own4_         ="B25009_006",    # own 4 persons in HH 
  own5_         ="B25009_007",    # own 5 persons in HH 
  own6_         ="B25009_008",    # own 6 persons in HH 
  own7p_        ="B25009_009",    # own 7+ persons in HH 
  rent1_        ="B25009_011",    # rent 1 person in HH
  rent2_        ="B25009_012",    # rent 2 persons in HH 
  rent3_        ="B25009_013",    # rent 3 persons in HH 
  rent4_        ="B25009_014",    # rent 4 persons in HH 
  rent5_        ="B25009_015",    # rent 5 persons in HH 
  rent6_        ="B25009_016",    # rent 6 persons in HH 
  rent7p_       ="B25009_017",    # rent 7+ persons in HH

# Race/Ethnicity variables; B03002: Hispanic or Latino Origin by Race. Universe=Total Population
  white_nonh_   ="B03002_003",   # White alone, not Hispanic
  black_nonh_   ="B03002_004",   # Black alone, not Hispanic
  asian_nonh_   ="B03002_006",   # Asian alone, not Hispanic
  total_nonh_   ="B03002_002",   # Total, not Hispanic
  total_hisp_   ="B03002_012",   # Total Hispanic

# Units
  unit1d_           ="B25024_002",    # 1 unit detached    
  unit1a_           ="B25024_003",		# 1 unit attached 
  unit2_            ="B25024_004",		# 2 units
  unit3_4_          ="B25024_005",		# 3 or 4 units
  unit5_9_          ="B25024_006",		# 5 to 9 units
  unit10_19_        ="B25024_007",		# 10 to 19 units
  unit20_49_        ="B25024_008",		# 20 to 49 units
  unit50p_          ="B25024_009",		# 50+ units
  mobile_           ="B25024_010",		# mobile homes
  boat_RV_Van_      ="B25024_011",		# boats, RVs, vans
  
# Employment - Universe = Population 16 years and Over.  Not included: there's also Civilian unemployed
  employed_         ="B23025_004",    # Civilian employed residents (employed residents is "employed" + "armed forces")
  armedforces_      ="B23025_006", 	  # Armed forces

# Household income. Universe = Households
  hhinc000_010_     ="B19001_002",    # Household income 0 to $10k 
  hhinc010_015_     ="B19001_003",		# Household income $10 to $15k
  hhinc015_020_     ="B19001_004",		# Household income $15 to $20k
  hhinc020_025_     ="B19001_005",		# Household income $20 to $25k
  hhinc025_030_     ="B19001_006",		# Household income $25 to $30k
  hhinc030_035_     ="B19001_007",		# Household income $30 to $35k
  hhinc035_040_     ="B19001_008",		# Household income $35 to $40k
  hhinc040_045_     ="B19001_009",		# Household income $40 to $45k
  hhinc045_050_     ="B19001_010",		# Household income $45 to $50k
  hhinc050_060_     ="B19001_011",		# Household income 50 to $60k
  hhinc060_075_     ="B19001_012",		# Household income 60 to $75k
  hhinc075_100_     ="B19001_013",		# Household income 75 to $100k
  hhinc100_125_     ="B19001_014",		# Household income $100 to $1$25k
  hhinc125_150_     ="B19001_015",		# Household income $1$25 to $150k
  hhinc150_200_     ="B19001_016",		# Household income $150 to $200k
  hhinc200p_        ="B19001_017",		# Household income $200k+
  
# C24010 Sex by Occupation for the Civilian Employed Population 16 Years and Over
# Occupation, male
  occ_m_manage_     ="C24010_005", # Management
  occ_m_prof_biz_   ="C24010_006", # Business and financial
  occ_m_prof_comp_  ="C24010_007", # Computer, engineering, and science
  occ_m_svc_comm_   ="C24010_012", # community and social service
  occ_m_prof_leg_   ="C24010_013", # Legal
  occ_m_prof_edu_   ="C24010_014", # Education, training, and library
  occ_m_svc_ent_    ="C24010_015", # Arts, design, entertainment, sports, and media
  occ_m_prof_heal_  ="C24010_016", # Healthcare practitioners and technical
  occ_m_svc_heal_   ="C24010_020", # Healthcare support
  occ_m_svc_fire_   ="C24010_022", # Fire fighting and prevention, and other protectiv
  occ_m_svc_law_    ="C24010_023", # Law enforcement workers
  occ_m_ret_eat_    ="C24010_024", # Food preparation and serving related
  occ_m_man_build_  ="C24010_025", # Building and grounds cleaning and maintenance
  occ_m_svc_pers_   ="C24010_026", # Personal care and service
  occ_m_ret_sales_  ="C24010_028", # Sales and related
  occ_m_svc_off_    ="C24010_029", # Office and administrative support
  occ_m_man_nat_    ="C24010_030", # Natural resources, construction, and maintenance
  occ_m_man_prod_   ="C24010_034", # Production, transportation, and material moving
  
# Occupation, female
  occ_f_manage_     ="C24010_041", # Management
  occ_f_prof_biz_   ="C24010_042", # Business and financial
  occ_f_prof_comp_  ="C24010_043", # Computer, engineering, and science
  occ_f_svc_comm_   ="C24010_048", # community and social service
  occ_f_prof_leg_   ="C24010_049", # Legal
  occ_f_prof_edu_   ="C24010_050", # Education, training, and library
  occ_f_svc_ent_    ="C24010_051", # Arts, design, entertainment, sports, and media
  occ_f_prof_heal_  ="C24010_052", # Healthcare practitioners and technical
  occ_f_svc_heal_   ="C24010_056", # Healthcare support
  occ_f_svc_fire_   ="C24010_058", # Fire fighting and prevention, and other protectiv
  occ_f_svc_law_    ="C24010_059", # Law enforcement workers
  occ_f_ret_eat_    ="C24010_060", # Food preparation and serving related
  occ_f_man_build_  ="C24010_061", # Building and grounds cleaning and maintenance
  occ_f_svc_pers_   ="C24010_062", # Personal care and service
  occ_f_ret_sales_  ="C24010_064", # Sales and related
  occ_f_svc_off_    ="C24010_065", # Office and administrative support
  occ_f_man_nat_    ="C24010_066", # Natural resources, construction, and maintenance
  occ_f_man_prod_   ="C24010_070"  # Production, transportation, and material moving
)
  
ACS_tract_variables <-  c(
# Households by number of workers.  Universe = Households
  hhwrks0_          = "B08202_002", # 0-worker HH
  hhwrks1_          = "B08202_003",	# 1-worker HH
  hhwrks2_          = "B08202_004",	# 2-worker HH
  hhwrks3p_         = "B08202_005", # 3+-worker HH

# Households by number of kids; B25012: Tenure by Families and Presence of Own Children. Universe = Occupied Housing Units
  ownkidsyes_       = "B25012_003", # Own with related kids under 18
  rentkidsyes_      = "B25012_011", # Rent with related kids under 18
  ownkidsno_        = "B25012_009", # Own without related kids under 18
  rentkidsno_       = "B25012_017"  # Rent without related kids under 18
)

# Get group quarters from Decennial census because ACS only includes these at the state level
DHC_tract_variables <-  c(
# Group quarters for tracts by age and type of resident
  gq_noninst_m_0017_univ      = "PCT19_024N", # Male non-inst. under 18 university
  gq_noninst_m_0017_mil       = "PCT19_025N", # Male non-inst. under 18 military
  gq_noninst_m_0017_oth       = "PCT19_028N", # Male non-inst. under 18 other
  gq_noninst_m_1864_univ      = "PCT19_056N", # Male non-inst. 18-64 university
  gq_noninst_m_1864_mil       = "PCT19_057N", # Male non-inst. 18-64 military
  gq_noninst_m_1864_oth       = "PCT19_060N", # Male non-inst. 18-64 other
  gq_noninst_m_65p_univ       = "PCT19_088N", # Male non-inst. 65+ university
  gq_noninst_m_65p_mil        = "PCT19_089N", # Male non-inst. 65+ military
  gq_noninst_m_65p_oth        = "PCT19_092N", # Male non-inst. 65+ other
  gq_noninst_f_0017_univ      = "PCT19_121N", # Female non-inst. under 18 university
  gq_noninst_f_0017_mil       = "PCT19_122N", # Female non-inst. under 18 military
  gq_noninst_f_0017_oth       = "PCT19_125N", # Female non-inst. under 18 other
  gq_noninst_f_1864_univ      = "PCT19_153N", # Female non-inst. 18-64 university
  gq_noninst_f_1864_mil       = "PCT19_154N", # Female non-inst. 18-64 military
  gq_noninst_f_1864_oth       = "PCT19_157N", # Female non-inst. 18-64 other
  gq_noninst_f_65p_univ       = "PCT19_185N", # Female non-inst. 65+ university
  gq_noninst_f_65p_mil        = "PCT19_186N", # Female non-inst. 65+ military
  gq_noninst_f_65p_oth        = "PCT19_189N"  # Female non-inst. 65+ other
)

# Summarize block population by block group and tract 

blockTAZBG <- BLOCK2020_TAZ1454 %>% 
  group_by(blockgroup) %>%
  summarize(BGTotal=sum(block_POPULATION))
print(paste("blockTAZBG has",nrow(blockTAZBG),"rows:"))
print(head(blockTAZBG))

blockTAZTract <- BLOCK2020_TAZ1454 %>% 
  group_by(tract) %>%
  summarize(TractTotal=sum(block_POPULATION))
print(paste("blockTAZTract has",nrow(blockTAZTract),"rows:"))
print(head(blockTAZTract))

# Create 2020 block share of total population for block/block group and block/tract, append to combined_block file
# Be mindful of divide by zero error associated with 0-pop block groups and tracts
# sharebg    = 2020 decennial census block share of block group
# sharetract = 2020 decennial census block share of tract

combined_block <- left_join(BLOCK2020_TAZ1454,blockTAZBG,by="blockgroup") %>% mutate(
  sharebg=if_else(block_POPULATION==0,0,block_POPULATION/BGTotal))

combined_block <- left_join(combined_block,blockTAZTract,by="tract") %>% mutate(
  sharetract=if_else(block_POPULATION==0,0,block_POPULATION/TractTotal))

print(paste("combined_block has",nrow(combined_block),"rows"))
print("head(combined_block):")
print(head(combined_block, n=20))

# Download ACS data (and DHC data for group quarters)
USE_TIDYCENSUS_CACHING = TRUE

ACS_tract_raw <- tidycensus::get_acs(
  geography = "tract", variables = ACS_tract_variables,
  state = state_code, county=baycounties,
  year=ACS_5year,
  output="wide",
  survey = "acs5",
  cache_table = USE_TIDYCENSUS_CACHING,
  key = censuskey)

ACS_BG_raw <- tidycensus::get_acs(
  geography = "block group", variables = ACS_BG_variables,
  state = state_code, county=baycounties,
  year=ACS_5year,
  output="wide",
  survey = "acs5",
  cache_table = USE_TIDYCENSUS_CACHING,
  key = censuskey)

DHC_tract_raw <- tidycensus::get_decennial(
  geography = "tract", variables = DHC_tract_variables,
  state = state_code, county=baycounties,
  year=2020,
  output="wide",
  sumfile = "dhc",
  cache_table = USE_TIDYCENSUS_CACHING,
  key = censuskey)

# Remove NAME variable from decennial files for later joining

DHC_tract_raw <- DHC_tract_raw %>% select(-NAME)

print(paste0("DHC_tract_raw (",nrow(DHC_tract_raw)," rows):"))
print(DHC_tract_raw)

# Remove MOEs from ACS variables,rename to drop "_E" suffix
# Drop NAME variable for later joining

ACS_tract_raw <- ACS_tract_raw %>% select(!(ends_with("_M"))) %>% select(-NAME)
ACS_BG_raw <- ACS_BG_raw %>% select(!(ends_with("_M"))) %>% select(-NAME)
names(ACS_tract_raw) <- str_replace_all(names(ACS_tract_raw), c("_E" = ""))
names(ACS_BG_raw) <- str_replace_all(names(ACS_BG_raw), c("_E" = ""))

print(paste0("ACS_tract_raw (",nrow(ACS_tract_raw)," rows):"))
print(ACS_tract_raw)

print(paste0("ACS_BG_raw (",nrow(ACS_BG_raw)," rows):"))
print(ACS_BG_raw)                                                                           

# Join specfied 5-year ACS and DHC block group and tract variables to combined_block file
# Combine and collapse ACS categories to get land use control totals, as appropriate
# Apply block share of ACS variables using block/block group and block/tract shares of 2020 total population

interim <- left_join(combined_block,ACS_BG_raw, by=c("blockgroup"="GEOID")) %>% 
  left_join(.,ACS_tract_raw, by=c("tract"="GEOID"))%>% 
  left_join(.,DHC_tract_raw, by=c("tract"="GEOID"))

print(paste0("interim (",nrow(interim)," rows):"))
print(interim)

workingdata <- interim %>% mutate(
  TOTHH=tothh*sharebg,
  HHPOP=hhpop*sharebg,
  EMPRES=(employed+armedforces)*sharebg,
  # household income moved to next step
  AGE0004=(male0_4+female0_4)*sharebg,
  AGE0519=(  male5_9+  male10_14+  male15_17+  male18_19+
           female5_9+female10_14+female15_17+female18_19)*sharebg,
  AGE2044=(  male20+  male21+  male22_24+  male25_29+  male30_34+  male35_39+  male40_44+
           female20+female21+female22_24+female25_29+female30_34+female35_39+female40_44)*sharebg,
  AGE4564=(  male45_49+  male50_54+  male55_59+  male60_61+  male62_64+
           female45_49+female50_54+female55_59+female60_61+female62_64)*sharebg,
  AGE65P=(  male65_66+  male67_69+  male70_74+  male75_79+  male80_84+  male85p+
          female65_66+female67_69+female70_74+female75_79+female80_84+female85p)*sharebg,
  AGE62P=(  male62_64+  male65_66+  male67_69+  male70_74+  male75_79+  male80_84+  male85p+
          female62_64+female65_66+female67_69+female70_74+female75_79+female80_84+female85p)*sharebg,
  # race/ethnicity
  white_nonh=white_nonh*sharebg,
  black_nonh=black_nonh*sharebg,
  asian_nonh=asian_nonh*sharebg,
  other_nonh=(total_nonh-(white_nonh+black_nonh+asian_nonh))*sharebg,   # "Other, non-Hisp is total non-Hisp minus white,black,Asian
  hispanic=total_hisp*sharebg,
  # single family versus mult-family
  SFDU=(unit1d+unit1a+mobile+boat_RV_Van)*sharebg,
  MFDU=(unit2+unit3_4+unit5_9+unit10_19+unit20_49+unit50p)*sharebg,
  # tenure
  hh_own=(own1+own2+own3+own4+own5+own6+own7p)*sharebg,
  hh_rent=(rent1+rent2+rent3+rent4+rent5+rent6+rent7p)*sharebg,
  # households by size
  hh_size_1=(own1+rent1)*sharebg,
  hh_size_2=(own2+rent2)*sharebg,
  hh_size_3=(own3+rent3)*sharebg,
  hh_size_4_plus=(own4+own5+own6+own7p+rent4+rent5+rent6+rent7p)*sharebg,
  # households by number of workers
  hh_wrks_0=hhwrks0*sharetract,
  hh_wrks_1=hhwrks1*sharetract,
  hh_wrks_2=hhwrks2*sharetract,
  hh_wrks_3_plus=hhwrks3p*sharetract,
  # households with children or not
  hh_kids_yes=(ownkidsyes+rentkidsyes)*sharetract,
  hh_kids_no=(ownkidsno+rentkidsno)*sharetract,
  # persons by occupation
  pers_occ_management   = (
    occ_m_manage    + occ_f_manage   )*sharebg,
  pers_occ_professional = (
    occ_m_prof_biz  + occ_f_prof_biz  +
    occ_m_prof_comp + occ_f_prof_comp +
    occ_m_prof_leg  + occ_f_prof_leg  +
    occ_m_prof_edu  + occ_f_prof_edu  +
    occ_m_prof_heal + occ_f_prof_heal)*sharebg,
  pers_occ_services     = (
    occ_m_svc_comm  + occ_f_svc_comm  +
    occ_m_svc_ent   + occ_f_svc_ent   +
    occ_m_svc_heal  + occ_f_svc_heal  +
    occ_m_svc_fire  + occ_f_svc_fire  +
    occ_m_svc_law   + occ_f_svc_law   +
    occ_m_svc_pers  + occ_f_svc_pers  +
    occ_m_svc_off   + occ_f_svc_off  )*sharebg,
  pers_occ_retail       = (
    occ_m_ret_eat   + occ_f_ret_eat   +
    occ_m_ret_sales + occ_f_ret_sales)*sharebg,
  pers_occ_manual       = (
    occ_m_man_build + occ_f_man_build +
    occ_m_man_nat   + occ_f_man_nat   +
    occ_m_man_prod  + occ_f_man_prod )*sharebg,
  pers_occ_military     = (armedforces)*sharebg,
  # group quarters
  gq_type_univ  =(
    gq_noninst_m_0017_univ + gq_noninst_m_1864_univ + gq_noninst_m_65p_univ  +
    gq_noninst_f_0017_univ + gq_noninst_f_1864_univ + gq_noninst_f_65p_univ)*sharetract,
  gq_type_mil   =(
    gq_noninst_m_0017_mil  + gq_noninst_m_1864_mil  + gq_noninst_m_65p_mil   +
    gq_noninst_f_0017_mil  + gq_noninst_f_1864_mil  + gq_noninst_f_65p_mil)*sharetract,
  gq_type_othnon=(
    gq_noninst_m_0017_oth  + gq_noninst_m_1864_oth  + gq_noninst_m_65p_oth   +
    gq_noninst_f_0017_oth  + gq_noninst_f_1864_oth  + gq_noninst_f_65p_oth)*sharetract)

print(paste0("workingdata (",nrow(workingdata)," rows):"))
print(workingdata)

# take out income columns and handle separately
workingdata_hhinc <- workingdata %>% select(
  starts_with(c("GEOID","blockgroup","tract","TAZ1454","sharebg","hhinc"))
) %>% tibble()
print(paste0("Initial workingdata_hhinc (",nrow(workingdata_hhinc)," rows):"))
print(workingdata_hhinc, n=20)

# pivot hhinc categories from columns to rows
workingdata_hhinc <- workingdata_hhinc %>% pivot_longer(
  cols = starts_with("hhinc"),
  names_to = "householdinc_acs_cat",
  values_to = "num_households",
  values_drop_na = TRUE
)
print(paste0("After pivoting hhinc categories to rows, workingdata_hhinc (",nrow(workingdata_hhinc)," rows):"))
print(workingdata_hhinc)

# join with mapping from householdinc_acs_cat to HHINCQ from PUMS
PUMS_hhinc_cat <- map_ACS5year_household_income_to_TM1_categories(ACS_5year)

workingdata_hhinc <- workingdata_hhinc %>% 
  # apply sharebg
  mutate(num_households = num_households * sharebg) %>%
  left_join(PUMS_hhinc_cat, 
    by="householdinc_acs_cat", 
    relationship="many-to-many") %>%
  # apply the share to households to allocate to hhincq
  mutate(num_households = num_households * acs_to_hhincq_share)

print(paste0("After joining with PUMS-based mapping, workingdata_hhinc (",nrow(workingdata_hhinc)," rows):"))
print(workingdata_hhinc)

# summarize to TAZ
TAZ_hhinc <- workingdata_hhinc %>%
  group_by(TAZ1454, HHINCQ) %>% 
  summarise(num_households = sum(num_households), .groups='drop') %>%
  pivot_wider(names_from = "HHINCQ", values_from = "num_households")

print(paste0("Resulting TAZ_hhinc (",nrow(TAZ_hhinc)," rows):"))
print(TAZ_hhinc)

# Summarize to TAZ and select only variables of interest
tazdata_census <- workingdata %>%
  group_by(TAZ1454) %>%
  summarize(  TOTHH                   =sum(TOTHH),
              HHPOP                   =sum(HHPOP),
              EMPRES                  =sum(EMPRES),
              AGE0004                 =sum(AGE0004),
              AGE0519                 =sum(AGE0519),
              AGE2044                 =sum(AGE2044),
              AGE4564                 =sum(AGE4564),
              AGE65P                  =sum(AGE65P),
              sum_age                 =AGE0004 + AGE0519 + AGE2044  +AGE4564 + AGE65P,
              SFDU                    =sum(SFDU),
              MFDU                    =sum(MFDU),
              hh_own                  =sum(hh_own),
              hh_rent                 =sum(hh_rent),
              hh_size_1               =sum(hh_size_1),
              hh_size_2               =sum(hh_size_2),
              hh_size_3               =sum(hh_size_3),
              hh_size_4_plus          =sum(hh_size_4_plus),
              hh_wrks_0               =sum(hh_wrks_0),
              hh_wrks_1               =sum(hh_wrks_1),
              hh_wrks_2               =sum(hh_wrks_2),
              hh_wrks_3_plus          =sum(hh_wrks_3_plus),
              hh_kids_yes             =sum(hh_kids_yes),
              hh_kids_no              =sum(hh_kids_no),
              AGE62P                  =sum(AGE62P),
              gq_type_univ            =sum(gq_type_univ),
              gq_type_mil             =sum(gq_type_mil),
              gq_type_othnon          =sum(gq_type_othnon),
              gqpop                   =gq_type_univ+gq_type_mil+gq_type_othnon,
              pers_occ_management     =sum(pers_occ_management),
              pers_occ_professional   =sum(pers_occ_professional),
              pers_occ_services       =sum(pers_occ_services),
              pers_occ_retail         =sum(pers_occ_retail),
              pers_occ_manual         =sum(pers_occ_manual),
              pers_occ_military       =sum(pers_occ_military),
              white_nonh              =sum(white_nonh),
              black_nonh              =sum(black_nonh),
              asian_nonh              =sum(asian_nonh),
              other_nonh              =sum(other_nonh),   
              hispanic                =sum(hispanic))

tazdata_census <- left_join(tazdata_census, TAZ_hhinc, by="TAZ1454", relationship="one-to-one")
# add county, County_name, DISTRICT, District_NAme, etc
tazdata_census <- left_join(tazdata_census, TAZ_SD_COUNTY, by=c("TAZ1454"="ZONE"))
# add employment
tazdata_census <- left_join(tazdata_census,employment, by="TAZ1454")

print(paste0("tazdata_census (", nrow(tazdata_census)," rows):"))
print(tazdata_census)
# print("str(tazdata_census):")
# print(str(tazdata_census))

print("DHC GQ population:")
DHC_gqpop <- tazdata_census %>%
  select(TAZ1454, gq_type_univ, gq_type_mil, gq_type_othnon, gqpop) %>% 
  left_join(., select(TAZ_SD_COUNTY,ZONE,County_Name), by=c("TAZ1454"="ZONE")) %>% 
  group_by(County_Name) %>% summarize(
    gq_type_univ  =sum(gq_type_univ), 
    gq_type_mil   =sum(gq_type_mil),
    gq_type_othnon=sum(gq_type_othnon),
    gqpop         =sum(gqpop))
print(DHC_gqpop)
print("Regional totals --")
print(paste("gq_type_univ  :", format(sum(DHC_gqpop$gq_type_univ),   nsmall=0, big.mark=',')))
print(paste("gq_type_mil   :", format(sum(DHC_gqpop$gq_type_mil),    nsmall=0, big.mark=',')))
print(paste("gq_type_othnon:", format(sum(DHC_gqpop$gq_type_othnon), nsmall=0, big.mark=',')))
print(paste("gqpop         :", format(sum(DHC_gqpop$gqpop),          nsmall=0, big.mark=',')))

# Sum constituent parts to compare with marginal totals
tazdata_census <- tazdata_census %>%
  mutate (
    sum_age            = AGE0004 + AGE0519 + AGE2044  +AGE4564 + AGE65P,       # Person totals by age
    sum_groupquarters  = gq_type_univ + gq_type_mil + gq_type_othnon,          # GQ by type
    sum_DU             = MFDU + SFDU,                                          # Households by dwelling unit (mult-family or single-family)
    sum_tenure         = hh_own + hh_rent,                                     # Households by tenure
    sum_size           = hh_size_1 + hh_size_2 + hh_size_3 + hh_size_4_plus,   # Now housing totals
    sum_hhworkers      = hh_wrks_0 + hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus,   # HHs by number of workers
    sum_kids           = hh_kids_yes + hh_kids_no,                             # HHs by kids or not
    sum_income         = HHINCQ1 + HHINCQ2 + HHINCQ3 + HHINCQ4,                # HHs by income
    sum_empres         = pers_occ_management + pers_occ_professional+          # Employed residents by industry
      pers_occ_services + pers_occ_retail + pers_occ_manual + pers_occ_military,
    TOTPOP             = sum_age,  # universe = total population
    gqpop              = round(gqpop,0),
    sum_ethnicity      = white_nonh+black_nonh+asian_nonh+other_nonh+hispanic
  )
print("households consistency checks")
print(tazdata_census %>% group_by(County_Name) %>% summarize(
  TOTHH        =sum(TOTHH), 
  sum_tenure   =sum(sum_tenure),
  sum_size     =sum(sum_size),
  sum_income   =sum(sum_income),
  sum_hhworkers=sum(sum_hhworkers),
  sum_kids     =sum(sum_kids)
))

print("population consistency checks")
print(tazdata_census %>% group_by(County_Name) %>% summarize(
  TOTPOP        =sum(TOTPOP),
  sum_age       =sum(sum_age),
  sum_ethnicity =sum(sum_ethnicity)))

# Round Data
tazdata_census <- tazdata_census %>%
  mutate_if(is.numeric,round,0)

# some of these are bigger than +/- 1 so commenting them out with TODO for now
# as in practice for 2023 we'll Scale the the ACS 1Year Totals

# population
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTPOP", c("AGE0004","AGE0519","AGE2044","AGE4564","AGE65P"))
# TODO: tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTPOP", c("white_nonh","black_nonh","asian_nonh","other_nonh","hispanic"))
# group quarters
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "gqpop",  c("gq_type_univ","gq_type_mil","gq_type_othnon"))
# households
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTHH",  c("hh_own","hh_rent"))
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTHH",  c("hh_size_1","hh_size_2","hh_size_3","hh_size_4_plus"))
# TODO: azdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTHH",  c("hh_kids_yes","hh_kids_no"))
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTHH", c("HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4"))
# TODO: tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "TOTHH",  c("hh_wrks_0","hh_wrks_1","hh_wrks_2","hh_wrks_3_plus"))
# employed residents
tazdata_census <- fix_rounding_artifacts(tazdata_census, "TAZ1454", "EMPRES", c("pers_occ_management","pers_occ_professional",
                                                                                "pers_occ_services","pers_occ_retail",
                                                                                "pers_occ_manual","pers_occ_military"))

# Add in population over age 62 variable that is also needed (but should not be rounded, so added at the end)
tazdata_census <- tazdata_census %>%
  mutate(SHPOP62P = if_else(TOTPOP==0,0,AGE62P/TOTPOP))

###############################################################################################################################################
#
# If there are more recent (but incomplete) alternative data sources, we may
# create updated county-based targets in the following steps

current_county_totals <- tazdata_census %>% 
  group_by(County_Name) %>% 
  summarise(
    TOTHH  = sum(TOTHH),
    TOTPOP = sum(TOTPOP),
    GQPOP  = sum(gqpop),
    HHPOP  = sum(HHPOP),
    EMPRES = sum(EMPRES),
    TOTEMP = sum(TOTEMP)
  )
print("current_county_totals:")
print(current_county_totals)

# assume targets are the same as we have to begin with, but adjust below
county_targets <- current_county_totals %>% mutate(
  TOTHH_target  = TOTHH,
  TOTPOP_target = TOTPOP,
  GQPOP_target  = GQPOP,
  HHPOP_target  = HHPOP,
  EMPRES_target = EMPRES,
  TOTEMP_target = TOTEMP,
)


# ACS_5year should be ACS_PUMS_1year + 2 -- if it's not, then scale up using ACS1-year totals
if (ACS_5year < ACS_PUMS_1year+2) {
  print("##########################################################################################")
  print(sprintf("Scaling to ACS 1Year Totals: ACS_5year %d < ACS_PUMS_1year + 2 = %d", ACS_5year, ACS_PUMS_1year + 2))

  ACS_target_vars = c(
    tothh_        ="B19001_001",    # Total households
    totpop_       ="B01001_001",    # Total population
    hhpop_        ="B28005_001",    # Universe: Population in households
    employed_     ="B23025_004",    # Civilian employed residents (employed residents is "employed" + "armed forces")
    armedforces_  ="B23025_006" 	  # Armed forces
  )

  simplify_col <- function(name) { gsub("_E", "", name) }

  ACS_1year_target <- tidycensus::get_acs(
      geography = "county", variables = ACS_target_vars,
      state = state_code, county=baycounties,
      year = ACS_PUMS_1year,
      output="wide",
      survey = "acs1",
      cache_table = USE_TIDYCENSUS_CACHING,
      key = censuskey)
  ACS_1year_target <- ACS_1year_target %>%
    select(-ends_with("_M")) %>%
    rename_with(simplify_col, ends_with("_E")) %>%
    mutate(
      NAME = str_replace_all(NAME," County, California", ""),
      empres = employed + armedforces) %>%
    select(-GEOID, -employed, -armedforces) %>%
    rename(
      County_Name   = NAME,
      TOTHH_target  = tothh,
      TOTPOP_target = totpop,
      HHPOP_target  = hhpop,
      EMPRES_target = empres
    ) %>% 
    mutate(GQPOP_target = TOTPOP_target - HHPOP_target)

  print("ACS_1year_target:")
  print(ACS_1year_target)

  # replace in county_targets
  county_targets <- county_targets %>% 
    select(-TOTHH_target, -TOTPOP_target, -HHPOP_target, -EMPRES_target, -GQPOP_target) %>%
    left_join(., ACS_1year_target, by="County_Name")
}

# factor EMPRES by LODES
print(sprintf("  Workers with h_county in BayArea: %s", format(
  lehd_lodes %>% filter(h_county %in% BAY_AREA_COUNTIES) %>% 
    summarise(TOTEMP=sum(TOTEMP)) %>% pull(TOTEMP),
  big.mark = ",", scientific = FALSE)))
print(sprintf("  Workers with w_county in BayArea: %s", format(
  lehd_lodes %>% filter(w_county %in% BAY_AREA_COUNTIES) %>%
    summarise(TOTEMP=sum(TOTEMP)) %>% pull(TOTEMP),
  big.mark = ",", scientific = FALSE)))
print(sprintf("  Workers with h_county AND w_county in BayArea: %s", format(
  lehd_lodes %>% filter(w_county %in% BAY_AREA_COUNTIES) %>% 
                 filter(h_county %in% BAY_AREA_COUNTIES) %>%
    summarise(TOTEMP=sum(TOTEMP)) %>% pull(TOTEMP),
  big.mark = ",", scientific = FALSE)))

# blend lehd_lodes and existing county_targets based upon EMPRES_LEHD_target
lehd_lodes_h_county <- lehd_lodes %>% 
  filter(w_county %in% BAY_AREA_COUNTIES) %>% # include on jobs in bay area
  filter(h_county %in% BAY_AREA_COUNTIES) %>% # held by residents of the bay area
  group_by(h_county) %>%
  summarise(EMPRES_LEHD_target=sum(TOTEMP)) %>%
  rename(County_Name = h_county) # EMPRES since we're summing to home county
print("lehd_lodes_h_county:")
print(lehd_lodes_h_county)

county_targets <- left_join(county_targets, lehd_lodes_h_county, by="County_Name")
print(sprintf("Incorporating EMPRES_LODES_WEIGHT=%.2f; county_targets before adjustment:", EMPRES_LODES_WEIGHT))
print(county_targets)

county_targets <- county_targets %>% 
  mutate(
    EMPRES_target = EMPRES_LODES_WEIGHT*EMPRES_LEHD_target + (1.0-EMPRES_LODES_WEIGHT)*EMPRES_target
  ) %>% select(-EMPRES_LEHD_target)
print("county_targets after adjustment:")
print(county_targets)

###############################################################################################################################################
# Implement county_targets
print("Implementing County Targets:")
  
county_targets <- county_targets %>% mutate(
    TOTHH_diff  = TOTHH_target  - TOTHH,
    TOTPOP_diff = TOTPOP_target - TOTPOP,
    HHPOP_diff  = HHPOP_target  - HHPOP,
    GQPOP_diff  = GQPOP_target  - GQPOP,
    EMPRES_diff = EMPRES_target - EMPRES,
    TOTEMP_diff = TOTEMP_target - TOTEMP
)
print(county_targets)

print("Regional totals:")
print(county_targets %>% summarise(across(where(is.numeric), sum)))
  
# update from most specific to least specific
# 1. group quarters population (includes employed residents and persons by age)
return_list <- update_gqop_to_county_totals(tazdata_census, county_targets, ACS_PUMS_1year)
tadata_census              <- return_list$source_df
detailed_GQ_county_targets <- return_list$detailed_GQ_county_targets

# 2. employed residents (not including households by workers)
tazdata_census_orig   <- update_empres_to_county_totals(tazdata_census, county_targets)

# use the generic version to verify these do the same thing (they do!)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets, 
  sum_var      = "EMPRES", 
  partial_vars = c("pers_occ_management", "pers_occ_professional", "pers_occ_services", 
                   "pers_occ_retail", "pers_occ_manual","pers_occ_military")
)

# 3. total households and population
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_age_target = TOTPOP_target), 
  sum_var      = "sum_age", 
  partial_vars = c("AGE0004", "AGE0519", "AGE2044", "AGE4564", "AGE65P")
)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_ethnicity_target = TOTPOP_target), 
  sum_var      = "sum_ethnicity", 
  partial_vars = c("white_nonh", "black_nonh", "asian_nonh", "other_nonh", "hispanic")
)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_DU_target = TOTHH_target), 
  sum_var      = "sum_DU", 
  partial_vars = c("SFDU", "MFDU")
)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_tenure_target = TOTHH_target), 
  sum_var      = "sum_tenure", 
  partial_vars = c("hh_own", "hh_rent")
)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_kids_target = TOTHH_target), 
  sum_var      = "sum_kids", 
  partial_vars = c("hh_kids_yes", "hh_kids_no")
)
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_income_target = TOTHH_target), 
  sum_var      = "sum_income", 
  partial_vars = c("HHINCQ1", "HHINCQ2", "HHINCQ3", "HHINCQ4")
)
# households by size are trickier because the partial columns have different weights
# start with a straightforward approach
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_size_target = TOTHH_target), 
  sum_var      = "sum_size", 
  partial_vars = c("hh_size_1", "hh_size_2", "hh_size_3", "hh_size_4_plus")
)
# Now make adjustment for HHPOP
# popsyn_ACS_PUMS_5year: https://github.com/BayAreaMetro/populationsim/blob/master/bay_area/create_seed_population.py
tazdata_census <- make_hhsizes_consistent_with_population(
  source_df             = tazdata_census, 
  target_df             = county_targets,
  size_or_workers       = "hh_size",
  popsyn_ACS_PUMS_5year = 2021
)
# Ditto fo households by workers
tazdata_census <- update_tazdata_to_county_target(
  source_df    = tazdata_census, 
  target_df    = county_targets %>% rename(sum_hhworkers_target = TOTHH_target), 
  sum_var      = "sum_hhworkers", 
  partial_vars = c("hh_wrks_0", "hh_wrks_1", "hh_wrks_2", "hh_wrks_3_plus")
)
# Now make adjustment for EMPRES
# popsyn_ACS_PUMS_5year: https://github.com/BayAreaMetro/populationsim/blob/master/bay_area/create_seed_population.py
tazdata_census <- make_hhsizes_consistent_with_population(
  source_df             = tazdata_census, 
  target_df             = county_targets,
  size_or_workers       = "hh_wrks",
  popsyn_ACS_PUMS_5year = 2021
)

print(paste0("tazdata_census (", nrow(tazdata_census)," rows):"))
print(tazdata_census)
# print("str(tazdata_census):")
# print(str(tazdata_census))

# Remove sum variables
tazdata_census <- tazdata_census %>%
  select(-sum_age,-sum_groupquarters,-sum_tenure,-sum_size,-sum_hhworkers,-sum_kids,-sum_income,-sum_empres, -sum_ethnicity)

### End of recoding

# Write out ethnic variables

ethnic <- tazdata_census %>% 
  select(TAZ1454,hispanic, white_nonh,black_nonh,asian_nonh,other_nonh,TOTPOP, COUNTY, County_Name)

write.csv(ethnic,file = file.path(argv$year, "TAZ1454_Ethnicity.csv"),row.names = FALSE)
print(paste("Wrote",file.path(argv$year,"TAZ1454_Ethnicity.csv")))

# Read in old PBA data sets and select variables for joining to new 2020 dataset
# Bring in school and parking data from 2015 TAZ data 
# Add HHLDS variable (same as TOTHH), select new 2015 output

# Bring in PBA 2050 2015 land use data for county equivalencies and other data needs
PBA2015 <- read_excel(PBA_TAZ_2015,sheet="census2015") 

PBA2015_joiner <- PBA2015 %>%
  select(ZONE,SD,TOTACRE,RESACRE,CIACRE,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TOPOLOGY,TERMINAL, ZERO)

tazdata_census <- left_join(PBA2015_joiner,tazdata_census, by=c("ZONE"="TAZ1454"))   # Join 2015 topology, parking, enrollment

# Save R version of data for 2020 to later inflate to 2023
output_file=file.path(argv$year, sprintf("TAZ Land Use File %d.rdata", argv$year))
save(tazdata_census,file=output_file)
print(paste("Wrote",output_file))

# Write out subsets of final data
 
tazdata_landuse <- tazdata_census %>%
  mutate(hhlds=TOTHH) %>%
  select(ZONE,DISTRICT,SD,COUNTY,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,TOTACRE,
         RESACRE,CIACRE,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TERMINAL,TOPOLOGY,ZERO,hhlds,
         gqpop) 

output_file <- file.path(argv$year, sprintf("TAZ1454 %d Land Use.csv", argv$year))
write.csv(tazdata_landuse, output_file, row.names = FALSE, quote = T)
print(paste("Wrote", output_file))

# Summarize ACS and employment data by superdistrict for both 2015 and the given year

district_summary_2015 <- PBA2015 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=TOTPOP-HHPOP) %>% 
  ungroup()

output_file <- file.path(2015, sprintf("TAZ1454 %d District Summary.csv", 2015))
write.csv(district_summary_2015, output_file, row.names = FALSE, quote = T)
print(paste("Wrote",output_file))

district_summary <- tazdata_census %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=sum(gqpop)) %>% 
  ungroup()

output_file <- file.path(argv$year, sprintf("TAZ1454 %d District Summary.csv", argv$year))
write.csv(district_summary, output_file, row.names = FALSE, quote = T)
print(paste("Wrote", output_file))

# Select out PopSim variables and export to separate csv

popsim_vars <- tazdata_census %>% 
  rename(TAZ=ZONE,gq_tot_pop=gqpop)%>%
  select(TAZ,TOTHH,TOTPOP,hh_own,hh_rent,hh_size_1,hh_size_2,hh_size_3,hh_size_4_plus,hh_wrks_0,hh_wrks_1,hh_wrks_2,hh_wrks_3_plus,
         hh_kids_no,hh_kids_yes,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,
         gq_tot_pop,gq_type_univ,gq_type_mil,gq_type_othnon)

output_file <- file.path(argv$year, sprintf("TAZ1454 %d Popsim Vars.csv", argv$year))
write.csv(popsim_vars, output_file, row.names = FALSE, quote = T)
print(paste("Wrote",output_file))

# region popsim vars
popsim_vars_region <- popsim_vars %>% 
  mutate(REGION=1) %>%
  group_by(REGION) %>%
  summarize(gq_num_hh_region=sum(gq_tot_pop))

output_file <- file.path(argv$year, sprintf("TAZ1454 %d Popsim Vars Region.csv", argv$year))
write.csv(popsim_vars_region, output_file, row.names = FALSE, quote = T)
print(paste("Wrote",output_file))

# county popsim vars
popsim_vars_county <- tazdata_census %>%
  group_by(COUNTY) %>% summarize(
    pers_occ_management  =sum(pers_occ_management),
    pers_occ_professional=sum(pers_occ_professional),
    pers_occ_services    =sum(pers_occ_services),
    pers_occ_retail      =sum(pers_occ_retail),
    pers_occ_manual      =sum(pers_occ_manual),
    pers_occ_military    =sum(pers_occ_military))

output_file <- file.path(argv$year, sprintf("TAZ1454 %d Popsim Vars County.csv", argv$year))
write.csv(popsim_vars_county, output_file, row.names = FALSE, quote = T)
print(paste("Wrote",output_file))

# Output into Tableau-friendly format

PBA2015_long <- PBA2015 %>%
  mutate(gqpop=TOTPOP-HHPOP) %>% 
  left_join(.,select(TAZ_SD_COUNTY,ZONE,County_Name,DISTRICT_NAME),by=c("ZONE")) %>% # add County_Name, DISTRICT_NAME
  mutate(Year=2015) %>% 
  select(ZONE,DISTRICT,DISTRICT_NAME,COUNTY, County_Name,Year,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

output_file <- file.path(2015, sprintf("TAZ1454_%d_long.csv", 2015))
write.csv(PBA2015_long,output_file,row.names = F)
print(paste("Wrote",output_file))

tazdata_census_long <- tazdata_census %>%
  mutate(Year=argv$year) %>% 
  select(ZONE,DISTRICT,DISTRICT_NAME,COUNTY,County_Name,Year,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

output_file <- file.path(argv$year, sprintf("TAZ1454_%d_long.csv", argv$year))
write.csv(tazdata_census_long,output_file,row.names = F)
print(paste("Wrote",output_file))
