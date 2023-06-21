library(foreign)
library(dplyr)

args=commandArgs(trailingOnly=TRUE)
input_dir <- args[1]

time_period_list <- c('AM','PM','MD','EA','EV')


for (tp in time_period_list){
  
  routelink_filename <- paste('trnlink', tp, '_ALLMSA.csv', sep='')
  linksum_filename <- paste('trnlink', tp, '_ALLMSA_linksum.csv', sep='')
  
  routelink_dbf <- paste('trnlink', tp, '_ALLMSA.dbf', sep='')
  linksum_dbf <- paste('trnlink', tp, '_ALLMSA_linksum.dbf', sep='')
  
  if (file.exists(paste(input_dir, routelink_filename, sep=''))){
    
    routeLink_csv = read.csv(paste(input_dir, routelink_filename, sep=''))
    write.dbf(routeLink_csv, paste(input_dir, routelink_dbf, sep=''))
    
  } else {
      print ("MSA File does not exist")
    }
  
  if (file.exists(paste(input_dir, linksum_filename, sep=''))){
    
    linksum_csv = read.csv(paste(input_dir, linksum_filename, sep=''))
    write.dbf(linksum_csv, paste(input_dir, linksum_filename, sep=''))
    
  }else {
    print ("Linksum File does not exist")
  }
  
}
