
# Script to identify inconsistencies between freeflow networks and their 
# corresponding tolls.csv files.

library(dplyr)
library(foreign)
library(readxl)

# Load files

NETWORK_DIR <- "L:/Application/Model_One/NextGenFwys/Networks/NGF_Networks_NoProject_03/092222 Build/net_2035_NextGenFwy"
NETWORK_DBF_PATH <- paste(NETWORK_DIR, "shapefile", "network_links.dbf", sep = "/")
TOLLS_CSV_PATH <- paste(NETWORK_DIR, "hwy", "tolls.csv", sep = "/")
TOLLCLASS_DES_PATH <- "C:/Users/natchison/Documents/GitHub/travel-model-one/utilities/NextGenFwys/TOLLCLASS_Designations.xlsx"

NETWORK_DBF <- read.dbf(NETWORK_DBF_PATH)
TOLLS_CSV <- read.csv(TOLLS_CSV_PATH)
TOLLCLASS_DES <- read_xlsx(TOLLCLASS_DES_PATH)

# Identify the unique USE/TOLLCLASS combinations in the network
net_use_tc <- unique(NETWORK_DBF[c("USE", "TOLLCLASS")])
net_use_tc <- filter(net_use_tc, TOLLCLASS != 0)
net_use_tc$use_tc <- paste("USE =", net_use_tc$USE, "TC =",
                           net_use_tc$TOLLCLASS, sep=" ")

# Verify that all USE/TOLLCLASS combos are in tolls.csv

tolls_use_tc <- unique(TOLLS_CSV[c("use", "tollclass")])
tolls_use_tc <- filter(tolls_use_tc, tollclass != 0)
tolls_use_tc$use_tc <- paste("USE =", tolls_use_tc$use, "TC =",
                            tolls_use_tc$tollclass, sep = " ")

missing_tc <- setdiff(net_use_tc$use_tc, tolls_use_tc$use_tc)
extra_tc <- setdiff(tolls_use_tc$use_tc, net_use_tc$use_tc)

print(paste("Tolls.csv is missing the following USE/TOLLCLASS combos:",
            paste(missing_tc, collapse = ", "), sep = " "))
print(paste("Tolls.csv includes the following extra USE/TOLLCLASS combos:",
            paste(extra_tc, collapse = ", "), sep = " "))