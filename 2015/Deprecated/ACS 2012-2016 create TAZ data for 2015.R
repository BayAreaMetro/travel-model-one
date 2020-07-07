
# ACS 2012-2016 create TAZ data for 2015.R
# Create "2015" TAZ data from ACS 2012-2016 
# SI
# October 25, 2018

# Notes
"

1. ACS data here is downloaded for the 2012-2016 5-year dataset. The end year can be updated 
   by changing the *ACS_year* variable. 

2. ACS block group variables used in all instances where not suppressed. If suppressed at the block group 
   level, tract-level data used instead. Suppressed variables may change if ACS_year is changed. This 
   should be checked, as this change could cause the script not to work.

"
# Import Libraries

suppressMessages(library(dplyr))
library(tidycensus)

# Set up directories, import TAZ/block equivalence, install census key, set ACS year,set CPI inflation
# X is mapped to MainModelShare for Shimon
# Z is MainModelShare for Others
if (Sys.getenv("USERNAME") == "SIsrael"){
  drive		       <- "X:/"
} else {
  drive                <- "Z:/"
}

wd                   <- paste0(drive,"petrale/output/")
employment_2015_data <- paste0(drive,"petrale/basemap/2015_employment_TAZ1454.csv")
setwd(wd)


blockTAZ2010         <- "M:/Data/GIS layers/TM1_taz_census2010/block_to_TAZ1454.csv"
censuskey            <- readLines("M:/Data/Census/API/api-key.txt")
baycounties          <- c("01","13","41","55","75","81","85","95","97")
census_api_key(censuskey, install = TRUE, overwrite = TRUE)

ACS_year <- 2016
sf1_year <- 2010
CPI_current <- 266.34  # CPI value for 2016
CPI_reference <- 180.20 # CPI value for 2000
CPI_ratio <- CPI_current/CPI_reference # 2016 CPI/2000 CPI

USERPROFILE          <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys", "Development")
PBA_TAZ_2010         <- file.path(BOX_TM, "Share Data",   "plan-bay-area-2040", "2010_06_003","tazData.csv")
school_parking_2015_data <- file.path(BOX_TM,"Share Data", "plan-bay-area-2040", "2015_06_002", "tazData.csv")


# Income table - Guidelines for HH income values used from ACS
"

    2000 income breaks 2016 CPI equivalent   Nearest 2016 ACS breakpoint
    ------------------ -------------------   ---------------------------
    $30,000            $44,341               $45,000
    $60,000            $88,681               $88,681* 
    $100,000           $147,802              $150,000
    ------------------ -------------------   ---------------------------

    * Because the 2016$ equivalent of $60,000 in 2000$ ($88,681) doesn't closely align with 2016 ACS income 
      categories, households within the $75,000-$99,999 category will be apportioned above and below $88,681. 
      Using the ACS 2012-2016 PUMS data, the share of households above $88,681 within the $75,000-$99,999 
      category is 0.4155574.That is, approximately 42 percent of HHs in the $75,000-$99,999 category will be 
      apportioned above this value (Q3) and 58 percent below it (Q2). The table below compares 2000$ and 2016$.

Household Income Category Equivalency, 2000$ and 2016$

          Year      Lower Bound     Upper Bound
          ----      ------------    -----------
HHINCQ1   2000      $-inf           $29,999
          2016      $-inf           $44,999
HHINCQ2   2000      $30,000         $59,999
          2016      $45,000         $88,680
HHINCQ3   2000      $60,000         $99,999
          2016      $88,681         $149,999
HHINCQ4   2000      $100,000        $inf
          2016      $150,000        $inf
          ----      -------------   -----------

"

shareabove88681 <- 0.4155574 # Use this value to later divvy up HHs in the 30-60k and 60-100k respective quartiles

# Import ACS library for variable inspection

ACS_table <- load_variables(year=2016, dataset="acs5", cache=TRUE)

# Set up ACS block group and tract variables for later API download. 

