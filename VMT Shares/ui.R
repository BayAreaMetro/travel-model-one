library(shiny)
library(ggplot2)

#dataset <- diamonds

shinyUI(fluidPage(
  titlePanel("Passenger Vehicle Miles Traveled"),
  
  fluidRow(
    column(4,
           # tags$areaname(cols=100),
           textInput("areaname", label=h4("Area name"),
                     value="Albany")
    ),
    column(8,
           textInput("tazs", label=h4("TAZs of Interest"),
                     value="1034,1035,1036,1037,1038,1039"),
           helpText("List comma-separated TAZs. e.g. '1034,1035,1036,1037,1038,1039'")
    )
  ),
  
  h3(textOutput("text1")),
  h4(textOutput("text2")),
  tableOutput("table1")

))