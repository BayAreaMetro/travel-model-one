library(tidyr)
library(dplyr)

NETWORKS        <- c("BASE","BLD")
TIMEPERIODS_PK  <- c("AM","PM")
TIMEPERIODS_5   <- c("EA","AM","MD","PM","EV")
VEHCLASSES_TOLL <- c("DA" ,"S2" ,"S3" ,"SML" ,"MED", "LRG")
VEHCLASSES      <- c("DA" ,"S2" ,"S3" ,"SM" ,"HV",
                     "DAT","S2T","S3T","SMT","HVT",
                     "DAAV","S2AV","S3AV")

data_wide <- read.table("avgload5period_vs_baseline_attr.csv", header=TRUE, sep=",", stringsAsFactors = FALSE)

# cspdTT_NET
varnames = c()
for (timeperiod in TIMEPERIODS_5) {
  for (network in NETWORKS) {
    varnames <- append(varnames, paste0("CSPD",timeperiod,"_",network))
  }
}

data_long_cspd <- gather(
  select(data_wide,append(c("A","B","IN_BASE","IN_BLD","TOLLCLASS_BASE","TOLLCLASS_BLD"),varnames)), 
    key="key_name", value="value", varnames) %>%
  separate(key_name, into=c("timeperiod","network"), sep="_") %>%
  mutate(timeperiod = substring(timeperiod,5,6),
         variable="cspd")

# TOLLTT_VVV_NET
varnames = c()
for (timeperiod in TIMEPERIODS_PK) {
  for (vehclass in VEHCLASSES_TOLL) {
    for (network in NETWORKS) {
      varnames <- append(varnames, paste0("TOLL",timeperiod,"_",vehclass,"_",network))
    }
  }
}


data_long_toll <- gather(
  select(data_wide,append(c("A","B","IN_BASE","IN_BLD","TOLLCLASS_BASE","TOLLCLASS_BLD"),varnames)),
    key="key_name", value="value", varnames) %>%
  separate(key_name, into=c("timeperiod","vehclass","network"), sep="_")  %>%
  mutate(timeperiod = substring(timeperiod,5,6),
         variable="toll")


# VOL24_S3T_BLD
varnames = c()
for (timeperiod in TIMEPERIODS_5) {
  for (vehclass in VEHCLASSES) {
    for (network in NETWORKS) {
      varnames <- append(varnames, paste0("VOL",timeperiod,"_",vehclass,"_",network))
    }
  }
}

data_long_vol <- gather(
  select(data_wide,append(c("A","B","IN_BASE","IN_BLD","TOLLCLASS_BASE","TOLLCLASS_BLD",
                            "DISTANCE_BASE","DISTANCE_BLD"),varnames)), 
    key="key_name", value="value", varnames) %>%
  separate(key_name, into=c("timeperiod","vehclass","network"), sep="_")  %>%
  mutate(timeperiod = substring(timeperiod,4,5),
         variable="VOL")

# add distance -> vmt
data_long_vol <- mutate(data_long_vol, DISTANCE=ifelse(network=="BASE",DISTANCE_BASE,DISTANCE_BLD)) %>% 
  select(-DISTANCE_BASE, -DISTANCE_BLD)

data_long_vmt <- mutate(data_long_vol, variable="VMT", value=value*DISTANCE) %>% select(-DISTANCE)
data_long_vol <- select(data_long_vol, -DISTANCE)

# put it all together and write
data_long <- rbind(mutate(data_long_cspd, vehclass=NA),
                   data_long_toll,
                   data_long_vol,
                   data_long_vmt)

# remove rows that aren't in that network
data_long <- filter(data_long, ((IN_BASE==1)&(network=="BASE")) | 
                               ((IN_BLD==1)&(network=="BLD"))) %>%
  select(-IN_BASE,-IN_BLD)

# set tollclass
data_long <- mutate(data_long, TOLLCLASS=ifelse(network=="BASE", TOLLCLASS_BASE, TOLLCLASS_BLD)) %>%
  select(-TOLLCLASS_BASE, -TOLLCLASS_BLD)

write.table(data_long, "avgload5period_vs_baseline_long.csv", sep=",", row.names=FALSE)