ACS_BG_variables <- c(tothh = "B25009_001",        #Total HHs, HH pop
                      hhpop = "B11002_001",

                      employed = "B23025_004",     # Employed residents is "employed" + "armed forces"
                      armedforces = "B23025_006", 
                   
                      #total_income = "B19001_001",
                      hhinc0_10 = "B19001_002",    # Income categories 
                      hhinc10_15 = "B19001_003",
                      hhinc15_20 = "B19001_004",
                      hhinc20_25 = "B19001_005",
                      hhinc25_30 = "B19001_006",
                      hhinc30_35 = "B19001_007",
                      hhinc35_40 = "B19001_008",
                      hhinc40_45 = "B19001_009",
                      hhinc45_50 = "B19001_010",
                      hhinc50_60 = "B19001_011",
                      hhinc60_75 = "B19001_012",
                      hhinc75_100 = "B19001_013",
                      hhinc100_125 = "B19001_014",
                      hhinc125_150 = "B19001_015",
                      hhinc150_200 = "B19001_016",
                      hhinc200p = "B19001_017",
                   
                      male0_4 = "B01001_003",      # Age data
                      male5_9 = "B01001_004",
                      male10_14 = "B01001_005",
                      male15_17 = "B01001_006",
                      male18_19 = "B01001_007",
                      male20 = "B01001_008",
                      male21 = "B01001_009",
                      male22_24 = "B01001_010",
                      male25_29 = "B01001_011",
                      male30_34 = "B01001_012",
                      male35_39 = "B01001_013",
                      male40_44 = "B01001_014",
                      male45_49 = "B01001_015",
                      male50_54 = "B01001_016",
                      male55_59 = "B01001_017",
                      male60_61 = "B01001_018",
                      male62_64 = "B01001_019",
                      male65_66 = "B01001_020",
                      male67_69 = "B01001_021",
                      male70_74 = "B01001_022",
                      male75_79 = "B01001_023",
                      male80_84 = "B01001_024",
                      male85p = "B01001_025",
                      female0_4 = "B01001_027",
                      female5_9 = "B01001_028",
                      female10_14 = "B01001_029",
                      female15_17 = "B01001_030",
                      female18_19 = "B01001_031",
                      female20 = "B01001_032",
                      female21 = "B01001_033",
                      female22_24 = "B01001_034",
                      female25_29 = "B01001_035",
                      female30_34 = "B01001_036",
                      female35_39 = "B01001_037",
                      female40_44 = "B01001_038",
                      female45_49 = "B01001_039",
                      female50_54 = "B01001_040",
                      female55_59 = "B01001_041",
                      female60_61 = "B01001_042",
                      female62_64 = "B01001_043",
                      female65_66 = "B01001_044",
                      female67_69 = "B01001_045",
                      female70_74 = "B01001_046",
                      female75_79 = "B01001_047",
                      female80_84 = "B01001_048",
                      female85p = "B01001_049",
                   
                      unit1d = "B25024_002",       # Single and multi-family dwelling unit data
                      unit1a = "B25024_003",
                      unit2 = "B25024_004",
                      unit3_4 = "B25024_005",
                      unit5_9 = "B25024_006",
                      unit10_19 = "B25024_007",
                      unit20_49 = "B25024_008",
                      unit50p = "B25024_009",
                      mobile = "B25024_010",
                      boat_RV_Van = "B25024_011",
                   
                      own1 = "B25009_003",        # Household size data
                      own2 = "B25009_004",
                      own3 = "B25009_005",
                      own4 = "B25009_006",
                      own5 = "B25009_007",
                      own6 = "B25009_008",
                      own7p = "B25009_009",
                      rent1 = "B25009_011",
                      rent2 = "B25009_012",
                      rent3 = "B25009_013",
                      rent4 = "B25009_014",
                      rent5 = "B25009_015",
                      rent6 = "B25009_016",
                      rent7p = "B25009_017",
                      
                      # these skip some numbers since there are nested levels
                      occ_m_manage    ="C24010_005", # Management
                      occ_m_prof_biz  ="C24010_006", # Business and financial
                      occ_m_prof_comp ="C24010_007", # Computer, engineering, and science
                      occ_m_svc_comm  ="C24010_012", # community and social service
                      occ_m_prof_leg  ="C24010_013", # Legal
                      occ_m_prof_edu  ="C24010_014", # Education, training, and library
                      occ_m_svc_ent   ="C24010_015", # Arts, design, entertainment, sports, and media
                      occ_m_prof_heal ="C24010_016", # Healthcare practitioners and technical
                      occ_m_svc_heal  ="C24010_020", # Healthcare support
                      occ_m_svc_fire  ="C24010_022", # Fire fighting and prevention, and other protective service workers
                      occ_m_svc_law   ="C24010_023", # Law enforcement workers
                      occ_m_ret_eat   ="C24010_024", # Food preparation and serving related
                      occ_m_man_build ="C24010_025", # Building and grounds cleaning and maintenance
                      occ_m_svc_pers  ="C24010_026", # Personal care and service
                      occ_m_ret_sales ="C24010_028", # Sales and related
                      occ_m_svc_off   ="C24010_029", # Office and administrative support
                      occ_m_man_nat   ="C24010_030", # Natural resources, construction, and maintenance
                      occ_m_man_prod  ="C24010_034", # Production, transportation, and material moving

                      occ_f_manage    ="C24010_041", # Management
                      occ_f_prof_biz  ="C24010_042", # Business and financial
                      occ_f_prof_comp ="C24010_043", # Computer, engineering, and science
                      occ_f_svc_comm  ="C24010_048", # community and social service
                      occ_f_prof_leg  ="C24010_049", # Legal
                      occ_f_prof_edu  ="C24010_050", # Education, training, and library
                      occ_f_svc_ent   ="C24010_051", # Arts, design, entertainment, sports, and media
                      occ_f_prof_heal ="C24010_052", # Healthcare practitioners and technical
                      occ_f_svc_heal  ="C24010_056", # Healthcare support
                      occ_f_svc_fire  ="C24010_058", # Fire fighting and prevention, and other protective service workers
                      occ_f_svc_law   ="C24010_059", # Law enforcement workers
                      occ_f_ret_eat   ="C24010_060", # Food preparation and serving related
                      occ_f_man_build ="C24010_061", # Building and grounds cleaning and maintenance
                      occ_f_svc_pers  ="C24010_062", # Personal care and service
                      occ_f_ret_sales ="C24010_064", # Sales and related
                      occ_f_svc_off   ="C24010_065", # Office and administrative support
                      occ_f_man_nat   ="C24010_066", # Natural resources, construction, and maintenance
                      occ_f_man_prod  ="C24010_070"  # Production, transportation, and material moving
                      )
                   
        
