library(shiny)
library(leaflet)
library(ggplot2)

shinyUI(fluidPage(
  titlePanel("Passenger Vehicle Miles Traveled"),
  
  fluidRow(
    column(12,
           leafletMap("map","100%",400,
                      initialTileLayer="//{s}.tiles.mapbox.com/v3/lmz.jni2k354/{z}/{x}/{y}.png",
                      initialTileLayerAttribution = HTML('Maps by <a href="http://www.mapbox.com/">Mapbox</a>'),
                      options=list(center=c(37.796864,-122.266018),
                                   zoom=11)
           ))
  ),
  fluidRow(
    column(12,
           htmlOutput("details")
           )
  ),
  
  fluidRow(
    column(4,
           # tags$areaname(cols=100),
           textInput("areaname", label=h4("Area name"),
                     value="Albany")
    ),
    column(8,
           textInput("tazs", label=h4("TAZs of Interest"),
                     value=""),
           helpText("List comma-separated TAZs. e.g."),
           pre("1034,1035,1036,1037,1038,1039")
    )
  ),
  
  h3(textOutput("text1")),
  h4(textOutput("text2")),
  dataTableOutput("table1"),
  
  tags$head(
    # define right aligned columns
    tags$style(paste(".table .alignRight {text-align:right;}",
                     "input#tazs {display:block; width:95%; }",
                     "pre {display:inline-block; }")),
    # test javascript
    tags$script(type="text/javascript",HTML("console.log('yo');"))
  )
))