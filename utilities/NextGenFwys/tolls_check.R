
# Script to identify inconsistencies between freeflow networks and their 
# corresponding tolls.csv files.

library(dplyr)
library(foreign)
library(readxl)

# Load files

NETWORK_DIR <- "L:/Application/Model_One/NextGenFwys/Networks/NGF_Networks_NoProject_03/net_2035_NextGenFwy_NoProject_03"
NETWORK_DBF_PATH <- paste(NETWORK_DIR, "shapefile", "network_links.dbf", sep = "/")
TOLLS_CSV_PATH <- paste(NETWORK_DIR, "hwy", "tolls.csv", sep = "/")
TOLLCLASS_DES_PATH <- "C:/Users/natchison/Documents/GitHub/travel-model-one/utilities/NextGenFwys/TOLLCLASS_Designations.xlsx"

NETWORK_DBF <- read.dbf(NETWORK_DBF_PATH)
TOLLS_CSV <- read.csv(TOLLS_CSV_PATH)
TOLLCLASS_DES <- read_xlsx(TOLLCLASS_DES_PATH)
colnames(TOLLCLASS_DES)[colnames(TOLLCLASS_DES) == "facility_name"] <- 
  "facility_name_toll_des"

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

# Create new tolls.csv with minimum tolls

da_col_names <- colnames(TOLLS_CSV)[grep("da", colnames(TOLLS_CSV))]
da_col_names <- da_col_names[-grep("ea", da_col_names)]
da_col_names <- da_col_names[-grep("ev", da_col_names)]

s2_col_names <- colnames(TOLLS_CSV)[grep("s2", colnames(TOLLS_CSV))]
s2_col_names <- s2_col_names[-grep("ea", s2_col_names)]
s2_col_names <- s2_col_names[-grep("ev", s2_col_names)]

min_tolls <- subset(TOLLS_CSV, toll_flat == 0)
min_tolls <- min_tolls %>% left_join(TOLLCLASS_DES, by=c("tollclass"))

min_tolls[,da_col_names] <- .03
min_tolls[,s2_col_names] <- ifelse(is.na(min_tolls$s2toll_mandatory), 0, .015)
min_tolls$facility_name <- min_tolls$facility_name_toll_des
min_tolls <- subset(min_tolls, select = -c(facility_name_toll_des, s2toll_mandatory))

new_tolls <- subset(TOLLS_CSV, toll_flat == 1)
new_tolls <- rbind(new_tolls, min_tolls)

new_tolls$use_tc <- paste("USE =", new_tolls$use, "TC =", 
                          new_tolls$tollclass, sep = " ")
`%notin%` <- Negate(`%in%`)
new_tolls <- subset(new_tolls, use_tc %notin% extra_tc)
new_tolls <- subset(new_tolls, select = -c(use_tc))

new_tolls <- new_tolls[order(new_tolls$tollclass),]

# Write new_tolls as tolls.csv and save the original tolls.csv as "tolls_old.csv"
write.csv(TOLLS_CSV, paste(NETWORK_DIR, "hwy", "tolls_old.csv", sep = "/"), row.names = FALSE)
write.csv(new_tolls, paste(NETWORK_DIR, "hwy", "tolls.csv", sep = "/"), row.names = FALSE)
