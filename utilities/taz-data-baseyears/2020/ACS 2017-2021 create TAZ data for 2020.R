# ACS 2017-2021 create TAZ data for 2020.R
# Create "2020" TAZ data from ACS 2017-2021 
# SI

# Notes

# The working directory is set as the location of the script. All other paths in TM1 will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

"

1. ACS data here is downloaded for the 2017-2021 5-year dataset. The end year can be updated 
   by changing the *ACS_year* variable. 

2. ACS block group variables used in all instances where not suppressed. If suppressed at the block group 
   level, tract-level data used instead. Suppressed variables may change if ACS_year is changed. This 
   should be checked, as this change could cause the script not to work.

3. Different than the effort for 2015, many small area variables (such as age, total population, etc.) are
   available from Census 2020 data. 

4. TAZs are scaled up to match Census 2020 totals 
   
"
# Import Libraries

suppressMessages(library(tidyverse))
library(tidycensus)
library(readxl)

# Set up directories, import TAZ/census block equivalence, install census key, set ACS year,set CPI inflation

blockTAZ2020_in      <- "M:/Data/GIS layers/TM1_taz_census2020/2020block_to_TAZ1454.csv"
censuskey            <- readLines("M:/Data/Census/API/api-key.txt")
baycounties          <- c("01","13","41","55","75","81","85","95","97")
state                <- "06"
census_api_key(censuskey, install = TRUE, overwrite = TRUE)

ACS_year <- 2021
sf1_year <- 2020
ACS_product="5"

USERPROFILE          <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
GITHUB_DIR           <- file.path(USERPROFILE,"Documents","GitHub")
if (Sys.getenv("USERNAME") %in% c("lzorn")) {
  GITHUB_DIR         <- file.path("E://GitHub")
  BOX_TM             <- file.path("E://Box/Modeling and Surveys")
}
PBA_TAZ_2015         <- file.path(BOX_TM, "Share Data", "plan-bay-area-2050", "tazdata","PBA50_FinalBlueprintLandUse_TAZdata.xlsx")

# Bring in 2020 TAZ employment data

#PETRALE              <- file.path(GITHUB_DIR,"petrale","applications","travel_model_lu_inputs")

# AO: Moved from Petrale to TM1 utilities Oct 2023
TM1                   <- file.path(GITHUB_DIR,'utilities','taz-data-baseyears')

emp_wagesal_2020      <- read.csv(file.path(TM1,"2020","Employment","lodes_wac_employment.csv"),header = T)
emp_selfemp_2020      <- read.csv(file.path(TM1,"2020","Self Employed Workers","taz_self_employed_workers_2020.csv"),header = T)

# Restructure employment frame to wide format
emp_selfemp_2020_w <- emp_selfemp_2020 %>%
  select(-c(X)) %>%
  pivot_wider(names_from = industry, values_from = value, values_fill = 0) %>%
  mutate(TOTEMP = rowSums(select(., -zone_id))) %>%
  arrange(zone_id) %>% 
  rename( c("zone_id" = "TAZ1454")) %>%
  rename_all(toupper)

# Combine the two employment frames - wage/salary, and self-employment
total_employment_2020 <- bind_rows(emp_wagesal_2020, emp_selfemp_2020_w,.id='src')

# Group by TAZ1454 and calculate the sum for total employment by taz (wage/salary plus self-employment)
employment_2020 <- total_employment_2020 %>%
  group_by(TAZ1454) %>%
  summarize_if(is.numeric, sum, na.rm = F)

baycounties <- c("01","13","41","55","75","81","85","95","97")
state_code <- "06" 

# Bring in PBA 2050 2015 land use data for county equivalencies and other data needs
# 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7= Napa; 8=Sonoma; 9=Marin

PBA2015 <- read_excel(PBA_TAZ_2015,sheet="census2015") 

PBA2015_county <- PBA2015 %>%                                    # Create and join TAZ/county equivalence
  select(ZONE,COUNTY) %>%
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
  ))

# Bring in superdistrict name for joining

superdistrict <- read_excel(file.path(TM1,"2015","TAZ1454 2015 Land Use.xlsx"),sheet="2010 District Summary") %>% 
                              select("DISTRICT","DISTRICT_NAME"="DISTRICT NAME") %>% 
                              filter(!(DISTRICT=="Bay Area")) %>% 
                              mutate(DISTRICT=as.numeric(DISTRICT))

