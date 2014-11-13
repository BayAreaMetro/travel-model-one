
library(dplyr)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)

cat("TARGET_DIR  = ",TARGET_DIR,"\n")
cat("ITER        = ",ITER,"\n")

# Read households
file_rundir       <- file.path(TARGET_DIR,"main",paste0("householdData_",ITER,".csv"))
file_archive      <- file.path(TARGET_DIR,"OUTPUT",paste0("householdData_",ITER,".csv"))
if (file.exists(file_rundir)) {
  households      <- tbl_df(read.table(file=file_rundir, header=TRUE, sep=","))
} else {
  households      <- tbl_df(read.table(file=file_archive,header=TRUE, sep=","))
}
households        <- select(households, hh_id, income) # just income
cat(paste("Read",prettyNum(nrow(households),big.mark=","),"households\n"))

# Read Individual Trips
file_rundir       <- file.path(TARGET_DIR,"main",paste0("indivTripData_",ITER,".csv"))
file_archive      <- file.path(TARGET_DIR,"OUTPUT",paste0("indivTripData_",ITER,".csv"))
if (file.exists(file_rundir)) {
  indiv_trips     <- tbl_df(read.table(file=file_rundir, header=TRUE, sep=","))
  outfile         <- file.path(TARGET_DIR,"main",paste0("indivTripDataIncome_",ITER,".csv"))
} else {
  indiv_trips     <- tbl_df(read.table(file=file_archive, header=TRUE, sep=","))
  outfile         <- file.path(TARGET_DIR,"OUTPUT",paste0("indivTripDataIncome_",ITER,".csv"))
}
cat(paste("Read",prettyNum(nrow(indiv_trips),big.mark=","),"indvidual trips\n"))

# Join and write it out
indiv_trips       <- left_join(indiv_trips, households)
write.table(indiv_trips, outfile, sep=",", row.names=TRUE)
remove(indiv_trips)
cat(paste("Wrote",outfile,"\n"))

# Read Joint Trips and recode a few variables
file_rundir       <- file.path(TARGET_DIR,"main",paste0("jointTripData_",ITER,".csv"))
file_archive      <- file.path(TARGET_DIR,"OUTPUT",paste0("jointTripData_",ITER,".csv"))
if (file.exists(file_rundir)) {
  joint_trips     <- tbl_df(read.table(file=file_rundir, header=TRUE, sep=","))
  outfile         <- file.path(TARGET_DIR,"main",paste0("jointTripDataIncome_",ITER,".csv"))
} else {
  joint_trips     <- tbl_df(read.table(file=file_archive, header=TRUE, sep=","))
  outfile         <- file.path(TARGET_DIR,"OUTPUT",paste0("jointTripDataIncome_",ITER,".csv"))
}
cat(paste("Read",prettyNum(nrow(joint_trips),big.mark=","),
            "joint trips or ",prettyNum(sum(joint_trips$num_participants),big.mark=","),
            "joint person trips\n"))
# Join and write it out
joint_trips        <- left_join(joint_trips, households)
write.table(joint_trips, outfile, sep=",", row.names=TRUE)
remove(joint_trips)
cat(paste("Wrote",outfile,"\n"))
