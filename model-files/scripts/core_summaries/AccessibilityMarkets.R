# Accessibility Markets

# See `M:\Application\Model One\Summary Scripts\Special\AccessibilityMarkets.sas`
#
# Much of this is from `CoreSummaries.Rmd`, but this short version is necessary because
# `CoreSummaries.Rmd` takes a while and won't always be run.

# Used by `metrics\RunResults.py`, the recoding of categories matches the accessibility column headers.

# Step 1: Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))

library(dplyr)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

# write results in TARGET_DIR/core_summaries
if (!file.exists(file.path(TARGET_DIR,"core_summaries"))) {
  dir.create(file.path(TARGET_DIR,"core_summaries"))
}
SAMPLESHARE <- as.numeric(SAMPLESHARE)

print(paste0("TARGET_DIR  = ",TARGET_DIR))
print(paste0("ITER        = ",ITER))
print(paste0("SAMPLESHARE = ",SAMPLESHARE))

# Step 2: Lookups

# For walk_subzones, see http://analytics.mtc.ca.gov/foswiki/Main/Household

######### walk subzones
LOOKUP_WALK_SUBZONE  <- data.frame(walk_subzone=c(0,1,2),
                                   walk_subzone_label=c("Cannot walk to transit",
                                                        "Short-walk to transit",
                                                        "Long-walk to transit"))
LOOKUP_WALK_SUBZONE$walk_subzone <- as.integer(LOOKUP_WALK_SUBZONE$walk_subzone)

# Step 3: Household files

## Read the household files and land use file

# There are two household files:

# * the model input file from the synthesized household/population (http://analytics.mtc.ca.gov/foswiki/Main/PopSynHousehold)
# * the model output file (http://analytics.mtc.ca.gov/foswiki/Main/Household)
input.pop.households <- read.table(file = file.path(TARGET_DIR,"popsyn","hhFile.csv"), 
                                   header=TRUE, sep=",")
input.ct.households  <- read.table(file = file.path(TARGET_DIR,"main",paste0("householdData_",ITER,".csv")), 
                                   header=TRUE, sep = ",")

## Join them

# Rename/drop some columns and join them on household id. Also join with tazData to get the super district and county.
input.pop.households <- select(input.pop.households, HHID, PERSONS, hworkers)
input.ct.households  <- select(input.ct.households, -jtf_choice)

# in case households aren't numeric - make the columns numeric
for(i in names(input.pop.households)){
  input.pop.households[[i]] <- as.numeric(input.pop.households[[i]])
}

# rename
names(input.pop.households)[names(input.pop.households)=="HHID"] <- "hh_id"

households <- inner_join(input.pop.households, input.ct.households, "hh_id")
# wrap as a d data frame tbl so it's nicer for printing
households <- tbl_df(households)
# clean up
remove(input.pop.households, input.ct.households)

## Recode a few new variables

# Create the following new household variables:
#   * income quartiles (`incQ`)
#   * worker categories (`workers`)
#   * dummy for households with children that don't drive (`kidsNoDr`)
#   * auto sufficiency (`autoSuff`)
#   * walk subzone label (`walk_subzone_label`)
#   * has Autonomous Vehicles (`hasAV`)
  
# incQ are Income Quartiles
LOOKUP_INCQ          <- data.frame(incQ=c(1,2,3,4),
                                   incQ_label=c("lowInc","medInc","highInc","veryHighInc"))
LOOKUP_INCQ$incQ     <- as.integer(LOOKUP_INCQ$incQ)

households    <- mutate(households, incQ=1*(income<30000) + 
                                         2*((income>=30000)&(income<60000)) +
                                         3*((income>=60000)&(income<100000)) +
                                         4*(income>=100000))
households    <- left_join(households, LOOKUP_INCQ, by=c("incQ"))

# workers are hworkers capped at 4
households    <- mutate(households, workers=4*(hworkers>=4) + hworkers*(hworkers<4))
WORKER_LABELS <- c("Zero", "One", "Two", "Three", "Four or more")