# Income table - Guidelines for HH income values used from ACS
"

    2000 income breaks 2021 CPI equivalent   Nearest 2021 ACS breakpoint
    ------------------ -------------------   ---------------------------
    $30,000            $51,563               $50,000
    $60,000            $103,125              $100,000 
    $100,000           $171,876              $171,876*
    ------------------ -------------------   ---------------------------

    * Because the 2021$ equivalent of $100,000 in 2000$ ($171,876) doesn't closely align with 2021 ACS income 
      categories, households within the $150,000-$199,999 category will be apportioned above and below $171,876. 
      Using the ACS 2017-2021 PUMS data, the share of households above $171,876 within the $150,000-$199,999 
      category is 0.5035511.That is, approximately 50 percent of HHs in the $150,000-$199,999 category will be 
      apportioned above this value (Q3) and approximately 50 percent below it (Q2). The table below compares 2000$ and 2021$.

Household Income Category Equivalency, 2000$ and 2017$

          Year      Lower Bound     Upper Bound
          ----      ------------    -----------
HHINCQ1   2000      $-inf           $29,999
          2021      $-inf           $49,999
HHINCQ2   2000      $30,000         $59,999
          2021      $50,000         $99,999
HHINCQ3   2000      $60,000         $99,999
          2021      $100,000        $171,876
HHINCQ4   2000      $100,000        $inf
          2021      $171,877        $inf
          ----      -------------   -----------

"

shareabove171876 <- 0.5035511 # Use this value to later divvy up HHs in the 60-100k and 100k+ respective quartiles.

# Import decennial census (DHC file) and ACS for variable inspection, use to get variable numbers

DHC_table <- load_variables(year=2020, dataset="dhc", cache=TRUE)
ACS_table <- load_variables(year=2021, dataset="acs5", cache=TRUE)

# Identify the 2020 decennial census variables
# Some variables skipped in sequence due to nesting

DHC_BG_variables <- c(

# Household totals
  
  tothh             ="H12_001N",    # Total HHs 
  hhpop             ="P15_001N",	  # HH pop 

# Age, male
  
  male0_4           ="P12_003N",    # male aged 0 to 4 
  male5_9           ="P12_004N",		# male aged 5 to 9 
  male10_14         ="P12_005N",		# male aged 10 to 14
  male15_17         ="P12_006N",		# male aged 15 to 17
  male18_19         ="P12_007N",		# male aged 18 to 19
  male20            ="P12_008N",		# male aged 20 
  male21            ="P12_009N",		# male aged 21 
  male22_24         ="P12_010N",		# male aged 22 to 24 
  male25_29         ="P12_011N",		# male aged 25 to 29 
  male30_34         ="P12_012N",		# male aged 30 to 34 
  male35_39         ="P12_013N",		# male aged 35 to 39 
  male40_44         ="P12_014N",		# male aged 40 to 44 
  male45_49         ="P12_015N",		# male aged 45 to 49 
  male50_54         ="P12_016N",		# male aged 50 to 54 
  male55_59         ="P12_017N",		# male aged 55 to 59 
  male60_61         ="P12_018N",		# male aged 60 to 61 
  male62_64         ="P12_019N",		# male aged 62 to 64 
  male65_66         ="P12_020N",		# male aged 65 to 66 
  male67_69         ="P12_021N",		# male aged 67 to 69 
  male70_74         ="P12_022N",		# male aged 70 to 74 
  male75_79         ="P12_023N",		# male aged 75 to 79 
  male80_84         ="P12_024N",		# male aged 80 to 84 
  male85p           ="P12_025N",		# male aged 85+ 

# Age, female   
    
  female0_4         ="P12_027N",   # female aged 0 to 4 
  female5_9         ="P12_028N",		# female aged 5 to 9 
  female10_14       ="P12_029N",		# female aged 10 to 14
  female15_17       ="P12_030N",		# female aged 15 to 17
  female18_19       ="P12_031N",		# female aged 18 to 19
  female20          ="P12_032N",		# female aged 20 
  female21          ="P12_033N",		# female aged 21 
  female22_24       ="P12_034N",		# female aged 22 to 24 
  female25_29       ="P12_035N",		# female aged 25 to 29 
  female30_34       ="P12_036N",		# female aged 30 to 34 
  female35_39       ="P12_037N",		# female aged 35 to 39 
  female40_44       ="P12_038N",		# female aged 40 to 44 
  female45_49       ="P12_039N",		# female aged 45 to 49 
  female50_54       ="P12_040N",		# female aged 50 to 54 
  female55_59       ="P12_041N",		# female aged 55 to 59 
  female60_61       ="P12_042N",		# female aged 60 to 61 
  female62_64       ="P12_043N",		# female aged 62 to 64 
  female65_66       ="P12_044N",		# female aged 65 to 66 
  female67_69       ="P12_045N",		# female aged 67 to 69 
  female70_74       ="P12_046N",		# female aged 70 to 74 
  female75_79       ="P12_047N",		# female aged 75 to 79 
  female80_84       ="P12_048N",		# female aged 80 to 84 
  female85p         ="P12_049N",		# female aged 85+ 

# Household size by tenure

  own1              ="H12_003N",    # own 1 person in HH 	     
  own2              ="H12_004N",    # own 2 persons in HH 
  own3              ="H12_005N",    # own 3 persons in HH 
  own4              ="H12_006N",    # own 4 persons in HH 
  own5              ="H12_007N",    # own 5 persons in HH 
  own6              ="H12_008N",    # own 6 persons in HH 
  own7p             ="H12_009N",    # own 7+ persons in HH 
  rent1             ="H12_011N",    # rent 1 person in HH
  rent2             ="H12_012N",    # rent 2 persons in HH 
  rent3             ="H12_013N",    # rent 3 persons in HH 
  rent4             ="H12_014N",    # rent 4 persons in HH 
  rent5             ="H12_015N",    # rent 5 persons in HH 
  rent6             ="H12_016N",    # rent 6 persons in HH 
  rent7p            ="H12_017N",    # rent 7+ persons in HH

# Race/Ethnicity variables

  white_nonh        ="P5_003N",   # White alone, not Hispanic
  black_nonh        ="P5_004N",   # Black alone, not Hispanic
  asian_nonh        ="P5_006N",   # Asian alone, not Hispanic
  total_nonh        ="P5_002N",   # Total, not Hispanic
  total_hisp        ="P5_010N")   # Total Hispanic

