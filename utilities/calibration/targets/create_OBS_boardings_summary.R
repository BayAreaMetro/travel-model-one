#######################################################
### Script to summarize MTC OBS boardings by hour and 
### Operator/Technology
### Author: Binny M Paul, binny.mathewpaul@rsginc.com
#######################################################
oldw <- getOption("warn")
options(warn = -1)
options(scipen=999)

library(dplyr)

Project_Dir <- file.path('E:','projects','clients','mtc')
OBS_Dir     <- file.path(Project_Dir, 'data','OBS_27Dec17')

OBS <- read.csv(file.path(OBS_Dir,'OBS_processed_weighted_RSG.csv'))

summary_boards_dep <- OBS[,c('survey_tech','operator','depart_hour','board_weight2015')] %>%
  filter(!is.na(survey_tech) & !is.na(operator) & !is.na(depart_hour) & !is.na(board_weight2015)) %>%
  group_by(survey_tech, operator, depart_hour) %>%
  summarise(boards = sum(board_weight2015)) %>%
  ungroup()
#write.csv(summary_boards_dep, file.path(Project_Dir, 'TM_1_5','Calibration','OBS_Summaries','OBS_Boardings_By_DepartureHour.csv'), row.names = F)

summary_boards_ret <- OBS[,c('survey_tech','operator','return_hour','board_weight2015')] %>%
  filter(!is.na(survey_tech) & !is.na(operator) & !is.na(return_hour) & !is.na(board_weight2015)) %>%
  group_by(survey_tech, operator, return_hour) %>%
  summarise(boards = sum(board_weight2015)) %>%
  ungroup()
#write.csv(summary_boards_ret, file.path(Project_Dir, 'TM_1_5','Calibration','OBS_Summaries','OBS_Boardings_By_ReturnHour.csv'), row.names = F)

hour_list <- seq(0,23)

df <- expand.grid(tech = unique(OBS$survey_tech), 
                  operator = unique(OBS$operator), 
                  hour = hour_list)

df$departure <- summary_boards_dep$boards[match(paste(df$tech, df$operator, df$hour, sep = "-"), 
                                                paste(summary_boards_dep$survey_tech, summary_boards_dep$operator, summary_boards_dep$depart_hour, sep = "-"))]

df$return <- summary_boards_ret$boards[match(paste(df$tech, df$operator, df$hour, sep = "-"), 
                                                paste(summary_boards_ret$survey_tech, summary_boards_ret$operator, summary_boards_ret$return_hour, sep = "-"))]

df[is.na(df)] <- 0
df$total <- df$departure + df$return

write.csv(df, file.path(Project_Dir, 'TM_1_5','Calibration','OBS_Summaries','OBS_Boardings_By_Hour.csv'), row.names = F)


# Turn back warnings;
options(warn = oldw)

