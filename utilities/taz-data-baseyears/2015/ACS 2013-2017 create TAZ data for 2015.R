# ACS 2013-2017 create TAZ data for 2015.R
# Create "2015" TAZ data from ACS 2013-2017 
# SI
# Updated 4/24/20 with new employment data

# Notes

# The working directory is set as the location of the script. All other paths in Petrale will be relative.

wd <- paste0(dirname(rstudioapi::getActiveDocumentContext()$path),"/")
setwd(wd)

"

1. ACS data here is downloaded for the 2013-2017 5-year dataset. The end year can be updated 
   by changing the *ACS_year* variable. 

2. ACS block group variables used in all instances where not suppressed. If suppressed at the block group 
   level, tract-level data used instead. Suppressed variables may change if ACS_year is changed. This 
   should be checked, as this change could cause the script not to work.

3. Group quarters data start with the decennial census data. There are some small TAZ-specific 
   additions from university growth that are incorporated in the script, and then TAZs are scaled up to match 
   ACS 2013-2017 county-level totals. 
   
"
# Import Libraries

suppressMessages(library(tidyverse))
library(tidycensus)
library(httr)

# Set up directories, import TAZ/census block equivalence, install census key, set ACS year,set CPI inflation

employment_2015_data           <- "M:/Data/BusinessData/Employment_by_TAZ_industry/BusinessData_2015_TAZ_industry_noincommute.csv"
school_2015_data               <- file.path(wd,"School Enrollment","tazData_enrollment.csv")

blockTAZ2010         <- "M:/Data/GIS layers/TM1_taz_census2010/block_to_TAZ1454.csv"
censuskey            <- readLines("M:/Data/Census/API/api-key.txt")
baycounties          <- c("01","13","41","55","75","81","85","95","97")
census_api_key(censuskey, install = TRUE, overwrite = TRUE)

ACS_year <- 2017
sf1_year <- 2010
ACS_product="5"
state="06"
CPI_current <- 274.92  # CPI value for 2017
CPI_reference <- 180.20 # CPI value for 2000
CPI_ratio <- CPI_current/CPI_reference # 2017 CPI/2000 CPI

USERPROFILE          <- gsub("\\\\","/", Sys.getenv("USERPROFILE"))
BOX_TM               <- file.path(USERPROFILE, "Box", "Modeling and Surveys")
PBA_TAZ_2010         <- file.path(BOX_TM, "Share Data",   "plan-bay-area-2040", "2010_06_003","tazData.csv")
parking_2015_data    <- file.path(BOX_TM,"Share Data", "plan-bay-area-2040", "2015_06_002", "tazData.csv")
PUMS2013_2017 = "M:/Data/Census/PUMS/PUMS 2013-17/pbayarea1317.Rdata"   # 2015 PUMS data for GQ adjustments

# County FIPS codes for ACS tract API calls

Alameda   <- "001"
Contra    <- "013"
Marin     <- "041"
Napa      <- "055"
Francisco <- "075"
Mateo     <- "081"
Clara     <- "085"
Solano    <- "095"
Sonoma    <- "097"

# Bring in PBA (2017) 2010 land use data for county equivalencies and later summaries
# 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7= Napa; 8=Sonoma; 9=Marin

PBA2010 <- read.csv(PBA_TAZ_2010,header=TRUE) 

PBA2010_county <- PBA2010 %>%                                    # Create and join TAZ/county equivalence
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


# Income table - Guidelines for HH income values used from ACS
"

    2000 income breaks 2017 CPI equivalent   Nearest 2017 ACS breakpoint
    ------------------ -------------------   ---------------------------
    $30,000            $45,769               $45,000
    $60,000            $91,538               $91,538* 
    $100,000           $152,564              $150,000
    ------------------ -------------------   ---------------------------

    * Because the 2017$ equivalent of $60,000 in 2000$ ($91,538) doesn't closely align with 2017 ACS income 
      categories, households within the $75,000-$99,999 category will be apportioned above and below $91,538. 
      Using the ACS 2013-2017 PUMS data, the share of households above $91,538 within the $75,000-$99,999 
      category is 0.3042492.That is, approximately 30 percent of HHs in the $75,000-$99,999 category will be 
      apportioned above this value (Q3) and 70 percent below it (Q2). The table below compares 2000$ and 2017$.

Household Income Category Equivalency, 2000$ and 2017$

          Year      Lower Bound     Upper Bound
          ----      ------------    -----------
HHINCQ1   2000      $-inf           $29,999
          2017      $-inf           $44,999
HHINCQ2   2000      $30,000         $59,999
          2017      $45,000         $91,537
HHINCQ3   2000      $60,000         $99,999
          2017      $91,538         $149,999
HHINCQ4   2000      $100,000        $inf
          2017      $150,000        $inf
          ----      -------------   -----------

"

shareabove91538 <- 0.3113032 # Use this value to later divvy up HHs in the 30-60k and 60-100k respective quartiles.

# Import ACS library for variable inspection