ACS_BG_variables <- c(
  
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
  
# Employment  
  
  employed_         ="B23025_004",    # Civilian employed residents (employed residents is "employed" + "armed forces")
  armedforces_      ="B23025_006", 	  # Armed forces

# Household income
                      
  hhinc0_10_        ="B19001_002",    # Household income 0 to $10k 
  hhinc10_15_       ="B19001_003",		# Household income $10 to $15k
  hhinc15_20_       ="B19001_004",		# Household income $15 to $20k
  hhinc20_25_       ="B19001_005",		# Household income $20 to $25k
  hhinc25_30_       ="B19001_006",		# Household income $25 to $30k
  hhinc30_35_       ="B19001_007",		# Household income $30 to $35k
  hhinc35_40_       ="B19001_008",		# Household income $35 to $40k
  hhinc40_45_       ="B19001_009",		# Household income $40 to $45k
  hhinc45_50_       ="B19001_010",		# Household income $45 to $50k
  hhinc50_60_       ="B19001_011",		# Household income 50 to $60k
  hhinc60_75_       ="B19001_012",		# Household income 60 to $75k
  hhinc75_100_      ="B19001_013",		# Household income 75 to $100k
  hhinc100_125_     ="B19001_014",		# Household income $100 to $1$25k
  hhinc125_150_     ="B19001_015",		# Household income $1$25 to $150k
  hhinc150_200_     ="B19001_016",		# Household income $150 to $200k
  hhinc200p_        ="B19001_017",		# Household income $200k+
  
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
  occ_f_man_prod_   ="C24010_070")  # Production, transportation, and material moving

# Households by number of workers, households by number of kids
                      
ACS_tract_variables <-  c(hhwrks0_                    = "B08202_002", # 0-worker HH
                          hhwrks1_                    = "B08202_003",	# 1-worker HH
                          hhwrks2_                    = "B08202_004",	# 2-worker HH
                          hhwrks3p_                   = "B08202_005", # 3+-worker HH
                                
                          ownkidsyes_                 = "B25012_003", # Own with related kids under 18
                          rentkidsyes_                = "B25012_011", # Rent with related kids under 18
                          ownkidsno_                  = "B25012_009", # Own without related kids under 18
                          rentkidsno_                 = "B25012_017"  # Rent without related kids under 18
                          )

# Group quarters for tracts by age and type of resident

DHC_tract_variables <-  c(gq_noninst_m_0017_univ      = "PCT19_024N", # Male non-inst. under 18 university
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
                          gq_noninst_f_65p_oth        = "PCT19_189N") # Female non-inst. 65+ other

# Bring in 2020 block/TAZ equivalency, create block group ID and tract ID fields for later joining to ACS data
# Add zero on that is lost in CSV conversion
# Remove San Quentin block from file and move other blocks with population in TAZ 1439 to adjacent 1438

