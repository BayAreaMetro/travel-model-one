#
# Join logsum outputs to households so that they're easier to map
#
## Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

library(dplyr)
library(tidyr)

TARGET_DIR     <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER           <- Sys.getenv("ITER")        # The iteration of model outputs to read

TARGET_DIR                <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
WORKLOGSUM_OUTFILE        <- file.path(TARGET_DIR,"logsums","person_workDCLogsum.csv")
WORKLOGSUM_OUTFILE_SPREAD <- file.path(TARGET_DIR,"logsums","workDCLogsum.csv")
MANDACC_OUTFILE_SPREAD    <- file.path(TARGET_DIR,"logsums","mandatoryAccessibilities.csv")
SHOPLOGSUM_OUTFILE        <- file.path(TARGET_DIR,"logsums","tour_shopDCLogsum.csv")
SHOPLOGSUM_OUTFILE_SPREAD <- file.path(TARGET_DIR,"logsums","shopDCLogsum.csv")
NONMANDACC_OUTFILE_SPREAD <- file.path(TARGET_DIR,"logsums","nonMandatoryAccessibilities.csv")

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

# create unique key -- one per taz+walksubzone
person_data    <- mutate(person_data,
                         tw_key=paste(case_when(income_group==1 ~ "lowInc",
                                             income_group==2 ~ "medInc",
                                             income_group==3 ~ "highInc",
                                             income_group==4 ~ "veryHighInc"),
                                   case_when(autos==0 ~ "0_autos",
                                             autos<workers ~ "autos_lt_workers",
                                             autos>=workers ~ "autos_ge_workers"),
                                   ifelse(autonomousVehicles>0, "AV","noAV"),
                                   sep="_"))
# another for just taz
person_data   <- mutate(person_data, key=paste0(tw_key, "_subz",walk_subzone))

work_person_data <- filter(person_data, type=="Full-time worker")

# write work logsums for full time workers
write.table(select(work_person_data, taz, walk_subzone, autos, autonomousVehicles, income_group, workDCLogsum),
            WORKLOGSUM_OUTFILE, sep=",", row.names=FALSE)

# spread - with taz-only key for mapping
person_data_spread <- spread(select(work_person_data,taz,key,workDCLogsum),
                             key=key, value=workDCLogsum)
write.table(person_data_spread, WORKLOGSUM_OUTFILE_SPREAD, sep=",", row.names=FALSE)

# spread - with taz+walk subzone key for consistency with old mandatoryAccessiblities file
person_data_spread <- spread(select(work_person_data,taz,walk_subzone,tw_key,workDCLogsum),
                             key=tw_key, value=workDCLogsum) %>% 
  rename(subzone=walk_subzone) %>%
  mutate(destChoiceAlt=3*(taz-1)+subzone)

# order the columns consistently with before
person_data_spread <- person_data_spread[
  c("lowInc_0_autos_noAV",     "lowInc_autos_lt_workers_noAV",     "lowInc_autos_lt_workers_AV",     "lowInc_autos_ge_workers_noAV",     "lowInc_autos_ge_workers_AV",
    "medInc_0_autos_noAV",     "medInc_autos_lt_workers_noAV",     "medInc_autos_lt_workers_AV",     "medInc_autos_ge_workers_noAV",     "medInc_autos_ge_workers_AV",
    "highInc_0_autos_noAV",    "highInc_autos_lt_workers_noAV",    "highInc_autos_lt_workers_AV",    "highInc_autos_ge_workers_noAV",    "highInc_autos_ge_workers_AV",
    "veryHighInc_0_autos_noAV","veryHighInc_autos_lt_workers_noAV","veryHighInc_autos_lt_workers_AV","veryHighInc_autos_ge_workers_noAV","veryHighInc_autos_ge_workers_AV",
    "destChoiceAlt","taz","subzone")]

write.table(person_data_spread, MANDACC_OUTFILE_SPREAD, sep=",", row.names=FALSE)

# non-mandatory
indivtour_data <- left_join(indivtour_data, person_data) %>% filter(tour_purpose=="shopping")

# write tour logsums for shopping tours
write.table(select(indivtour_data, taz, walk_subzone, autos, autonomousVehicles, income_group, dcLogsum),
            SHOPLOGSUM_OUTFILE, sep=",", row.names=FALSE)
# spread
indivtour_data_spread <- spread(select(indivtour_data,taz,key,dcLogsum),
                                key=key, value=dcLogsum)
write.table(indivtour_data_spread, SHOPLOGSUM_OUTFILE_SPREAD, sep=",", row.names=FALSE)

# spread - with taz+walk subzone key for consistency with old mandatoryAccessiblities file
indivtour_data_spread <- spread(select(indivtour_data,taz,walk_subzone,tw_key,dcLogsum),
                                key=tw_key, value=dcLogsum) %>% 
  rename(subzone=walk_subzone) %>%
  mutate(destChoiceAlt=3*(taz-1)+subzone)

# order the columns consistently with before
indivtour_data_spread <- indivtour_data_spread[
  c("lowInc_0_autos_noAV",     "lowInc_autos_lt_workers_noAV",     "lowInc_autos_lt_workers_AV",     "lowInc_autos_ge_workers_noAV",     "lowInc_autos_ge_workers_AV",
    "medInc_0_autos_noAV",     "medInc_autos_lt_workers_noAV",     "medInc_autos_lt_workers_AV",     "medInc_autos_ge_workers_noAV",     "medInc_autos_ge_workers_AV",
    "highInc_0_autos_noAV",    "highInc_autos_lt_workers_noAV",    "highInc_autos_lt_workers_AV",    "highInc_autos_ge_workers_noAV",    "highInc_autos_ge_workers_AV",
    "veryHighInc_0_autos_noAV","veryHighInc_autos_lt_workers_noAV","veryHighInc_autos_lt_workers_AV","veryHighInc_autos_ge_workers_noAV","veryHighInc_autos_ge_workers_AV",
    "destChoiceAlt","taz","subzone")]

write.table(indivtour_data_spread, NONMANDACC_OUTFILE_SPREAD, sep=",", row.names=FALSE)
