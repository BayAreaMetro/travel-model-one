# Utility script to convert standard MTC TAZ data from CSV to DBF

library(foreign)

F_INPUT   <- Sys.getenv("F_INPUT")  # The location of the input and output file
F_OUTPUT  <- Sys.getenv("F_OUTPUT")

# switch slashes around
F_INPUT   <- gsub("\\\\","/",F_INPUT)
F_OUTPUT  <- gsub("\\\\","/",F_OUTPUT)

print(paste0("F_INPUT  = [",F_INPUT, "]\n"))
print(paste0("F_OUTPUT = [",F_OUTPUT,"]\n"))

data_df <- read.table(file = F_INPUT, header = TRUE, sep = ",", stringsAsFactors = FALSE)

write.dbf(data_df, F_OUTPUT, factor2char = TRUE, max_nchar = 254)