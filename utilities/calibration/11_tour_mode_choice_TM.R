library(dplyr)
library(tidyr)

# For RStudio, these can be set in the .Rprofile
TARGET_DIR   <- Sys.getenv("TARGET_DIR")  # The location of the input files
ITER         <- Sys.getenv("ITER")        # The iteration of model outputs to read
SAMPLESHARE  <- Sys.getenv("SAMPLESHARE") # Sampling

TARGET_DIR   <- gsub("\\\\","/",TARGET_DIR) # switch slashes around
OUTPUT_DIR   <- file.path(TARGET_DIR, "OUTPUT", "calibration")
if (!file.exists(OUTPUT_DIR)) { dir.create(OUTPUT_DIR) }

stopifnot(nchar(TARGET_DIR  )>0)
stopifnot(nchar(ITER        )>0)
stopifnot(nchar(SAMPLESHARE )>0)

SAMPLESHARE <- as.numeric(SAMPLESHARE)

cat("TARGET_DIR  = ",TARGET_DIR, "\n")
cat("ITER        = ",ITER,       "\n")
cat("SAMPLESHARE = ",SAMPLESHARE,"\n")

input.pop.households <- read.table(file = file.path(TARGET_DIR,"INPUT","popsyn","hhFile.calib.2015.csv"),
                                   header=TRUE, sep=",") %>%
  select(HHID, TAZ, PERSONS, hworkers)

ao_results           <- read.table(file=file.path(TARGET_DIR,"OUTPUT","main","aoResults.csv"), header=TRUE, sep=",")

indiv_tour_results   <- read.table(file=file.path(TARGET_DIR,"OUTPUT","main",paste0("indivTourData_",ITER,".csv")),
                                   header=TRUE, sep=",") %>% 
  select(hh_id, person_id, tour_id, tour_category, tour_purpose, tour_mode)

joint_tour_results   <- read.table(file=file.path(TARGET_DIR,"OUTPUT","main",paste0("jointTourData_",ITER,".csv")),
                                   header=TRUE, sep=",") %>% 
  select(hh_id, tour_participants, tour_id, tour_category, tour_purpose, tour_mode)

# create num_participants, indiv_joint column
joint_tour_results$tour_participants <- as.character(joint_tour_results$tour_participants)
count_participants <- function(x) { length(strsplit(x," ")[[1]]) }
joint_tour_results <- mutate(joint_tour_results, 
                             num_participants=count_participants(tour_participants),
                             indiv_joint="joint")
indiv_tour_results <- mutate(indiv_tour_results,
                             num_participants=1,
                             indiv_joint="indiv")

# put them together
tour_results <- rbind(select(indiv_tour_results, -person_id),
                      select(joint_tour_results, -tour_participants))

# add number of workers and number of vehicles to indiv_tour_results
tour_results <- left_join(tour_results, ao_results, by=c("hh_id"="HHID"))
tour_results <- left_join(tour_results, input.pop.households, by=c("hh_id"="HHID"))

tour_results <- mutate(tour_results, 
                       auto_suff=if_else(AO==0, "Autos=0", if_else(AO<hworkers, "Autos<Workers", "Autos>=Workers")))

# summarize to "auto_sufficiency", indiv_joint, tour purpose and tour mode
tour_summary <- group_by(tour_results, auto_suff, indiv_joint, tour_purpose, tour_mode) %>% 
  summarise(num_tours=sum(num_participants)) %>%
  mutate(num_tours=num_tours/SAMPLESHARE)

# move auto_sufficiency to columns
tour_summary_spread <- spread(tour_summary, key=auto_suff, value=num_tours)

# reorder
tour_summary_spread <- tour_summary_spread[c("indiv_joint","tour_purpose","tour_mode",
                                             "Autos=0","Autos<Workers","Autos>=Workers")]
# fillNA
tour_summary_spread[is.na(tour_summary_spread)] <- 0


# save it
outfile <- file.path(OUTPUT_DIR, paste0("11_tour_mode_choice_TM.csv"))
write.table(tour_summary_spread, outfile, sep=",", row.names=FALSE)
cat("Wrote ",outfile,"\n")