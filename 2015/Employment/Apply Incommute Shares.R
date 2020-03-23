# Apply Incommute Shares.R
# Apply incommute shares to employment data
# March 22, 2020
# SI

# Import Libraries

suppressMessages(library(tidyverse))
library(readxl)

# Set working directory

wd <- "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment"
setwd(wd)

# Location of data files

employment_data     = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/taz_esri_lodes_nets032320.xlsx"
incommute_data      = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/2012-2016 CTPP Places to Superdistrict Equivalency.xlsx"
industry_share_data = "C:/Users/sisrael/Documents/GitHub/petrale/applications/travel_model_lu_inputs/2015/Employment/ACS 2013-2017 Incommute by Industry.xlsx"

# Bring in employment data

employment        <- read_excel (employment_data,sheet="Summary_SingleHeader") 
incommute_eq      <- read_excel (incommute_data,sheet="TAZ Incommute Equivalence") 
incommute_share   <- read_excel (incommute_data,sheet="Comp_SD Incommute Equivalence")
industry_share    <- read_excel (industry_share_data,sheet="Ind_Incommute_Share")


