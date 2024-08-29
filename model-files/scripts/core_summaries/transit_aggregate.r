print("Start")
.libPaths(Sys.getenv("R_LIB"))
.libPaths()
library(tidyverse)
library(sf)
library(data.table)
library(foreign)
library(future.apply)
library(readxl)

library(stringr)
library(tidyverse)

# Part 1 - General functions to read Cube line files

concatLines <- function(allLines,sttNum,stpNum){
  return(paste0(unlist(str_trim(allLines[sttNum:stpNum])),collapse = ''))
}

replaceLineNodesUntil <- function(lineNodesUntil,keywordStr,valStr){
  indexHW <- gregexpr(keywordStr,lineNodesUntil)[[1]][1]
  if(indexHW!=-1){
    strInitial <- substr(lineNodesUntil,1,indexHW-1)
    strRest    <- substr(lineNodesUntil,indexHW+9,nchar(lineNodesUntil))
    indexRest   <- gregexpr(',',strRest)[[1]][1]
    strFinal <- substr(strRest,indexRest+1,nchar(strRest))
    if(valStr!=-1){
      paste0(strInitial,gsub("\\", "", keywordStr, fixed=TRUE),'=',valStr,',',strFinal)
    }
    else
      paste0(strInitial,strFinal)
  }
  else {
    indexHW <- gregexpr('HEADWAY',lineNodesUntil)[[1]][1]
    strInitial <- substr(lineNodesUntil,1,indexHW-1)
    strRest    <- substr(lineNodesUntil,indexHW,nchar(lineNodesUntil))
    if(valStr!=-1){
      paste0(strInitial,gsub("\\", "", keywordStr, fixed=TRUE),'=',valStr,',',strRest)
    }
    else{
      lineNodesUntil
    }
  }
}

extractKeyword <- function(lineNodesUntilSample,keywordStr){
  retval <- "-99"
  if(gregexpr(keywordStr,lineNodesUntilSample)[[1]][1]!=-1){
    retval <- gsub(',',' ',substr(lineNodesUntilSample,gregexpr(keywordStr,lineNodesUntilSample)[[1]][1]+nchar(keywordStr)+1,nchar(lineNodesUntilSample)))
    retval <- (substr(retval,1,gregexpr(' ',retval)[[1]][1]-1))
  }
  retval
}

extractHeadWays <- function(lineNodesUntilSample){
  # Getting the headways
  h_1 <- -1 
  h_2 <- -1
  h_3 <- -1
  if(gregexpr('HEADWAY\\[1\\]',lineNodesUntilSample)[[1]][1]!=-1){
    h_1 <- gsub(',',' ',substr(lineNodesUntilSample,gregexpr('HEADWAY\\[1\\]',lineNodesUntilSample)[[1]][1]+11,nchar(lineNodesUntilSample)))
    h_1 <- as.integer(substr(h_1,1,gregexpr(' ',h_1)[[1]][1]-1))
  }
  if(gregexpr('HEADWAY=',lineNodesUntilSample)[[1]][1]!=-1){
    h_1 <- gsub(',',' ',substr(lineNodesUntilSample,gregexpr('HEADWAY=',lineNodesUntilSample)[[1]][1]+8,nchar(lineNodesUntilSample)))
    h_1 <- as.integer(substr(h_1,1,gregexpr(' ',h_1)[[1]][1]-1))
  }  
  if(gregexpr('HEADWAY\\[2\\]',lineNodesUntilSample)[[1]][1]!=-1){
    h_2 <- gsub(',',' ',substr(lineNodesUntilSample,gregexpr('HEADWAY\\[2\\]',lineNodesUntilSample)[[1]][1]+11,nchar(lineNodesUntilSample)))
    h_2 <- as.integer(substr(h_2,1,gregexpr(' ',h_2)[[1]][1]-1))
  }
  if(gregexpr('HEADWAY\\[3\\]',lineNodesUntilSample)[[1]][1]!=-1){
    h_3 <- gsub(',',' ',substr(lineNodesUntilSample,gregexpr('HEADWAY\\[3\\]',lineNodesUntilSample)[[1]][1]+11,nchar(lineNodesUntilSample)))
    h_3 <- as.integer(substr(h_3,1,gregexpr(' ',h_3)[[1]][1]-1))
  }
  
  return(c(h_1,h_2,h_3))
  
}