ACS_tract_variables <-c(hhwrks0 = "B08202_002",     # Households by number of workers
                        hhwrks1 = "B08202_003",
                        hhwrks2 = "B08202_004",
                        hhwrks3p = "B08202_005",
                   
                        ownkidsyes = "B25012_003",  # Presence of related kids under 18, by tenure
                        rentkidsyes = "B25012_011", 
                        ownkidsno = "B25012_009",
                        rentkidsno = "B25012_017"
                        )

sf1_table <- load_variables(year=2010, dataset="sf1", cache=TRUE)

sf1_tract_variables <-
  c(gq_noninst_m_0017_univ = "P043010",
    gq_noninst_m_0017_mil  = "P043011",
    gq_noninst_m_0017_oth  = "P043012",
    gq_noninst_m_1864_univ = "P043020",
    gq_noninst_m_1864_mil  = "P043021",
    gq_noninst_m_1864_oth  = "P043022",
    gq_noninst_m_65p_univ  = "P043030",
    gq_noninst_m_65p_mil   = "P043031",
    gq_noninst_m_65p_oth   = "P043032",
    gq_noninst_f_0017_univ = "P043041",
    gq_noninst_f_0017_mil  = "P043042",
    gq_noninst_f_0017_oth  = "P043043",
    gq_noninst_f_1864_univ = "P043051",
    gq_noninst_f_1864_mil  = "P043052",
    gq_noninst_f_1864_oth  = "P043053",
    gq_noninst_f_65p_univ  = "P043061",
    gq_noninst_f_65p_mil   = "P043062",
    gq_noninst_f_65p_oth   = "P043063")

# Bring in 2010 block/TAZ equivalency, create block group ID and tract ID fields for later joining to ACS data

blockTAZ <- read.csv(blockTAZ2010,header=TRUE) %>% mutate(      
  blockgroup = paste0("0",substr(GEOID10,1,11)),
  tract = paste0("0",substr(GEOID10,1,10))) 

# Summarize block population by block group and tract 

