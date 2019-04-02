library(dplyr)
library(tidyr)

CALTRAIN_TAZ_FILE <- "X:\\travel-model-one-calibration\\utilities\\calibration\\caltrain_tazs.csv"

# read wlk_com_wlk for AM, PM
com_skim <- data.frame()
for (timeperiod in c("AM","PM")) {
  skim_table <- read.table(paste0("trnskm",timeperiod,"_wlk_com_wlk.csv"), header=TRUE, sep=",") %>% 
    mutate(timeperiod=timeperiod) %>% rename(OTAZ=orig, DTAZ=dest)
  com_skim <- rbind(com_skim, skim_table)
}
remove(skim_table)

caltrain_tazs <- read.table(CALTRAIN_TAZ_FILE, header=TRUE, sep=",")

# report out all stations to Fourth and Townsend
# and all stations to San Jose Diridon
SF_caltrain <- caltrain_tazs[ which(caltrain_tazs$Station == "Caltrain Fourth/Townsend"), ]
SJ_caltrain <- caltrain_tazs[ which(caltrain_tazs$Station == "Caltrain San Jose Diridon"),]
SF16_BART   <- data.frame("Node"=15515, "Station"="BART 16th St. Mission", "TAZ"=106)

# San Francisco Caltrain
to_SF <- data.frame(caltrain_tazs) %>% rename(OTAZ=TAZ, OStation=Station, ONode=Node)
to_SF <- merge(to_SF,     rename(SF_caltrain, DTAZ=TAZ, DStation=Station, DNode=Node), by=NULL)
to_SF <- to_SF[which(to_SF$ONode != to_SF$DNode),]  # remove SF to SF

to_SF_AMPM <- rbind(mutate(to_SF, timeperiod="AM"), mutate(to_SF, timeperiod="PM"))
to_SF_AMPM <- left_join(to_SF_AMPM, com_skim)

# San Jose Caltrain
to_SJ <- data.frame(caltrain_tazs) %>% rename(OTAZ=TAZ, OStation=Station, ONode=Node)
to_SJ <- merge(to_SJ,     rename(SJ_caltrain, DTAZ=TAZ, DStation=Station, DNode=Node), by=NULL)
to_SJ <- to_SJ[which(to_SJ$ONode != to_SJ$DNode),]  # remove SJ to SJ

to_SJ_AMPM <- rbind(mutate(to_SJ, timeperiod="AM"), mutate(to_SJ, timeperiod="PM"))
to_SJ_AMPM <- left_join(to_SJ_AMPM, com_skim)

# 16th Street SF BART
to_SF16 <- data.frame(caltrain_tazs) %>% rename(OTAZ=TAZ, OStation=Station, ONode=Node)
to_SF16 <- merge(to_SF16,     rename(SF16_BART, DTAZ=TAZ, DStation=Station, DNode=Node), by=NULL)
to_SF16 <- to_SF16[which(to_SF16$ONode != to_SF16$DNode),]  # remove SF16 to SF16

to_SF16_AMPM <- rbind(mutate(to_SF16, timeperiod="AM"), mutate(to_SF16, timeperiod="PM"))
to_SF16_AMPM <- left_join(to_SF16_AMPM, com_skim)

# put them together and output for tableau
to_all_AMPM <- rbind(to_SF_AMPM, to_SJ_AMPM, to_SF16_AMPM)
to_all_AMPM[is.na(to_all_AMPM)] <- 0  # replace NA with zero; boards is an indicator of paths found

outfile      <- "caltrain_SF_SJ_skims.csv"
write.table(to_all_AMPM, outfile, sep=",", row.names=FALSE)
print(paste("Wrote",outfile))