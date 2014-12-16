library(RODBC)

# Model run code
MODEL_RUN  <- "2010_03_YYY"
# Location of the core summaries from the model run
SOURCE_DIR <- paste0("C:/Users/lzorn/Documents/", MODEL_RUN, "/core_summaries/")
# ODBC Connection name
ODBC_CONNECTION <- "VMT Shares"
# SQL Server Table Prefix
TABLE_PREFIX <- "[lzorn]"

print(paste("Connecting to ODBC connection",ODBC_CONNECTION))
cat("Enter UID     : ")
ODBC_UID <- readLines(con="stdin",1)
cat("Enter Password: ")
ODBC_PWD <- readLines(con="stdin",1)

#### Connect to the SQL Server via ODBC ####
# 1. Download ODBC driver (http://www.microsoft.com/en-us/download/details.aspx?id=36434)
# 2. Search Windows ODBC --> 'Set up data sources (ODBC)
# 3. Add ODBC Driver 11 for SQL Server connection, name connection "VMT Shares"
connection <- odbcConnect(ODBC_CONNECTION, ODBC_UID, ODBC_PWD)

#### Load AutoTripsVMT_personsHomeWork.rdata ####
# Load the data we calculated as part of core_summaries
full_filename = file.path(SOURCE_DIR,"AutoTripsVMT_personsHomeWork.rdata")
print(paste("Reading",full_filename))
load(full_filename)
AutoTripsVMT_personsHomeWork <- model_summary
remove(model_summary)

# Define table name #
phw_tablename <- paste0("personsHomeWork_",MODEL_RUN)
full_phw_tablename <- paste0(TABLE_PREFIX,".[",phw_tablename,"]")

# Save it
save_start <- proc.time()
retcode <- sqlSave(connection, AutoTripsVMT_personsHomeWork, phw_tablename)
save_end <- proc.time()
print(paste("Saved",full_phw_tablename,"in:"))
print(save_end-save_start)

#### Load AutoTripsVMT_perOrigDestHomeWork.rdata ####
# Load the data we calculated as part of core_summaries
full_filename = file.path(SOURCE_DIR,"AutoTripsVMT_perOrigDestHomeWork.rdata")
print(paste("Reading",full_filename))
load(full_filename)
AutoTripsVMT_perOrigDestHomeWork <- model_summary
remove(model_summary)

# Define table name #
phw_tablename <- paste0("perOrigDestHomeWork_",MODEL_RUN)
full_phw_tablename <- paste0(TABLE_PREFIX,".[",phw_tablename,"]")

# Save it
save_start <- proc.time()
retcode <- sqlSave(connection, AutoTripsVMT_perOrigDestHomeWork, phw_tablename)
save_end <- proc.time()
print(paste("Saved",full_phw_tablename,"in:"))
print(save_end-save_start)






