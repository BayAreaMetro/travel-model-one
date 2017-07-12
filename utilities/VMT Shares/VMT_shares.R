#
# Simple non-shiny VMT shares script
# 
# Using model data in MODEL_DIR

library(dplyr)  # note !! notation requires dplyr 0.6.0 or after
library(xlsx)

MAX_TAZ        <- 1454
MODEL_DIR      <- "M:/Application/Model One/RTP2013/Scenarios/2010_03_YYY/OUTPUT/core_summaries"
MODEL_RUN      <- "2010_03_YYY"

load(file.path(MODEL_DIR, "AutoTripsVMT_personsHomeWork.rdata"))
persons_hwlocs <- model_summary
remove(model_summary)
print(head(persons_hwlocs))
## columns: COUNTY   county_name   taz WorkLocation  freq

load(file.path(MODEL_DIR, "AutoTripsVMT_perOrigDestHomeWork.rdata"))
vmt_hwlocs <- model_summary
remove(model_summary)
print(head(vmt_hwlocs))
## columns: orig_taz dest_taz   taz WorkLocation   vmt vmt_indiv vmt_joint trips

#
# and TAZ set definitions in this xlsx file
#
TAZ_SET_DEF    <- "M:/Data/Priority Development Areas/TAZ_intersect_PDAs.xlsx"
taz_set_df     <- read.xlsx(TAZ_SET_DEF, sheetIndex=1, stringsAsFactors=FALSE)
INDEX_COL      <- "name"
TAZ_COL        <- "TAZ1454"
PERCENT_COL    <- "INT_over_TAZ"

print(head(taz_set_df))

all_summary <- data.frame()

