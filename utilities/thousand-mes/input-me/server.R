library(shiny)

# This is the model run we're starting with
NROWS      <- 5

household_frame <- ""

# reads the last n lines of the given file and returns them (as a vector of characters)
# faster than other methods!
tailfile <- function(file, n) {
  bufferSize <- 1024L
  size <- file.info(file)$size
  
  if (size < bufferSize) {
    bufferSize <- size
  }
  
  pos <- size - bufferSize
  text <- character()
  k    <- 0L
  
  f    <- file(file, "rb")
  on.exit(close(f))
  
  while(TRUE) {
    seek(f, where=pos)
    chars <- readChar(f, nchars=bufferSize)
    k     <- k + length(gregexpr(pattern="\\r\\n", text=chars)[[1L]])
    text  <- paste0(text, chars)
    
    if (k > n || pos == 0L) {
      break
    }
    
    pos <- max(pos-bufferSize, 0L)
  }
  
  tail(strsplit(text, "\\r\\n")[[1L]], n)
}

# Define server logic required to draw a histogram
shinyServer(function(input, output) {

  print("shinyServer")
  HHFILE     <- ""
  PERFILE    <- ""
  LAST_HHID  <- 0
  LAST_PERID <- 0
  HH_DF      <- ""
  PER_DF     <- ""
  CREATE_ERROR  <- ""
  CREATE_STATUS <- ""

  # read the last lines of the households file so we have the columns correct
  read_households_and_persons <- reactive({
    status     <- ""
    error      <- ""

    popsyn_dir <- file.path(input$pivot_dir, "INPUT", "popsyn")
    # read the head of the household files
    hhfiles <- list.files(popsyn_dir, pattern="hh.*csv", full.names=TRUE)
    if (length(hhfiles) == 0) {
      error      <- paste0(error,"No household files found in ",popsyn_dir,"\n")
    }
    else {
      HHFILE  <<- hhfiles[1]
      if (length(hhfiles) != 1) {
        status <- paste0(status,"Multiple hhfiles found. Using ", HHFILE,"\n")
      } else {
        status <- paste0(status,"Using ", HHFILE,"\n")
      }
      # read the first NROWS rows
      HH_DF <<- data.frame(read.table(HHFILE, header=TRUE, sep=",", nrows=NROWS))
      # read the last NROWS rows and prepend the column names header
      last_part <- c( paste0(colnames(HH_DF), collapse=","),
                      tailfile(HHFILE, NROWS) )
      # append the last NROWS to HH_DF
      con    <- textConnection(last_part)
      HH_DF <<- rbind(HH_DF, data.frame(read.csv(con)))
      close(con)
      # print(HH_DF)
    }
    
    # read the head of the person file
    perfiles <- list.files(popsyn_dir, pattern="person.*csv", full.names=TRUE)
    if (length(perfiles) == 0) {
      error      <- paste0(error,"No person files found in ",popsyn_dir,"\n")
    }
    else {
      PERFILE  <<- perfiles[1]
      if (length(perfiles) != 1) {
        status <- paste0(status,"Multiple hhfiles found. Using ", PERFILE,"\n")
      } else {
        status <- paste0(status,"Using ", PERFILE,"\n")
      }
      # read the first NROWS rows
      PER_DF <<- data.frame(read.table(PERFILE, header=TRUE, sep=",", nrows=NROWS))
      # read the last NROWS rows and prepend the columns header
      last_part <- c( paste0(colnames(PER_DF), collapse=","),
                      tailfile(PERFILE, NROWS) )
      # append the last NROWS to PER_DF
      con     <- textConnection(last_part)
      PER_DF <<- rbind(PER_DF, data.frame(read.csv(con)))
      close(con)
      # print(PER_DF)
      LAST_HHID   <<- PER_DF$HHID[NROWS*2]
      status       <- paste0(status, "Household ID will be ",LAST_HHID+1,"\n")
      LAST_PERID  <<- PER_DF$PERID[NROWS*2]
      status       <- paste0(status, "Person ID will be ",LAST_PERID+1,"\n")
    }
    
    list(HH_DF, PER_DF, LAST_HHID, LAST_PERID, error, status)
  })
  

  # This will execute when household variables are updated.
  # Returns a list of (name_frame, household_frame, person_frame)
  household_data <- reactive({
    household_frame <- data.frame(HH_DF)
    person_frame    <- data.frame(PER_DF)
    name_frame      <- data.frame(HHID=c(1), PERID=c(1), person_name=c("tbd"), stringsAsFactors=FALSE)
    hh_inc          <- 0
    hhagecat        <- 1
    hworkers        <- 0
    hwork_f         <- 0
    hwork_p         <- 0
    hnwork          <- 0
    hretire         <- 0
    huniv           <- 0
    hpresch         <- 0
    hschpred        <- 0
    hschdriv        <- 0
    hadnwst         <- 0
    hadwpst         <- 0
    hadkids         <- 0
    hhages          <- c(0,0,0,0,0,0,0,0,0,0)
    
    for (person_num in seq(from=1, to=input$persons, by=1)) {
      person_name     <- input[[paste0("name",person_num)]]
      
      # temp vars for readability
      person_age      <- strtoi(input[[paste0("age"   ,person_num)]])
      pagecat         <- 1*((person_age>=5)&(person_age<=11)) +
                         2*((person_age>=12)&(person_age<=15)) + 
                         3*((person_age>=16)&(person_age<=17)) +
                         4*((person_age>=18)&(person_age<=24)) +
                         5*((person_age>=25)&(person_age<=34)) +
                         6*((person_age>=35)&(person_age<=49)) +
                         7*((person_age>=50)&(person_age<=64)) +
                         8*((person_age>=65)&(person_age<=79)) +
                         9*(person_age>=80)
      hhages[pagecat+1] <- hhages[pagecat+1] + 1
      
      person_relate   <- strtoi(input[[paste0("relate",person_num)]])
      if (person_relate == 1) { hhagecat <- 1*(person_age<=64) + 2*(person_age>=65) }
      
      # div by 1.44 to convert to 2000$
      person_earns    <- min(325000,as.integer(input[[paste0("earns" ,person_num)]]/1.44))
      person_poverty  <- min(500,as.integer(100*person_earns/8600))
      hh_inc          <- hh_inc + person_earns
      
      hhinccat1       <- 0
      if      (hh_inc <  20000) { hhinccat1 <- 1 }
      else if (hh_inc <  50000) { hhinccat1 <- 2 }
      else if (hh_inc < 100000) { hhinccat1 <- 3 }
      else                      { hhinccat1 <- 4 }
      
      hhinccat2       <- 0
      if      (hh_inc <  10000) { hhinccat2 <- 1 }
      else if (hh_inc <  20000) { hhinccat2 <- 2 }
      else if (hh_inc <  30000) { hhinccat2 <- 3 }
      else if (hh_inc <  40000) { hhinccat2 <- 4 }
      else if (hh_inc <  50000) { hhinccat2 <- 5 }
      else if (hh_inc <  60000) { hhinccat2 <- 6 }
      else if (hh_inc <  75000) { hhinccat2 <- 7 }
      else if (hh_inc < 100000) { hhinccat2 <- 8 }
      else                      { hhinccat2 <- 9 }
      
      person_esr      <- strtoi(input[[paste0("esr"   ,person_num)]])
      person_workhours<- strtoi(input[[paste0("hours" ,person_num)]])
      person_weeks    <- strtoi(input[[paste0("weeks" ,person_num)]])
      person_employed <- (person_esr==1)|(person_esr==2)|(person_esr==4)|(person_esr==5)
      pemploy         <- 1*(person_employed&(person_workhours>=35)) +
                         2*(person_employed&(person_workhours< 35)) +
                         3*(person_esr>=6)                          +
                         4*((person_esr==0)|(person_esr==3))
      

      if ((person_esr == 1)|(person_esr==3)) {
        hworkers <- hworkers + 1
        if (person_workhours >= 35) { hwork_f <- hwork_f + 1 }
        else                        { hwork_p <- hwork_p + 1 }
      }
      
      person_gender   <- strtoi(input[[paste0("sex"   ,person_num)]])
      person_msp      <- strtoi(input[[paste0("msp"   ,person_num)]])
      
      person_grade    <- strtoi(input[[paste0("grade" ,person_num)]])
      pstudent        <- 1*((person_grade>=1)&(person_grade<=5)) +
                         2*((person_grade>=6)&(person_grade<=7)) +
                         3*( person_grade==0)
      ptype           <- 1*(pemploy==1) +
                         2*(pemploy==2) +
                         4*(person_esr==6) +
                         5*(person_esr==7)
      
      if (pstudent==2)                                     { ptype <- 3 }
      if ((pstudent==1)&(person_age>=15)&(person_age<=18)) { ptype <- 6 }
      if ((pstudent==1)&(person_age<16))                   { ptype <- 7 }
      if ((pstudent==3)&(person_age<6))                    { ptype <- 8 }

      if (pstudent==2)                                     { huniv <- huniv + 1 }
      if ((ptype==4)|(ptype==8))                           { hnwork <- hnwork + 1 }
      if (ptype==5)                                        { hretire <- hretire + 1 }
      if (person_grade==1)                                 { hpresch <- hpresch + 1 }
      if (ptype==7)                                        { hschpred <- hschpred + 1 }
      if (ptype==6)                                        { hschdriv <- hschdriv + 1 }
      if ((pstudent<=2)&(pemploy>2))                       { hadnwst <- hadnwst + 1 }
      if ((pstudent<=2)&(pemploy<=2))                      { hadwpst <- hadwpst + 1 }
      
      padkid          <- 2
      if ((person_relate>=3)&(person_relate<=5)&(person_age>18)) padkid <- 1
      
      if (padkid==1) { hadkids <- hadkids + 1 }
      
      person <- c(
        1,                                    # HID
        person_num,                           # PERID
        person_age,                           # AGE
        person_relate,                        # RELATE, relationship to householder
        person_esr -1*(person_esr==7),        # ESR, employment status
        person_grade,                         # GRADE of students or children under 3
        person_num,                           # PNUM, person number
        0,                                    # PAUG, augmented person flag; 0 = not augmented
        0,                                    # DDP, data-defined flag; 0 = collected
        person_gender,                        # SEX, really gender and binary
        person_weeks,                         # WEEKS worked in 1999
        person_workhours,                     # HOURS worked per week in 1999
        person_msp,                           # MSP, marital status
        person_poverty,                       # POVERTY, poverty status
        person_earns,                         # EARNS, personal income
        pagecat,                              # pagecat, age category
        pemploy,                              # pemploy, employment status
        pstudent,                             # pstudent, student status
        ptype,                                # ptype, person type
        padkid                                # padkid, person is adult kid living at home
      )
      person_frame[person_num,] <- as.integer(person)
      name_frame[person_num,]   <- c(1, person_num, person_name)
    }
    
    # 1 - one-family house detached from any other house; 2 - duplex or apartment; 3 - mobile home, boat, RV, van, etc.
    htypdwel <- 0
    if (input$bldgsz == 2)                    { htypdwel <- 1 }
    if ((input$bldgsz>=3)&(input$bldgsz<=9))  { htypdwel <- 2 }
    if ((input$bldgsz==1)|(input$bldgsz==10)) { htypdwel <- 3 }
    
    # 0 - single family home, 1 other
    if (htypdwel==1) { hmultiunit <- 0 }
    else             { hmultiunit <- 1 }
    
    hownrent <- 2
    if (input$tenure<=2) { hownrent <- 1 }
    
    household <- c(
      1,                                      # HHID
      strtoi(input[["taz"]]),                 # TAZ
      0,                                      # SERIALNO
      0,                                      # PUMA5
      hh_inc,                                 # HHINC, household income
      strtoi(input$persons),                  # PERSONS, number of persons
      strtoi(input$hht),                      # HHT, household/family type
      strtoi(input$unittype),                 # UNITTYPE, housing unit type
      strtoi(input$noc),                      # NOC, number of own children in household
      strtoi(input$bldgsz),                   # BLDGSZ, building size
      strtoi(input$tenure),                   # TENURE, home ownership
      0,                                      # VEHICL, number of vehicles available.  Won't this be modeled?
      hhinccat1,                              # hinccat1, household income categorization number 1
      hhinccat2,                              # hinccat2, household income categorization number 2
      hhagecat,                               # hhagecat, head of household age category
      min(strtoi(input$persons), 4),          # hsizecat, household size category
      1*(strtoi(input$hht) <= 3) + 
        2*(strtoi(input$hht) >= 4),           # hfamily, household family type
      strtoi(input$unittype),                 # hunittype, household unit type
      min(strtoi(input$noc),1),               # hNOCcat, number of children category
      min(hworkers,3),                        # hwrkrcat, number of workers in the household category
      hhages[ 1],                             # h0004, household members age 0 to 4
      hhages[ 2],                             # h0511, household members age 5 to 11
      hhages[ 3],                             # h1215, household members age 12 to 15
      hhages[ 4],                             # h1617, household members age 16 to 17
      hhages[ 5],                             # h1824, household members age 18 to 24
      hhages[ 6],                             # h2534, household members age 25 to 34
      hhages[ 7],                             # h3549, household members age 35 to 49
      hhages[ 8],                             # h5064, household members age 50 to 64
      hhages[ 9],                             # h6579, household members age 65 to 79
      hhages[10],                             # h80up, household members age 80 and older
      hworkers,                               # hworkers, household members who work
      hwork_f,                                # hwork_f, household members who work full-time
      hwork_p,                                # hwork_p, household members who work part-time
      huniv,                                  # huniv, household members who are university students
      hnwork,                                 # hnwork, household members who do not work, do not attend school, and are not retired
      hretire,                                # hretire, household members who are retired	
      hpresch,                                # hpresch, pre-school age children in the household	
      hschpred,                               # hschpred, school age, pre-driving-age children in the household
      hschdriv,                               # hschdriv, school age, driving age children in the household
      htypdwel,                               # htypdwel, type of dwelling (BLDGSZ based)
      hownrent,                               # hownrent, home ownership
      hadnwst,                                # hadnwst, non-working students in the household
      hadwpst,                                # hadwpst, working students in the household
      hadkids,                                # hadkids, adult children living in the household (families with persons age 18 to 24 living in a household with older family members)
      0,                                      # bucketBin, used by the population synthesizer	
      0,                                      # originalPUMA
      hmultiunit                              # hmultiunit, multi-unit housing dummy variable	
    )
    
    household_frame[1,] <- as.integer(household)
    
    # I like to leave these for a while to make sure the table looks similar to the real data
    # delete the extra rows
    if (input$persons < nrow(person_frame))  person_frame <- person_frame[1:input$persons,]
    if (nrow(household_frame) > 1)           household_frame <- household_frame[1:1,]
    
    # print(name_frame)
    # print(household_frame)
    # print(person_frame)
    
    # duplicate names
    name_expanded <- name_frame[rep(row.names(name_frame), input$me_count), 1:ncol(name_frame)]
    name_expanded$PERID      <- (LAST_PERID+1):(LAST_PERID+nrow(name_expanded))
    name_expanded$HHID       <- 1:nrow(name_expanded)
    name_expanded$HHID       <- (name_expanded$HHID+1) %/% input$persons
    name_expanded$HHID       <- name_expanded$HHID + LAST_HHID

    # duplicate household
    household_expanded <- household_frame[rep(row.names(household_frame), input$me_count), 1:ncol(household_frame)]
    household_expanded$HHID  <- (LAST_HHID+1):(LAST_HHID+nrow(household_expanded))

    # duplicate persons
    person_expanded          <- person_frame[rep(row.names(person_frame), input$me_count), 1:ncol(person_frame)]
    person_expanded$PERID    <- (LAST_PERID+1):(LAST_PERID+nrow(person_expanded))
    person_expanded$HHID     <- 1:nrow(person_expanded) -1
    person_expanded$HHID     <- floor(person_expanded$HHID / input$persons)
    person_expanded$HHID     <- person_expanded$HHID + LAST_HHID + 1
    
    # print(name_expanded)
    # print(household_expanded)
    # print(person_expanded)

    list(name_frame,    household_frame,    person_frame,
         name_expanded, household_expanded, person_expanded)
  })
  
  have_required_fields <- reactive({
    missing     <- 0
    missing_msg <- ""
    if (input$taz == "") {
      missing <- missing + 1
      missing_msg <- paste0(missing_msg, "Please enter the Location (TAZ) of the Household\n")
    }
    for (person_num in seq(from=1, to=input$persons, by=1)) {
      person_name     <- input[[paste0("name",person_num)]]
      if (person_name == "") {
        missing <- missing + 1
        missing_msg <- paste0(missing_msg, "Please enter the Person ",person_num," Name\n")
      }
    }
    list(missing, missing_msg)
  })
  
  # returns (error, status)
  preprocess <- reactive({
    # returns (HH_DF, PER_DF, LAST_HHID, LAST_PERID, error, status)
    hh_and_pers <- read_households_and_persons()
    
    # if an error, just return it
    if (nchar(hh_and_pers[[5]])>0) {
      list(hh_and_pers[[5]], hh_and_pers[[6]])
    } 
    # if we haven't said go yet, don't go
    else if (input$go_button == 0) {
      list(hh_and_pers[[5]], hh_and_pers[[6]])
    }
    # if we have, check required fields
    else if (input$go_button > 0) {
      missing <- have_required_fields()
      list(missing[[2]], hh_and_pers[[6]])
    }
  })

  output$error  <- renderText({
    error_status <- preprocess()
    paste0(error_status[[1]], CREATE_ERROR)
  })


  output$status <- renderText({
    error_status <- preprocess()
    paste0(error_status[[2]], CREATE_STATUS)
  })
  
  output$model_dir <- renderUI({
    # only guess it if it hasn't been set
    textInput("model_dir",label="Model Directory",
              value=paste0(input$pivot_dir,"_",input$me_count,input$name1,"s"))
  })
  
  observeEvent(input$go_button, {
    CREATE_ERROR  <<- ""
    CREATE_STATUS <<- ""
    error_status <- preprocess()
    if (nchar(error_status[[1]])==0) {
      print("Creating model files!")
      if (dir.exists(input$model_dir)) {
        CREATE_ERROR <<- paste0("Directory [",input$model_dir,"] already exists")
      } else {
        # create the directory
        dir.create(input$model_dir, mode = "0777")
        status         <- paste0("Created ",input$model_dir)
        CREATE_STATUS <<- paste0("\n\n",status,"\n")
        print(status)

                # copy the input
        pivot_input = file.path(input$pivot_dir, "INPUT")
        model_input = file.path(input$model_dir, "INPUT")
        file.copy(from=pivot_input, to=input$model_dir, recursive=TRUE, copy.mode=TRUE, copy.date=TRUE)
        status         <- paste0("Copied ",pivot_input," to ",model_input)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)
        
        # write the name table
        hhdata <- household_data()
        name_file <- file.path(input$model_dir,"INPUT","popsyn","names.csv")
        write.table(hhdata[[4]], file=name_file, quote=FALSE, sep=",", row.names=FALSE)
        status         <- paste0("Created ",name_file)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)
        
        # write the household table (append)
        hh_file <- file.path(input$model_dir,"INPUT","popsyn",basename(HHFILE))
        write.table(hhdata[[5]], file=hh_file, append=TRUE,quote=FALSE, sep=",", row.names=FALSE, col.names=FALSE)
        status         <- paste0("Appended hh to ",hh_file)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)

        # write the person table (append)
        per_file <- file.path(input$model_dir,"INPUT","popsyn",basename(PERFILE))
        write.table(hhdata[[6]], file=per_file, append=TRUE,quote=FALSE, sep=",", row.names=FALSE, col.names=FALSE)
        status         <- paste0("Appended persons to ",per_file)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)

        # copy CTRAMP
        pivot_input = file.path(input$pivot_dir, "CTRAMP")
        model_input = file.path(input$model_dir, "CTRAMP")
        file.copy(from=pivot_input, to=input$model_dir, recursive=TRUE, copy.mode=TRUE, copy.date=TRUE)
        status         <- paste0("Copied ",pivot_input," to ",model_input)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)

        # copy runmodel
        pivot_input = file.path(input$pivot_dir, "RunModel.bat")
        model_input = file.path(input$model_dir, "RunModel.bat")
        file.copy(from=pivot_input, to=input$model_dir, copy.mode=TRUE, copy.date=TRUE)
        status         <- paste0("Copied ",pivot_input," to ",model_input)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)
        
        # copy runCoreSummaries
        pivot_input = file.path(input$pivot_dir, "RunCoreSummaries.bat")
        model_input = file.path(input$model_dir, "RunCoreSummaries.bat")
        file.copy(from=pivot_input, to=input$model_dir, copy.mode=TRUE, copy.date=TRUE)
        status         <- paste0("Copied ",pivot_input," to ",model_input)
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)
        
        status         <- "Model is ready to run"
        CREATE_STATUS <<- paste0(CREATE_STATUS,status,"\n")
        print(status)
      }
    }
  })
  
  output$name_table <- renderTable({
    hhdata <- household_data()
    hhdata[[1]]
  })
  
  output$household_table <- renderTable({
    hhdata <- household_data()
    hhdata[[2]]
  })
  
  output$person_table <- renderTable({
    hhdata <- household_data()
    hhdata[[3]]
  })
  
  output$householdOutput <- renderText({
    "what's up"
  })
  
  outputOptions(output, "error", suspendWhenHidden=FALSE)
  outputOptions(output, "status", suspendWhenHidden=FALSE)
})