extractNodesVector <- function(lineNodesSample){
  # Return the nodes in a vector format 
  temp1 <- str_split(gsub(' ',',',gsub('  ',' ',gsub('NODES =',' ',gsub('NODES=',' ',gsub('N =',' ',gsub('N=',' ',gsub(',',' ',lineNodesSample))))))),',')
  temp2 <- lapply(temp1,function(x) grep("^[-0123456789]", x))
  nodeVector <- lapply(unlist(temp1)[unlist(temp2)],as.integer)
  return(nodeVector)
}

extractEndOfString <- function(strArg){
  strStartType <- substr(strArg,1,1)
  strArgRest <- substr(strArg,2,nchar(strArg))
  if(strStartType=='"'){
    retval <- substr(strArg,2, regexpr('["]',strArgRest)[1])
  }else if(strStartType=="'"){
    retval <- substr(strArg,2, regexpr("[']",strArgRest)[1])
  }else{
    retval <- substr(strArg,1, regexpr('[ ,]',strArgRest)[1])
  }
  return(retval)
}

readTLFile <- function(TL_fname){
  inpLines <- readLines(TL_fname)  
  
  #Remove Comments
  linesThatAreComments <- unlist(lapply(inpLines,function(x) substr(x,1,1)==';'))
  inpLines <- inpLines[!linesThatAreComments]
  
  lineIdent <- unlist(lapply(inpLines,function(x) (substr(x,1,4)=='LINE')|(substr(x,2,5)=='LINE') ))
  table(lineIdent)
  sttPositions <- (1:length(lineIdent))[lineIdent]
  stpPositions <- sttPositions[2:length(sttPositions)]-1
  stpPositions[length(sttPositions)] <- length(lineIdent)
  
  linesComplete <- lapply(1:length(sttPositions),function(x) concatLines(inpLines,sttPositions[x],stpPositions[x]) )
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('NAME=',x)[1]+5,nchar(x)) )
  #temp2 <- lapply(temp1,function(x) substr(x,1,regexpr('[ ,]',x)[1]) )
  #lineNames <- lapply(temp2,function(x) gsub('[ \"\',]','',x))
  lineNames <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('LONGNAME=',x)[1]+9,nchar(x)) )
  lineLongNames <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('SHORTNAME=',x)[1]+10,nchar(x)) )
  lineShortNames <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('OPERATOR=',x)[1]+9,nchar(x)) )
  lineOPERATOR <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('USERA1=',x)[1]+7,nchar(x)) )
  lineUSERA1 <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  temp1 <- lapply(linesComplete,function(x) substr(x,regexpr('USERA2=',x)[1]+7,nchar(x)) )
  lineUSERA2 <- unlist(lapply(temp1,function(x) extractEndOfString(x) ))
  
  lineNodesUntil <- lapply(linesComplete,function(x) substr(x,1,ifelse(gregexpr('N=',x)[[1]][1]>1,
                                                                       gregexpr('N=',x)[[1]][1],
                                                                       gregexpr('NODES=',x)[[1]][1])-1) )
  lineNodes      <- lapply(linesComplete,function(x) substr(x,ifelse(gregexpr('N=',x)[[1]][1]>1,
                                                                     gregexpr('N=',x)[[1]][1],
                                                                     gregexpr('NODES=',x)[[1]][1]),nchar(x)) )
  
  nodeVector <- lapply(lineNodes,extractNodesVector)
  lineHeadway <- lapply(lineNodesUntil,extractHeadWays)
  
  lineSpeed <- lapply(linesComplete, function(x) ifelse(is.na(str_match(x, "SPEED=(.*?),")[,2]), "", str_match(x, "SPEED=(.*?),")[,2])) #for now, only get the first SPEED
  
  
  lineMode <- lapply(lineNodesUntil,extractKeyword,'MODE')
  
  
  retObject <- lapply(1:length(linesComplete),
                      function(x) 
                        list(lineNames=unlist(lineNames[x]),
                             lineLongNames=unlist(lineLongNames[x]),
                             lineShortNames=unlist(lineShortNames[x]),
                             lineMode=unlist(lineMode[x]),
                             
                             lineOPERATOR=unlist(lineOPERATOR[x]),
                             lineUSERA1=unlist(lineUSERA1[x]),
                             lineUSERA2=unlist(lineUSERA2[x]),
                             
                             lineNumber= x
                        ))
  names(retObject) <- lineNames
  return(retObject)
}

