# Utility script to convert standard MTC TAZ data from CSV to DBF

library(foreign)
library(dplyr)

F_INPUT   <- Sys.getenv("F_INPUT")  # The location of the input and output file
F_OUTPUT  <- Sys.getenv("F_OUTPUT")

# switch slashes around
F_INPUT   <- gsub("\\\\","/",F_INPUT)
F_OUTPUT  <- gsub("\\\\","/",F_OUTPUT)

print(paste0("F_INPUT  = [",F_INPUT, "]\n"))
print(paste0("F_OUTPUT = [",F_OUTPUT,"]\n"))

data_df <- read.table(file = F_INPUT, header = TRUE, sep = ",", stringsAsFactors = FALSE)

for (colname in c("AGREMPN","FPSEMPN","HEREMPN","RETEMPN","MWTEMPN","OTHEMPN","TOTEMP",
                  "HHINCQ1","HHINCQ2","HHINCQ3","HHINCQ4","HHPOP","TOTHH","GQPOP","RES_UNITS","TOTPOP","MFDU","SFDU","EMPRES",
                  "AGE0004","AGE0519","AGE2044","AGE4564","AGE65P","gq_type_univ","gq_type_mil","gq_type_othnon","gq_tot_pop",
                  "hh_size_1","hh_size_2","hh_size_3","hh_size_4_plus","county",
                  "hh_wrks_0","hh_wrks_1","hh_wrks_2","hh_wrks_3_plus","hh_kids_no","hh_kids_yes",
                  "district","topology","zero","hsenroll","collpte","collfte")) {
    if (colname %in% colnames(data_df)) {
        data_df[,colname] <- as.integer(data_df[,colname])
    }
}
print(head(data_df))
write.dbf(data_df, F_OUTPUT, factor2char = TRUE, max_nchar = 254)