blockTAZ <- read.csv(blockTAZ2020_in,header=TRUE) %>% mutate(      
  blockgroup = paste0("0",blockgroup),
  tract = paste0("0",tract)) %>% 
  filter (!(NAME=="Block 1007, Block Group 1, Census Tract 1220, Marin County, California")) %>%  # San Quentin block
  mutate(TAZ1454=case_when(
    NAME=="Block 1006, Block Group 1, Census Tract 1220, Marin County, California"   ~ as.integer(1438),
    NAME=="Block 1002, Block Group 1, Census Tract 1220, Marin County, California"   ~ as.integer(1438),
    TRUE                                                                             ~ TAZ1454
  ))

# Summarize block population by block group and tract 

blockTAZBG <- blockTAZ %>% 
  group_by(blockgroup) %>%
  summarize(BGTotal=sum(block_POPULATION))

blockTAZTract <- blockTAZ %>% 
  group_by(tract) %>%
  summarize(TractTotal=sum(block_POPULATION))

# Create 2020 block share of total population for block/block group and block/tract, append to comnbined_block file
# Be mindful of divide by zero error associated with 0-pop block groups and tracts

combined_block <- left_join(blockTAZ,blockTAZBG,by="blockgroup") %>% mutate(
  sharebg=if_else(block_POPULATION==0,0,block_POPULATION/BGTotal))

combined_block <- left_join(combined_block,blockTAZTract,by="tract") %>% mutate(
  sharetract=if_else(block_POPULATION==0,0,block_POPULATION/TractTotal))

# Function to make tract and block group data API calls by county for ACS 2017-2021

ACS_tract_raw <- get_acs(
          geography = "tract", variables = ACS_tract_variables,
          state = state_code, county=baycounties,
          year=ACS_year,
          output="wide",
          survey = "acs5",
          key = censuskey)

ACS_BG_raw <- get_acs(
  geography = "block group", variables = ACS_BG_variables,
  state = state_code, county=baycounties,
  year=ACS_year,
  output="wide",
  survey = "acs5",
  key = censuskey)

DHC_tract_raw <- get_decennial(
  geography = "tract", variables = DHC_tract_variables,
  state = state_code, county=baycounties,
  year=2020,
  output="wide",
  sumfile = "dhc",
  key = censuskey)

DHC_BG_raw <- get_decennial(
  geography = "block group", variables = DHC_BG_variables,
  state = state_code, county=baycounties,
  year=2020,
  output="wide",
  sumfile = "dhc",
  key = censuskey)

# Remove NAME variable from decennial files for later joining

DHC_tract_raw <- DHC_tract_raw %>% select(-NAME)
DHC_BG_raw    <- DHC_BG_raw %>% select(-NAME)

# Remove MOEs from ACS variables,rename to drop "_E" suffix
# Drop NAME variable for later joining

ACS_tract_raw <- ACS_tract_raw %>% select(!(ends_with("_M"))) %>% select(-NAME)
ACS_BG_raw <- ACS_BG_raw %>% select(!(ends_with("_M"))) %>% select(-NAME)
names(ACS_tract_raw) <- str_replace_all(names(ACS_tract_raw), c("_E" = ""))
names(ACS_BG_raw) <- str_replace_all(names(ACS_BG_raw), c("_E" = ""))
                                                                             

# Join 2017-2021 ACS and DHC block group and tract variables to combined_block file
# Combine and collapse ACS categories to get land use control totals, as appropriate
# Apply block share of 2013-2017 ACS variables using block/block group and block/tract shares of 2020 total population

interim <- left_join(combined_block,ACS_BG_raw, by=c("blockgroup"="GEOID")) %>% 
  left_join(.,ACS_tract_raw, by=c("tract"="GEOID"))%>% 
  left_join(.,DHC_BG_raw, by=c("blockgroup"="GEOID"))%>%
  left_join(.,DHC_tract_raw, by=c("tract"="GEOID"))