blockTAZBG <- blockTAZ %>% 
  group_by(blockgroup) %>%
  summarize(BGTotal=sum(block_POPULATION))
  
blockTAZTract <- blockTAZ %>% 
  group_by(tract) %>%
  summarize(TractTotal=sum(block_POPULATION))

# Create 2010 block share of total population for block/block group and block/tract, append to comnbined_block file
# Be mindful of divide by zero error associated with 0-pop block groups and tracts

combined_block <- left_join(blockTAZ,blockTAZBG,by="blockgroup") %>% mutate(
  sharebg=if_else(block_POPULATION==0,0,block_POPULATION/BGTotal))

combined_block <- left_join(combined_block,blockTAZTract,by="tract") %>% mutate(
  sharetract=if_else(block_POPULATION==0,0,block_POPULATION/TractTotal))

# Peform ACS calls for raw block group and tract data

ACS_BG_raw <- get_acs(geography = "block group", variables = ACS_BG_variables,
                 state = "06", county=baycounties,
                 year=ACS_year,
                 output="wide",
                 survey = "acs5")

ACS_tract_raw <- get_acs(geography = "tract", variables = ACS_tract_variables,
                      state = "06", county=baycounties,
                      year=ACS_year,
                      output="wide",
                      survey = "acs5")

sf1_tract_raw <- get_decennial(geography = "tract", variables = sf1_tract_variables,
                            state = "06", county=baycounties,
                            year=sf1_year,
                            output="wide")

# Join 2016 ACS block group and tract variables to combined_block file
# Combine and collapse ACS categories to get land use control totals, as appropriate
# Apply block share of 2016 ACS variables using block/block group and block/tract shares of 2010 total population
# Note that "E" on the end of each variable is appended by tidycensus package to denote "estimate"

