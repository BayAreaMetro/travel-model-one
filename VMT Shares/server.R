library(shiny)
library(dplyr)
library(reshape2)
library(ggplot2)

MAX_TAZ <- 1454

load("C:/Users/lzorn/Documents/2010_03_YYY/core_summaries/AutoTripsVMT_personsHomeWork.rdata")
persons_hwlocs <- model_summary
remove(model_summary)
print(head(persons_hwlocs))

load("C:/Users/lzorn/Documents/2010_03_YYY/core_summaries/AutoTripsVMT_perOrigDestHomeWork.rdata")
vmt_hwlocs <- model_summary
remove(model_summary)
print(head(vmt_hwlocs))

shinyServer(function(input, output) {

  output$text1 <- renderText({
    paste("Vehicle Miles Traveled for ",input$areaname)
  })
  
  output$text2 <- renderText({
    "(Simulation Year 2010; Simulation ID: 2010_03_YYY)"
  })
  
  output$table1 <- renderDataTable({
    # Create taz_frame: data frame containing the TAZs in the input
    taz_str_list <- do.call("rbind", strsplit(input$tazs,","))
    taz_frame    <- data.frame(apply(taz_str_list, 2, as.numeric))
    names(taz_frame) <- c("taz")
    
    # Create taz_mapping: data frame mapping all TAZs to 1 iff the TAZ
    # in the input list
    taz_mapping  <- data.frame(matrix(0,nrow=MAX_TAZ,ncol=2))
    names(taz_mapping) <- c("taz","in_area")
    taz_mapping$taz    <- 1:MAX_TAZ
    taz_mapping$in_area[taz_frame$taz] <- 1
    
    # Left join to add live_in_area and work_in_area
    persons_hwlocs <- left_join(persons_hwlocs,
                                mutate(taz_mapping, live_in_area=in_area) %.% 
                                  select(taz,live_in_area))
    persons_hwlocs <- left_join(persons_hwlocs,
                                mutate(taz_mapping, WorkLocation=taz, work_in_area=in_area) %.% 
                                  select(WorkLocation,work_in_area))
    persons_hwlocs$work_in_area[persons_hwlocs$WorkLocation==0] <- -1
  
    persons_summary <- summarise(group_by(select(persons_hwlocs,
                                                 live_in_area,work_in_area,freq), 
                                          live_in_area,work_in_area), persons=sum(freq))    
    # share
    persons_summary$share <- prop.table(persons_summary$persons)*100

    
    # Left join to add live_in_area and work_in_area
    vmt_hwlocs <- left_join(vmt_hwlocs,
                            mutate(taz_mapping, live_in_area=in_area) %.% 
                              select(taz,live_in_area))
    vmt_hwlocs <- left_join(vmt_hwlocs,
                            mutate(taz_mapping, WorkLocation=taz, work_in_area=in_area) %.% 
                              select(WorkLocation,work_in_area))
    vmt_hwlocs$work_in_area[vmt_hwlocs$WorkLocation==0] <- -1
    # Left join to origin_in_area and dest_in_area
    vmt_hwlocs <- left_join(vmt_hwlocs,
                            mutate(taz_mapping, orig_taz=taz, orig_in_area=in_area) %.%
                              select(orig_taz,orig_in_area))
    vmt_hwlocs <- left_join(vmt_hwlocs,
                            mutate(taz_mapping, dest_taz=taz, dest_in_area=in_area) %.%
                              select(dest_taz,dest_in_area))
    vmt_hwlocs <- mutate(vmt_hwlocs, vmt_category=orig_in_area+dest_in_area)
    
    # Summarize to live_in_area, work_in_area, vmt_category
    vmt_summary <- summarise(group_by(select(vmt_hwlocs,
                                             live_in_area,work_in_area,vmt_category,vmt), 
                                             live_in_area,work_in_area,vmt_category),
                             vmt=sum(vmt))
    # Melt/dcast the vmt across vmt_categories
    vmt_summary <- dcast(melt(vmt_summary,id.vars=c("live_in_area","work_in_area","vmt_category")), 
                         live_in_area+work_in_area ~ vmt_category, value.var="value")
    vmt_summary <- vmt_summary[c("live_in_area","work_in_area",2,1,0)]
    names(vmt_summary)[names(vmt_summary)==0] <- "Entirely Outside"
    names(vmt_summary)[names(vmt_summary)==1] <- "Partially In"
    names(vmt_summary)[names(vmt_summary)==2] <- "Entirely Within"
    
    vmt_summary$Total <- vmt_summary$"Entirely Within" + 
                         vmt_summary$"Partially In" +
                         vmt_summary$"Entirely Outside"
  
    all_summary <- left_join(persons_summary, vmt_summary)
    # reorder
    all_summary <- all_summary[order(-all_summary$live_in_area,-all_summary$work_in_area),]
    all_summary$live_in_area[all_summary$live_in_area==1]  <- "Live in area"
    all_summary$live_in_area[all_summary$live_in_area==0]  <- "Live out of area"
    all_summary$work_in_area[all_summary$work_in_area==1]  <- "Work in area"
    all_summary$work_in_area[all_summary$work_in_area==0]  <- "Work out of area"
    all_summary$work_in_area[all_summary$work_in_area==-1] <- "Non-worker"
    
    all_summary
  }, options = list("paging"=FALSE,      # no paging
                    "searching"=FALSE,   # no search/filter boxes
                    "columnDefs"= list(list("className"="alignRight",
                                            "targets"=list(2,3,4,5,6,7)),
                                       list("type"="num-fmt",
                                            "targets"=list(2,3,4,5,6,7))
                                       # list("render"="function(data,type,full,meta) { console.log('hi'); console.log(data); console.log(type); console.log(full); console.log(meta); return '123';}",
                                       #      "targets"=list(2,3))
                                       )
                    )
  )
  
})