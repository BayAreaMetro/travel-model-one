library(shiny)

# This is the model run we're starting with
PIVOT_DIR  <- "D:/Projects/2010_05_003"
POPSYN_DIR <- file.path(PIVOT_DIR, "INPUT", "popsyn")
NROWS      <- 5
STATUS     <- ""
ERROR      <- ""
HH_DF      <- ""
PER_DF     <- ""

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

# todo: too slow
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
    con <- textConnection(last_part)
    HH_DF <<- rbind(HH_DF, data.frame(read.csv(con)))
    close(con)
    print(HH_DF)
  }
}

# todo: too slow
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
    con <- textConnection(last_part)
    PER_DF <<- rbind(PER_DF, data.frame(read.csv(con)))
    close(con)
    print(PER_DF)
    print(PER_DF$PERID[10])
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
    "bunnies"
  })
})