#AllBridgesModeIncome.R
#Analyze people crossing all bridges by drive alone/carpool and income
#Paths established by model, by assigning CTPP tract-level data put into TAZ matrix
#October 23, 2017

suppressMessages(library(dplyr))

# Set up directories with csv files 

# Assignment
assignment = "M:/Application/Model One/RTP2017/Scenarios/2015_06_002/OUTPUT/Bridge Analysis/version 3/loadAM_CTPP.csv"
# Where to export summaries
summary_out = "M:/Data/Requests/Rebecca Long/RM3/Bay Bridge Crossers by Income/"

# Read in data, append bridge names based on network links, and rename variables of interest.

final <- read.csv(assignment, header=TRUE, stringsAsFactors=F) %>% 
  select(A,B,V1_1,V2_1,V3_1,V4_1,V5_1,V6_1,V7_1,V8_1) %>%
    mutate(bridge =
      ifelse((A==1622 & B==1668) | (A==1673 & B==1621),"antioch",
      ifelse((A==6973 & B==2784) | (A==2783 & B==6972),"bay",
      ifelse((A==2135 & B==2130) | (A==2131 & B==2136),"benicia",
      ifelse((A==2206 & B==11637) | (A==11667 & B==11634) | (A==9506 & B==9285),"carquinez", # includes HOV lane
      ifelse((A==5939 & B==3896) | (A==3880 & B==5938),"dumbarton",
      ifelse((A==7318 & B==7316) | (A==7317 & B==7315),"goldengate",
      ifelse((A==7853 & B==2341) | (A==2342 & B==7894),"richmond",
      ifelse((A==6383 & B==3642) | (A==3650 & B==6381),"sanmateo",
      ifelse((A==11739 & B==11726) | (A==11726 & B==11739),"sr37","none"))))))))))%>%
  rename(lt35_drivealone=V1_1,	
          gt35_50_drivealone=V2_1,
          gt50_75_drivealone=V3_1,
          gt75_drivealone=V4_1,
          lt35_carpool=V5_1,	
          gt35_50_carpool=V6_1,	
          gt50_75_carpool=V7_1,	
          gt75_carpool=V8_1)

# Summarize data, append a total by bridge, and export csv.

output <- final %>%
  filter(bridge!="none") %>%
  group_by(bridge) %>%
  summarize(lt35_drivealone = sum(lt35_drivealone),
            gt35_50_drivealone = sum(gt35_50_drivealone),
            gt50_75_drivealone=sum(gt50_75_drivealone),
            gt75_drivealone=sum(gt75_drivealone),
            lt35_carpool=sum(lt35_carpool),	
            gt35_50_carpool=sum(gt35_50_carpool),	
            gt50_75_carpool=sum(gt50_75_carpool),	
            gt75_carpool=sum(gt75_carpool))%>%
  rowwise()%>%
  mutate(total_drivealone=lt35_drivealone+gt35_50_drivealone+gt50_75_drivealone+gt75_drivealone,
         total_carpool=lt35_carpool+gt35_50_carpool+gt50_75_carpool+gt75_carpool,
         total_drive=total_drivealone+total_carpool)
  
            
write.csv(output, paste0(summary_out, "CTPP2006-2010_assigned_bridgeVolumes.csv"), row.names = FALSE, quote = T)          





