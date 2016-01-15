# Utility script to convert standard MTC TAZ data from CSV to DBF

library(foreign)

F_INPUT  = "input.csv"
F_OUTPUT = "output.dbf"

data_df <- read.table(file = F_INPUT, header = TRUE, sep = ",", stringsAsFactors = FALSE)

write.dbf(data_df, F_OUTPUT, factor2char = TRUE, max_nchar = 254)