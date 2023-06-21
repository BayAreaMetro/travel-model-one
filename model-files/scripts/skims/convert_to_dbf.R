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
  
  routeLink_csv = read.csv(paste(input_dir, routelink_filename, sep=''))
  
  #linksum_csv = read.csv(paste(input_dir,sub_dir, linksum_filename), sep='//')
  
  write.dbf(routeLink_csv, paste(input_dir, routelink_dbf, sep=''))
  #write.dbf(linksum_csv, paste(input_dir,sub_dir, linksum_dbf), sep='//')
  
  print(paste(routeLink_csv,' File converted to dbf', sep=""))
  #print(paste(linksum_dbf,' File converted to dbf', sep=""))
  
}