workingdata <- interim %>% mutate(
  TOTHH=tothh*sharebg,
  HHPOP=hhpop*sharebg,
  EMPRES=(employed+armedforces)*sharebg,
  HHINCQ1=(hhinc0_10+
             hhinc10_15+
             hhinc15_20+
             hhinc20_25+
             hhinc25_30+
             hhinc30_35+
             hhinc35_40+
             hhinc40_45+
             hhinc45_50)*sharebg,
  HHINCQ2=(  hhinc50_60+
             hhinc60_75+
             hhinc75_100)*sharebg,
  HHINCQ3=(  hhinc100_125+
             hhinc125_150+
             (hhinc150_200*(1-shareabove171876)))*sharebg, # Apportions HHs below $171,876 within $150,000-$200,000 range
  HHINCQ4=((hhinc150_200*shareabove171876)+                # Apportions HHs above $171,876 within $150,000-$200,000 range
             hhinc200p)*sharebg,
  AGE0004=(male0_4+female0_4)*sharebg,
  AGE0519=(male5_9+
             male10_14+
             male15_17+
             male18_19+
             female5_9+
             female10_14+
             female15_17+
             female18_19)*sharebg,
  AGE2044=(male20+
             male21+
             male22_24+
             male25_29+
             male30_34+
             male35_39+
             male40_44+
             female20+
             female21+
             female22_24+
             female25_29+
             female30_34+
             female35_39+
             female40_44)*sharebg,
  AGE4564=(male45_49+
             male50_54+
             male55_59+
             male60_61+
             male62_64+
             female45_49+
             female50_54+
             female55_59+
             female60_61+
             female62_64)*sharebg,
  AGE65P=(male65_66+
            male67_69+
            male70_74+
            male75_79+
            male80_84+
            male85p+
            female65_66+
            female67_69+
            female70_74+
            female75_79+
            female80_84+
            female85p)*sharebg,
  AGE62P=(male62_64+
            male65_66+
            male67_69+
            male70_74+
            male75_79+
            male80_84+
            male85p+
            female62_64+
            female65_66+
            female67_69+
            female70_74+
            female75_79+
            female80_84+
            female85p)*sharebg,
  white_nonh=white_nonh*sharebg,
  black_nonh=black_nonh*sharebg,
  asian_nonh=asian_nonh*sharebg,
  other_nonh=(total_nonh-(white_nonh+black_nonh+asian_nonh))*sharebg,   # "Other, non-Hisp is total non-Hisp minus white,black,Asian
  hispanic=total_hisp*sharebg,
  SFDU=(unit1d+
          unit1a+
          mobile+
          boat_RV_Van)*sharebg,
  MFDU=(unit2+
          unit3_4+
          unit5_9+
          unit10_19+
          unit20_49+
          unit50p)*sharebg,
  hh_own=(own1+own2+own3+own4+own5+own6+own7p)*sharebg,
  hh_rent=(rent1+rent2+rent3+rent4+rent5+rent6+rent7p)*sharebg,
  hh_size_1=(own1+rent1)*sharebg,
  hh_size_2=(own2+rent2)*sharebg,
  hh_size_3=(own3+rent3)*sharebg,
  hh_size_4_plus=(own4+
                   own5+
                   own6+
                   own7p+
                   rent4+
                   rent5+
                   rent6+
                   rent7p)*sharebg,
  hh_wrks_0=hhwrks0*sharetract,
  hh_wrks_1=hhwrks1*sharetract,
  hh_wrks_2=hhwrks2*sharetract,
  hh_wrks_3_plus=hhwrks3p*sharetract,
  hh_kids_yes=(ownkidsyes+rentkidsyes)*sharetract,
  hh_kids_no=(ownkidsno+rentkidsno)*sharetract,
  pers_occ_management   = (occ_m_manage    + occ_f_manage   )*sharebg,
  pers_occ_professional = (occ_m_prof_biz  + occ_f_prof_biz  +
                           occ_m_prof_comp + occ_f_prof_comp +
                           occ_m_prof_leg  + occ_f_prof_leg  +
                           occ_m_prof_edu  + occ_f_prof_edu  +
                           occ_m_prof_heal + occ_f_prof_heal)*sharebg,
  pers_occ_services     = (occ_m_svc_comm  + occ_f_svc_comm  +
                           occ_m_svc_ent   + occ_f_svc_ent   +
                           occ_m_svc_heal  + occ_f_svc_heal  +
                           occ_m_svc_fire  + occ_f_svc_fire  +
                           occ_m_svc_law   + occ_f_svc_law   +
                           occ_m_svc_pers  + occ_f_svc_pers  +
                           occ_m_svc_off   + occ_f_svc_off  )*sharebg,
  pers_occ_retail       = (occ_m_ret_eat   + occ_f_ret_eat   +
                           occ_m_ret_sales + occ_f_ret_sales)*sharebg,
  pers_occ_manual       = (occ_m_man_build + occ_f_man_build +
                           occ_m_man_nat   + occ_f_man_nat   +
                           occ_m_man_prod  + occ_f_man_prod )*sharebg,
  pers_occ_military     = (armedforces)*sharebg,
  gq_type_univ  =(gq_noninst_m_0017_univ +
                         gq_noninst_m_1864_univ +
                         gq_noninst_m_65p_univ  +
                         gq_noninst_f_0017_univ +
                         gq_noninst_f_1864_univ +
                         gq_noninst_f_65p_univ)*sharetract,
         gq_type_mil   =(gq_noninst_m_0017_mil  +
                         gq_noninst_m_1864_mil  +
                         gq_noninst_m_65p_mil   +
                         gq_noninst_f_0017_mil  +
                         gq_noninst_f_1864_mil  +
                         gq_noninst_f_65p_mil)*sharetract,
         gq_type_othnon=(gq_noninst_m_0017_oth  +
                         gq_noninst_m_1864_oth  +
                         gq_noninst_m_65p_oth   +
                         gq_noninst_f_0017_oth  +
                         gq_noninst_f_1864_oth  +
                         gq_noninst_f_65p_oth)*sharetract)