ACS_table <- load_variables(year=2017, dataset="acs5", cache=TRUE)

# Set up ACS block group and tract variables for later API download. 
# Block group calls broken up into 3 groups of <50 variables each, due to API limit
# Some variables skipped in sequence due to nesting

ACS_BG_variables1 <- paste0("B25009_001E,",     # Total HHs
                      "B11002_001E,",		# HH pop
                      
                      "B23025_004E,",   # Employed residents (employed residents is "employed" + "armed forces")
                      "B23025_006E,", 	# Armed forces
                      
                      "B19001_002E,",   # Household income 0 to $10k 
                      "B19001_003E,",		# Household income $10 to $15k
                      "B19001_004E,",		# Household income $15 to $20k
                      "B19001_005E,",		# Household income $20 to $25k
                      "B19001_006E,",		# Household income $25 to $30k
                      "B19001_007E,",		# Household income $30 to $35k
                      "B19001_008E,",		# Household income $35 to $40k
                      "B19001_009E,",		# Household income $40 to $45k
                      "B19001_010E,",		# Household income $45 to $50k
                      "B19001_011E,",		# Household income 50 to $60k
                      "B19001_012E,",		# Household income 60 to $75k
                      "B19001_013E,",		# Household income 75 to $100k
                      "B19001_014E,",		# Household income $100 to $1$25k
                      "B19001_015E,",		# Household income $1$25 to $150k
                      "B19001_016E,",		# Household income $150 to $200k
                      "B19001_017E,",		# Household income $200k+
                      
                      "B01001_003E,",   # male aged 0 to 4 
                      "B01001_004E,",		# male aged 5 to 9 
                      "B01001_005E,",		# male aged 10 to 14
                      "B01001_006E,",		# male aged 15 to 17
                      "B01001_007E,",		# male aged 18 to 19
                      "B01001_008E,",		# male aged 20 
                      "B01001_009E,",		# male aged 21 
                      "B01001_010E,",		# male aged 22 to 24 
                      "B01001_011E,",		# male aged 25 to 29 
                      "B01001_012E,",		# male aged 30 to 34 
                      "B01001_013E,",		# male aged 35 to 39 
                      "B01001_014E,",		# male aged 40 to 44 
                      "B01001_015E,",		# male aged 45 to 49 
                      "B01001_016E,",		# male aged 50 to 54 
                      "B01001_017E,",		# male aged 55 to 59 
                      "B01001_018E,",		# male aged 60 to 61 
                      "B01001_019E,",		# male aged 62 to 64 
                      "B01001_020E,",		# male aged 65 to 66 
                      "B01001_021E,",		# male aged 67 to 69 
                      "B01001_022E,",		# male aged 70 to 74 
                      "B01001_023E,",		# male aged 75 to 79 
                      "B01001_024E,",		# male aged 80 to 84 
                      "B01001_025E,",		# male aged 85+ 
                      "B01001_027E,",		# female aged 0 to 4 
                      "B01001_028E,",		# female aged 5 to 9 
                      "B01001_029E,",		# female aged 10 to 14
                      "B01001_030E,",		# female aged 15 to 17
                      "B01001_031E")		# female aged 18 to 19

ACS_BG_variables2 <- paste0("B01001_032E,",     # female aged 20  
                      "B01001_033E,",         	# female aged 21  
                      "B01001_034E,",		# female aged 22 to 24
                      "B01001_035E,",		# female aged 25 to 29
                      "B01001_036E,",		# female aged 30 to 34
                      "B01001_037E,",		# female aged 35 to 39
                      "B01001_038E,",		# female aged 40 to 44
                      "B01001_039E,",		# female aged 45 to 49
                      "B01001_040E,",		# female aged 50 to 54
                      "B01001_041E,",		# female aged 55 to 59
                      "B01001_042E,",		# female aged 60 to 61
                      "B01001_043E,",		# female aged 62 to 64
                      "B01001_044E,",		# female aged 65 to 66
                      "B01001_045E,",		# female aged 67 to 69
                      "B01001_046E,",		# female aged 70 to 74
                      "B01001_047E,",		# female aged 75 to 79
                      "B01001_048E,",		# female aged 80 to 84
                      "B01001_049E,",		# female aged 85+ 
                      
                      "B25024_002E,",   # 1 unit detached    
                      "B25024_003E,",		# 1 unit attached 
                      "B25024_004E,",		# 2 units
                      "B25024_005E,",		# 3 or 4 units
                      "B25024_006E,",		# 5 to 9 units
                      "B25024_007E,",		# 10 to 19 units
                      "B25024_008E,",		# 20 to 49 units
                      "B25024_009E,",		# 50+ units
                      "B25024_010E,",		# mobile homes
                      "B25024_011E,",		# boats, RVs, vans
                      
                      "B25009_003E,",           # own 1 person in HH 	     
                      "B25009_004E,",		# own 2 persons in HH 
                      "B25009_005E,",		# own 3 persons in HH 
                      "B25009_006E,",		# own 4 persons in HH 
                      "B25009_007E,",		# own 5 persons in HH 
                      "B25009_008E,",		# own 6 persons in HH 
                      "B25009_009E,",		# own 7+ persons in HH 
                      "B25009_011E,",		# rent 1 person in HH
                      "B25009_012E,",		# rent 2 persons in HH 
                      "B25009_013E,",		# rent 3 persons in HH 
                      "B25009_014E,",		# rent 4 persons in HH 
                      "B25009_015E,",		# rent 5 persons in HH 
                      "B25009_016E,",		# rent 6 persons in HH 
                      "B25009_017E")		# rent 7+ persons in HH
                      
                      # these skip some numbers since there are nested levels
