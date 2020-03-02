# Initialization: Set the workspace and load needed libraries
.libPaths(Sys.getenv("R_LIB"))
library(plyr) # this must be first
library(dplyr)
library(reshape2)

model_dirs <- data.frame(scenario_id=c('2035_05_631',
                                       '2035_05_632',
                                       '2035_05_633',
                                       '2035_05_634'),
                         dir=c("D:/Projects/2035_05_631",
                               "A:/Projects/2035_05_632",
                               "E:/Projects/2035_05_633",
                               "A:/Projects/2035_05_634"), stringsAsFactors=FALSE
)

for (i in 1:nrow(model_dirs)) {
  TARGET_DIR   <- gsub("\\\\","/",model_dirs[i,'dir']) # switch slashes around
  SCENARIO_ID  <- model_dirs[i,'scenario_id']
  cat(SCENARIO_ID," => ",TARGET_DIR,"\n")

  input.pop.households <- read.table(file = file.path(TARGET_DIR,"popsyn","hhFile.csv"), 
                                     header=TRUE, sep=",") %>% select(HHID, PERSONS, HINC) %>% 
                          rename(income=HINC)

  input.pop.persons    <- read.table(file = file.path(TARGET_DIR,"popsyn","personFile.csv"),
                                     header=TRUE, sep=",") %>% select(HHID, PERID, AGE, SEX) %>%
                          rename(age=AGE)  %>%
                          mutate(gender=ifelse(SEX==1,'m','f')) %>% select(-SEX)

  persons <- left_join(input.pop.persons, input.pop.households) %>%
             mutate(incQ=1*(income<30000) + 
                         2*((income>=30000)&(income<60000)) +
                         3*((income>=60000)&(income<100000)) +
                         4*(income>=100000)) %>%
             mutate(age_group='?')
  remove(input.pop.households, input.pop.persons)

  persons$age_group[(persons$age <= 4)                    ] <- ' 0- 4'		
  persons$age_group[(persons$age >= 5)&(persons$age <= 14)] <- ' 5-14'		
  persons$age_group[(persons$age >=15)&(persons$age <= 29)] <- '15-29'		
  persons$age_group[(persons$age >=30)&(persons$age <= 44)] <- '30-44'		
  persons$age_group[(persons$age >=45)&(persons$age <= 59)] <- '45-59'		
  persons$age_group[(persons$age >=60)&(persons$age <= 69)] <- '60-69'		
  persons$age_group[(persons$age >=70)&(persons$age <= 79)] <- '70-79'		
  persons$age_group[(persons$age >=80)                    ] <- '80+'

  summary <- rbind(
    tbl_df(dplyr::summarise(group_by(persons, age_group, gender), count=n())) %>% mutate(incQ="all"),
    tbl_df(dplyr::summarise(group_by(persons, age_group, gender, incQ), count=n()))
  ) %>% mutate(scenario_id=SCENARIO_ID)
  
  if (i==1) {
    all_summary <- summary
  } else {
    all_summary <- rbind(all_summary, summary)
  }
}

write.table(all_summary, file.path("M:/Application/Model One/RTP2017/Scenarios/Across-Scenarios-2035-Round-03/ITHIM_demog.csv"), sep=",", row.names=FALSE)