# Summarize to TAZ and select only variables of interest

temp0 <- workingdata %>%
  group_by(TAZ1454) %>%
  summarize(  TOTHH                   =sum(TOTHH),
              HHPOP                   =sum(HHPOP),
              EMPRES                  =sum(EMPRES),
              HHINCQ1                 =sum(HHINCQ1),
              HHINCQ2                 =sum(HHINCQ2),
              HHINCQ3                 =sum(HHINCQ3),
              HHINCQ4                 =sum(HHINCQ4),
              AGE0004                 =sum(AGE0004),
              AGE0519                 =sum(AGE0519),
              AGE2044                 =sum(AGE2044),
              AGE4564                 =sum(AGE4564),
              AGE65P                  =sum(AGE65P),
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

# Confirmed values for 2020 are:
    # Total regional HH pop is 7590783
    # Total regional non-institutional GQ pop is 126779
    # Total regional institutional pop is 48078
    # Total pop (including institutional pop) is 7765640
    # Total pop (excluding institutional pop) is 7717562
  
# Apply households by number of workers correction factors
# The initial table values are actually households by number of "commuters" (people at work - not sick, vacation - in the ACS reference week)
# This overstates 0-worker households and understates 3+-worker households. A correction needs to be applied.
# Correction factors are calculated in ACSPUMS_WorkerTotals_2017-2021_Comparisons.xls, in
# petrale\applications\travel_model_lu_inputs\2020\Workers
# 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7= Napa; 8=Sonoma; 9=Marin
# "counties" vector is defined below with this county order

counties  <- c(1,2,3,4,5,6,7,8,9)                             # Matching county values for factor ordering

workers0  <- c(0.75147,0.74299,0.68878,0.59029,0.80718,0.79450,0.70344,0.83817,0.81702)
workers1  <- c(1.05364,1.02063,1.04834,1.06543,1.01895,1.02327,1.09197,1.03080,1.05727)
workers2	<- c(1.06342,1.06356,1.05941,1.14105,1.07070,1.06588,1.08631,1.08274,1.06551)
workers3p	<- c(1.18711,1.18950,1.15641,1.27100,1.15972,1.20442,1.18671,1.10573,1.13854)


temp1 <- temp0 %>%
  left_join(.,PBA2015_county,by=c("TAZ1454"="ZONE")) %>% 
  mutate(
    hh_wrks_0      = hh_wrks_0*workers0[match(COUNTY,counties)], # Apply the above index values for correction factors
    hh_wrks_1      = hh_wrks_1*workers1[match(COUNTY,counties)],
    hh_wrks_2      = hh_wrks_2*workers2[match(COUNTY,counties)],
    hh_wrks_3_plus = hh_wrks_3_plus*workers3p[match(COUNTY,counties)]) 

# Sum constituent parts to compare with marginal totals
# Begin process of scaling constituent values so category subtotals match marginal totals for 2020

temp_rounded_adjusted <- temp1 %>%
  mutate (
    sum_age            = AGE0004 + AGE0519 + AGE2044  +AGE4564 + AGE65P,       # Person totals by age
    sum_groupquarters  = gq_type_univ + gq_type_mil + gq_type_othnon,          # GQ by type
    sum_tenure         = hh_own + hh_rent,                                     # Households by tenure
    sum_size           = hh_size_1 + hh_size_2 + hh_size_3 + hh_size_4_plus,   # Now housing totals
    sum_hhworkers      = hh_wrks_0 + hh_wrks_1 + hh_wrks_2 + hh_wrks_3_plus,   # HHs by number of workers
    sum_kids           = hh_kids_yes + hh_kids_no,                             # HHs by kids or not
    sum_income         = HHINCQ1 + HHINCQ2 + HHINCQ3 + HHINCQ4,                # HHs by income
    sum_empres         = pers_occ_management + pers_occ_professional+          # Employed residents by industry
      pers_occ_services + pers_occ_retail + pers_occ_manual + pers_occ_military,
    HHPOP              = round(HHPOP,0),                                        # Round and sum total pop from HH and GQ pop
    gqpop              = round(gqpop,0),
    TOTPOP             = HHPOP+gqpop, 
    sum_ethnicity      = white_nonh+black_nonh+asian_nonh+other_nonh+hispanic,
    
# Create inflation/deflation factors
# Empres takes a 2-step approach. The first step (init) scales the total empres to constituent parts (they likely already agree)
# Second step (empres_factor) scales 2017-2021 5-year totals to value that is the average of ACS 2019 and 2021 Table 23025 values
# The average of 2019 and 2021 is a proxy for ACS 2020 data that is missing due to Covid lack of data collection
# Values calculated in ACSPUMS_WorkerTotals_2017-2021_Comparisons.xls, with location provided above
    
    age_factor         = if_else(sum_age==0,0,TOTPOP/sum_age),
    gq_factor          = if_else(sum_groupquarters==0,0,gqpop/sum_groupquarters),
    tenure_factor      = if_else(sum_tenure==0,0,TOTHH/sum_tenure),
    size_factor        = if_else(sum_size==0,0,TOTHH/sum_size),
    hhworkers_factor   = if_else(sum_hhworkers==0,0,TOTHH/sum_hhworkers),
    kids_factor        = if_else(sum_kids==0,0,TOTHH/sum_kids),
    income_factor      = if_else(sum_income==0,0,TOTHH/sum_income),
    empres_init_factor = if_else(sum_empres==0,0,EMPRES/sum_empres),
    empres_factor      = case_when(
                         County_Name=="Alameda"            ~ empres_init_factor*0.98670,
                         County_Name=="Contra Costa"       ~ empres_init_factor*0.99733,
                         County_Name=="Marin"              ~ empres_init_factor*0.98121,
                         County_Name=="Napa"               ~ empres_init_factor*0.97815,
                         County_Name=="San Francisco"      ~ empres_init_factor*0.96432,
                         County_Name=="San Mateo"          ~ empres_init_factor*0.97861,
                         County_Name=="Santa Clara"        ~ empres_init_factor*0.98314,
                         County_Name=="Solano"             ~ empres_init_factor*0.99228,
                         County_Name=="Sonoma"             ~ empres_init_factor*0.99204
    ),
    ethnicity_factor   = if_else(sum_ethnicity==0,0,TOTPOP/sum_ethnicity),

# Apply factors to correct for scale up or down constituent parts to match marginal totals

    AGE0004               = AGE0004          * age_factor,         # Persons by age correction
    AGE0519               = AGE0519          * age_factor,  
    AGE2044               = AGE2044          * age_factor,  
    AGE4564               = AGE4564          * age_factor,
    AGE65P                = AGE65P           * age_factor,

    white_nonh            = white_nonh       * ethnicity_factor,  # Persons by ethnicity correction
    black_nonh            = black_nonh       * ethnicity_factor,
    asian_nonh            = asian_nonh       * ethnicity_factor,
    other_nonh            = other_nonh       * ethnicity_factor,
    hispanic              = hispanic         * ethnicity_factor,

    gq_type_univ          = gq_type_univ     * gq_factor,          # Group quarters by type
    gq_type_mil           = gq_type_mil      * gq_factor,
    gq_type_othnon        = gq_type_othnon   * gq_factor,

    hh_own                = hh_own           * tenure_factor,      # Households by tenure
    hh_rent               = hh_rent          * tenure_factor,      

    hh_size_1             = hh_size_1        * size_factor,        # Households by size
    hh_size_2             = hh_size_2        * size_factor,
    hh_size_3             = hh_size_3        * size_factor,
    hh_size_4_plus        = hh_size_4_plus   * size_factor,

    hh_wrks_0             = hh_wrks_0        * hhworkers_factor,   # Households by number of workers   
    hh_wrks_1             = hh_wrks_1        * hhworkers_factor,
    hh_wrks_2             = hh_wrks_2        * hhworkers_factor,
    hh_wrks_3_plus        = hh_wrks_3_plus   * hhworkers_factor,

    hh_kids_yes           = hh_kids_yes      * kids_factor,        # Households by presence of kids
    hh_kids_no            = hh_kids_no       * kids_factor,

    HHINCQ1               = HHINCQ1          * income_factor,      # Households by income  
    HHINCQ2               = HHINCQ2          * income_factor,
    HHINCQ3               = HHINCQ3          * income_factor,
    HHINCQ4               = HHINCQ4          * income_factor,

    EMPRES=EMPRES*empres_factor,                                   # Employed residents total then by occupation  
    pers_occ_management   = pers_occ_management   * empres_factor, 
    pers_occ_professional = pers_occ_professional * empres_factor,            
    pers_occ_services     = pers_occ_services     * empres_factor,
    pers_occ_retail       = pers_occ_retail       * empres_factor, 
    pers_occ_manual       = pers_occ_manual       * empres_factor,
    pers_occ_military     = pers_occ_military     * empres_factor) %>% 

# Round Data, remove sum variables and factors
# Add in population over age 62 variable that is also needed (but should not be rounded, so added at the end)
  
    select (-age_factor,-gq_factor,-tenure_factor, -size_factor,-hhworkers_factor,-kids_factor,-income_factor,-empres_init_factor,
            -empres_factor,-sum_age,-sum_groupquarters,-sum_size,-sum_hhworkers,-sum_kids,-sum_income,-sum_empres, 
            -sum_ethnicity,-ethnicity_factor) %>% 
    mutate_if(is.numeric,round,0) %>%
    mutate(SHPOP62P = if_else(TOTPOP==0,0,AGE62P/TOTPOP)) %>% 
 
# Scaling adjustments were done above, now make fix small variations due to rounding for precisely-matching totals
# Find max value in categorical data to adjust totals so they match univariate totals
# For example, the households by income across categories should sum to equal total HHs
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total

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
                             "hispanic")],                                           ties.method="first"))%>% 
    