ACS_BG_variables3 <- paste0("C24010_005E,", # Management
                      "C24010_006E,", # Business and financial
                      "C24010_007E,", # Computer, engineering, and science
                      "C24010_012E,", # community and social service
                      "C24010_013E,", # Legal
                      "C24010_014E,", # Education, training, and library
                      "C24010_015E,", # Arts, design, entertainment, sports, and media
                      "C24010_016E,", # Healthcare practitioners and technical
                      "C24010_020E,", # Healthcare support
                      "C24010_022E,", # Fire fighting and prevention, and other protectiv
                      "C24010_023E,", # Law enforcement workers
                      "C24010_024E,", # Food preparation and serving related
                      "C24010_025E,", # Building and grounds cleaning and maintenance
                      "C24010_026E,", # Personal care and service
                      "C24010_028E,", # Sales and related
                      "C24010_029E,", # Office and administrative support
                      "C24010_030E,", # Natural resources, construction, and maintenance
                      "C24010_034E,", # Production, transportation, and material moving
                      
                      "C24010_041E,", # Management
                      "C24010_042E,", # Business and financial
                      "C24010_043E,", # Computer, engineering, and science
                      "C24010_048E,", # community and social service
                      "C24010_049E,", # Legal
                      "C24010_050E,", # Education, training, and library
                      "C24010_051E,", # Arts, design, entertainment, sports, and media
                      "C24010_052E,", # Healthcare practitioners and technical
                      "C24010_056E,", # Healthcare support
                      "C24010_058E,", # Fire fighting and prevention, and other protectiv
                      "C24010_059E,", # Law enforcement workers
                      "C24010_060E,", # Food preparation and serving related
                      "C24010_061E,", # Building and grounds cleaning and maintenance
                      "C24010_062E,", # Personal care and service
                      "C24010_064E,", # Sales and related
                      "C24010_065E,", # Office and administrative support
                      "C24010_066E,", # Natural resources, construction, and maintenance
                      "C24010_070E,",  # Production, transportation, and material moving
                      
                      "B03002_003E,",   # White alone, not Hispanic
                      "B03002_004E,",   # Black alone, not Hispanic
                      "B03002_006E,",   # Asian alone, not Hispanic
                      "B03002_002E,",   # Total, not Hispanic
                      "B03002_012E")   # Total Hispanic
                      


