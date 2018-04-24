#########################################################################
# Caluating VMT per capita by place of residence and place of work
#########################################################################


# Caluating vmt
#########################################################################
load("M:/Application/Model One/RTP2017/Scenarios/2015_06_002/OUTPUT/core_summaries/AutoTripsVMT_perOrigDestHomeWork.rdata")

# to see what's in the file
head(model_summary)

# if dplyr not installed, type install.packages("dplyr")

library(dplyr)

#group_by
# %>%, hit control shift m, to get piping
# by place of residence
total_vmt_by_residence = model_summary %>%
   group_by(taz) %>%
   summarise(total_vmt = sum(vmt))

# export to csv
# note / direction
write.csv(total_vmt_by_residence, "M:/Application/Model One/VMT_maps/total_vmt_by_residence.csv")

# by place of work
total_vmt_by_workplace = model_summary %>%
   group_by(WorkLocation) %>%
   summarise(total_vmt = sum(vmt))

# export to csv
# note / direction
write.csv(total_vmt_by_workplace, "M:/Application/Model One/VMT_maps/total_vmt_by_workplace.csv")

# Caluating population
#########################################################################

load("M:/Application/Model One/RTP2017/Scenarios/2015_06_002/OUTPUT/core_summaries/AutoTripsVMT_personsHomeWork.rdata")
head(model_summary)

# by place of residence
total_pop_by_residence = model_summary %>%
   group_by(taz) %>%
   summarise(total_pop = sum(freq))

# export to csv
# note / direction
write.csv(total_pop_by_residence, "M:/Application/Model One/VMT_maps/total_pop_by_residence.csv")

# by place of work
total_pop_by_workplace = model_summary %>%
   group_by(WorkLocation) %>%
   summarise(total_pop = sum(freq))

# export to csv
# note / direction
write.csv(total_pop_by_workplace, "M:/Application/Model One/VMT_maps/total_pop_by_workplace.csv")

# link the tables and calculate vmt per capita
#########################################################################
vmt_pop_by_residence = merge(total_vmt_by_residence, total_pop_by_residence, by="taz")
vmt_pop_by_residence$vmtpercapita = vmt_pop_by_residence$total_vmt / vmt_pop_by_residence$total_pop
write.csv(vmt_pop_by_residence, "M:/Application/Model One/VMT_maps/vmt_pop_by_residence.csv")

vmt_pop_by_workplace = merge(total_vmt_by_workplace, total_pop_by_workplace, by="WorkLocation")
vmt_pop_by_workplace$vmtpercapita = vmt_pop_by_workplace$total_vmt / vmt_pop_by_workplace$total_pop
write.csv(vmt_pop_by_workplace, "M:/Application/Model One/VMT_maps/vmt_pop_by_workplace.csv")

# shape file was downloaded from: https://mtc.maps.arcgis.com/home/item.html?id=57e4e331d2a042938760cc9397218ad0