workingdata <- left_join(combined_block,ACS_BG_raw, by=c("blockgroup"="GEOID"))
workingdata <- left_join(workingdata,ACS_tract_raw, by=c("tract"="GEOID"))%>% mutate(
  TOTHH=tothhE*sharebg,
  HHPOP=hhpopE*sharebg,
  EMPRES=(employedE+armedforcesE)*sharebg,
  HHINCQ1=(hhinc0_10E+
             hhinc10_15E+
             hhinc15_20E+
             hhinc20_25E+
             hhinc25_30E+
             hhinc30_35E+
             hhinc35_40E+
             hhinc40_45E)*sharebg,
  HHINCQ2=(hhinc45_50E+
             hhinc50_60E+
             hhinc60_75E+
             (hhinc75_100E*(1-shareabove88681)))*sharebg, # Apportions HHs below $88,681 within $75,000-$100,000
  HHINCQ3=((hhinc75_100E*shareabove88681)+                # Apportions HHs above $88,681 within $75,000-$100,000
             hhinc100_125E+
             hhinc125_150E)*sharebg,
  HHINCQ4=(hhinc150_200E+hhinc200pE)*sharebg,
  AGE0004=(male0_4E+female0_4E)*sharebg,
  AGE0519=(male5_9E+
             male10_14E+
             male15_17E+
             male18_19E+
             female5_9E+
             female10_14E+
             female15_17E+
             female18_19E)*sharebg,
  AGE2044=(male20E+
             male21E+
             male22_24E+
             male25_29E+
             male30_34E+
             male35_39E+
             male40_44E+
             female20E+
             female21E+
             female22_24E+
             female25_29E+
             female30_34E+
             female35_39E+
             female40_44E)*sharebg,
  AGE4564=(male45_49E+
             male50_54E+
             male55_59E+
             male60_61E+
             male62_64E+
             female45_49E+
             female50_54E+
             female55_59E+
             female60_61E+
             female62_64E)*sharebg,
  AGE65P=(male65_66E+
            male67_69E+
            male70_74E+
            male75_79E+
            male80_84E+
            male85pE+
            female65_66E+
            female67_69E+
            female70_74E+
            female75_79E+
            female80_84E+
            female85pE)*sharebg,
  AGE62P=(male62_64E+
            male65_66E+
            male67_69E+
            male70_74E+
            male75_79E+
            male80_84E+
            male85pE+
            female62_64E+
            female65_66E+
            female67_69E+
            female70_74E+
            female75_79E+
            female80_84E+
            female85pE)*sharebg,
  SFDU=(unit1dE+
          unit1aE+
          mobileE+
          boat_RV_VanE)*sharebg,
  MFDU=(unit2E+
          unit3_4E+
          unit5_9E+
          unit10_19E+
          unit20_49E+
          unit50pE)*sharebg,
  hh_size_1=(own1E+rent1E)*sharebg,
  hh_size_2=(own2E+rent2E)*sharebg,
  hh_size_3=(own3E+rent3E)*sharebg,
  hh_size_4_plus=(own4E+
                   own5E+
                   own6E+
                   own7pE+
                   rent4E+
                   rent5E+
                   rent6E+
                   rent7pE)*sharebg,
  hh_wrks_0=hhwrks0E*sharetract,
  hh_wrks_1=hhwrks1E*sharetract,
  hh_wrks_2=hhwrks2E*sharetract,
  hh_wrks_3_plus=hhwrks3pE*sharetract,
  hh_kids_yes=(ownkidsyesE+rentkidsyesE)*sharetract,
  hh_kids_no=(ownkidsnoE+rentkidsnoE)*sharetract,
  pers_occ_management   = (occ_m_manageE    + occ_f_manageE   )*sharebg,
  pers_occ_professional = (occ_m_prof_bizE  + occ_f_prof_bizE  +
                           occ_m_prof_compE + occ_f_prof_compE +
                           occ_m_prof_legE  + occ_f_prof_legE  +
                           occ_m_prof_eduE  + occ_f_prof_eduE  +
                           occ_m_prof_healE + occ_f_prof_healE)*sharebg,
  pers_occ_services     = (occ_m_svc_commE  + occ_f_svc_commE  +
                           occ_m_svc_entE   + occ_f_svc_entE   +
                           occ_m_svc_healE  + occ_f_svc_healE  +
                           occ_m_svc_fireE  + occ_f_svc_fireE  +
                           occ_m_svc_lawE   + occ_f_svc_lawE   +
                           occ_m_svc_persE  + occ_f_svc_persE  +
                           occ_m_svc_offE   + occ_f_svc_offE  )*sharebg,
  pers_occ_retail       = (occ_m_ret_eatE   + occ_f_ret_eatE   +
                           occ_m_ret_salesE + occ_f_ret_salesE)*sharebg,
  pers_occ_manual       = (occ_m_man_buildE + occ_f_man_buildE +
                           occ_m_man_natE   + occ_f_man_natE   +
                           occ_m_man_prodE  + occ_f_man_prodE )*sharebg
)
# sf1
workingdata <- left_join(workingdata,sf1_tract_raw, by=c("tract"="GEOID")) %>%
  mutate(gq_type_univ  =(gq_noninst_m_0017_univ +
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

temp <- workingdata %>%
  group_by(TAZ1454) %>%
  summarize(  TOTHH=sum(TOTHH),
              HHPOP=sum(HHPOP),
              EMPRES=sum(EMPRES),
              HHINCQ1=sum(HHINCQ1),
              HHINCQ2=sum(HHINCQ2),
              HHINCQ3=sum(HHINCQ3),
              HHINCQ4=sum(HHINCQ4),
              AGE0004=sum(AGE0004),
              AGE0519=sum(AGE0519),
              AGE2044=sum(AGE2044),
              AGE4564=sum(AGE4564),
              AGE65P=sum(AGE65P),
              SFDU=sum(SFDU),
              MFDU=sum(MFDU),
              hh_size_1=sum(hh_size_1),
              hh_size_2=sum(hh_size_2),
              hh_size_3=sum(hh_size_3),
              hh_size_4_plus=sum(hh_size_4_plus),
              hh_wrks_0=sum(hh_wrks_0),
              hh_wrks_1=sum(hh_wrks_1),
              hh_wrks_2=sum(hh_wrks_2),
              hh_wrks_3_plus=sum(hh_wrks_3_plus),
              hh_kids_yes=sum(hh_kids_yes),
              hh_kids_no=sum(hh_kids_no),
              AGE62P=sum(AGE62P),
              gq_type_univ         =sum(gq_type_univ),
              gq_type_mil          =sum(gq_type_mil),
              gq_type_othnon       =sum(gq_type_othnon),
              gqpop                =gq_type_univ+gq_type_mil+gq_type_othnon,
              pers_occ_management  =sum(pers_occ_management),
              pers_occ_professional=sum(pers_occ_professional),
              pers_occ_services    =sum(pers_occ_services),
              pers_occ_retail      =sum(pers_occ_retail),
              pers_occ_manual      =sum(pers_occ_manual),
              pers_occ_military    =sum(gq_type_mil)
              ) %>%
  mutate(TOTPOP = HHPOP+gqpop)

# Round data, find max value in categorical data to adjust totals so they match univariate totals
# For example, the households by income across categories should sum to equal total HHs
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total
# Add in population over age 62 variable that's also needed (but shouldn't be rounded, so added at the end)

temp_rounded <- temp %>%
  mutate_if(is.numeric,round,0) %>%
  mutate (
    max_pop    = max.col(.[c("HHPOP","gqpop")],                                      ties.method="first"),
    max_income = max.col(.[c("HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4")],              ties.method="first"),
    max_age    = max.col(.[c("AGE0004","AGE0519","AGE2044","AGE4564","AGE65P")],     ties.method="first"),
    max_size   = max.col(.[c("hh_size_1","hh_size_2","hh_size_3","hh_size_4_plus")], ties.method="first"),
    max_workers= max.col(.[c("hh_wrks_0","hh_wrks_1","hh_wrks_2","hh_wrks_3_plus")], ties.method="first"),
    max_kids   = max.col(.[c("hh_kids_yes","hh_kids_no")],                           ties.method="first"),
    SHPOP62P   =if_else(TOTPOP==0,0,AGE62P/TOTPOP)
    ) 

# Now use max values determined above to find appropriate column for adjustment

temp_rounded_adjusted <- temp_rounded %>% mutate(
  # Balance HH and GQ pop
  HHPOP = if_else(max_pop==1,HHPOP+(TOTPOP-(HHPOP+gqpop)),HHPOP),
  gqpop = if_else(max_pop==2,gqpop+(TOTPOP-(HHPOP+gqpop)),gqpop),
  # Balance population by age
  AGE0004 = if_else(max_age==1,AGE0004+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE0004),
  AGE0519 = if_else(max_age==2,AGE0519+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE0519),
  AGE2044 = if_else(max_age==3,AGE2044+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE2044),
  AGE4564 = if_else(max_age==4,AGE4564+(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE4564),
  AGE65P  = if_else(max_age==5,AGE65P +(TOTPOP-(AGE0004+AGE0519+AGE2044+AGE4564+AGE65P)),AGE65P),
  # Balance HH income categories
  HHINCQ1 = if_else(max_income==1,HHINCQ1+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ1),
  HHINCQ2 = if_else(max_income==2,HHINCQ2+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ2),
  HHINCQ3 = if_else(max_income==3,HHINCQ3+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ3),
  HHINCQ4 = if_else(max_income==4,HHINCQ4+(TOTHH-(HHINCQ1+HHINCQ2+HHINCQ3+HHINCQ4)),HHINCQ4),
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
  hh_kids_no  = if_else(max_kids==2,hh_kids_no +(TOTHH-(hh_kids_yes+hh_kids_no)),hh_kids_no)
  ) %>%
  select(-max_pop,-max_income,-max_age,-max_size,-max_workers,-max_kids,-AGE62P)
  

# Read in 2010 data and select variables for joining to 2015 data
# Bring in updated 2015 employment for joining
# Bring in school and parking data from PBA 2040, 2015 TAZ data 
# Join "2015" census-derived data to 2010/2015 reused variables and 2015 employment
# Add HHLDS variable (same as TOTHH), select new 2015 output

PBA2010 <- read.csv(PBA_TAZ_2010,header=TRUE) 
PBA2010_joiner <- PBA2010%>%
  select(ZONE,DISTRICT,SD,COUNTY,TOTACRE,RESACRE,CIACRE,AREATYPE,TOPOLOGY,ZERO,sftaz)

employment_2015 <- read.csv(employment_2015_data,header=TRUE) %>%
  rename(TOTEMP=EMPNUM,HEREMPN=HEREEMPN)               # Rename total employment and HEREMPN variables to match

school_parking_2015 <- read.csv(school_parking_2015_data, header=TRUE) %>% 
  select(ZONE,HSENROLL,COLLFTE,COLLPTE,PRKCST,OPRKCST,TERMINAL)

joined_10_15 <- left_join(PBA2010_joiner,temp_rounded_adjusted, by=c("ZONE"="TAZ1454"))
joined_10_15_employment <- left_join(joined_10_15,employment_2015, by=c("ZONE"="TAZ1454"))

New2015 <- left_join(joined_10_15_employment,school_parking_2015, by="ZONE")%>% 
  mutate(hhlds=TOTHH) %>%
  select(ZONE,DISTRICT,SD,COUNTY,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,TOTACRE,
         RESACRE,CIACRE,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,AREATYPE,HSENROLL,COLLFTE,COLLPTE,TERMINAL,TOPOLOGY,ZERO,hhlds,sftaz,
         gqpop)


# Summarize ACS and employment data by superdistrict for both 2010 and 2015

summed10 <- PBA2010 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=sum(gqpop))

summed15 <- New2015 %>%
  group_by(DISTRICT) %>%
  summarize(TOTHH=sum(TOTHH),HHPOP=sum(HHPOP),TOTPOP=sum(TOTPOP),EMPRES=sum(EMPRES),SFDU=sum(SFDU),MFDU=sum(MFDU),
            HHINCQ1=sum(HHINCQ1),HHINCQ2=sum(HHINCQ2),HHINCQ3=sum(HHINCQ3),HHINCQ4=sum(HHINCQ4),TOTEMP=sum(TOTEMP),
            AGE0004=sum(AGE0004),AGE0519=sum(AGE0519),AGE2044=sum(AGE2044),AGE4564=sum(AGE4564),AGE65P=sum(AGE65P),
            RETEMPN=sum(RETEMPN),FPSEMPN=sum(FPSEMPN),HEREMPN=sum(HEREMPN),AGREMPN=sum(AGREMPN),MWTEMPN=sum(MWTEMPN),
            OTHEMPN=sum(OTHEMPN),HSENROLL=sum(HSENROLL),COLLFTE=sum(COLLFTE),COLLPTE=sum(COLLPTE),gqpop=sum(gqpop))

# Export new 2015 data, 2010 and 2015 district summary data

write.csv(New2015, "TAZ1454 2015 Land Use.csv", row.names = FALSE, quote = T)
write.csv(summed10, "TAZ1454 2010 District Summary.csv", row.names = FALSE, quote = T)
write.csv(summed15, "TAZ1454 2015 District Summary.csv", row.names = FALSE, quote = T)

# Select out PopSim variables and export to separate csv

popsim_vars <- temp_rounded_adjusted %>% 
  rename(TAZ=TAZ1454,gq_tot_pop=gqpop)%>%
  select(TAZ,TOTHH,TOTPOP,hh_size_1,hh_size_2,hh_size_3,hh_size_4_plus,hh_wrks_0,hh_wrks_1,hh_wrks_2,hh_wrks_3_plus,
         hh_kids_no,hh_kids_yes,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,
         gq_tot_pop,gq_type_univ,gq_type_mil,gq_type_othnon)

write.csv(popsim_vars, "TAZ1454 2015 Popsim Vars.csv", row.names = FALSE, quote = T)

# region popsim vars
popsim_vars_region <- popsim_vars %>% 
  mutate(REGION=1) %>%
  group_by(REGION) %>%
  summarize(gq_num_hh_region=sum(gq_tot_pop))

write.csv(popsim_vars_region, "TAZ1454 2015 Popsim Vars Region.csv", row.names = FALSE, quote = T)

# county popsim vars
popsim_vars_county <- joined_10_15 %>%
  group_by(COUNTY) %>% summarize(
    pers_occ_management  =sum(pers_occ_management),
    pers_occ_professional=sum(pers_occ_professional),
    pers_occ_services    =sum(pers_occ_services),
    pers_occ_retail      =sum(pers_occ_retail),
    pers_occ_manual      =sum(pers_occ_manual),
    pers_occ_military    =sum(pers_occ_military))

write.csv(popsim_vars_county, "TAZ1454 2015 Popsim Vars County.csv", row.names = FALSE, quote = T)