# Now use max values determined above to find appropriate column for adjustment

   mutate(
    
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
  
  select(-max_age,-max_gq,-max_tenure,-max_size,-max_workers,-max_kids,-max_income,-max_occ, -max_eth)

### End of recoding

# Write out ethnic variables

ethnic <- temp_rounded_adjusted %>% 
  select(TAZ1454,hispanic, white_nonh,black_nonh,asian_nonh,other_nonh,TOTPOP, COUNTY, County_Name)

write.csv (ethnic,file = "TAZ1454_Ethnicity.csv",row.names = FALSE)

# Read in old PBA data sets and select variables for joining to new 2020 dataset
# Join 2020 employment data
# Bring in school and parking data from 2015 TAZ data 
# Add HHLDS variable (same as TOTHH), select new 2015 output

PBA2015_joiner <- PBA2015%>%
  select(ZONE,DISTRICT,SD,TOTACRE,RESACRE,CIACRE,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TOPOLOGY,TERMINAL, ZERO)

joined_15_20      <- left_join(PBA2015_joiner,temp_rounded_adjusted, by=c("ZONE"="TAZ1454")) # Join 2015 topology, parking, enrollment
joined_employment <- left_join(joined_15_20,employment_2020, by=c("ZONE"="TAZ1454"))        # Join employment

# Save R version of data for 2020 to later inflate to 2023

final_2020 <- joined_employment
save(final_2020,file="TAZ Land Use File 2020.rdata")

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
  select(TAZ,TOTHH,TOTPOP,hh_own,hh_rent,hh_size_1,hh_size_2,hh_size_3,hh_size_4_plus,hh_wrks_0,hh_wrks_1,hh_wrks_2,hh_wrks_3_plus,
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

# Output into Tableau-friendly format

PBA2015_long <- PBA2015 %>%
  mutate(gqpop=TOTPOP-HHPOP) %>% 
  left_join(.,PBA2015_county,by=c("ZONE","COUNTY")) %>% 
  left_join(.,superdistrict,by="DISTRICT") %>% 
  mutate(Year=2015) %>% 
  select(ZONE,DISTRICT,DISTRICT_NAME,COUNTY, County_Name,Year,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

New2020_long <- New2020 %>%
  left_join(.,PBA2015_county,by=c("ZONE","COUNTY")) %>% 
  left_join(.,superdistrict,by="DISTRICT") %>% 
  mutate(Year=2020) %>% 
  select(ZONE,DISTRICT,DISTRICT_NAME,COUNTY,County_Name,Year,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

write.csv(PBA2015_long,file.path(TM1,"2015","TAZ1454_2015_long.csv"),row.names = F)
write.csv(New2020_long,"TAZ1454_2020_long.csv",row.names = F)
