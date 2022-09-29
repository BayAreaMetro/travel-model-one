#
# In order to run successfully, TM1 requires that all combinations of USE and
# non-zero TOLLCLASS in the input network have their time period and vehicle 
# class-specific tolls represented in the input tolls.csv file. This script 
# checks that all USE/TC combos are present in a given network's corresponding
# tolls.csv. 
#
# Any USE/TC combos found in the network but not the tolls.csv are assigned the 
# minimum toll of 3 cents per mile during the AM, MD, and PM periods. The Toll
# Designation file developed for the Next Gen Freeway Study is used to identify
# facility names and any mandatory S2 tolls. TC's with a mandatory S2 toll are
# assigned at a 50% discount (1.5 cents per mile)
#
# Any USE/TC combos found in the tolls.csv but not the network are dropped from
# the tolls.csv.
# 


library(dplyr)
library(foreign)
library(readxl)

# Load files

NETWORK_DIR <- "L:/Application/Model_One/NextGenFwys/Networks/NGF_Networks_02"
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

# Identify the unique USE/TOLLCLASS combinations in the tolls.csv

tolls_use_tc <- distinct(TOLLS_CSV, tollclass, use, .keep_all = TRUE)
tolls_use_tc <- filter(tolls_use_tc, tollclass != 0)
tolls_use_tc$use_tc <- paste("USE =", tolls_use_tc$use, "TC =",
                             tolls_use_tc$tollclass, sep = " ")

# Compare the USE/TC combos in the network and tolls.csv

missing_tc <- setdiff(net_use_tc$use_tc, tolls_use_tc$use_tc)
extra_tc <- setdiff(tolls_use_tc$use_tc, net_use_tc$use_tc)

# Drop the extra USE/TC combos from the tolls.csv

`%notin%` <- Negate(`%in%`)
new_tolls <- subset(tolls_use_tc, use_tc %notin% extra_tc)

# For any missing USE/TC combos, append the minimum tolls to the tolls.csv
# (using the tollclass designation file to identify the facility names and the 
# TC's that have mandatory S2 discounts)

min_tolls <- subset(net_use_tc, use_tc %in% missing_tc)
min_tolls <- min_tolls %>% left_join(TOLLCLASS_DES, by=c("TOLLCLASS"="tollclass"))

missing_des <- paste(subset(min_tolls, is.na(TOLLCLASS))$TOLLCLASS, collapse = ", ")

sink(LOG_OUTPUT)
print("Tolls.csv is missing the following USE/TOLLCLASS combos:")
print(missing_tc)
print("Tolls.csv includes the following extra USE/TOLLCLASS combos:")
print(extra_tc)
print("The following TOLLCLASS values are missing from the Tollclass Designation file:")
print(missing_des)
sink()

colnames(min_tolls) <- c("use", "tollclass", "use_tc", "facility_name", "s2toll_mandatory")
min_tolls$fac_index <- min_tolls$tollclass*1000 + min_tolls$use  # Calculate the facility index from the use and tollclass
min_tolls$tollseg <- rep(0, nrow(min_tolls))
min_tolls$tolltype <- rep("unknown", nrow(min_tolls))
min_tolls <- min_tolls %>% select("facility_name", "fac_index", "tollclass", 
                                  "tollseg", "tolltype", "use", "s2toll_mandatory")

min_toll_vals <- as.data.frame(matrix(0, nrow(min_tolls), (ncol(TOLLS_CSV)-6)))
colnames(min_toll_vals) <- colnames(TOLLS_CSV)[7:length(colnames(TOLLS_CSV))]

min_tolls <- cbind(min_tolls, min_toll_vals)

# Identify the fields that will be assigned the minimum toll of 3 cents/mile
min_col_names <- colnames(TOLLS_CSV)[grep("toll", colnames(TOLLS_CSV))]
min_col_names <- min_col_names[-grep("s2", min_col_names)]
min_col_names <- min_col_names[-grep("s3", min_col_names)]
min_col_names <- min_col_names[-grep("ea", min_col_names)]
min_col_names <- min_col_names[-grep("ev", min_col_names)]
min_col_names <- min_col_names[-grep("tollclass", min_col_names)]
min_col_names <- min_col_names[-grep("tollseg", min_col_names)]
min_col_names <- min_col_names[-grep("tolltype", min_col_names)]
min_col_names <- min_col_names[-grep("toll_flat", min_col_names)]

min_tolls[,min_col_names] <- .03

# Identify the S2 fields for tollclasses that have mandatory S2 tolls
s2_col_names <- colnames(TOLLS_CSV)[grep("s2", colnames(TOLLS_CSV))]
s2_col_names <- s2_col_names[-grep("ea", s2_col_names)]
s2_col_names <- s2_col_names[-grep("ev", s2_col_names)]

min_tolls[,s2_col_names] <- ifelse(is.na(min_tolls$s2toll_mandatory), 0, .015)

min_tolls <- subset(min_tolls, select= -c(s2toll_mandatory))

new_tolls <- subset(new_tolls, select= -c(use_tc))
new_tolls <- rbind(new_tolls, min_tolls)
new_tolls <- new_tolls[order(new_tolls$tollclass),]

file.rename(TOLLS_CSV_PATH, paste(NETWORK_DIR, "hwy", "tolls_old.csv", sep = "/"))
write.csv(new_tolls, paste(NETWORK_DIR, "hwy", "tolls.csv", sep = "/"), row.names = FALSE)