ACS_tract_variables <-c(hhwrks0 = "B08202_002",     # 0-worker HH
                        hhwrks1 = "B08202_003",	    # 1-worker HH
                        hhwrks2 = "B08202_004",	    # 2-worker HH
                        hhwrks3p = "B08202_005",    # 3+-worker HH
                   
                        ownkidsyes = "B25012_003",  # Own with related kids under 18
                        rentkidsyes = "B25012_011", # Rent with related kids under 18
                        ownkidsno = "B25012_009",   # Own without related kids under 18
                        rentkidsno = "B25012_017"   # Rent without related kids under 18
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

# Function to make tract data API calls by county
# For a brief time, 2013-2017 API no longer supported vectorized county calls, and they had to be made individually
# TODO: Revert this process back to the API as the Census Bureau has fixed vectorized calls for BGs and tracts

f.tract.call <- function (baycounty){
                      get_acs(geography = "tract", variables = ACS_tract_variables,
                      state = "06", county=baycounty,
                      year=ACS_year,
                      output="wide",
                      survey = "acs5",
                      key = censuskey)
}

# Now make tract calls by county and concatenate all counties into a single file

Alameda_tracts <- f.tract.call(Alameda)
Contra_tracts <- f.tract.call(Contra)
Marin_tracts <- f.tract.call(Marin)
Napa_tracts <- f.tract.call(Napa)
Francisco_tracts <- f.tract.call(Francisco)
Mateo_tracts <- f.tract.call(Mateo)
Clara_tracts <- f.tract.call(Clara)
Solano_tracts <- f.tract.call(Solano)
Sonoma_tracts <- f.tract.call(Sonoma)
ACS_tract_raw <- rbind(Alameda_tracts,Contra_tracts,Marin_tracts,Napa_tracts,Francisco_tracts,
                       Mateo_tracts,Clara_tracts,Solano_tracts,Sonoma_tracts)

# Create index of Bay Area tracts to pass into block group API calls 
# 2013-2017 API no longer supports county->block group, and now relies on county -> tract -> block group calls

tract_index <- ACS_tract_raw %>%
  mutate(
    county=substr(GEOID,3,5),
    tract=substr(GEOID,6,11)
      ) %>%
  select(county,tract)

# Manual function for converting API calls into data frame (due to tidycensus not working for county -> block group downloads)
# The "geography_fields" argument helps convert relevant (variable, not geographic) columns to numeric format

f.data <- function(url,geography_fields){  
  furl <- content(RETRY("GET",url,times=10))         # Retry the API up to 10 times to overcome choking of API call
  for (i in 1:length(furl)){
    if (i==1) header <- furl [[i]]
    if (i==2){
      temp <- lapply(furl[[i]], function(x) ifelse(is.null(x), NA, x))
      output_data <- data.frame(temp, stringsAsFactors=FALSE)
      names (output_data) <- header
    }
    if (i>2){
      temp <- lapply(furl[[i]], function(x) ifelse(is.null(x), NA, x))
      tempdf <- data.frame(temp, stringsAsFactors=FALSE)
      names (tempdf) <- header
      output_data <- rbind (output_data,tempdf)
    }
  }
  for(j in 2:(ncol(output_data)-geography_fields)) {
    output_data[,j] <- as.numeric(output_data[,j])
  }
  return (output_data)
}

# Function for creating URLs to pass into tract -> block group API calls

f.url <- function (ACS_BG_variables,county,tract) {paste0("https://api.census.gov/data/",ACS_year,"/acs/acs",ACS_product,"?get=NAME,",
                                                   ACS_BG_variables,"&for=block%20group:*&in=state:",state,"%20county:",county,
                                                   "%20tract:",tract,"&key=",censuskey)}

# Create wrapper to either perform API calls or not depending on presence of cached block group data
# Block group calls done for all 1588 Bay Area tracts (done in 3 tranches because API limited to calls of 50 variables)
# The "4" in the call refers to the number of columns at the end of the API call devoted to geography (not numeric)
# Numeric values are changed by the f.data function from character to numeric
# Note that, because the API call process is so long, these data are also saved in the working directory (Petrale)
# Calls 1-3 are saved in "ACS 2013-2017 Block Group Vars1-3", respectively

# Call 1

if (file.exists("ACS 2013-2017 Block Group Vars1.csv")) {source("Import block group data.R")
  } else {                      # Wrapper checks for cached block group variables, then runs a script to import them
                                # Only checks for first of three BG files, but that should be sufficient
                                # Else run the API block group calls to retrieve the data
for(k in 1:nrow(tract_index)) {  
  if (k==1) {
    bg_df1 <- f.data(f.url(ACS_BG_variables1,tract_index[k,"county"],tract_index[k,"tract"]),4)
  }
  if (k>=2) {
    subsequent_df <- f.data(f.url(ACS_BG_variables1,tract_index[k,"county"],tract_index[k,"tract"]),4)
    bg_df1 <- rbind(bg_df1,subsequent_df)
  }
  if (k%%10==0) {print(paste(k, "tracts have been called for Call 1"))} # Monitor progress of this step, as it's long.
}

# Call 2

for(k in 1:nrow(tract_index)) {
  if (k==1) {
    bg_df2 <- f.data(f.url(ACS_BG_variables2,tract_index[k,"county"],tract_index[k,"tract"]),4)
  }
  if (k>=2) {
    subsequent_df <- f.data(f.url(ACS_BG_variables2,tract_index[k,"county"],tract_index[k,"tract"]),4)
    bg_df2 <- rbind(bg_df2,subsequent_df)
  }
  if (k%%10==0) {print(paste(k, "tracts have been called for Call 2"))} # Monitor progress of this step, as it's long.
}

# Call 3

for(k in 1:nrow(tract_index)) {
  if (k==1) {
    bg_df3 <- f.data(f.url(ACS_BG_variables3,tract_index[k,"county"],tract_index[k,"tract"]),4)
  }
  if (k>=2) {
    subsequent_df <- f.data(f.url(ACS_BG_variables3,tract_index[k,"county"],tract_index[k,"tract"]),4)
    bg_df3 <- rbind(bg_df3,subsequent_df)
  }
  if (k%%10==0) {print(paste(k, "tracts have been called for Call 3"))} # Monitor progress of this step, as it's long.
}
  
}                                   # End of wrapper

# Combine three data tranches into single data frame

ACS_BG_preraw <- left_join (bg_df1,bg_df2,by=c("NAME","state","county","block group","tract"))
ACS_BG_preraw <- left_join (ACS_BG_preraw,bg_df3,by=c("NAME","state","county","block group","tract"))


# Rename block group variables 
names(ACS_BG_preraw) <- str_replace_all(names(ACS_BG_preraw), c(" " = "_"))   # Remove space in variable name, 
                                                                              # "block group" to "block_group"
ACS_BG_raw <- ACS_BG_preraw %>%
  rename(	 tothhE = B25009_001E,        #Total HHs, HH pop
           hhpopE = B11002_001E,
           
           employedE = B23025_004E,     # Employed residents is employedE +armed forcesE
           armedforcesE = B23025_006E, 
           
           hhinc0_10E = B19001_002E,    # Income categories 
           hhinc10_15E = B19001_003E,
           hhinc15_20E = B19001_004E,
           hhinc20_25E = B19001_005E,
           hhinc25_30E = B19001_006E,
           hhinc30_35E = B19001_007E,
           hhinc35_40E = B19001_008E,
           hhinc40_45E = B19001_009E,
           hhinc45_50E = B19001_010E,
           hhinc50_60E = B19001_011E,
           hhinc60_75E = B19001_012E,
           hhinc75_100E = B19001_013E,
           hhinc100_125E = B19001_014E,
           hhinc125_150E = B19001_015E,
           hhinc150_200E = B19001_016E,
           hhinc200pE = B19001_017E,
           
           male0_4E = B01001_003E,      # Age data
           male5_9E = B01001_004E,
           male10_14E = B01001_005E,
           male15_17E = B01001_006E,
           male18_19E = B01001_007E,
           male20E = B01001_008E,
           male21E = B01001_009E,
           male22_24E = B01001_010E,
           male25_29E = B01001_011E,
           male30_34E = B01001_012E,
           male35_39E = B01001_013E,
           male40_44E = B01001_014E,
           male45_49E = B01001_015E,
           male50_54E = B01001_016E,
           male55_59E = B01001_017E,
           male60_61E = B01001_018E,
           male62_64E = B01001_019E,
           male65_66E = B01001_020E,
           male67_69E = B01001_021E,
           male70_74E = B01001_022E,
           male75_79E = B01001_023E,
           male80_84E = B01001_024E,
           male85pE = B01001_025E,
           female0_4E = B01001_027E,
           female5_9E = B01001_028E,
           female10_14E = B01001_029E,
           female15_17E = B01001_030E,
           female18_19E = B01001_031E,
           female20E = B01001_032E,
           female21E = B01001_033E,
           female22_24E = B01001_034E,
           female25_29E = B01001_035E,
           female30_34E = B01001_036E,
           female35_39E = B01001_037E,
           female40_44E = B01001_038E,
           female45_49E = B01001_039E,
           female50_54E = B01001_040E,
           female55_59E = B01001_041E,
           female60_61E = B01001_042E,
           female62_64E = B01001_043E,
           female65_66E = B01001_044E,
           female67_69E = B01001_045E,
           female70_74E = B01001_046E,
           female75_79E = B01001_047E,
           female80_84E = B01001_048E,
           female85pE = B01001_049E,
           
           white_nonhE = B03002_003E,    # Demographic data 
           black_nonhE = B03002_004E,    
           asian_nonhE = B03002_006E,    
           total_nonhE = B03002_002E,    
           total_hispE = B03002_012E,    
           
           unit1dE = B25024_002E,       # Single and multi-family dwelling unit data
           unit1aE = B25024_003E,
           unit2E = B25024_004E,
           unit3_4E = B25024_005E,
           unit5_9E = B25024_006E,
           unit10_19E = B25024_007E,
           unit20_49E = B25024_008E,
           unit50pE = B25024_009E,
           mobileE = B25024_010E,
           boat_RV_VanE = B25024_011E,
           
           own1E = B25009_003E,        # Household size data
           own2E = B25009_004E,
           own3E = B25009_005E,
           own4E = B25009_006E,
           own5E = B25009_007E,
           own6E = B25009_008E,
           own7pE = B25009_009E,
           rent1E = B25009_011E,
           rent2E = B25009_012E,
           rent3E = B25009_013E,
           rent4E = B25009_014E,
           rent5E = B25009_015E,
           rent6E = B25009_016E,
           rent7pE = B25009_017E,
           
           # these skip some numbers since there are nested levels
           occ_m_manageE    = C24010_005E, # Management
           occ_m_prof_bizE  = C24010_006E, # Business and financial
           occ_m_prof_compE = C24010_007E, # Computer, engineering, and science
           occ_m_svc_commE  = C24010_012E, # community and social service
           occ_m_prof_legE  = C24010_013E, # Legal
           occ_m_prof_eduE  = C24010_014E, # Education, training, and library
           occ_m_svc_entE   = C24010_015E, # Arts, design, entertainment, sports, and media
           occ_m_prof_healE = C24010_016E, # Healthcare practitioners and technical
           occ_m_svc_healE  = C24010_020E, # Healthcare support
           occ_m_svc_fireE  = C24010_022E, # Fire fighting and prevention, and other protectiv
           occ_m_svc_lawE   = C24010_023E, # Law enforcement workers
           occ_m_ret_eatE   = C24010_024E, # Food preparation and serving related
           occ_m_man_buildE = C24010_025E, # Building and grounds cleaning and maintenance
           occ_m_svc_persE  = C24010_026E, # Personal care and service
           occ_m_ret_salesE = C24010_028E, # Sales and related
           occ_m_svc_offE   = C24010_029E, # Office and administrative support
           occ_m_man_natE   = C24010_030E, # Natural resources, construction, and maintenance
           occ_m_man_prodE  = C24010_034E, # Production, transportation, and material moving
           
           occ_f_manageE    = C24010_041E, # Management
           occ_f_prof_bizE  = C24010_042E, # Business and financial
           occ_f_prof_compE = C24010_043E, # Computer, engineering, and science
           occ_f_svc_commE  = C24010_048E, # community and social service
           occ_f_prof_legE  = C24010_049E, # Legal
           occ_f_prof_eduE  = C24010_050E, # Education, training, and library
           occ_f_svc_entE   = C24010_051E, # Arts, design, entertainment, sports, and media
           occ_f_prof_healE = C24010_052E, # Healthcare practitioners and technical
           occ_f_svc_healE  = C24010_056E, # Healthcare support
           occ_f_svc_fireE  = C24010_058E, # Fire fighting and prevention, and other protectiv
           occ_f_svc_lawE   = C24010_059E, # Law enforcement workers
           occ_f_ret_eatE   = C24010_060E, # Food preparation and serving related
           occ_f_man_buildE = C24010_061E, # Building and grounds cleaning and maintenance
           occ_f_svc_persE  = C24010_062E, # Personal care and service
           occ_f_ret_salesE = C24010_064E, # Sales and related
           occ_f_svc_offE   = C24010_065E, # Office and administrative support
           occ_f_man_natE   = C24010_066E, # Natural resources, construction, and maintenance
           occ_f_man_prodE  = C24010_070E  # Production, transportation, and material moving
        ) %>%
  mutate(
    GEOID=paste0(state,county,tract,block_group),
    tract=paste0(state,county,tract)
  )



# Make decennial census calls

sf1_tract_raw <- get_decennial(geography = "tract", variables = sf1_tract_variables,
                            state = "06", county=baycounties,
                            year=sf1_year,
                            output="wide",
                            key=censuskey)

# Join 2013-2017 ACS block group and tract variables to combined_block file
# Combine and collapse ACS categories to get land use control totals, as appropriate
# Apply block share of 2013-2017 ACS variables using block/block group and block/tract shares of 2010 total population
# Note that "E" on the end of each variable is appended by tidycensus package to denote "estimate"

workingdata <- left_join(combined_block,ACS_BG_raw, by=c("blockgroup"="GEOID","tract"))          
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
             (hhinc75_100E*(1-shareabove91538)))*sharebg, # Apportions HHs below $91,538 within $75,000-$100,000
  HHINCQ3=((hhinc75_100E*shareabove91538)+                # Apportions HHs above $91,538 within $75,000-$100,000
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
  white_nonh=white_nonhE*sharebg,
  black_nonh=black_nonhE*sharebg,
  asian_nonh=asian_nonhE*sharebg,
  other_nonh=(total_nonhE-(white_nonhE+black_nonhE+asian_nonhE))*sharebg,   # "Other, non-Hisp is total non-Hisp minus white,black,Asian
  hispanic=total_hispE*sharebg,
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
                           occ_m_man_prodE  + occ_f_man_prodE )*sharebg,
  pers_occ_military     = (armedforcesE)*sharebg
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