# auto sufficiency
LOOKUP_AUTOSUFF          <- data.frame(autoSuff=c(0,1,2),
                                autoSuff_label=c("0_autos","autos_lt_workers","autos_ge_workers"))
LOOKUP_AUTOSUFF$autoSuff <- as.integer(LOOKUP_AUTOSUFF$autoSuff)

households    <- mutate(households, autoSuff=1*((autos>0)&(autos<hworkers)) +
                                             2*((autos>0)&(autos>=hworkers)))
households    <- left_join(households, LOOKUP_AUTOSUFF, by=c("autoSuff"))

# walk subzone label
households    <- left_join(households, LOOKUP_WALK_SUBZONE, by=c("walk_subzone"))

# has Autonomous Vehicles
households    <- mutate(households, hasAV=ifelse(autonomousVehicles>0,1,0))

# Step 4: Person files

# There are two person files:

#  * the model input file from the synthesized household/population (http://analytics.mtc.ca.gov/foswiki/Main/PopSynPerson)
#  * the model output file (http://analytics.mtc.ca.gov/foswiki/Main/Person)

## Read the person file
input.ct.persons     <- read.table(file = file.path(TARGET_DIR,"main",paste0("personData_",ITER,".csv")),
                                   header=TRUE, sep = ",")

## Join them
persons              <- input.ct.persons
# Get incQ from Households
persons              <- left_join(persons, select(households, hh_id, incQ, incQ_label, 
                                                  taz, autoSuff, autoSuff_label, hasAV, walk_subzone, walk_subzone_label), by=c("hh_id"))

# wrap as a d data frame tbl so it's nicer for printing
persons              <- tbl_df(persons)
# clean up
remove(input.ct.persons)


## Accessibility Market Summaries
# select workers only
workers          <- subset(persons, (type=="Full-time worker"           |
                                    type=="Part-time worker"            ))
workers_students <- subset(persons, (type=="Full-time worker"           |
                                     type=="Part-time worker"           |
                                     type=="University student"         |
                                     type=="Student of non-driving age" |
                                     type=="Student of driving age"     ))

# Step 5: summarise
workers_summary          <- summarise(group_by(workers,
                                               taz, walk_subzone, walk_subzone_label,
                                               incQ, incQ_label, autoSuff, autoSuff_label, hasAV), freq=n())
workers_summary$freq     <- workers_summary$freq / SAMPLESHARE

workers_students_summary <- summarise(group_by(workers_students,
                                               taz, walk_subzone, walk_subzone_label,
                                               incQ, incQ_label, autoSuff, autoSuff_label, hasAV), freq=n())
workers_students_summary$freq <- workers_students_summary$freq / SAMPLESHARE

persons_summary          <- summarise(group_by(persons,
                                               taz, walk_subzone, walk_subzone_label,
                                               incQ, incQ_label, autoSuff, autoSuff_label, hasAV), freq=n())
persons_summary$freq     <- persons_summary$freq / SAMPLESHARE

names(workers_summary)[names(workers_summary)=="freq"] <- "num_workers"
names(workers_students_summary)[names(workers_students_summary)=="freq"] <- "num_workers_students"
names(persons_summary)[names(persons_summary)=="freq"] <- "num_persons"

acc_market_summary <- left_join(persons_summary, workers_summary)
acc_market_summary <- left_join(acc_market_summary, workers_students_summary)

# Make NAs zero
acc_market_summary[is.na(acc_market_summary)] <- 0

write.table(acc_market_summary, file.path(TARGET_DIR,"core_summaries","AccessibilityMarkets.csv"), sep=",", row.names=FALSE)
model_summary <- acc_market_summary  # name it generically for rdata
save(model_summary, file=file.path(TARGET_DIR,"core_summaries","AccessibilityMarkets.rdata"))

