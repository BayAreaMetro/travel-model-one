library(shiny)

# This is the model run we're starting with
PIVOT_DIR  <- "D:/Projects/2010_05_003"
POPSYN_DIR <- file.path(PIVOT_DIR, "INPUT", "popsyn")
NROWS      <- 5
STATUS     <- ""
ERROR      <- ""
HH_DF      <- ""
PER_DF     <- ""
LAST_HHID  <- 0
LAST_PERID <- 0
household_frame <= ""

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

# read the last lines of the households file so we have the columns correct
read_households <- function(POPSYN_DIR) {
  # read the head of the household files
  hhfiles <- list.files(POPSYN_DIR, pattern="hh.*csv", full.names=TRUE)
  if (length(hhfiles) == 0) {
    ERROR <<- paste0(ERROR,"No household files found in ",POPSYN_DIR,"\n")
  }
  else {
    hhfile  <- hhfiles[1]
    if (length(hhfiles) != 1) {
      STATUS <<- paste0(STATUS,"Multiple hhfiles found. Using ", hhfile,"\n")
    } else {
      STATUS <<- paste0(STATUS,"Using ", hhfile,"\n")
    }
    # read the first NROWS rows
    HH_DF <<- data.frame(read.table(hhfile, header=TRUE, sep=",", nrows=NROWS))
    # read the last NROWS rows and prepend the column names header
    last_part <- c( paste0(colnames(HH_DF), collapse=","),
                    tailfile(hhfile, NROWS) )
    # append the last NROWS to HH_DF
    con    <- textConnection(last_part)
    HH_DF <<- rbind(HH_DF, data.frame(read.csv(con)))
    close(con)
    print(HH_DF)
  }
}

# read the last few lines of the persons file so we have the columns correct
read_persons <- function(POPSYN_DIR) {
  # read the head of the person file
  perfiles <- list.files(POPSYN_DIR, pattern="person.*csv", full.names=TRUE)
  if (length(perfiles) == 0) {
    ERROR <<- paste0(ERROR,"No person files found in ",POPSYN_DIR,"\n")
  }
  else {
    perfile  <- perfiles[1]
    if (length(perfiles) != 1) {
      STATUS <<- paste0(STATUS,"Multiple hhfiles found. Using ", perfile,"\n")
    } else {
      STATUS <<- paste0(STATUS,"Using ", perfile,"\n")
    }
    # read the first NROWS rows
    PER_DF <<- data.frame(read.table(perfile, header=TRUE, sep=",", nrows=NROWS))
    # read the last NROWS rows and prepend the columns header
    last_part <- c( paste0(colnames(PER_DF), collapse=","),
                    tailfile(perfile, NROWS) )
    # append the last NROWS to PER_DF
    con     <- textConnection(last_part)
    PER_DF <<- rbind(PER_DF, data.frame(read.csv(con)))
    close(con)
    print(PER_DF)
    LAST_HHID   <<- PER_DF$HHID[NROWS*2]
    STATUS      <<- paste0(STATUS, "Household ID will be ",LAST_HHID+1,"\n")
    LAST_PERID  <<- PER_DF$PERID[NROWS*2] + 1
    STATUS      <<- paste0(STATUS, "Person ID will be ",LAST_PERID+1,"\n")
  }
}

# Define server logic required to draw a histogram
shinyServer(function(input, output) {

  print("shinyServer")
  STATUS <<- ""
  read_households(POPSYN_DIR)
  read_persons(POPSYN_DIR)

  # this will execute when household variables are updated
  household_data <- reactive({
    household_frame <- data.frame(HH_DF)
    person_frame    <- data.frame(PER_DF)
    name_frame      <- data.frame(HHID=c(LAST_HHID+1), PERID=c(LAST_PERID+1), person_name=c("tbd"), stringsAsFactors=FALSE)
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
        LAST_HHID+1,                          # HID
        LAST_PERID+person_num,                # PERID
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
      name_frame[person_num,]   <- c(LAST_HHID+1, LAST_PERID+person_num, person_name)
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
      LAST_HHID+1,                            # HHID
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
    
    list(name_frame, household_frame, person_frame, "hi")
  })
  
  create_model_files <- reactive({
    validate(
      need(input$taz != "", "Please enter a TAZ")
    )
    print(input$createModelFiles)
    "bunnies"
  })
  print(ERROR)
  print(STATUS)
  output$error  <- renderText({ERROR})
  
  output$log <- renderText({
    STATUS
  })
  
  output$status <- renderText({
    hhdata <- household_data()
    bunnies <- create_model_files()
    bunnies
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
})