temp0 <- workingdata %>%
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
              gqpop2010            =gq_type_univ+gq_type_mil+gq_type_othnon,
              pers_occ_management  =sum(pers_occ_management),
              pers_occ_professional=sum(pers_occ_professional),
              pers_occ_services    =sum(pers_occ_services),
              pers_occ_retail      =sum(pers_occ_retail),
              pers_occ_manual      =sum(pers_occ_manual),
              pers_occ_military    =sum(pers_occ_military),
              white_nonh           =sum(white_nonh),
              black_nonh           =sum(black_nonh),
              asian_nonh           =sum(asian_nonh),
              other_nonh           =sum(other_nonh),   
              hispanic             =sum(hispanic))
  

# Correct GQ population to sum to ACS PUMS 2015 total, outlined in Steps 1-3 below
"
1. Add in additional GQ population for growth 2010-2015 from M. Reilly file, 
petrale/applications/travel_model_lu_inputs/2015/Group Quarters/gq_add_00051015.csv:

Location                                                  	TAZ1454    extra_gq
------------------------------------------------------    	-------    --------
Kennedy Grad at Stanford					                            353		      436
Munger East AND Ng House at Stanford	                   	    354        	120
Metropolitan, Channing Bowditch, Maximo Commons at UCB	  	  1008 		    348
------------------------------------------------------    	-------    --------

