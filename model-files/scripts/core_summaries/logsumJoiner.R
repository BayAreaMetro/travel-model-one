#
# Join logsum outputs to households so that they're easier to map
#
library(dplyr)
library(tidyr)

TARGET_DIR     <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER           <- Sys.getenv("ITER")        # The iteration of model outputs to read

TARGET_DIR                <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
WORKLOGSUM_OUTFILE        <- file.path(TARGET_DIR,"logsums","person_workDCLogsum.csv")
WORKLOGSUM_OUTFILE_SPREAD <- file.path(TARGET_DIR,"logsums","workDCLogsum.csv")
SHOPLOGSUM_OUTFILE        <- file.path(TARGET_DIR,"logsums","tour_shopDCLogsum.csv")
SHOPLOGSUM_OUTFILE_SPREAD <- file.path(TARGET_DIR,"logsums","shopDCLogsum.csv")

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)

print(paste("TARGET_DIR  = ",TARGET_DIR))
print(paste("ITER        = ",ITER))

person_data    <- read.table(file = file.path(TARGET_DIR,"logsums",paste0("personData_",ITER,".csv")),    header=TRUE, sep=",")
household_data <- read.table(file = file.path(TARGET_DIR,"logsums",paste0("householdData_",ITER,".csv")), header=TRUE, sep=",")
indivtour_data <- read.table(file = file.path(TARGET_DIR,"logsums",paste0("indivTourData_",ITER,".csv")), header=TRUE, sep=",")

# join household_data into person_data
person_data    <- left_join(person_data, household_data)

# sort by person_id
person_data    <- person_data[order(person_data$person_id),]

# make incgroup variable
income_vals    <- sort(unique(person_data$income))
person_data    <- mutate(person_data, income_group=match(income, income_vals))

# create unique key
person_data    <- mutate(person_data,
                         key=paste0("auto",autos,
                                    "_av",autonomousVehicles,
                                    "_inc",income_group))
work_person_data <- filter(person_data, type=="Full-time worker")

# write work logsums for full time workers
write.table(select(work_person_data, taz, autos, autonomousVehicles, income_group, workDCLogsum),
            WORKLOGSUM_OUTFILE, sep=",", row.names=FALSE)

# spread
person_data_spread <- spread(select(work_person_data,taz,key,workDCLogsum),
                             key=key, value=workDCLogsum)
write.table(person_data_spread, WORKLOGSUM_OUTFILE_SPREAD, sep=",", row.names=FALSE)


# non-mandatory
indivtour_data <- left_join(indivtour_data, person_data) %>% filter(tour_purpose=="shopping")

# write tour logsums for shopping tours
write.table(select(indivtour_data, taz, autos, autonomousVehicles, income_group, dcLogsum),
            SHOPLOGSUM_OUTFILE, sep=",", row.names=FALSE)
# spread
indivtour_data_spread <- spread(select(indivtour_data,taz,key,dcLogsum),
                             key=key, value=dcLogsum)
write.table(indivtour_data_spread, SHOPLOGSUM_OUTFILE_SPREAD, sep=",", row.names=FALSE)
