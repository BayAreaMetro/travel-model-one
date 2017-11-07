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
      
      person_relate   <- strtoi(input[[paste0("relate",person_num)]])
      
      # div by 1.44 to convert to 2000$
      person_earns    <- min(325000,as.integer(input[[paste0("earns" ,person_num)]]/1.44))
      person_poverty  <- min(500,as.integer(100*person_earns/8600))

      person_esr      <- strtoi(input[[paste0("esr"   ,person_num)]])
      person_workhours<- strtoi(input[[paste0("hours" ,person_num)]])
      person_weeks    <- strtoi(input[[paste0("weeks" ,person_num)]])
      person_employed <- (person_esr==1)|(person_esr==2)|(person_esr==4)|(person_esr==5)
      pemploy         <- 1*(person_employed&(person_workhours>=35)) +
                         2*(person_employed&(person_workhours< 35)) +
                         3*(person_esr>=6)                          +
                         4*((person_esr==0)|(person_esr==3))
      
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
      
      padkid          <- 2
      if ((person_relate>=3)&(person_relate<=5)&(person_age>18)) padkid <- 1
      
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
      person_frame[person_num,] <- person
      name_frame[person_num,]   <- c(LAST_HHID+1, LAST_PERID+person_num, person_name)
    }
    
    household <- c(
      LAST_HHID+1,  # HHID
      strtoi(input[["taz"]]),    # TAZ
      0, # SERIALNO
      0, # PUMA5
      0, # HHINC
      0, # PERSONS
      0, # HHT
      0, # UNITTYPE
      0, # NOC
      0, # BLDGSZ
      0, # TENURE
      0, # VEHICL
      0, # hinccat1
      0, # hinccat2
      0, # hhagecat
      0, # hsizecat
      0, # hfamily
      0, # hunittype
      0, # hNOCcat
      0, # hwrkrcat
      0, # h0004
      0, # h0511
      0, # h1215
      0, # h1617
      0, # h1824
      0, # h2534
      0, # h3549
      0, # h5064
      0, # h6579
      0, # h80up
      0, # hworkers
      0, # hwork_f
      0, # hwork_p
      0, # huniv
      0, # hnwork
      0, # hretire
      0, # hpresch
      0, # hschpred
      0, # hschdriv
      0, # htypdwel
      0, # hownrent
      0, # hadnwst
      0, # hadwpst
      0, # hadkids
      0, # bucketBin
      0, # originalPUMA
      0  # hmultiunit
    )
    
    household_frame[1,] <- household
    
    # I like to leave these for a while to make sure the table looks similar to the real data
    # delete the extra rows
    if (input$persons < nrow(person_frame))  person_frame <- person_frame[1:input$persons,]

    print(name_frame)
    print(household_frame)
    print(person_frame)
    "done"
  })
  
  print(ERROR)
  print(STATUS)
  output$error  <- renderText({ERROR})
  output$status <- renderText({STATUS})
  
  # Expression that generates a histogram. The expression is
  # wrapped in a call to renderPlot to indicate that:
  #
  #  1) It is "reactive" and therefore should re-execute automatically
  #     when inputs change
  #  2) Its output type is a plot
  
  output$householdOutput <- renderText({
    household_data()
  })
})