2. Sum total 2010 GQ to compare to ACS PUMS 2013-2017 GQ

3. Create factor corrections to apply to TAZs; apply them 
"

# Create data frame for added GQ pop (only three TAZs have empirically-collected data for updates)
# Join to temp0 file and add GQ pop, then remove column

added_gq <- data.frame(TAZ1454=1:1454,extra_gq=0) %>%
  mutate(extra_gq=case_when(
    TAZ1454 == 353  ~ 436,                              
    TAZ1454 == 354  ~ 120,
    TAZ1454 == 1008 ~ 348,
    TRUE ~ extra_gq                                    # All other values kept at zero
  ))

temp1 <- left_join(temp0,added_gq, by="TAZ1454") %>%
  mutate(gqpop2010=gqpop2010+extra_gq) %>%
  select(-extra_gq)

# Sum GQ 2010 population by county

sum_gq10 <- left_join(temp1,PBA2010_county,by=c("TAZ1454"="ZONE")) %>%
  group_by(County_Name,COUNTY) %>%
  summarize(sum10=sum(gqpop2010)) 

# Bring in 2013-2017 PUMS and perform the same summary, then join with the 2010 data
# Create GQ adjustment factor

load (PUMS2013_2017) 

sum_gq15 <- pbayarea1317 %>%
  mutate(County_Name=as.character(County_Name)) %>%           # Bug fix to override County_Name as factor
  filter(RELP==17) %>%
  group_by(County_Name) %>%
  summarize(sum15=sum(PWGTP))