fillna = function(DT,val) {
  DT_ret <- copy(DT)
  for (j in seq_len(ncol(DT_ret)))
    set(DT_ret,which(is.na(DT_ret[[j]])),j,val)
  return(DT_ret)
}



# Part 2 - process the assignment outputs, merge with line file and summarise/output



trn_dr <- paste0(Sys.getenv("MODEL_DIR"),"/trn")
iter <- "/TransitAssignment.iter3/"

lineObj1  <- readTLFile(paste0(trn_dr,iter,"transitAM.lin"))
dd  <-  as.data.frame(matrix(unlist(lineObj1), nrow=length(unlist(lineObj1[1])))) %>% t() %>% data.frame()
names(dd) <- c('linename','longname','shortname','mode','operator','usera1','usera2','slnum')


temp_names <- list.files(paste0(trn_dr,iter),pattern = "^trnlink[a-zA-Z_]{14}.csv$")
temp <- paste0(paste0(trn_dr,iter),temp_names)

read_for <- function(iloop){
  fn_csv_str <- temp[iloop]
  df1 <- fread(fn_csv_str) %>% select(1:9)
  names(df1) <- c('A','B','Time','Mode','Plot','StopA','StopB','Distance','Name')
  df2 <- read.dbf(gsub('csv','dbf',fn_csv_str)) %>% data.table()
  df2 <- df2 %>% select(AB_VOL ,AB_BRDA ,AB_XITA ,AB_BRDB ,AB_XITB ,BA_VOL ,BA_BRDA ,BA_XITA ,BA_BRDB ,BA_XITB)
  df_all <- bind_cols(df1,df2)
  df_all$source <- temp_names[iloop]
  return(df_all)
}

plan(multisession, workers = 15)
system.time(temp2 <- future_lapply(1:length(temp),read_for))
temp3 <- rbindlist(temp2,fill=TRUE)

temp3 <- temp3 %>% mutate(
  period = substr(source,8,9),
  access = substr(source,11,13),
  trmode = substr(source,15,17),
  egress = substr(source,19,21)
)

output_summary <- temp3 %>% group_by(Mode) %>% summarise(numboardings=sum(AB_BRDA,na.rm=T)) %>% filter(Mode>=10) %>% data.table()
print("Summary by mode")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'mode_summary.csv'))


output_summary <- temp3 %>% filter(Mode==120) %>% group_by(A,access) %>% summarise(boardings=sum(AB_BRDA,na.rm=T)) %>% 
  pivot_wider(names_from=access,values_from=boardings) %>% data.table()
print("summary by station for BART")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'BART_station_summary.csv'))

output_summary <- temp3 %>% filter(Mode==133) %>% group_by(A,access) %>% summarise(boardings=sum(AB_BRDA,na.rm=T)) %>% 
  pivot_wider(names_from=access,values_from=boardings)  %>% data.table()
print("summary by station for ACE")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'ACE_station_summary.csv'))

output_summary <- temp3 %>% filter(Mode==130) %>% group_by(A,access) %>% summarise(boardings=sum(AB_BRDA,na.rm=T)) %>% 
  pivot_wider(names_from=access,values_from=boardings)  %>% data.table()
print("summary by station for Caltrain")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'Caltrain_station_summary.csv'))

output_summary <- temp3 %>% filter(Mode==111) %>% group_by(A,access) %>% summarise(boardings=sum(AB_BRDA,na.rm=T)) %>% 
  pivot_wider(names_from=access,values_from=boardings)  %>% data.frame()
print("summary by station for VTA")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'VTA_station_summary.csv'))

final_transit <- temp3 %>% left_join(dd,by=c('Name'='linename'))
final_transit_2 <- final_transit %>% filter(!is.na(mode)) %>% select(-Plot,-BA_VOL,-BA_BRDA,-BA_XITA,-BA_BRDB,-BA_XITB,-usera1,-usera2,-slnum,-source,-mode)


output_summary <- final_transit_2 %>% filter(Mode==30|Mode==84) %>% group_by(Name, longname, shortname) %>%
  summarise(boardings = sum(AB_BRDA,na.rm=T)) %>% data.frame()
print("AC Transit  by route")
output_summary
write_csv(output_summary,paste0(trn_dr,iter,'ACT_route_summary.csv'))

write_csv(final_transit_2,paste0(trn_dr,iter,'trnlink_final.csv'))
