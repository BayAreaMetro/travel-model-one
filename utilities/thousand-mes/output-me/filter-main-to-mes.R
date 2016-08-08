.libPaths(Sys.getenv("R_LIB"))

library(dplyr)

TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)

cat("TARGET_DIR  = ",TARGET_DIR, "\n")
cat("ITER        = ",ITER,       "\n")

# write results in TARGET_DIR/main/just_mes
if (!file.exists(file.path(TARGET_DIR,"main","just_mes"))) {
  dir.create(file.path(TARGET_DIR,"main","just_mes"))
}

main_files = c("householdData",
               "personData",
               "indivTourData",
               "jointTourData",
               "indivTripData",
               "jointTripData",
               "wsLocResults")

# First, read names file
names_file <- file.path(TARGET_DIR,"popsyn","names.csv")
mes_df     <- read.table(names_file, header=TRUE, sep=",")
mes_df$me  <- 1

# Just hh and me
me_hhs_df  <- unique(select(mes_df, HHID, me))

for (filenum in 1:length(main_files))
{
  full_file <- file.path(TARGET_DIR,"main",paste0(main_files[filenum],"_",ITER,".csv"))
  print(paste0("Reading ",full_file))
  full_df   <- read.table(file=full_file, header=TRUE, sep=",")
  # join to mes, filter to me==1, and delete me row
  print("  Filtering")
  if (main_files[filenum]=="wsLocResults") {
    full_df <- left_join(full_df, me_hhs_df, by=c("HHID")) %>% filter(me==1) %>% select(-me)
  } else {
    full_df <- left_join(full_df, me_hhs_df, by=c("hh_id"="HHID")) %>% filter(me==1) %>% select(-me)
  }
  # save it
  out_file  <- file.path(TARGET_DIR,"main","just_mes",paste0(main_files[filenum],"_",ITER,".csv"))
  write.table(full_df, out_file, sep=",", row.names=FALSE, quote=FALSE)
  print(paste0("  Wrote ",out_file))
}