gqcounty1015 <- left_join(sum_gq10,sum_gq15,by="County_Name") %>%
  mutate(gqfactor=sum15/sum10) %>%                            # Factor is ratio of GQ15/GQ10, by county  
  arrange(COUNTY)                                             # Sort by COUNTY variable, so factors in correct order

gqfactor <- gqcounty1015$gqfactor                             # Ordered vector of factors to apply   
counties  <- c(1,2,3,4,5,6,7,8,9)                             # Matching county values for factor ordering
 
# Apply GQ factor to reconcile adjust 2010 decennial with 2013-2017 PUMS

temp2 <- left_join(temp1,PBA2010_county,by=c("TAZ1454"="ZONE")) %>%
  mutate(
    gqpop = gqpop2010*gqfactor[match(COUNTY,counties)]
  )


# Apply households by number of workers correction factors
# Values from ACS2013-2017_PUMS2013-2017_HH_Worker_Correction_Factors.csv, in
# petrale\applications\travel_model_lu_inputs\2015\Workers
# 1=San Francisco; 2=San Mateo; 3=Santa Clara; 4=Alameda; 5=Contra Costa; 6=Solano; 7= Napa; 8=Sonoma; 9=Marin
# "counties" vector is defined above with this county order

workers0  <- c(0.72439,0.71045,0.65234,0.61093,0.81432,0.79221,0.71026,0.81646,0.81952)
workers1  <- c(1.05499,1.01626,1.04675,1.06364,1.02079,1.03487,1.06679,1.04652,1.04665)
workers2  <- c(1.07740,1.08066,1.08075,1.15069,1.07611,1.10324,1.08483,1.06913,1.06500)
workers3p <- c(1.21757,1.21119,1.20479,1.34201,1.15367,1.11889,1.26523,1.15975,1.18261)

temp3 <- temp2 %>%
  mutate(
    hh_wrks_0      = hh_wrks_0*workers0[match(COUNTY,counties)], # Apply the above index values for correction factors
    hh_wrks_1      = hh_wrks_1*workers1[match(COUNTY,counties)],
    hh_wrks_2      = hh_wrks_2*workers2[match(COUNTY,counties)],
    hh_wrks_3_plus = hh_wrks_3_plus*workers3p[match(COUNTY,counties)]) 

# Zero out ages for people in TAZ 1439 (San Quentin)
# Begin process of scaling constituent values so category subtotals match marginal totals

### Beginning of recoding

temp_rounded_adjusted <- temp3 %>%
  mutate(
    AGE0004 = if_else(TAZ1454==1439,0,AGE0004),                # Zero out population components in San Quentin TAZ
    AGE0519 = if_else(TAZ1454==1439,0,AGE0519),                # All institutional group quarters
    AGE2044 = if_else(TAZ1454==1439,0,AGE2044),                # Total pop and gq pop already 0
    AGE4564 = if_else(TAZ1454==1439,0,AGE4564),
    AGE65P =  if_else(TAZ1454==1439,0,AGE65P),
    AGE62P =  if_else(TAZ1454==1439,0,AGE62P)
  ) %>% 
  
# Sum constituent parts to compare with marginal totals
  
  mutate (
    sum_age            = AGE0004 + AGE0519 + AGE2044  +AGE4564 + AGE65P,       # First person totals by age
    sum_groupquarters  = gq_type_univ + gq_type_mil + gq_type_othnon,          # GQ by type
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
    
    age_factor         = if_else(sum_age==0,0,TOTPOP/sum_age),
    gq_factor          = if_else(sum_groupquarters==0,0,gqpop/sum_groupquarters),
    size_factor        = if_else(sum_size==0,0,TOTHH/sum_size),
    hhworkers_factor   = if_else(sum_hhworkers==0,0,TOTHH/sum_hhworkers),
    kids_factor        = if_else(sum_kids==0,0,TOTHH/sum_kids),
    income_factor      = if_else(sum_income==0,0,TOTHH/sum_income),
    empres_factor      = if_else(sum_empres==0,0,EMPRES/sum_empres),
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

    pers_occ_management   = pers_occ_management   * empres_factor, # Employed residents by occupation
    pers_occ_professional = pers_occ_professional * empres_factor,            
    pers_occ_services     = pers_occ_services     * empres_factor,
    pers_occ_retail       = pers_occ_retail       * empres_factor, 
    pers_occ_manual       = pers_occ_manual       * empres_factor,
    pers_occ_military     = pers_occ_military     * empres_factor) %>% 