for (geog in unique(taz_set_df[[INDEX_COL]])) {
  print(paste0("geog [", geog, "]"))
  taz_frame_df <- taz_set_df[ taz_set_df[INDEX_COL] == geog, ]
  print(taz_frame_df)

  # Create taz_mapping: data frame mapping all TAZs to % of TAZ in the geographical unit
  taz_mapping          <- data.frame(taz=1:MAX_TAZ)
  colnames(taz_mapping)<- c(TAZ_COL)
  taz_mapping          <- left_join(taz_mapping, taz_frame_df[c(TAZ_COL,PERCENT_COL)])
  taz_mapping[is.na(taz_mapping)] <- 0
  
  # rename columns
  colnames(taz_mapping) <- c("taz","in_percent")

  # Left join persons to add live_in_percent and work_in_percent
  persons_hwlocs_geog <- left_join(persons_hwlocs, 
                                   mutate(taz_mapping, live_in_percent=in_percent) %>% 
                                     select(taz,live_in_percent))
  persons_hwlocs_geog <- left_join(persons_hwlocs_geog, 
                                   mutate(taz_mapping, WorkLocation=taz, work_in_percent=in_percent) %>% 
                                     select(WorkLocation,work_in_percent))
  
  # Allocate persons to 6 person categories
  persons_hwlocs_geog <- mutate(persons_hwlocs_geog,
                                live_in_work_in   = ifelse(WorkLocation==0,0, live_in_percent*work_in_percent*freq),
                                live_in_work_out  = ifelse(WorkLocation==0,0, live_in_percent*(1.0-work_in_percent)*freq),
                                live_out_work_in  = ifelse(WorkLocation==0,0, (1.0-live_in_percent)*work_in_percent*freq),
                                live_out_work_out = ifelse(WorkLocation==0,0, (1.0-live_in_percent)*(1.0-work_in_percent)*freq),
                                live_in_no_work   = ifelse(WorkLocation!=0,0, live_in_percent*freq),
                                live_out_no_work  = ifelse(WorkLocation!=0,0, (1.0-live_in_percent)*freq))
  # Just keep relevant columns to sum
  pgroup_colnames <- c("live_in_work_in",  "live_in_work_out",
                       "live_out_work_in", "live_out_work_out",
                       "live_in_no_work",  "live_out_no_work")
  persons_hwlocs_geog_6 <- persons_hwlocs_geog %>%
    ungroup() %>%
    select(live_in_work_in,  live_in_work_out,
           live_out_work_in, live_out_work_out,
           live_in_no_work,  live_out_no_work)
  persons_geog <- t(data.frame(colSums(persons_hwlocs_geog_6, na.rm=TRUE)))
  print(persons_geog)
  
  # Left join VMT to add live_in_percent and work_in_percent
  vmt_hwlocs_geog <- left_join(vmt_hwlocs,
                               mutate(taz_mapping, live_in_percent=in_percent) %>% 
                                select(taz,live_in_percent))
  vmt_hwlocs_geog <- left_join(vmt_hwlocs_geog,
                               mutate(taz_mapping, WorkLocation=taz, work_in_percent=in_percent) %>% 
                                select(WorkLocation,work_in_percent))
  # these are fractions
  vmt_hwlocs_geog <- mutate(vmt_hwlocs_geog,
                            live_in_work_in   = ifelse(WorkLocation==0,0, live_in_percent*work_in_percent),
                            live_in_work_out  = ifelse(WorkLocation==0,0, live_in_percent*(1.0-work_in_percent)),
                            live_out_work_in  = ifelse(WorkLocation==0,0, (1.0-live_in_percent)*work_in_percent),
                            live_out_work_out = ifelse(WorkLocation==0,0, (1.0-live_in_percent)*(1.0-work_in_percent)),
                            live_in_no_work   = ifelse(WorkLocation!=0,0, live_in_percent),
                            live_out_no_work  = ifelse(WorkLocation!=0,0, (1.0-live_in_percent)))
  
  # Left join to origin_in_area and dest_in_area
  vmt_hwlocs_geog <- left_join(vmt_hwlocs_geog,
                          mutate(taz_mapping, orig_taz=taz, orig_in_percent=in_percent) %>% select(orig_taz,orig_in_percent))
  vmt_hwlocs_geog <- left_join(vmt_hwlocs_geog,
                          mutate(taz_mapping, dest_taz=taz, dest_in_percent=in_percent) %>% select(dest_taz,dest_in_percent))
  vmt_hwlocs_geog <- mutate(vmt_hwlocs_geog,
                            vmt_within  = orig_in_percent*dest_in_percent*vmt,
                            vmt_outside = (1.0-orig_in_percent)*(1.0-dest_in_percent)*vmt,
                            vmt_partial = orig_in_percent*(1.0-dest_in_percent)*vmt + (1.0-orig_in_percent)*dest_in_percent*vmt)
  
  vmt_colnames <- c()
  for (person_group in pgroup_colnames) {
    for (vmt_group in c("vmt_within","vmt_outside","vmt_partial")) {
      vmt_hwlocs_geog[paste(person_group, vmt_group)] = vmt_hwlocs_geog[person_group]*vmt_hwlocs_geog[vmt_group]
      vmt_colnames <- c(vmt_colnames, paste(person_group, vmt_group))
    }
  }
  vmt_hwlocs_geog_18 <- vmt_hwlocs_geog[vmt_colnames]
  vmt_geog <- t(data.frame(colSums(vmt_hwlocs_geog_18, na.rm=TRUE)))
  print(vmt_geog)
  
  # put it all together
  geog_summary <- tbl_df(cbind(persons_geog, vmt_geog))
  geog_summary$geog <- geog
  
  if (nrow(all_summary)==0) {
    all_summary <- geog_summary
  } else {
    all_summary <- rbind(all_summary, geog_summary)
  }
  
  # for testing
  # if (geog=="Adeline Street") {
  #   break
  # }
}

# write it
write.table(all_summary, file=file.path(dirname(TAZ_SET_DEF), paste0("VMT_", MODEL_RUN, ".csv")), sep=",", row.names=FALSE)