# Round Data, remove sum variables and factors
# Add in population over age 62 variable that is also needed (but should not be rounded, so added at the end)
  
    select (-age_factor,-gq_factor,-size_factor,-hhworkers_factor,-kids_factor,-income_factor,-empres_factor,
            -sum_age,-sum_groupquarters,-sum_size,-sum_hhworkers,-sum_kids,-sum_income,-sum_empres, -sum_ethnicity,
            -ethnicity_factor) %>% 
    mutate_if(is.numeric,round,0) %>%
    mutate(SHPOP62P = if_else(TOTPOP==0,0,AGE62P/TOTPOP)) %>% 
 
# Scaling adjustments were done above, now make fix small variations due to rounding for precisely-matching totals
# Find max value in categorical data to adjust totals so they match univariate totals
# For example, the households by income across categories should sum to equal total HHs
# If unequal, the largest constituent cell is adjusted up or down such that the category sums match the marginal total

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
  
  select(-max_age,-max_gq,-max_size,-max_workers,-max_kids,-max_income,-max_occ, -max_eth)

### End of recoding

# Write out ethnic variables

ethnic <- temp_rounded_adjusted %>% 
  select(TAZ1454,hispanic, white_nonh,black_nonh,asian_nonh,other_nonh,TOTPOP, COUNTY, County_Name)

write.csv (ethnic,file = "TAZ1454_Ethnicity.csv",row.names = FALSE)

# Read in old PBA data sets and select variables for joining to new 2015 dataset
# Bring in updated 2015 employment for joining
# Bring in school and parking data from PBA 2040, 2015 TAZ data 
# Add HHLDS variable (same as TOTHH), select new 2015 output

PBA2010_joiner <- PBA2010%>%
  select(ZONE,DISTRICT,SD,TOTACRE,RESACRE,CIACRE,AREATYPE,TOPOLOGY,ZERO,sftaz)

employment_2015 <- read.csv(employment_2015_data,header=TRUE) 

parking_2015 <- read.csv(parking_2015_data, header=TRUE) %>% 
  select(ZONE,PRKCST,OPRKCST,TERMINAL)

school_2015 <- read.csv(school_2015_data, header=TRUE) %>% 
  select(ZONE,HSENROLL,COLLFTE,COLLPTE)

joined_10_15      <- left_join(PBA2010_joiner,temp_rounded_adjusted, by=c("ZONE"="TAZ1454")) # Join 2010 topology
joined_parking    <- left_join(joined_10_15,parking_2015, by="ZONE")                         # Join PBA 2015 parking
joined_school     <- left_join(joined_parking, school_2015, by="ZONE")                       # Join schools
joined_employment <- left_join(joined_school,employment_2015, by=c("ZONE"="TAZ1454"))        # Join employment
 
New2015 <- joined_employment %>%
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

# Optional code below for other analyses

# ------------------------------------------------------------------------------------------------

"# Output into Tableau-friendly format

Tableau2015 <- New2015 %>%
  select(ZONE,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value2015,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)

Tableau2010 <- PBA2010 %>%
  select(ZONE,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop) %>%
  gather(Variable,Value2010,TOTHH,HHPOP,TOTPOP,EMPRES,SFDU,MFDU,HHINCQ1,HHINCQ2,HHINCQ3,HHINCQ4,SHPOP62P,TOTEMP,AGE0004,AGE0519,AGE2044,AGE4564,AGE65P,RETEMPN,FPSEMPN,HEREMPN,AGREMPN,
         MWTEMPN,OTHEMPN,PRKCST,OPRKCST,HSENROLL,COLLFTE,COLLPTE,gqpop)"

#Tableau10_15 <- left_join(Tableau2010,Tableau2015,by = c("ZONE","Variable"))

#write.csv(Tableau10_15, "Tableau_2010_2015_Comparison.csv", row.names = FALSE, quote = T)


"RMWG_Summary <- New2015 %>%
  mutate(housing_units=SFDU+MFDU) %>% 
  group_by(COUNTY) %>% 
  summarize(population=sum(TOTPOP),households=sum(TOTHH),units=sum(housing_units),group=sum(gqpop),jobs=sum(TOTEMP),
            residents=sum(EMPRES))"


# write.csv(RMWG_Summary, "RMWG_Summary.csv", row.names = FALSE, quote = T)
            

